"""`HRNetLandmarkDetector`(실제 HRNet 백엔드) 검증.

체크포인트(OneDrive 수동 다운로드, 255MB)나 torch 없이도 검증 가능한 부분만 다룬다:
① 체크포인트가 없을 때 깔끔하게 실패하는지(torch import 전에 걸러짐 — 무거운 의존성 없이도
테스트 가능), ② 294개 원시 출력을 카테고리별 `LandmarkType`으로 매핑하는 로직(`registry`의
`DF2_CATEGORY_RANGES`/`DF2_LANDMARK_MAPPING`을 그대로 적용하는 부분)이 맞는지.

실제 모델 추론(`_run_model`)은 `AI/validation/garment-landmark-check/verify_hrnet_landmarks.py`로
이미 실사진 검증했다 — 여기서 다시 안 한다.
"""

import pytest
from garment_measurement import registry
from garment_measurement.contracts import GarmentCategory, LandmarkType
from garment_measurement.landmark_detector import (
    HRNetLandmarkDetector,
    LandmarkDetectorNotReady,
)


def test_missing_checkpoint_fails_before_needing_torch():
    """체크포인트 파일이 없으면 torch를 import하기도 전에 실패한다 — torch 없는 환경에서도
    이 실패 자체는 검증할 수 있어야 한다."""
    detector = HRNetLandmarkDetector(checkpoint_path="/no/such/checkpoint.pth")

    with pytest.raises(LandmarkDetectorNotReady):
        detector.detect("https://example.test/scan.jpg", 1, GarmentCategory.short_sleeve_top)


def test_detect_maps_raw_294_output_to_category_landmarks(monkeypatch, tmp_path):
    """`_run_model`이 돌려주는 294개 (x, y, confidence) 중, 카테고리 구간·매핑에 해당하는
    것만 `LandmarkType`이 붙어 나와야 한다."""
    fake_checkpoint = tmp_path / "fake.pth"
    fake_checkpoint.write_bytes(b"")  # 존재 여부만 확인하므로 내용은 필요 없다

    detector = HRNetLandmarkDetector(checkpoint_path=str(fake_checkpoint))
    detector._ensure_loaded = lambda: None  # torch 로딩 자체를 건너뛴다

    raw = [(0.0, 0.0, 0.0)] * 294
    # short_sleeve_top(오프셋 0)의 4번(neckline_center), 7번(shoulder_left)만 값을 채운다.
    raw[3] = (100.0, 50.0, 0.9)
    raw[6] = (10.0, 60.0, 0.8)
    monkeypatch.setattr(detector, "_run_model", lambda image_url, bbox: raw)

    landmarks = detector.detect(
        "https://example.test/scan.jpg", 1, GarmentCategory.short_sleeve_top
    )

    by_type = {lm.type: lm for lm in landmarks}
    assert by_type[LandmarkType.neckline_center].pixel_x == 100.0
    assert by_type[LandmarkType.neckline_center].pixel_y == 50.0
    assert by_type[LandmarkType.shoulder_left].confidence == 0.8


def test_detect_reads_the_correct_category_offset(monkeypatch, tmp_path):
    """trousers는 오프셋이 0이 아니다(short_sleeve_top 25개 뒤) — 엉뚱한 구간을 읽으면 안 된다."""
    fake_checkpoint = tmp_path / "fake.pth"
    fake_checkpoint.write_bytes(b"")

    detector = HRNetLandmarkDetector(checkpoint_path=str(fake_checkpoint))
    detector._ensure_loaded = lambda: None

    raw = [(0.0, 0.0, 0.0)] * 294
    offset, _ = registry.DF2_CATEGORY_RANGES[GarmentCategory.trousers]
    # trousers 로컬 1번(waist_left)은 전체 인덱스로 offset+0.
    raw[offset] = (55.0, 66.0, 0.7)
    monkeypatch.setattr(detector, "_run_model", lambda image_url, bbox: raw)

    landmarks = detector.detect("https://example.test/scan.jpg", 1, GarmentCategory.trousers)

    by_type = {lm.type: lm for lm in landmarks}
    assert by_type[LandmarkType.waist_left].pixel_x == 55.0
    assert by_type[LandmarkType.waist_left].pixel_y == 66.0
