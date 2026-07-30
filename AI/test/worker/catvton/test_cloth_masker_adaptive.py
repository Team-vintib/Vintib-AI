"""`cloth_masker.py`의 적응형 마스킹 연결부(`apply_adaptive_adjustment`) 검증.

`model.cloth_masker`를 import하려면 SCHP/DensePose가 torch·torchvision·detectron2까지
끌고 온다 — 그런 무거운 스택이 없는 환경(CI 기본)에서는 통째로 스킵한다. cv2/numpy만
있으면 되는 순수 비율 계산(`compute_mask_adjustment` 등)은 `test_adaptive_fit.py`가 이미
커버한다 — 여기서는 계산된 값을 실제 마스크 배열에 "적용"하는 부분만 본다.
"""

import numpy as np
import pytest

cloth_masker = pytest.importorskip("model.cloth_masker")


def _rectangle_mask(height: int, width: int, top: int, bottom: int, left: int, right: int):
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[top:bottom, left:right] = 1
    return mask


def _torso_densepose(height: int, width: int, torso_top: int, torso_bottom: int):
    """`part_mask_of(['torso'], ...)`가 인식하도록 DENSE_INDEX_MAP의 torso 인덱스(1)로
    채운 합성 densepose 마스크."""
    densepose = np.zeros((height, width), dtype=np.uint8)
    densepose[torso_top:torso_bottom, :] = 1
    return densepose


def test_zero_dilation_and_full_cutoff_leaves_mask_unchanged():
    """dilation_px=0, cutoff_ratio=1.0(둘 다 무조정 신호)이면 원본 마스크 그대로여야 한다."""
    mask = _rectangle_mask(100, 100, top=20, bottom=80, left=20, right=80)
    densepose = _torso_densepose(100, 100, torso_top=20, torso_bottom=80)

    result = cloth_masker.apply_adaptive_adjustment(
        mask, densepose, dilation_px=0.0, cutoff_ratio=1.0
    )

    assert np.array_equal(result, mask)


def test_positive_dilation_expands_mask_area():
    mask = _rectangle_mask(100, 100, top=40, bottom=60, left=40, right=60)
    densepose = _torso_densepose(100, 100, torso_top=40, torso_bottom=60)

    result = cloth_masker.apply_adaptive_adjustment(
        mask, densepose, dilation_px=10.0, cutoff_ratio=1.0
    )

    assert result.sum() > mask.sum()
    # 원래 마스크였던 픽셀은 팽창 후에도 여전히 마스크 안에 있어야 한다.
    assert np.all(result[mask.astype(bool)] == 1)


def test_negative_dilation_shrinks_mask_area():
    mask = _rectangle_mask(100, 100, top=20, bottom=80, left=20, right=80)
    densepose = _torso_densepose(100, 100, torso_top=20, torso_bottom=80)

    result = cloth_masker.apply_adaptive_adjustment(
        mask, densepose, dilation_px=-10.0, cutoff_ratio=1.0
    )

    assert result.sum() < mask.sum()
    # 수축된 마스크는 원래 마스크의 부분집합이어야 한다(새 영역이 생기면 안 됨).
    assert np.all(result[~mask.astype(bool)] == 0)


def test_cutoff_ratio_below_one_removes_lower_portion():
    """cutoff_ratio=0.5면 torso 하단 절반이 마스크에서 제외돼야 한다(기존 cropped 로직과
    같은 구조 — 상수만 연속값으로 바뀜)."""
    mask = _rectangle_mask(100, 100, top=0, bottom=100, left=0, right=100)
    densepose = _torso_densepose(100, 100, torso_top=0, torso_bottom=100)

    result = cloth_masker.apply_adaptive_adjustment(
        mask, densepose, dilation_px=0.0, cutoff_ratio=0.5
    )

    assert result[40, 50] == 1  # torso 상단 근처는 남아있어야 한다
    assert result[90, 50] == 0  # torso 하단은 잘려나가야 한다
