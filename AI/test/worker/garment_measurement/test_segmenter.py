"""`GrabCutGarmentSegmenter`(실제 CV 백엔드) 검증.

`cv2`가 없는 환경(CI)에서는 스킵된다. 합성 이미지(단색 배경 위 대비되는 색의 큰 사각형)로
원단이 "있다"고 판정되는지, 대비가 없는 빈 배경에서는 "없다"고 판정되는지 본다 — 실제 사진
임계치 보정은 이 테스트 밖(실측 데이터 필요).
"""

import tempfile
from pathlib import Path

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from garment_measurement.segmenter import GrabCutGarmentSegmenter  # noqa: E402


def _write_temp_png(frame) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()  # Windows에서는 핸들이 열린 채로 남아 있으면 나중에 못 지운다.
    cv2.imwrite(tmp.name, frame)
    return tmp.name


@pytest.fixture
def garment_like_image_path():
    """단색 배경(회색) 위에 대비되는 색(빨강)의 큰 사각형 — "옷"을 흉내낸다."""
    frame = np.full((600, 800, 3), 200, dtype=np.uint8)  # 밝은 회색 배경
    cv2.rectangle(frame, (150, 100), (650, 500), (40, 40, 220), thickness=-1)  # 빨강 사각형(BGR)
    path = _write_temp_png(frame)
    yield path
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def uniform_image_path():
    """대비가 전혀 없는 단색 이미지 — 원단이 없는 상황을 흉내낸다."""
    frame = np.full((600, 800, 3), 128, dtype=np.uint8)
    path = _write_temp_png(frame)
    yield path
    Path(path).unlink(missing_ok=True)


def test_finds_a_high_contrast_central_region(garment_like_image_path):
    segmenter = GrabCutGarmentSegmenter()
    result = segmenter.segment(garment_like_image_path, product_id=1)

    assert result.found is True


def test_uniform_image_is_not_found(uniform_image_path):
    segmenter = GrabCutGarmentSegmenter()
    result = segmenter.segment(uniform_image_path, product_id=1)

    assert result.found is False
