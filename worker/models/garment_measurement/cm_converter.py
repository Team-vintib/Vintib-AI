"""랜드마크 픽셀 좌표 → 실측(cm) 환산 — 순수 기하 연산, 무거운 의존성 없음.

`pixel_to_cm_ratio`(기준 물체 검출 단계가 계산)를 랜드마크 간 픽셀 거리에 곱하기만 한다.
의존성이 없어서 mock/실 백엔드 구분 없이 항상 이 실제 구현을 그대로 쓴다 — 다른 단계처럼
`registry`에 스왑 지점을 두지 않는다.

측정 항목과 그 근거 랜드마크 쌍:
- SHOULDER_WIDTH = 거리(SHOULDER_LEFT, SHOULDER_RIGHT)
- SLEEVE_LENGTH  = 거리(SHOULDER, SLEEVE_END) 좌우 평균 — 한쪽만 있으면 그쪽만 쓴다
- TOTAL_LENGTH   = 거리(NECKLINE_CENTER, HEM_CENTER)
- HEM_WIDTH      = 거리(HEM_LEFT, HEM_RIGHT)

가슴단면(pit-to-pit)은 겨드랑이 랜드마크가 아직 `LandmarkType`에 없어서 v1 범위 밖이다.

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from __future__ import annotations

import math

from .contracts import Landmark, LandmarkType, Measurement, MeasurementType

# 좌/우 구분 없이 한 쌍으로 재는 항목.
_PAIRED_MEASUREMENTS: dict[MeasurementType, tuple[LandmarkType, LandmarkType]] = {
    MeasurementType.shoulder_width: (LandmarkType.shoulder_left, LandmarkType.shoulder_right),
    MeasurementType.total_length: (LandmarkType.neckline_center, LandmarkType.hem_center),
    MeasurementType.hem_width: (LandmarkType.hem_left, LandmarkType.hem_right),
}

# 소매길이는 좌/우 각각 잴 수 있어 평균을 낸다 — 둘 다 없으면 측정하지 않는다.
_SLEEVE_SIDES: tuple[tuple[LandmarkType, LandmarkType], ...] = (
    (LandmarkType.shoulder_left, LandmarkType.sleeve_end_left),
    (LandmarkType.shoulder_right, LandmarkType.sleeve_end_right),
)


def _pixel_distance(a: Landmark, b: Landmark) -> float:
    return math.hypot(a.pixel_x - b.pixel_x, a.pixel_y - b.pixel_y)


def convert(landmarks: list[Landmark], pixel_to_cm_ratio: float) -> list[Measurement]:
    """검출된 랜드마크 중 필요한 쌍이 갖춰진 항목만 계산해 돌려준다.

    랜드마크가 일부 빠져 있어도(신뢰도 낮아 걸러졌거나 프레임 밖) 계산 가능한 항목은 계산한다 —
    하나라도 없다고 전체를 실패시키지 않는다.
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

    sleeve_length = _sleeve_length(by_type, pixel_to_cm_ratio)
    if sleeve_length is not None:
        measurements.append(sleeve_length)

    return measurements


def _sleeve_length(
    by_type: dict[LandmarkType, Landmark], pixel_to_cm_ratio: float
) -> Measurement | None:
    values_cm: list[float] = []
    confidences: list[float] = []
    for shoulder_type, sleeve_end_type in _SLEEVE_SIDES:
        if shoulder_type not in by_type or sleeve_end_type not in by_type:
            continue
        a, b = by_type[shoulder_type], by_type[sleeve_end_type]
        values_cm.append(_pixel_distance(a, b) * pixel_to_cm_ratio)
        confidences.append(min(a.confidence, b.confidence))

    if not values_cm:
        return None
    return Measurement(
        type=MeasurementType.sleeve_length,
        value_cm=round(sum(values_cm) / len(values_cm), 1),
        confidence=min(confidences),
    )
