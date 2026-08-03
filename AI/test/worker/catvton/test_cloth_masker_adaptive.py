"""`cloth_masker.py`의 적응형 마스킹 연결부(`apply_adaptive_adjustment`) 검증.

`model.cloth_masker`를 import하려면 SCHP/DensePose가 torch·torchvision·detectron2까지
끌고 온다 — 그런 무거운 스택이 없는 환경(CI 기본)에서는 통째로 스킵한다. cv2/numpy만
있으면 되는 순수 비율 계산(`compute_mask_adjustment` 등)은 `test_adaptive_fit.py`가 이미
커버한다 — 여기서는 계산된 값을 실제 마스크 배열에 "적용"하는 부분만 본다.

마스크를 잘라 기장을 연속적으로 줄이는 축은 없다 — 그 자리에 맨살을 우발적으로 새로
생성해야 해서 AI 가드레일상 정책적으로 뺐다. 너비(스키니/배기) 축만 검증한다.

반팔/반바지 레퍼런스 대응(마스크를 의류/피부 영역으로 나눠 채우는 기능)도 실험했었지만,
실사 알파테스트에서 CatVTON이 "피부" 개념 자체를 학습한 적이 없어(본인 피부 패치 조건
이미지든, cross-attention을 되살린 텍스트 프롬프트든) 안정적으로 안 먹힌다는 게 확인돼
범위에서 뺐다(`adaptive_fit.py` docstring 참고).
"""

import numpy as np
import pytest

cloth_masker = pytest.importorskip("model.cloth_masker")


def _rectangle_mask(height: int, width: int, top: int, bottom: int, left: int, right: int):
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[top:bottom, left:right] = 1
    return mask


def test_zero_dilation_leaves_mask_unchanged():
    """dilation_px=0(무조정 신호)이면 원본 마스크 그대로여야 한다."""
    mask = _rectangle_mask(100, 100, top=20, bottom=80, left=20, right=80)

    result = cloth_masker.apply_adaptive_adjustment(mask, dilation_px=0.0)

    assert np.array_equal(result, mask)


def test_positive_dilation_expands_mask_area():
    mask = _rectangle_mask(100, 100, top=40, bottom=60, left=40, right=60)

    result = cloth_masker.apply_adaptive_adjustment(mask, dilation_px=10.0)

    assert result.sum() > mask.sum()
    # 원래 마스크였던 픽셀은 팽창 후에도 여전히 마스크 안에 있어야 한다.
    assert np.all(result[mask.astype(bool)] == 1)


def test_negative_dilation_shrinks_mask_area():
    mask = _rectangle_mask(100, 100, top=20, bottom=80, left=20, right=80)

    result = cloth_masker.apply_adaptive_adjustment(mask, dilation_px=-10.0)

    assert result.sum() < mask.sum()
    # 수축된 마스크는 원래 마스크의 부분집합이어야 한다(새 영역이 생기면 안 됨).
    assert np.all(result[~mask.astype(bool)] == 0)


def test_mask_vertical_extent_is_never_reduced():
    """폭만 조절하고 신체가 덮이는 세로 범위(위/아래 끝)는 안 바뀌어야 한다 — 맨살 노출을
    피하려고 길이 축을 아예 뺀 설계 의도를 지키는지 확인."""
    mask = _rectangle_mask(100, 100, top=10, bottom=90, left=30, right=70)

    shrunk = cloth_masker.apply_adaptive_adjustment(mask, dilation_px=-5.0)

    rows_with_mask = np.where(shrunk.any(axis=1))[0]
    # distanceTransform은 대각선 방향으로도 깎여나가서 정확히 dilation_px만큼만 줄지는
    # 않는다 — 세로 범위가 큰 폭으로 줄지 않았는지(=길이 축이 관여하지 않는지)만 확인한다.
    assert rows_with_mask.min() <= 10 + 10
    assert rows_with_mask.max() >= 90 - 10
