"""`OpenCVContourReferenceDetector`(실제 CV 백엔드) 검증.

`cv2`가 없는 환경(CI — `AI/requirements-dev.txt`엔 opencv가 없다)에서는 스킵된다.
합성 이미지(검은 배경 위 흰 A4 비율 사각형)로 검출 자체가 되는지, 계산된 `pixel_to_cm_ratio`가
실제 규격(210x297mm)과 맞는지 본다 — 실제 사진 임계치 보정은 이 테스트 밖(실측 데이터 필요).
"""

import tempfile
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from garment_measurement import registry  # noqa: E402
from garment_measurement.reference_detector import (  # noqa: E402
    OpenCVContourReferenceDetector,
)


def _a4_test_image(short_px: int = 300, margin_px: int = 100) -> str:
    """검은 배경 위에 A4 비율(1:sqrt(2))의 흰 사각형을 그린 임시 이미지 파일 경로를 돌려준다."""
    long_px = round(short_px * registry.A4_ASPECT_RATIO)
    height = short_px + margin_px * 2
    width = long_px + margin_px * 2

    frame = np.zeros((height, width, 3), dtype=np.uint8)
    top_left = (margin_px, margin_px)
    bottom_right = (margin_px + long_px, margin_px + short_px)
    cv2.rectangle(frame, top_left, bottom_right, (255, 255, 255), thickness=-1)

    # Windows에서는 핸들이 열린 채로 남아 있으면 나중에 못 지운다 — 바로 닫는다.
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    cv2.imwrite(tmp.name, frame)
    return tmp.name


@pytest.fixture
def a4_image_path():
    path = _a4_test_image()
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def blank_image_path():
    path = _a4_test_image()  # 재사용 후 덮어씀 — 사각형 없는 순수 검은 이미지로 교체
    frame = np.zeros((400, 500, 3), dtype=np.uint8)
    cv2.imwrite(path, frame)
    yield path
    Path(path).unlink(missing_ok=True)


def test_detects_a4_shaped_rectangle(a4_image_path):
    detector = OpenCVContourReferenceDetector()
    result = detector.detect(a4_image_path, product_id=1)

    assert result.found is True
    assert result.pixel_to_cm_ratio is not None


def test_pixel_to_cm_ratio_matches_known_short_side():
    """짧은 변을 정확히 300px로 그렸으니, 21.0cm / 300px 근처가 나와야 한다."""
    path = _a4_test_image(short_px=300)
    try:
        detector = OpenCVContourReferenceDetector()
        result = detector.detect(path, product_id=1)

        expected = (registry.A4_WIDTH_MM / 10.0) / 300.0
        assert result.pixel_to_cm_ratio == pytest.approx(expected, rel=0.02)
    finally:
        Path(path).unlink(missing_ok=True)


def test_no_rectangle_means_not_found(blank_image_path):
    detector = OpenCVContourReferenceDetector()
    result = detector.detect(blank_image_path, product_id=1)

    assert result.found is False
    assert result.pixel_to_cm_ratio is None


def test_off_ratio_rectangle_is_rejected():
    """A4 비율(1:1.414)과 크게 다른 정사각형은 기준 물체로 잡히면 안 된다."""
    frame = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.rectangle(frame, (100, 100), (400, 400), (255, 255, 255), thickness=-1)  # 1:1 정사각형

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    cv2.imwrite(tmp.name, frame)
    try:
        detector = OpenCVContourReferenceDetector()
        result = detector.detect(tmp.name, product_id=1)
        assert result.found is False
    finally:
        Path(tmp.name).unlink(missing_ok=True)
