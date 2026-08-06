"""의류 형태·핏 일관성 — 실루엣 IoU 변동 + 엣지 일관성.

**측정 대상**: 시퀀스가 회전하는 동안 형태가 "같은 물체"로 유지되는가. 턴테이블은 기하가
고정돼 있어 변동이 작아야 하고, I2V 는 프레임마다 형태를 다시 생성하므로 커지기 쉽다.

전부 순수 numpy다 — CI 에서 그대로 돈다. 외부 세그멘터를 쓰지 않고 밝기 임계치로 실루엣을
뽑는 이유는 두 방식(턴테이블/I2V)에 **같은 전처리**를 적용해야 비교가 성립하기 때문이다.
임계치가 잘못되면 지표 전체가 무의미해지므로 `foreground_ratio` 를 함께 리포트한다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_SOBEL_X = np.array([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]])
_SOBEL_Y = _SOBEL_X.T


def mask_iou(a: np.ndarray, b: np.ndarray) -> float:
    """두 이진 마스크의 IoU. 합집합이 비면 1.0(둘 다 빈 = 완전 일치)."""
    a_bool, b_bool = np.asarray(a, dtype=bool), np.asarray(b, dtype=bool)
    union = int(np.logical_or(a_bool, b_bool).sum())
    if union == 0:
        return 1.0
    return float(np.logical_and(a_bool, b_bool).sum() / union)


def _convolve3(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """3x3 컨볼루션. scipy 없이 padding + 슬라이딩 합으로."""
    padded = np.pad(image, 1, mode="edge")
    out = np.zeros_like(image, dtype=np.float64)
    for dy in range(3):
        for dx in range(3):
            weight = kernel[dy, dx]
            if weight == 0.0:
                continue
            out += weight * padded[dy : dy + image.shape[0], dx : dx + image.shape[1]]
    return out


def edge_map(frame: np.ndarray, *, relative_threshold: float = 0.2) -> np.ndarray:
    """Sobel 크기의 상대 임계치로 엣지 이진맵을 만든다.

    절대 임계치를 쓰지 않는 이유: I2V 출력은 전체 대비/밝기가 턴테이블과 달라서 절대값으로
    비교하면 "I2V 가 엣지가 적다"는 가짜 결론이 나온다. 프레임 최댓값 대비로 정규화한다.
    """
    luma = np.asarray(frame, dtype=np.float64)
    if luma.ndim == 3:
        luma = luma.mean(axis=-1)
    magnitude = np.hypot(_convolve3(luma, _SOBEL_X), _convolve3(luma, _SOBEL_Y))
    peak = float(magnitude.max())
    if peak <= 0:
        return np.zeros(magnitude.shape, dtype=bool)
    return magnitude > (relative_threshold * peak)


def _cv(values: np.ndarray) -> float:
    """변동계수(std/mean). 스케일이 다른 시퀀스끼리 비교하려면 표준편차만으로는 안 된다."""
    values = np.asarray(values, dtype=np.float64)
    mean = float(values.mean())
    if abs(mean) < 1e-12:
        return 0.0
    return float(values.std() / mean)


@dataclass(frozen=True)
class SilhouetteMetrics:
    """실루엣·엣지 일관성. **낮을수록 좋은 값과 높을수록 좋은 값이 섞여 있다** — 이름에 명시."""

    #: 인접 프레임 실루엣 IoU 평균 (높을수록 좋음)
    consecutive_iou_mean: float
    #: 그 표준편차 (낮을수록 좋음) — "튀는 프레임"이 있는지
    consecutive_iou_std: float
    #: 최솟값 (높을수록 좋음) — 최악 프레임
    consecutive_iou_min: float
    #: 실루엣 면적의 변동계수 (낮을수록 좋음)
    area_cv: float
    #: 엣지 밀도의 변동계수 (낮을수록 좋음) — 디테일이 프레임마다 생기고 사라지는지
    edge_density_cv: float
    #: 인접 프레임 엣지맵 IoU 평균 (높을수록 좋음)
    consecutive_edge_iou_mean: float
    #: 전경 비율 평균 — **임계치 sanity check 용.** 0 이나 1 에 가까우면 임계치가 틀렸다.
    foreground_ratio_mean: float
    num_frames: int

    def as_row(self) -> dict[str, float]:
        return {
            "silhouette_iou_mean": self.consecutive_iou_mean,
            "silhouette_iou_std": self.consecutive_iou_std,
            "silhouette_iou_min": self.consecutive_iou_min,
            "silhouette_area_cv": self.area_cv,
            "edge_density_cv": self.edge_density_cv,
            "edge_iou_mean": self.consecutive_edge_iou_mean,
            "foreground_ratio_mean": self.foreground_ratio_mean,
        }


def silhouette_metrics(
    frames: np.ndarray,
    masks: np.ndarray,
    *,
    edge_threshold: float = 0.2,
) -> SilhouetteMetrics:
    """프레임 시퀀스의 형태 일관성.

    Args:
        frames: `(T, H, W, 3)` uint8.
        masks: `(T, H, W)` bool — `render.synthetic.frames_to_masks` 산출물.
    """
    frames = np.asarray(frames)
    masks = np.asarray(masks, dtype=bool)
    if len(frames) != len(masks):
        raise ValueError(f"프레임 수 불일치: frames={len(frames)} masks={len(masks)}")
    if len(frames) < 2:
        raise ValueError("일관성 지표는 프레임이 2장 이상이어야 계산됩니다")

    ious = np.array([mask_iou(masks[t - 1], masks[t]) for t in range(1, len(masks))])
    areas = masks.reshape(len(masks), -1).sum(axis=1).astype(np.float64)

    edges = np.stack([edge_map(f, relative_threshold=edge_threshold) for f in frames])
    edge_density = edges.reshape(len(edges), -1).mean(axis=1)
    edge_ious = np.array([mask_iou(edges[t - 1], edges[t]) for t in range(1, len(edges))])

    return SilhouetteMetrics(
        consecutive_iou_mean=float(ious.mean()),
        consecutive_iou_std=float(ious.std()),
        consecutive_iou_min=float(ious.min()),
        area_cv=_cv(areas),
        edge_density_cv=_cv(edge_density),
        consecutive_edge_iou_mean=float(edge_ious.mean()),
        foreground_ratio_mean=float(masks.mean()),
        num_frames=int(len(frames)),
    )
