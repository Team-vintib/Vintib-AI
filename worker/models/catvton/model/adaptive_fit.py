"""체형-의류 스펙 차이 → 마스크 조정량 순수 계산.

cv2 등 무거운 의존성이 전혀 없다 — `garment_measurement/cm_converter.py`가 검증한 패턴을
그대로 따른다(순수 계산과 실제 마스크 조작을 분리해서 순수 계산 쪽만 CI에서 바로 테스트).
실제 마스크 배열에 값을 적용하는 쪽(`distanceTransform` 등)은 `cloth_masker.py`에 있다.

설계: `.claude/plans/ai/011-tryon-adaptive-masking.md`

**입력이 없으면(`None`) 결과도 `None`이다.** "측정값 없음"과 "비율 1.0(무변화)"은 다른
상태라서 구분해야 한다 — 호출부가 `None`을 보면 기존 `fit_type` 고정 로직으로 폴백한다.

지금 실제로 짝지을 수 있는 축:
- 길이(상의/원피스/바지): body_height_cm ↔ TOTAL_LENGTH/OUTSEAM_LENGTH. "키 대비 적정 기장"은
  인구통계 데이터 없이는 근사치일 수밖에 없어서 `reference_ratio` 상수(첫 버전 어림값)를
  쓴다 — 알파 테스트 데이터가 쌓이면 보정 대상이다.
- 너비(바지 허리): body_waist_cm ↔ WAIST_WIDTH. 평평하게 편 원단 폭은 몸에 딱 맞았을 때
  둘레의 절반과 같다는 물리적 관계를 쓰므로 인체 비율 가정이 없어 길이 축보다 근거가
  명확하다. 다만 BE `member_body_profile`에 waist 컬럼이 아직 없어(`.claude/requests/be/
  005-tryon-adaptive-fit-data.md`) 실제로는 `body_circumference_cm=None`이 들어와 항상
  스킵된다 — 데이터가 생기면 바로 켜지는 구조로만 미리 준비해둔다.
- 상의/원피스 가슴(bust) 너비 축은 범위 밖이다 — 겨드랑이 랜드마크가 없어 대응하는 의류
  치수 자체가 없다(`AI/app/measurement/schemas.py`의 `MeasurementType` 참고).
"""

from __future__ import annotations


def compute_length_adjustment(
    body_height_cm: float | None,
    garment_length_cm: float | None,
    reference_ratio: float,
) -> float | None:
    """ "이 사람 키 대비 이 옷이 얼마나 길거나 짧은지"를 비율로 반환한다.

    1.0이면 `reference_ratio`대로 정확히 맞는 기장, 1보다 크면 상대적으로 긴 기장,
    작으면 상대적으로 짧은 기장이다. 둘 중 하나라도 없거나 0 이하면 `None`.
    """
    if body_height_cm is None or garment_length_cm is None:
        return None
    if body_height_cm <= 0 or garment_length_cm <= 0:
        return None
    return (garment_length_cm / body_height_cm) / reference_ratio


def compute_width_adjustment(
    body_circumference_cm: float | None,
    garment_flat_width_cm: float | None,
) -> float | None:
    """옷이 몸통 둘레 대비 얼마나 여유(또는 타이트)있게 재단됐는지를 비율로 반환한다.

    평평하게 편 원단 폭(앞판+뒷판 중 한쪽)은 몸에 딱 맞았을 때 둘레의 절반과 같다는 물리적
    관계를 쓴다. 1.0이면 몸에 딱 맞는 폭, 1보다 크면 여유 있음(오버사이즈), 작으면 타이트.
    """
    if body_circumference_cm is None or garment_flat_width_cm is None:
        return None
    if body_circumference_cm <= 0 or garment_flat_width_cm <= 0:
        return None
    return garment_flat_width_cm / (body_circumference_cm / 2.0)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def ratio_to_dilation_px(
    ratio: float | None,
    scale_px: float = 20.0,
    max_px: float = 40.0,
) -> float:
    """폭 비율(1.0 근처가 중립)을 실제 팽창 픽셀 수로 매핑한다.

    `ratio`가 `None`이면(측정값 없음) 0.0 — 마스크를 전혀 안 건드린다. 1.0보다 크면 양수
    (팽창=여유), 작으면 음수(수축=타이트)를 돌려준다. `cloth_masker.py`가 이 값을
    `distanceTransform` 기반 재threshold에 그대로 쓴다(음수는 수축).
    """
    if ratio is None:
        return 0.0
    return _clamp((ratio - 1.0) * scale_px, -max_px, max_px)


def ratio_to_cutoff_ratio(
    ratio: float | None,
    base: float = 0.7,
    scale: float = 0.3,
) -> float:
    """길이 비율(1.0 근처가 중립)을 torso 컷오프 비율로 매핑한다.

    `ratio`가 `None`이면 1.0(컷오프 없음 — 원본 길이 그대로) — 기존 `regular` 동작과 같다.
    `base`는 기존 `adjust_mask_for_fit`의 `cropped` 고정값(0.7)을 그대로 이어받은 중립점이다.
    """
    if ratio is None:
        return 1.0
    return _clamp(base + (ratio - 1.0) * scale, 0.3, 1.0)
