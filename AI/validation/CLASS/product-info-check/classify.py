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
    # --- 패션 도메인 특화 후보(2026-08-03 추가) ---
    # 위 4종은 전부 범용 체크포인트다. §14 실측에서 대분류 직접 질의가 0.35까지 떨어진 게
    # "CLIP은 의류 사진에서 아우터/상의 같은 도메인 구분을 애초에 못 배웠다"는 가설로
    # 이어져서, 패션 상품 이미지로 파인튜닝된 체크포인트를 같은 정답셋에 돌려본다.
    #
    # fashion_clip: FashionCLIP 2.0. LAION CLIP ViT-B/32 위에 패션 상품 80만 건으로
    #   파인튜닝. 모델 카드 기준 zero-shot 분류 weighted macro F1이 베이스 LAION CLIP보다
    #   FMNIST 0.78->0.83 / KAGL 0.71->0.73 / DEEP 0.58->0.62. 순정 CLIP 아키텍처라
    #   기존 로딩 경로(AutoModel forward -> image_embeds/text_embeds)를 그대로 탄다.
    # marqo_fashion_clip / marqo_fashion_siglip: Marqo가 GCL(카테고리·색상·소재까지 학습
    #   신호로 쓰는 대조학습)로 파인튜닝한 검색용 임베딩 모델. 자사 벤치마크 기준
    #   FashionCLIP 2.0 대비 recall@1 +22% / +57%. **색상을 명시적 학습 신호로 썼다는 게
    #   이 스파이크에 특히 맞는다** — 카테고리뿐 아니라 §17에서 막혀 있는 색상 쪽에도
    #   후보로 넣는 이유다(color.py의 COLOR_BACKENDS 참고).
    # zooclaw_fashion_siglip2: SigLIP2-base-patch16-384 기반 최신(2026-06) 후보. 검색
    #   목적으로 증류 파인튜닝됐고 zero-shot 분류는 부차 용도라 기대치는 낮게 잡는다 —
    #   "더 최신/더 큰 게 실제로 더 나은가"를 확인하는 대조군.
    "fashion_clip": "patrickjohncyh/fashion-clip",
    "marqo_fashion_clip": "Marqo/marqo-fashionCLIP",
    "marqo_fashion_siglip": "Marqo/marqo-fashionSigLIP",
    "zooclaw_fashion_siglip2": "srpone/zooclaw-fashionsiglip2",
}

# 모델별 로딩/스코어링 옵션. **여기 없는 키는 기존 동작 그대로다**(기본값이 기존 3종의
# 경로와 동일) — 새 후보를 추가하면서 이미 실측이 끝난 백엔드의 숫자가 바뀌면 비교가
# 무의미해지므로, 차이가 나는 모델만 여기에 명시한다.
#
# - `trust_remote_code`: Marqo 두 모델은 open_clip 래퍼를 원격 코드로 싣는다(별도로
#   `pip install open_clip_torch` 필요).
# - `feature_api`: forward가 image_embeds/text_embeds를 안 주고
#   `get_image_features()`/`get_text_features()`로만 노출하는 모델(Marqo 래퍼).
# - `text_padding`: SigLIP 계열 토크나이저는 고정 길이(max_length) 패딩이 학습 조건이다.
#   기존 `siglip_so400m`은 `padding=True`로 이미 실측이 끝나 그대로 두지만(§V2a),
#   새 SigLIP 후보는 처음부터 모델 카드대로 맞춘다.
CATEGORY_MODEL_LOAD_OPTIONS: dict[str, dict] = {
    "marqo_fashion_clip": {
        "trust_remote_code": True,
        "feature_api": True,
        "text_padding": "max_length",
    },
    "marqo_fashion_siglip": {
        "trust_remote_code": True,
        "feature_api": True,
        "text_padding": "max_length",
    },
    "zooclaw_fashion_siglip2": {"text_padding": "max_length"},
}

