"""V2a — 카테고리(소분류 30-way) zero-shot 분류 백엔드 + 1단계/2단계 오케스트레이션.

레지스트리 이름은 CH012 §6 워커 설계(`worker/models/product_info/registry.py`의
`PRODUCT_INFO_BACKENDS`/`ACTIVE_PRODUCT_INFO_BACKEND`, 환경변수 `PRODUCT_INFO_BACKEND`)와
그대로 맞춘다 — 이 스파이크에서 검증한 백엔드를 나중에 프로덕션으로 승격할 때 이름을
다시 맞출 필요가 없게 하기 위해서다.

`CategoryClassifier`는 "이미지 1장 vs 라벨 문구 여러 개"의 코사인 유사도만 계산하는
얇은 인터페이스로 두고, 1단계(30-way 한 번) vs 2단계(대분류 6-way -> 소분류)는 이
인터페이스 위에 오케스트레이션 함수(`classify_one_stage`/`classify_two_stage`)로 얹는다 —
백엔드를 늘려도 오케스트레이션 로직을 중복할 필요가 없다.

**CLIP과 SigLIP의 "공식" zero-shot 스코어링 방식은 다르다**(CLIP은 코사인+softmax, SigLIP은
학습 목적함수 자체가 pairwise sigmoid라 로짓 스케일/바이어스를 쓴 sigmoid가 "공식"에 더
가깝다). 이 스파이크는 둘 다 코사인 유사도 + temperature softmax로 통일해서 비교한다 —
후보 간 상대 순위(top-1/top-3)와 score 분포 모양(V4)을 비교하는 게 목적이라 단순화했다.
SigLIP 성능이 유독 기대에 못 미치면 이 단순화부터 의심할 것.
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from taxonomy import (
    ALL_SUBCATEGORIES,
    MAJOR_CATEGORIES,
    MAJOR_PROMPT_TEMPLATES,
    PROMPT_TEMPLATES,
    SUBCATEGORIES,
)

# --------------------------------------------------------------------------
# 레지스트리 — model_selection/model_registry.py 관례. 키 하나만 바꾸면 스왑된다.
# --------------------------------------------------------------------------
CATEGORY_MODELS: dict[str, str] = {
    "clip_vit_b32": "openai/clip-vit-base-patch32",
    "clip_vit_l14": "openai/clip-vit-large-patch14",
    "siglip_so400m": "google/siglip-so400m-patch14-384",
    # V1에서 "+ ONNX 변환본" 후보 대표로 하나만 변환해 비교한다(세 후보 전부 변환은 이
    # 스파이크 범위를 넘어선다) — CPU 지연이 가장 급한 건 어차피 큰 모델이 아니라 상시
    # 후보인 ViT-B/32라서 이걸 골랐다.
    "clip_vit_b32_onnx": "openai/clip-vit-base-patch32",
}
ACTIVE_CATEGORY_BACKEND = os.environ.get("PRODUCT_INFO_BACKEND", "mock")


@dataclass
class Candidate:
    code: str
    score: float


@dataclass
class ClassificationResult:
    predicted: str
    score: float
    candidates: list[Candidate]  # score 내림차순, top-k
    backend: str = ""


class CategoryClassifier(ABC):
    """교체 경계. 이미지 1장과 라벨 문구 리스트를 받아 라벨별 유사도 점수를 반환한다.

    카테고리 코드 자체를 몰라도 된다 — 호출부(`classify_one_stage`/`classify_two_stage`)가
    "어떤 라벨 집합을 물어볼지"를 결정하고, 이 인터페이스는 순수하게 이미지-텍스트 유사도만
    계산한다. 그래서 대분류 6-way든 소분류 30-way든 같은 메서드로 처리된다.
    """

    name: str

    @abstractmethod
    def score_labels(self, image_path: Path, label_texts: list[str]) -> list[float]:
        """`label_texts`와 같은 길이의 점수 리스트. 값의 스케일은 백엔드마다 다를 수 있다
        (mock은 0~1 임의값, 실백엔드는 temperature-softmax 확률) — evaluate.py는 반드시
        백엔드별로 분포를 따로 본다(V4가 "분포가 실제로 분리되는가"를 확인하는 이유)."""
        ...


# --------------------------------------------------------------------------
# mock — torch 없이도 전 경로가 끝까지 돌게 하는 기본 백엔드. 파일명+라벨 해시로
# 결정적인 점수를 만든다(진짜 유사도는 아니지만 재현 가능하고 top-1이 매번 바뀌지 않는다).
# --------------------------------------------------------------------------
class MockCategoryClassifier(CategoryClassifier):
    name = "mock"

    def score_labels(self, image_path: Path, label_texts: list[str]) -> list[float]:
        raw = []
        for text in label_texts:
            digest = hashlib.sha256(f"{image_path}::{text}".encode()).hexdigest()
            raw.append(int(digest[:8], 16) / 0xFFFFFFFF)
        total = sum(raw) or 1.0
        return [v / total for v in raw]  # 합이 1이 되게 정규화 — softmax 흉내


# --------------------------------------------------------------------------
# CLIP / SigLIP zero-shot — transformers AutoModel/AutoProcessor로 이미지·텍스트 임베딩을
# 뽑아 코사인 유사도 + temperature softmax로 점수를 만든다.
# --------------------------------------------------------------------------
class EmbeddingZeroShotClassifier(CategoryClassifier):
    """CLIP/SigLIP 공용 구현. `model_id`만 다르면 서브클래스 없이도 재사용 가능하지만,
    레지스트리 키와 1:1로 매핑되는 이름을 노출하려고 얇은 서브클래스로 감싼다.

    **카테고리 전용이 아니다** — `score_labels(image, texts)`는 "이미지 vs 임의의 텍스트
    라벨 목록"의 코사인 유사도만 계산하는 도메인 중립 로직이라, `color.py`의
    `ClipZeroShotColorExtractor`가 색상 라벨 목록을 넘겨 그대로 재사용한다(합성/composition,
    상속 아님 — `ColorExtractor` ABC와 타입이 다르므로)."""

    TEMPERATURE = 100.0  # CLIP의 학습된 logit_scale(~100)과 비슷한 값으로 고정

    def __init__(self, model_id: str):
        self.model_id = model_id
        self._model = None
        self._processor = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoModel, AutoProcessor

        self._processor = AutoProcessor.from_pretrained(self.model_id)
        self._model = AutoModel.from_pretrained(self.model_id)
        self._model.eval()
        self._torch = torch

    def score_labels(self, image_path: Path, label_texts: list[str]) -> list[float]:
        import torch
        from PIL import Image

        self._load()
        with Image.open(image_path) as img:
            image = img.convert("RGB")

        inputs = self._processor(text=label_texts, images=image, return_tensors="pt", padding=True)
        with torch.no_grad():
            out = self._model(**inputs)

        image_embeds = out.image_embeds / out.image_embeds.norm(dim=-1, keepdim=True)
        text_embeds = out.text_embeds / out.text_embeds.norm(dim=-1, keepdim=True)
        sims = (image_embeds @ text_embeds.T).squeeze(0) * self.TEMPERATURE
        probs = torch.softmax(sims, dim=-1)
        return probs.tolist()

    def score_label_groups(
        self, image_path: Path, label_prompt_groups: list[list[str]]
    ) -> list[float]:
        """`score_labels`의 프롬프트 앙상블 버전. 라벨 하나당 문구 변형 여러 개(템플릿 x
        동의어 조합)를 받아, 원조 CLIP zero-shot 레시피(프롬프트별 정규화 임베딩 평균 ->
        재정규화)로 라벨당 대표 임베딩 하나를 만든 뒤 코사인 유사도 + softmax를 낸다.
        단일 문구의 어휘 노이즈를 줄이려는 목적 — `color.py`의 색상 프롬프트 개선안 1·2번."""
        import torch
        from PIL import Image

        self._load()
        with Image.open(image_path) as img:
            image = img.convert("RGB")

        flat_texts = [text for group in label_prompt_groups for text in group]
        inputs = self._processor(text=flat_texts, images=image, return_tensors="pt", padding=True)
        with torch.no_grad():
            out = self._model(**inputs)

        image_embeds = out.image_embeds / out.image_embeds.norm(dim=-1, keepdim=True)
        text_embeds = out.text_embeds / out.text_embeds.norm(dim=-1, keepdim=True)

        group_embeds = []
        offset = 0
        for group in label_prompt_groups:
            n = len(group)
            group_mean = text_embeds[offset : offset + n].mean(dim=0)
            group_embeds.append(group_mean / group_mean.norm())
            offset += n

        label_embeds = torch.stack(group_embeds)
        sims = (image_embeds @ label_embeds.T).squeeze(0) * self.TEMPERATURE
        probs = torch.softmax(sims, dim=-1)
        return probs.tolist()


class ClipCategoryClassifier(EmbeddingZeroShotClassifier):
    name = "clip"

    def __init__(self, model_key: str):
        super().__init__(CATEGORY_MODELS[model_key])
        self.name = model_key


class SiglipCategoryClassifier(EmbeddingZeroShotClassifier):
    name = "siglip_so400m"

    def __init__(self):
        super().__init__(CATEGORY_MODELS["siglip_so400m"])


# --------------------------------------------------------------------------
# ONNX 변환본 — optimum으로 내보낸 CLIP ViT-B/32. 최초 호출 시 로컬에 변환·캐시한다.
# --------------------------------------------------------------------------
class OnnxClipCategoryClassifier(CategoryClassifier):
    name = "clip_vit_b32_onnx"

    _CACHE_DIR = Path(__file__).resolve().parent / ".onnx_cache" / "clip_vit_b32"

    def __init__(self):
        self._session = None
        self._processor = None

    def _load(self):
        if self._session is not None:
            return
        from optimum.onnxruntime import ORTModelForFeatureExtraction  # noqa: F401
        from transformers import AutoProcessor

        # optimum의 CLIP 전용 ORT 래퍼가 image/text 인코더를 하나로 묶어 내보내지 않는
        # 버전 차이가 있어, 여기서는 export 자체를 최초 호출 시점에 지연시키고 실패하면
        # 명확한 메시지로 알린다 — 스파이크 코드라 변환 파이프라인을 완전 자동화하기보다는
        # 사용자가 `optimum-cli export onnx --model openai/clip-vit-base-patch32 <dir>`로
        # 직접 변환해 `_CACHE_DIR`에 두는 경로를 우선한다.
        if not self._CACHE_DIR.exists():
            raise RuntimeError(
                f"ONNX 변환본이 없다: {self._CACHE_DIR}\n"
                "먼저 다음을 실행할 것:\n"
                f"  optimum-cli export onnx --model {CATEGORY_MODELS['clip_vit_b32_onnx']} "
                f"--task zero-shot-image-classification {self._CACHE_DIR}"
            )
        from optimum.onnxruntime import ORTModelForZeroShotImageClassification

        self._processor = AutoProcessor.from_pretrained(self._CACHE_DIR)
        self._model = ORTModelForZeroShotImageClassification.from_pretrained(self._CACHE_DIR)

    def score_labels(self, image_path: Path, label_texts: list[str]) -> list[float]:
        import torch
        from PIL import Image

        self._load()
        with Image.open(image_path) as img:
            image = img.convert("RGB")
        inputs = self._processor(text=label_texts, images=image, return_tensors="pt", padding=True)
        out = self._model(**inputs)
        probs = torch.softmax(torch.as_tensor(out.logits_per_image[0]), dim=-1)
        return probs.tolist()


CATEGORY_BACKENDS: dict[str, "callable[[], CategoryClassifier]"] = {
    "mock": MockCategoryClassifier,
    "clip_vit_b32": lambda: ClipCategoryClassifier("clip_vit_b32"),
    "clip_vit_l14": lambda: ClipCategoryClassifier("clip_vit_l14"),
    "siglip_so400m": SiglipCategoryClassifier,
    "clip_vit_b32_onnx": OnnxClipCategoryClassifier,
}


def get_category_classifier(name: str | None = None) -> CategoryClassifier:
    key = name or ACTIVE_CATEGORY_BACKEND
    try:
        return CATEGORY_BACKENDS[key]()
    except KeyError as exc:
        raise ValueError(
            f"unknown category backend: {key!r} (choices: {list(CATEGORY_BACKENDS)})"
        ) from exc


# --------------------------------------------------------------------------
# 오케스트레이션 — 1단계(30-way 한 번) vs 2단계(대분류 6-way -> 소분류)
# --------------------------------------------------------------------------
def _top_candidates(codes: list[str], scores: list[float], top_k: int = 3) -> list[Candidate]:
    pairs = sorted(zip(codes, scores), key=lambda p: -p[1])
    return [Candidate(code=c, score=float(s)) for c, s in pairs[:top_k]]


def classify_one_stage(
    classifier: CategoryClassifier, image_path: Path, template_key: str, top_k: int = 3
) -> ClassificationResult:
    """소분류 30종을 한 번에 물어본다."""
    template = PROMPT_TEMPLATES[template_key]
    labels = list(ALL_SUBCATEGORIES)
    texts = [template(code) for code in labels]
    scores = classifier.score_labels(image_path, texts)
    candidates = _top_candidates(labels, scores, top_k)
    return ClassificationResult(
        predicted=candidates[0].code,
        score=candidates[0].score,
        candidates=candidates,
        backend=classifier.name,
    )


def classify_major_only(
    classifier: CategoryClassifier, image_path: Path, template_key: str, top_k: int = 3
) -> ClassificationResult:
    """대분류(depth 2) 6종만 물어본다 — `classify_two_stage()`의 1차 질의를 단독으로 떼어
    쓰고 싶을 때(예: 대분류만 필요한 실험) 이 함수를 쓴다. `top_k`는 6종 중에서 뽑으므로
    `classify_one_stage`보다 후보 폭이 좁다."""
    template = MAJOR_PROMPT_TEMPLATES[template_key]
    labels = list(MAJOR_CATEGORIES)
    texts = [template(code) for code in labels]
    scores = classifier.score_labels(image_path, texts)
    candidates = _top_candidates(labels, scores, top_k)
    return ClassificationResult(
        predicted=candidates[0].code,
        score=candidates[0].score,
        candidates=candidates,
        backend=classifier.name,
    )


def classify_two_stage(
    classifier: CategoryClassifier, image_path: Path, template_key: str, top_k: int = 3
) -> ClassificationResult:
    """대분류 6-way를 먼저 묻고, 그 대분류 안의 소분류만 다시 묻는다.

    최종 score는 두 단계 확률의 곱(대분류 확률 x 소분류 확률)이다 — 1단계 결과와 스케일이
    다르므로 evaluate.py의 V4 캘리브레이션은 반드시 (모드, 필드) 조합별로 분포를 따로 본다.
    """
    major_template = MAJOR_PROMPT_TEMPLATES[template_key]
    template = PROMPT_TEMPLATES[template_key]
    major_labels = list(MAJOR_CATEGORIES)
    major_texts = [major_template(m) for m in major_labels]
    major_scores = classifier.score_labels(image_path, major_texts)
    major_idx = max(range(len(major_scores)), key=lambda i: major_scores[i])
    chosen_major = major_labels[major_idx]
    major_score = major_scores[major_idx]

    sub_labels = list(SUBCATEGORIES[chosen_major])
    sub_texts = [template(code) for code in sub_labels]
    sub_scores = classifier.score_labels(image_path, sub_texts)
    candidates = _top_candidates(sub_labels, sub_scores, top_k)
    combined_score = major_score * candidates[0].score

    return ClassificationResult(
        predicted=candidates[0].code,
        score=combined_score,
        candidates=candidates,
        backend=classifier.name,
    )
