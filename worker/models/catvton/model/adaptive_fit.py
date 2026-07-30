"""체형-의류 스펙 차이 → 마스크 조정량 순수 계산.

cv2 등 무거운 의존성이 전혀 없다 — `garment_measurement/cm_converter.py`가 검증한 패턴을
그대로 따른다(순수 계산과 실제 마스크 조작을 분리해서 순수 계산 쪽만 CI에서 바로 테스트).
실제 마스크 배열에 값을 적용하는 쪽(`distanceTransform` 등)은 `cloth_masker.py`에 있다.

설계: `.claude/plans/ai/011-tryon-adaptive-masking.md`

**입력이 없으면(`None`) 결과도 `None`이다.** "측정값 없음"과 "비율 1.0(무변화)"은 다른
상태라서 구분해야 한다 — 호출부가 `None`을 보면 기존 `fit_type` 고정 로직으로 폴백한다.

**길이(기장) 축은 의도적으로 뺐다.** 처음엔 키 대비 총장 비율로 마스크 하단을 잘라 크롭
길이를 연속적으로 조절하려 했는데, 이 방식은 항상 잘려나간 부분(팔뚝·다리 등)의 맨살을
diffusion이 새로 생성해야 한다 — AI 가드레일상 맨살 생성은 정책적으로 피해야 해서 폐기했다.
실제로 우리가 원했던 건 "옷이 짧아지는 것"이 아니라 "핏(스키니/배기)이 조절되는 것"이라, 옷이
덮는 신체 범위 자체는 그대로 두고 폭만 조절하는 너비 축만 남긴다.

지금 실제로 쓰는 축:
- **너비(바지 허리)**: body_waist_cm ↔ WAIST_WIDTH. 평평하게 편 원단 폭은 몸에 딱 맞았을 때
  둘레의 절반과 같다는 물리적 관계를 쓴다. 다만 BE `member_body_profile`에 waist 컬럼이
  아직 없어(`.claude/requests/be/005-tryon-adaptive-fit-data.md`) 실제로는
  `body_circumference_cm=None`이 들어와 항상 스킵된다 — 데이터가 생기면 바로 켜지는 구조로만
  미리 준비해둔다.
- **상의/원피스는 아직 축이 없다** — 가슴(bust) 너비 축에 대응하는 의류 치수가 없다(겨드랑이
  랜드마크 미지원, `AI/app/measurement/schemas.py`의 `MeasurementType` 참고). 데이터가 없는
  동안은 `fit_type` 고정 로직으로 폴백한다.
"""

from __future__ import annotations


def compute_width_adjustment(
    body_circumference_cm: float | None,
    garment_flat_width_cm: float | None,
) -> float | None:
    """옷이 몸통 둘레 대비 얼마나 여유(또는 타이트)있게 재단됐는지를 비율로 반환한다.

    평평하게 편 원단 폭(앞판+뒷판 중 한쪽)은 몸에 딱 맞았을 때 둘레의 절반과 같다는 물리적
    관계를 쓴다. 1.0이면 몸에 딱 맞는 폭, 1보다 크면 여유 있음(배기), 작으면 타이트(스키니).
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
    (팽창=배기), 작으면 음수(수축=스키니)를 돌려준다. `cloth_masker.py`가 이 값을
    `distanceTransform` 기반 재threshold에 그대로 쓴다(음수는 수축).
    """
    if ratio is None:
        return 0.0
    return _clamp((ratio - 1.0) * scale_px, -max_px, max_px)


def compute_mask_adjustment(
    part: str,
    body_measurements: dict | None,
    garment_measurements: dict | None,
) -> float | None:
    """`part`(CatVTON `mask_type`, 'upper'/'lower'/'overall'/'inner'/'outer')에 맞는
    신체/의류 측정값 쌍을 골라 `dilation_px`를 계산한다.

    `body_measurements`는 `{"height_cm": ..., "waist_cm": ...}` 형태(BE `member_body_profile`
    필드명에서 `body_` 접두어만 뗀 키), `garment_measurements`는 `AI/app/measurement/schemas.py`
    `MeasurementType` 값을 키로 쓰는 dict다.

    측정값이 없거나(`None`/빈 dict), `part`가 'lower'가 아니어서 대응하는 너비 축 자체가
    없으면 `None`을 반환한다 — 호출부는 이때 기존 `adjust_mask_for_fit(fit_type)`으로
    폴백해야 한다.
    """
    if not body_measurements or not garment_measurements or part != "lower":
        return None

    width_ratio = compute_width_adjustment(
        body_measurements.get("waist_cm"),
        garment_measurements.get("WAIST_WIDTH"),
    )
    if width_ratio is None:
        return None

    return ratio_to_dilation_px(width_ratio)