# 패션 특화 후보만 모아둔 목록 — 노트북이 "범용 baseline vs 패션 특화" 스윕을 돌 때 쓴다.
FASHION_CATEGORY_BACKENDS: tuple[str, ...] = (
    "fashion_clip",
    "marqo_fashion_clip",
    "marqo_fashion_siglip",
    "zooclaw_fashion_siglip2",
)

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

    def __init__(
        self,
        model_id: str,
        trust_remote_code: bool = False,
        feature_api: bool = False,
        text_padding: bool | str = True,
    ):
        """옵션 3개의 기본값은 기존(openai CLIP / google SigLIP) 경로와 동일하다 —
        의미는 `CATEGORY_MODEL_LOAD_OPTIONS` 주석 참고. 직접 넘기기보다
        `make_embedding_classifier(model_key)`로 레지스트리에서 받아 쓰는 걸 권장한다."""
        self.model_id = model_id
        self._trust_remote_code = trust_remote_code
        self._feature_api = feature_api
        self._text_padding = text_padding
        self._model = None
        self._processor = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoModel, AutoProcessor

        self._processor = AutoProcessor.from_pretrained(
            self.model_id, trust_remote_code=self._trust_remote_code
        )
        self._model = AutoModel.from_pretrained(
            self.model_id, trust_remote_code=self._trust_remote_code
        )
        self._model.eval()
        self._torch = torch

    def _embed(self, image_path: Path, texts: list[str]):
        """이미지 1장 + 텍스트 N개를 L2 정규화된 임베딩 쌍으로 인코딩한다.

        `feature_api=True`면 forward 대신 `get_image_features()`/`get_text_features()`를
        쓴다 — Marqo의 open_clip 래퍼는 `__call__` 결과에 image_embeds/text_embeds를
        노출하지 않는다. 정규화는 여기서 직접 한다(래퍼의 `normalize=True` 인자에
        의존하지 않는다 — 순정 HF 모델에는 그 인자가 없어서 경로가 갈린다)."""
        import torch
        from PIL import Image

        self._load()
        with Image.open(image_path) as img:
            image = img.convert("RGB")

        inputs = self._processor(
            text=texts, images=image, return_tensors="pt", padding=self._text_padding
        )
        with torch.no_grad():
            if self._feature_api:
                image_embeds = self._model.get_image_features(inputs["pixel_values"])
                text_embeds = self._model.get_text_features(inputs["input_ids"])
            else:
                out = self._model(**inputs)
                image_embeds, text_embeds = out.image_embeds, out.text_embeds

        image_embeds = image_embeds / image_embeds.norm(dim=-1, keepdim=True)
        text_embeds = text_embeds / text_embeds.norm(dim=-1, keepdim=True)
        return image_embeds, text_embeds

    def score_labels(self, image_path: Path, label_texts: list[str]) -> list[float]:
        import torch

        image_embeds, text_embeds = self._embed(image_path, label_texts)
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

        flat_texts = [text for group in label_prompt_groups for text in group]
        image_embeds, text_embeds = self._embed(image_path, flat_texts)

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


def make_embedding_classifier(model_key: str) -> EmbeddingZeroShotClassifier:
    """레지스트리 키 하나로 체크포인트 + 로딩 옵션을 함께 조립한다.

    `color.py`도 같은 함수를 쓴다 — 옵션(`trust_remote_code`/`feature_api`/`text_padding`)이
    두 곳에 따로 적히면 카테고리에선 되고 색상에선 안 뜨는 식으로 어긋난다."""
    classifier = EmbeddingZeroShotClassifier(
        CATEGORY_MODELS[model_key], **CATEGORY_MODEL_LOAD_OPTIONS.get(model_key, {})
    )
    classifier.name = model_key
    return classifier


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
    "clip_vit_b32": lambda: make_embedding_classifier("clip_vit_b32"),
    "clip_vit_l14": lambda: make_embedding_classifier("clip_vit_l14"),
    "siglip_so400m": lambda: make_embedding_classifier("siglip_so400m"),
    "clip_vit_b32_onnx": OnnxClipCategoryClassifier,
    # 패션 도메인 특화 후보 — CATEGORY_MODELS 주석 참고.
    **{key: (lambda k=key: make_embedding_classifier(k)) for key in FASHION_CATEGORY_BACKENDS},
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
