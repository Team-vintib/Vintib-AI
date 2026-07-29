"""`worker/models/garment_measurement/cm_converter.py` 순수 기하 로직 검증.

무거운 의존성이 전혀 없어서(`contracts`만 씀) mock/실 백엔드 구분 없이 항상 실제 구현을 그대로
테스트한다 — `pytest.importorskip`이 필요 없다.
"""

from garment_measurement.cm_converter import convert
from garment_measurement.contracts import Landmark, LandmarkType, MeasurementType


def _landmark(landmark_type: LandmarkType, x: float, y: float, confidence: float = 0.9) -> Landmark:
    return Landmark(type=landmark_type, pixel_x=x, pixel_y=y, confidence=confidence)


def test_shoulder_width_is_the_pixel_distance_times_ratio():
    landmarks = [
        _landmark(LandmarkType.shoulder_left, 0.0, 0.0),
        _landmark(LandmarkType.shoulder_right, 300.0, 0.0),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    shoulder = next(m for m in measurements if m.type is MeasurementType.shoulder_width)
    assert shoulder.value_cm == 30.0


def test_missing_landmark_pair_is_skipped_not_errored():
    """랜드마크 일부가 빠져도(프레임 밖·신뢰도 낮음) 나머지는 계산해야 한다."""
    landmarks = [_landmark(LandmarkType.shoulder_left, 0.0, 0.0)]  # 오른쪽 어깨 없음

    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    assert all(m.type is not MeasurementType.shoulder_width for m in measurements)


def test_empty_landmarks_produce_no_measurements():
    assert convert([], pixel_to_cm_ratio=0.1) == []


def test_measurement_confidence_is_the_minimum_of_its_landmark_pair():
    landmarks = [
        _landmark(LandmarkType.hem_left, 0.0, 0.0, confidence=0.95),
        _landmark(LandmarkType.hem_right, 100.0, 0.0, confidence=0.62),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    hem_width = next(m for m in measurements if m.type is MeasurementType.hem_width)
    assert hem_width.confidence == 0.62


def test_sleeve_length_averages_both_sides_when_both_present():
    landmarks = [
        _landmark(LandmarkType.shoulder_left, 0.0, 0.0),
        _landmark(LandmarkType.sleeve_end_left, 0.0, 200.0),  # 좌: 200px
        _landmark(LandmarkType.shoulder_right, 0.0, 0.0),
        _landmark(LandmarkType.sleeve_end_right, 0.0, 240.0),  # 우: 240px
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    sleeve = next(m for m in measurements if m.type is MeasurementType.sleeve_length)
    assert sleeve.value_cm == 22.0  # (200 + 240) / 2 * 0.1


def test_sleeve_length_uses_one_side_when_only_one_is_available():
    landmarks = [
        _landmark(LandmarkType.shoulder_left, 0.0, 0.0),
        _landmark(LandmarkType.sleeve_end_left, 0.0, 150.0),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    sleeve = next(m for m in measurements if m.type is MeasurementType.sleeve_length)
    assert sleeve.value_cm == 15.0


def test_total_length_uses_neckline_to_hem_center():
    landmarks = [
        _landmark(LandmarkType.neckline_center, 100.0, 50.0),
        _landmark(LandmarkType.hem_center, 100.0, 550.0),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    total = next(m for m in measurements if m.type is MeasurementType.total_length)
    assert total.value_cm == 50.0  # 500px * 0.1
