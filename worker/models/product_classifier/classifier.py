"""카테고리(소분류 35-way) 분류 — 모델 교체 경계.

`worker/models/quality_vlm/describer.py`의 `DefectDescriber(ABC)` + `build_describer()`
패턴을 그대로 따른다 — 여기가 카테고리 분류 모델 교체의 유일한 지점이다. 결과 데이터 모양은
`contracts.py`(게이트웨이 스키마와 대조되는 계약 사본)에 있다.

설계: `.claude/plans/ai/CH012-~2.MD`
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from PIL import Image

from . import registry
from .contracts import CategoryCandidate, CategoryPrediction, build_category_prediction
from .taxonomy import ALL_SUBCATEGORIES, Subcategory
from .thresholds import CATEGORY_THRESHOLDS, resolve_action


class ClassifierNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치·체크포인트 없음 등)."""


def _drop_incompatible_keys(checkpoint_state: dict, model: Any) -> dict:
    """`app/pricing/clip_embed.py::_drop_incompatible_keys()`와 동일 로직 — `validation/`을
    프로덕션(`worker/`도 배포 이미지에 안 들어가지만 같은 원칙)에서 import하지 않는 규약이라
    복사한다. 키 존재 + shape 일치만 남긴다 — `strict=False`는 shape 불일치 키까지 봐주지
    않아 RuntimeError가 난다."""
    model_state = model.state_dict()
    return {
        key: value
        for key, value in checkpoint_state.items()
        if key in model_state and model_state[key].shape == value.shape
    }


class CategoryClassifier(ABC):
    """이미지 1장 -> 소분류 예측. **여기가 카테고리 모델 교체 경계다.**"""

    @abstractmethod
    def classify(self, image: Image.Image) -> CategoryPrediction:
        raise NotImplementedError


class MockCategoryClassifier(CategoryClassifier):
    """정적 결과로 채운다(의존성 없음). CI/기본 경로.

    항상 소분류 목록의 첫 항목(JACKET)을 score=0.0으로 반환한다 — 실제 추론이 아니라
    "파이프라인이 끝까지 도는가"만 확인하는 용도다. score=0.0이면
    `thresholds.resolve_action()`이 항상 `"none"`을 반환하므로, mock 결과가 실수로
    자동 채움되는 일은 없다.
    """

    def classify(self, image: Image.Image) -> CategoryPrediction:
        placeholder = ALL_SUBCATEGORIES[0]
        return build_category_prediction(
            subcategory=placeholder,
            score=0.0,
            action=resolve_action(0.0, CATEGORY_THRESHOLDS),
            candidates=[CategoryCandidate(subcategory=placeholder, score=0.0)],
        )


class FineTunedClipCategoryClassifier(CategoryClassifier):
    """파인튜닝된 CLIP backbone + 선형 헤드(체크포인트 기반).

    체크포인트는 `AI/validation/CLASS/product-info-finetune/aihub_finetune_vit.py`가 만든
    형식이다 — `model_id`/`task`/`variant`/`classes`(헤드 출력 인덱스 순서)/
    `backbone_state_dict`/`head_state_dict`를 한 `.pt` 파일에 담는다. `classes` 문자열은
    `taxonomy.py`의 `Subcategory.value`와 1:1이어야 한다(같은 taxonomy로 학습됐다는 전제).

    ⚠️ **`variant`가 "masked"면 학습 데이터가 AI-Hub 정답 polygon으로 배경을 제거한
    크롭이었다는 뜻이다.** 실서비스 사진엔 그런 정답 마스크가 없어 원본을 그대로 넣으면
    입력 분포가 학습 때와 달라질 수 있다 — 로드 시점에 로그로 남겨 무엇을 쓰고 있는지
    드러낸다. `"raw"`면 이 문제가 없다.

    무거운 의존성(torch/transformers)은 지연 import — mock 백엔드 경로는 이 클래스 자체가
    안 만들어지므로 아무 것도 안 당겨온다.
    """

    def __init__(self, checkpoint_path: str) -> None:
        self._checkpoint_path = checkpoint_path
        self._bundle: tuple[Any, Any, Any, list[str]] | None = None

    def _ensure_loaded(self) -> None:
        if self._bundle is not None:
            return
        if not self._checkpoint_path:
            raise ClassifierNotReady(
                "카테고리 체크포인트 경로가 설정되지 않았습니다"
                "(PRODUCT_CLASSIFIER_CATEGORY_CHECKPOINT 환경변수)"
            )
        try:
            import torch
            from transformers import AutoModel, AutoProcessor
        except ImportError as exc:
            raise ClassifierNotReady(
                f"카테고리 백엔드에는 torch/transformers가 필요합니다: {exc}"
            ) from exc

        try:
            checkpoint = torch.load(self._checkpoint_path, map_location="cpu")
        except (FileNotFoundError, OSError) as exc:
            raise ClassifierNotReady(f"카테고리 체크포인트를 열 수 없습니다: {exc}") from exc

        variant = checkpoint.get("variant", "?")
        print(f"[product_classifier] 카테고리 체크포인트 로드 — variant={variant!r}")

        model_id = checkpoint["model_id"]
        model = AutoModel.from_pretrained(model_id)
        model.load_state_dict(
            _drop_incompatible_keys(checkpoint["backbone_state_dict"], model), strict=False
        )
        model.eval()
        processor = AutoProcessor.from_pretrained(model_id, use_fast=True)

        classes: list[str] = checkpoint["classes"]
        head_weight = checkpoint["head_state_dict"]["weight"]
        head = torch.nn.Linear(head_weight.shape[1], head_weight.shape[0])
        head.load_state_dict(checkpoint["head_state_dict"])
        head.eval()

        self._bundle = (model, processor, head, classes)

    def classify(self, image: Image.Image) -> CategoryPrediction:
        import torch

        self._ensure_loaded()
        assert self._bundle is not None
        model, processor, head, classes = self._bundle

        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(pixel_values=inputs["pixel_values"])
            if hasattr(features, "pooler_output"):
                features = features.pooler_output
            probs = torch.softmax(head(features), dim=-1)[0].tolist()

        ranked = sorted(zip(classes, probs), key=lambda pair: -pair[1])
        top_label, top_score = ranked[0]
        candidates = [
            CategoryCandidate(subcategory=Subcategory(label), score=score)
            for label, score in ranked[:3]
        ]
        return build_category_prediction(
            subcategory=Subcategory(top_label),
            score=top_score,
            action=resolve_action(top_score, CATEGORY_THRESHOLDS),
            candidates=candidates,
        )


def build_classifier(key: str | None = None) -> CategoryClassifier:
    """레지스트리 키에 맞는 분류기를 만든다. **여기가 유일한 카테고리 모델 스왑 지점이다.**

    워커는 `PRODUCT_CLASSIFIER_CATEGORY_BACKEND` 환경변수로 이 키를 넘긴다.
    """
    resolved = key or registry.ACTIVE_CATEGORY_BACKEND
    if resolved == "mock":
        return MockCategoryClassifier()
    if resolved == "clip_finetuned":
        return FineTunedClipCategoryClassifier(
            registry.FINE_TUNED_CATEGORY_CONFIG["checkpoint_path"]
        )
    raise ClassifierNotReady(f"아직 구현되지 않은 카테고리 백엔드입니다: {resolved!r}")
