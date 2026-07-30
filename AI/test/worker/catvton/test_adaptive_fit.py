"""`worker/models/catvton/model/adaptive_fit.py` 순수 계산 검증.

cv2/torch 의존성이 전혀 없어서(SCHP/DensePose 등 무거운 형제 모듈은 import되지 않는다 —
`model/`에 `__init__.py`가 없는 네임스페이스 패키지이기 때문) mock/실 백엔드 구분 없이 항상
실제 구현을 그대로 테스트한다.

길이(기장) 축은 없다 — 마스크 하단을 잘라 기장을 줄이면 그 자리에 맨살을 새로 생성해야 해서
AI 가드레일상 정책적으로 뺐다(모듈 docstring 참고). 너비(스키니/배기) 축만 검증한다.
"""

import pytest

from model.adaptive_fit import (
    compute_mask_adjustment,
    compute_width_adjustment,
    ratio_to_dilation_px,
)

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


# --- compute_mask_adjustment ----------------------------------------------------


def test_mask_adjustment_is_none_when_body_measurements_missing():
    """측정값이 하나라도 없으면 폴백 신호로 None을 돌려준다 — 호출부가 fit_type으로 폴백."""
    assert compute_mask_adjustment("lower", None, {"WAIST_WIDTH": 42.0}) is None


def test_mask_adjustment_is_none_when_garment_measurements_missing():
    assert compute_mask_adjustment("lower", {"waist_cm": 84.0}, None) is None


def test_mask_adjustment_is_none_when_both_are_empty_dicts():
    assert compute_mask_adjustment("lower", {}, {}) is None


def test_mask_adjustment_is_none_for_upper_no_width_axis_yet():
    """상의는 가슴 너비 축이 없다(bust 랜드마크 미지원) — waist_cm/WAIST_WIDTH를 넣어도
    무시하고 항상 None(호출부는 fit_type 폴백)이어야 한다."""
    result = compute_mask_adjustment(
        "upper",
        {"waist_cm": 84.0},
        {"WAIST_WIDTH": 999.0},
    )
    assert result is None


def test_mask_adjustment_lower_uses_waist_width():
    result = compute_mask_adjustment(
        "lower",
        {"waist_cm": 84.0},
        {"WAIST_WIDTH": 42.0},
    )
    assert result == 0.0  # 84/2=42(정확히 기준) — 중립값


def test_mask_adjustment_lower_reflects_roomier_or_tighter_fit():
    roomy = compute_mask_adjustment("lower", {"waist_cm": 60.0}, {"WAIST_WIDTH": 50.0})
    tight = compute_mask_adjustment("lower", {"waist_cm": 90.0}, {"WAIST_WIDTH": 35.0})
    assert roomy > 0.0
    assert tight < 0.0


def test_mask_adjustment_lower_without_waist_data_is_none():
    """바지 허리 데이터가 없으면(BE 컬럼 미확정 상태) None — 폴백."""
    assert compute_mask_adjustment("lower", {}, {"WAIST_WIDTH": 42.0}) is None
