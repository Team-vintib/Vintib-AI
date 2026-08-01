"""카테고리(소분류 30-way) 분류 — 모델 교체 경계.

`worker/models/quality_vlm/describer.py`의 `DefectDescriber(ABC)` + `build_describer()`
패턴을 그대로 따른다 — 여기가 카테고리 분류 모델 교체의 유일한 지점이다. 결과 데이터 모양은
`contracts.py`(게이트웨이 스키마와 대조되는 계약 사본)에 있다.

**실백엔드는 아직 없다.** `AI/validation/CLASS/product-info-check/`에서 CLIP 파인튜닝
검증이 끝난 뒤 `ClipFinetunedClassifier` 같은 클래스를 추가하고 `registry.py`의
`CATEGORY_BACKENDS`에 등록한다(2026-08-02 판단).

설계: `.claude/plans/ai/CH012-~2.MD`
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from PIL import Image

from . import registry
from .contracts import CategoryCandidate, CategoryPrediction, build_category_prediction
from .taxonomy import ALL_SUBCATEGORIES
from .thresholds import CATEGORY_THRESHOLDS, resolve_action


class ClassifierNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치 등)."""


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


def build_classifier(key: str | None = None) -> CategoryClassifier:
    """레지스트리 키에 맞는 분류기를 만든다. **여기가 유일한 카테고리 모델 스왑 지점이다.**

    워커는 `PRODUCT_CLASSIFIER_CATEGORY_BACKEND` 환경변수로 이 키를 넘긴다.
    """
    resolved = key or registry.ACTIVE_CATEGORY_BACKEND
    if resolved == "mock":
        return MockCategoryClassifier()
    raise ClassifierNotReady(f"아직 구현되지 않은 카테고리 백엔드입니다: {resolved!r}")
