"""`worker/models/catvton/model/adaptive_fit.py` 순수 계산 검증.

cv2/torch 의존성이 전혀 없어서(SCHP/DensePose 등 무거운 형제 모듈은 import되지 않는다 —
`model/`에 `__init__.py`가 없는 네임스페이스 패키지이기 때문) mock/실 백엔드 구분 없이 항상
실제 구현을 그대로 테스트한다.
"""

import pytest

from model.adaptive_fit import (
    compute_length_adjustment,
    compute_mask_adjustment,
    compute_width_adjustment,
    ratio_to_cutoff_ratio,
    ratio_to_dilation_px,
)

# --- compute_length_adjustment ------------------------------------------------


def test_length_adjustment_returns_one_when_ratio_matches_reference():
    # 170cm 키에 기준 비율 0.4라면 "정확히 맞는" 기장은 68cm.
    result = compute_length_adjustment(
        body_height_cm=170.0, garment_length_cm=68.0, reference_ratio=0.4
    )
    assert result == 1.0


def test_length_adjustment_above_one_means_relatively_long():
    result = compute_length_adjustment(
        body_height_cm=170.0, garment_length_cm=85.0, reference_ratio=0.4
    )
    assert result == 85.0 / 170.0 / 0.4
    assert result > 1.0


def test_length_adjustment_is_none_when_height_missing():
    assert compute_length_adjustment(None, 68.0, reference_ratio=0.4) is None


def test_length_adjustment_is_none_when_garment_length_missing():
    assert compute_length_adjustment(170.0, None, reference_ratio=0.4) is None


def test_length_adjustment_is_none_for_non_positive_inputs():
    assert compute_length_adjustment(0.0, 68.0, reference_ratio=0.4) is None
    assert compute_length_adjustment(170.0, -1.0, reference_ratio=0.4) is None


# --- compute_width_adjustment --------------------------------------------------


def test_width_adjustment_returns_one_when_garment_matches_half_circumference():
    # 허리둘레 84cm면 몸에 딱 맞는 평평한 폭은 42cm.
    result = compute_width_adjustment(body_circumference_cm=84.0, garment_flat_width_cm=42.0)
    assert result == 1.0


def test_width_adjustment_above_one_means_roomier_than_body():
    result = compute_width_adjustment(body_circumference_cm=84.0, garment_flat_width_cm=50.0)
    assert result == 50.0 / 42.0
    assert result > 1.0


def test_width_adjustment_is_none_when_either_input_missing():
    assert compute_width_adjustment(None, 42.0) is None
    assert compute_width_adjustment(84.0, None) is None
    assert compute_width_adjustment(None, None) is None


# --- ratio_to_dilation_px -------------------------------------------------------


def test_dilation_px_is_zero_when_ratio_is_none():
    """측정값이 없으면(ratio=None) 마스크를 전혀 안 건드린다."""
    assert ratio_to_dilation_px(None) == 0.0


def test_dilation_px_is_zero_at_neutral_ratio():
    assert ratio_to_dilation_px(1.0) == 0.0


def test_dilation_px_is_positive_for_roomier_ratio():
    assert ratio_to_dilation_px(1.2, scale_px=20.0, max_px=40.0) == pytest.approx(4.0)


def test_dilation_px_is_negative_for_tighter_ratio():
    assert ratio_to_dilation_px(0.8, scale_px=20.0, max_px=40.0) == pytest.approx(-4.0)


def test_dilation_px_is_clamped_at_extremes():
    assert ratio_to_dilation_px(10.0, scale_px=20.0, max_px=40.0) == 40.0
    assert ratio_to_dilation_px(-10.0, scale_px=20.0, max_px=40.0) == -40.0


# --- ratio_to_cutoff_ratio -------------------------------------------------------


def test_cutoff_ratio_is_full_length_when_ratio_is_none():
    """측정값이 없으면(ratio=None) 컷오프 없이 원본 길이 그대로."""
    assert ratio_to_cutoff_ratio(None) == 1.0


def test_cutoff_ratio_equals_base_at_neutral_ratio():
    assert ratio_to_cutoff_ratio(1.0, base=0.7, scale=0.3) == 0.7


def test_cutoff_ratio_increases_for_relatively_long_garment():
    result = ratio_to_cutoff_ratio(1.5, base=0.7, scale=0.3)
    assert result == pytest.approx(0.85)


def test_cutoff_ratio_is_clamped_between_point3_and_1():
    assert ratio_to_cutoff_ratio(10.0, base=0.7, scale=0.3) == 1.0
    assert ratio_to_cutoff_ratio(-10.0, base=0.7, scale=0.3) == 0.3


# --- compute_mask_adjustment ----------------------------------------------------


def test_mask_adjustment_is_none_when_body_measurements_missing():
    """측정값이 하나라도 없으면 폴백 신호로 None을 돌려준다 — 호출부가 fit_type으로 폴백."""
    assert compute_mask_adjustment("upper", None, {"TOTAL_LENGTH": 68.0}) is None


def test_mask_adjustment_is_none_when_garment_measurements_missing():
    assert compute_mask_adjustment("upper", {"height_cm": 170.0}, None) is None


def test_mask_adjustment_is_none_when_both_are_empty_dicts():
    assert compute_mask_adjustment("upper", {}, {}) is None


def test_mask_adjustment_upper_uses_total_length_only_no_width_axis():
    """상의는 가슴 너비 축이 없어서(bust 랜드마크 없음) waist_cm/WAIST_WIDTH가 있어도
    무시하고 dilation_px는 항상 0.0이어야 한다."""
    result = compute_mask_adjustment(
        "upper",
        {"height_cm": 170.0, "waist_cm": 84.0},
        {"TOTAL_LENGTH": 68.0, "WAIST_WIDTH": 999.0},
    )
    assert result is not None
    dilation_px, cutoff_ratio = result
    assert dilation_px == 0.0


def test_mask_adjustment_lower_uses_outseam_and_waist_width():
    result = compute_mask_adjustment(
        "lower",
        {"height_cm": 170.0, "waist_cm": 84.0},
        {"OUTSEAM_LENGTH": 102.0, "WAIST_WIDTH": 42.0},
    )
    # 170*0.60=102(정확히 기준), 84/2=42(정확히 기준) — 둘 다 중립값이어야 한다.
    assert result == (0.0, 0.7)


def test_mask_adjustment_lower_without_waist_data_still_uses_length_axis():
    """바지 허리 데이터가 없으면(BE 컬럼 미확정 상태) 너비 축만 스킵하고 길이 축은 그대로
    계산해야 한다."""
    result = compute_mask_adjustment(
        "lower",
        {"height_cm": 170.0},
        {"OUTSEAM_LENGTH": 102.0},
    )
    assert result is not None
    dilation_px, _cutoff_ratio = result
    assert dilation_px == 0.0  # waist 데이터가 없어 폭 축은 항상 무조정
