"""키/몸무게로 평균 체형 치수를 근사한다.

**실측이 아니다.** BE `member_body_profile`엔 아직 `height_cm`/`weight_kg`만 확정 컬럼이고
가슴/허리/엉덩이 실측 컬럼은 없다(`.codex/requests/be/003-onboarding-tryon-profile-api.md`,
아직 열려있음). 실측 컬럼이 생기면 그 값을 우선 쓰고, 이 근사치는 폴백으로만 남긴다.

공식: 키 대비 신체 부위별 평균 비율(패턴 제도에서 흔히 쓰는 경험적 비율)에, 표준체중
기준(BMI 22) 대비 몸무게 편차를 보정 계수로 곱한다. 정밀한 의학적 회귀식이 아니라
**대략적인 근사치**다 — 실측 데이터가 쌓이면 계수를 조정해야 한다.
"""

from __future__ import annotations

REFERENCE_BMI = 22.0  # "표준 체중" 기준점
BMI_ADJUSTMENT_PER_POINT = 0.012  # BMI가 기준점보다 1 높을/낮을 때마다 치수를 이 비율만큼 증감

# 키 대비 부위별 평균 비율 (키 1일 때 각 부위 둘레/너비의 비율)
HEIGHT_RATIOS: dict[str, float] = {
    "shoulder_cm": 0.259,
    "chest_cm": 0.52,
    "waist_cm": 0.45,
    "hip_cm": 0.54,
    "calf_cm": 0.215,
}

MIN_HEIGHT_CM = 100.0
MAX_HEIGHT_CM = 220.0
MIN_WEIGHT_KG = 30.0
MAX_WEIGHT_KG = 200.0


def estimate_body_measurements(height_cm: float, weight_kg: float) -> dict[str, float]:
    """키(cm)/몸무게(kg) -> 근사 신체 치수(cm) 딕셔너리.

    `HEIGHT_RATIOS`의 각 키(shoulder_cm/chest_cm/waist_cm/hip_cm/calf_cm)를 그대로
    반환한다. 값이 범위 밖이면 `ValueError` — 호출부(워커)가 이걸 잡아서 근사를
    건너뛰고 "regular fit" 고정으로 폴백해야 한다.
    """
    if not (MIN_HEIGHT_CM <= height_cm <= MAX_HEIGHT_CM):
        raise ValueError(f"height_cm이 상식적인 범위를 벗어남: {height_cm}")
    if not (MIN_WEIGHT_KG <= weight_kg <= MAX_WEIGHT_KG):
        raise ValueError(f"weight_kg이 상식적인 범위를 벗어남: {weight_kg}")

    bmi = weight_kg / (height_cm / 100) ** 2
    bmi_factor = 1.0 + (bmi - REFERENCE_BMI) * BMI_ADJUSTMENT_PER_POINT

    return {
        key: round(height_cm * ratio * bmi_factor, 1)
        for key, ratio in HEIGHT_RATIOS.items()
    }
