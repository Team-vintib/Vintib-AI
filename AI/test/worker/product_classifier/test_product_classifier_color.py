"""product_classifier 색상 추출기 mock 백엔드 + 팩토리 검증."""

import pytest
from PIL import Image
from product_classifier.color import (
    PALETTE,
    ColorExtractorNotReady,
    MockColorExtractor,
    build_color_extractor,
)


@pytest.fixture
def image() -> Image.Image:
    return Image.new("RGB", (10, 10))


def test_build_color_extractor_defaults_to_mock():
    assert isinstance(build_color_extractor(), MockColorExtractor)


def test_mock_extractor_never_autofills(image):
    prediction = MockColorExtractor().extract(image)
    assert prediction.primary.score == 0.0
    assert prediction.primary.action == "none"
    assert prediction.secondary is None


def test_mock_extractor_primary_code_is_in_palette(image):
    prediction = MockColorExtractor().extract(image)
    assert prediction.primary.code in PALETTE
    assert prediction.primary.hex == PALETTE[prediction.primary.code]


def test_build_color_extractor_rejects_unknown_backend():
    with pytest.raises(ColorExtractorNotReady, match="아직 구현되지 않은"):
        build_color_extractor("no_such_backend")
