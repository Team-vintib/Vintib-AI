"""product_classifier 카테고리 분류기 mock 백엔드 + 팩토리 검증."""

import pytest
from PIL import Image
from product_classifier.classifier import (
    ClassifierNotReady,
    MockCategoryClassifier,
    build_classifier,
)


@pytest.fixture
def image() -> Image.Image:
    return Image.new("RGB", (10, 10))


def test_build_classifier_defaults_to_mock():
    assert isinstance(build_classifier(), MockCategoryClassifier)


def test_mock_classifier_never_autofills(image):
    # score=0.0이라 항상 action="none" — mock 결과가 실수로 폼을 자동 채우면 안 된다.
    prediction = MockCategoryClassifier().classify(image)
    assert prediction.score == 0.0
    assert prediction.action == "none"


def test_mock_classifier_result_is_serializable(image):
    prediction = MockCategoryClassifier().classify(image)
    payload = prediction.to_dict()
    assert payload["value"] == prediction.subcategory.value
    assert payload["path"]
    assert payload["candidates"]


def test_build_classifier_rejects_unknown_backend():
    with pytest.raises(ClassifierNotReady, match="아직 구현되지 않은"):
        build_classifier("no_such_backend")
