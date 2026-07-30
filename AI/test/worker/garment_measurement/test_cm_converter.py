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


def test_total_length_uses_shoulder_to_hem_center_not_neckline():
    """총장의 시작점은 목선 중심(NECKLINE_CENTER, 칼라가 파여 있어 옷의 최고점보다 낮다)이
    아니라 어깨 끝점(SHOULDER_LEFT/RIGHT, 실제 최고점)이어야 한다 — 실사진 검증에서 목선
    기준으로 재면 총장이 실제보다 짧게 나오는 걸 확인해 바꿨다."""
    landmarks = [
        _landmark(LandmarkType.neckline_center, 0.0, 80.0),  # 어깨보다 아래(칼라가 파임)
        _landmark(LandmarkType.shoulder_left, 0.0, 0.0),
        _landmark(LandmarkType.shoulder_right, 0.0, 0.0),
        _landmark(LandmarkType.hem_center, 0.0, 550.0),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    total = next(m for m in measurements if m.type is MeasurementType.total_length)
    assert total.value_cm == 55.0  # 550px(어깨~밑단) * 0.1 — 목선 기준(47.0px*0.1=47.0)이 아니다


def test_total_length_averages_both_shoulders_when_heights_differ():
    landmarks = [
        _landmark(LandmarkType.shoulder_left, 0.0, 0.0),
        _landmark(LandmarkType.shoulder_right, 0.0, 40.0),  # 오른쪽 어깨가 더 낮게 검출됨
        _landmark(LandmarkType.hem_center, 0.0, 500.0),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    total = next(m for m in measurements if m.type is MeasurementType.total_length)
    assert total.value_cm == 48.0  # (500 + 460) / 2 * 0.1


def test_total_length_uses_one_shoulder_when_only_one_is_available():
    landmarks = [
        _landmark(LandmarkType.shoulder_left, 0.0, 0.0),
        _landmark(LandmarkType.hem_center, 0.0, 400.0),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    total = next(m for m in measurements if m.type is MeasurementType.total_length)
    assert total.value_cm == 40.0


# --- 바지(TROUSERS) 전용 측정 --------------------------------------------------


def test_waist_width_is_the_pixel_distance_times_ratio():
    landmarks = [
        _landmark(LandmarkType.waist_left, 0.0, 0.0),
        _landmark(LandmarkType.waist_right, 400.0, 0.0),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    waist = next(m for m in measurements if m.type is MeasurementType.waist_width)
    assert waist.value_cm == 40.0


def test_inseam_length_averages_both_legs_from_crotch():
    landmarks = [
        _landmark(LandmarkType.crotch, 100.0, 0.0),
        _landmark(LandmarkType.hem_left_inner, 100.0, 300.0),  # 좌: 300px
        _landmark(LandmarkType.hem_right_inner, 100.0, 340.0),  # 우: 340px
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    inseam = next(m for m in measurements if m.type is MeasurementType.inseam_length)
    assert inseam.value_cm == 32.0  # (300 + 340) / 2 * 0.1


def test_outseam_length_averages_both_legs_from_waist():
    landmarks = [
        _landmark(LandmarkType.waist_left, 0.0, 0.0),
        _landmark(LandmarkType.hem_left_outer, 0.0, 900.0),
        _landmark(LandmarkType.waist_right, 400.0, 0.0),
        _landmark(LandmarkType.hem_right_outer, 400.0, 900.0),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    outseam = next(m for m in measurements if m.type is MeasurementType.outseam_length)
    assert outseam.value_cm == 90.0


def test_leg_opening_width_uses_one_side_when_only_one_is_available():
    landmarks = [
        _landmark(LandmarkType.hem_left_outer, 0.0, 0.0),
        _landmark(LandmarkType.hem_left_inner, 160.0, 0.0),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    opening = next(m for m in measurements if m.type is MeasurementType.leg_opening_width)
    assert opening.value_cm == 16.0


def test_top_and_trouser_landmarks_never_produce_each_others_measurements():
    """상의/바지 랜드마크가 섞여 들어와도, 실제로 있는 것만 계산된다(카테고리 분기가 없어도 됨)."""
    landmarks = [
        _landmark(LandmarkType.shoulder_left, 0.0, 0.0),
        _landmark(LandmarkType.waist_left, 0.0, 0.0),
    ]
    measurements = convert(landmarks, pixel_to_cm_ratio=0.1)

    assert measurements == []
