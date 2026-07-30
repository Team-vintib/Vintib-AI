"""랜드마크 픽셀 좌표 → 실측(cm) 환산 — 순수 기하 연산, 무거운 의존성 없음.

`pixel_to_cm_ratio`(기준 물체 검출 단계가 계산)를 랜드마크 간 픽셀 거리에 곱하기만 한다.
의존성이 없어서 mock/실 백엔드 구분 없이 항상 이 실제 구현을 그대로 쓴다 — 다른 단계처럼
`registry`에 스왑 지점을 두지 않는다.

측정 항목과 그 근거 랜드마크 쌍 — 카테고리(상의/원피스 vs 바지)에 따라 다른 항목을 쓴다.
어느 카테고리든, 필요한 랜드마크 쌍이 검출 안 됐으면(신뢰도 낮아 걸러졌거나 프레임 밖) 그
항목만 건너뛴다 — 하나라도 없다고 전체를 실패시키지 않는다.

**상의(SHORT_SLEEVE_TOP) / 원피스(LONG_SLEEVE_DRESS) 공통**:
- SHOULDER_WIDTH = 거리(SHOULDER_LEFT, SHOULDER_RIGHT)
- SLEEVE_LENGTH  = 거리(SHOULDER, SLEEVE_END) 좌우 평균
- TOTAL_LENGTH   = 거리(NECKLINE_CENTER, HEM_CENTER)
- HEM_WIDTH      = 거리(HEM_LEFT, HEM_RIGHT)

가슴단면(pit-to-pit)은 겨드랑이 랜드마크가 아직 `LandmarkType`에 없어서 범위 밖이다.

**바지(TROUSERS)**:
- WAIST_WIDTH       = 거리(WAIST_LEFT, WAIST_RIGHT)
- INSEAM_LENGTH     = 거리(CROTCH, HEM_*_INNER) 좌우 평균 — 사타구니~밑단 안쪽
- OUTSEAM_LENGTH    = 거리(WAIST_*, HEM_*_OUTER) 좌우 평균 — 허리~밑단 바깥쪽
- LEG_OPENING_WIDTH = 거리(HEM_*_OUTER, HEM_*_INNER) 좌우 평균 — 바짓단 너비

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from __future__ import annotations

import math

from .contracts import Landmark, LandmarkType, Measurement, MeasurementType

# 좌/우 구분 없이 한 쌍으로 재는 항목(카테고리 무관하게 이 중 landmark가 갖춰진 것만 계산됨).
_PAIRED_MEASUREMENTS: dict[MeasurementType, tuple[LandmarkType, LandmarkType]] = {
    MeasurementType.shoulder_width: (LandmarkType.shoulder_left, LandmarkType.shoulder_right),
    MeasurementType.total_length: (LandmarkType.neckline_center, LandmarkType.hem_center),
    MeasurementType.hem_width: (LandmarkType.hem_left, LandmarkType.hem_right),
    MeasurementType.waist_width: (LandmarkType.waist_left, LandmarkType.waist_right),
}

# 좌/우 각각 잴 수 있어 평균 내는 항목. 한쪽만 검출돼도 그쪽만으로 계산한다.
_AVERAGED_MEASUREMENTS: dict[MeasurementType, tuple[tuple[LandmarkType, LandmarkType], ...]] = {
    MeasurementType.sleeve_length: (
        (LandmarkType.shoulder_left, LandmarkType.sleeve_end_left),
        (LandmarkType.shoulder_right, LandmarkType.sleeve_end_right),
    ),
    MeasurementType.inseam_length: (
        (LandmarkType.crotch, LandmarkType.hem_left_inner),
        (LandmarkType.crotch, LandmarkType.hem_right_inner),
    ),
    MeasurementType.outseam_length: (
        (LandmarkType.waist_left, LandmarkType.hem_left_outer),
        (LandmarkType.waist_right, LandmarkType.hem_right_outer),
    ),
    MeasurementType.leg_opening_width: (
        (LandmarkType.hem_left_outer, LandmarkType.hem_left_inner),
        (LandmarkType.hem_right_outer, LandmarkType.hem_right_inner),
    ),
}


def _pixel_distance(a: Landmark, b: Landmark) -> float:
    return math.hypot(a.pixel_x - b.pixel_x, a.pixel_y - b.pixel_y)


def convert(landmarks: list[Landmark], pixel_to_cm_ratio: float) -> list[Measurement]:
    """검출된 랜드마크 중 필요한 쌍이 갖춰진 항목만 계산해 돌려준다.

    카테고리를 별도로 안 받는 이유: `LandmarkType`이 카테고리마다 겹치지 않게 설계돼 있어서
    (상의/원피스 랜드마크와 바지 랜드마크는 이름 자체가 다르다), landmarks 목록에 실제로 뭐가
    들어있는지만 보면 어느 항목을 계산할 수 있는지 자연히 정해진다 — 카테고리 분기가 필요 없다.
    """
    by_type = {lm.type: lm for lm in landmarks}
    measurements: list[Measurement] = []

    for measurement_type, (type_a, type_b) in _PAIRED_MEASUREMENTS.items():
        if type_a not in by_type or type_b not in by_type:
            continue
        a, b = by_type[type_a], by_type[type_b]
        measurements.append(
            Measurement(
                type=measurement_type,
                value_cm=round(_pixel_distance(a, b) * pixel_to_cm_ratio, 1),
                confidence=min(a.confidence, b.confidence),
            )
        )

    for measurement_type, sides in _AVERAGED_MEASUREMENTS.items():
        averaged = _averaged_measurement(measurement_type, sides, by_type, pixel_to_cm_ratio)
        if averaged is not None:
            measurements.append(averaged)

    return measurements


def _averaged_measurement(
    measurement_type: MeasurementType,
    sides: tuple[tuple[LandmarkType, LandmarkType], ...],
    by_type: dict[LandmarkType, Landmark],
    pixel_to_cm_ratio: float,
) -> Measurement | None:
    values_cm: list[float] = []
    confidences: list[float] = []
    for type_a, type_b in sides:
        if type_a not in by_type or type_b not in by_type:
            continue
        a, b = by_type[type_a], by_type[type_b]
        values_cm.append(_pixel_distance(a, b) * pixel_to_cm_ratio)
        confidences.append(min(a.confidence, b.confidence))

    if not values_cm:
        return None
    return Measurement(
        type=measurement_type,
        value_cm=round(sum(values_cm) / len(values_cm), 1),
        confidence=min(confidences),
    )
