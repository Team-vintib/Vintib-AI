"""텍스처 안정성 — optical flow 보정 잔차 / 지각적 플리커 / 회전 일관성.

**측정 대상**: 프레임 사이 변화가 "카메라가 돌아서 생긴 변화"인지 "텍스처가 새로 생성돼서
생긴 변화"인지 구분한다. 그래서 raw 프레임 차분이 아니라 **flow 로 보정한 뒤의 잔차**를 본다 —
회전에 의한 정상적 이동은 flow 가 흡수하고, 남은 잔차가 곧 플리커/재생성이다.

세 축이 있다.

1. `flow_residual` — flow 로 정합한 뒤 남는 밝기 차. 낮을수록 좋다.
2. `temporal_perceptual` — 인접 프레임 지각 거리의 평균/표준편차. 표준편차가 크면 튀는 프레임이 있다.
3. 회전 일관성 — 방향이 중간에 뒤집히지 않는지(`direction_flip_ratio`), 그리고 좌우 대칭
   프레임쌍이 실제로 대칭인지(`symmetry_error`).

`ZeroFlowEstimator`(기본)를 쓰면 `flow_residual` 은 **raw 차분과 같아진다** — 그 상태의 숫자를
"flow 보정 후"라고 읽으면 안 된다. 그래서 결과에 `flow_backend` 를 함께 담는다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


class FlowEstimator(ABC):
    """두 프레임 사이 optical flow."""

    name: str = "abstract"

    @abstractmethod
    def estimate(self, previous: np.ndarray, current: np.ndarray) -> np.ndarray:
        """`(H, W, 2)` float — `[..., 0]` = dx, `[..., 1]` = dy."""


class ZeroFlowEstimator(FlowEstimator):
    """항등 flow. **의존성 없는 기본값이며 flow 보정을 하지 않는다.**

    이걸 쓰면 잔차 = raw 프레임 차분이다. 턴테이블/I2V 를 **같은 조건**으로 비교하는 데는
    여전히 유효하지만(둘 다 보정 없음), "회전에 의한 변화를 제거했다"고 해석하면 틀린다.
    """

    name = "dummy"

    def estimate(self, previous: np.ndarray, current: np.ndarray) -> np.ndarray:
        height, width = np.asarray(previous).shape[:2]
        return np.zeros((height, width, 2), dtype=np.float64)


class FarnebackFlowEstimator(FlowEstimator):
    """OpenCV Farneback dense flow. cv2 가 있을 때만."""

    name = "opencv_farneback"

    def __init__(self, **kwargs) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError(
                "opencv-python 이 없습니다: pip install opencv-python "
                "(또는 eval.flow_backend=dummy)"
            ) from exc
        self._cv2 = cv2
        self._params = {
            "pyr_scale": 0.5,
            "levels": 3,
            "winsize": 15,
            "iterations": 3,
            "poly_n": 5,
            "poly_sigma": 1.2,
            "flags": 0,
            **kwargs,
        }

    def estimate(self, previous: np.ndarray, current: np.ndarray) -> np.ndarray:
        cv2 = self._cv2
        prev_gray = cv2.cvtColor(np.asarray(previous, dtype=np.uint8), cv2.COLOR_RGB2GRAY)
        curr_gray = cv2.cvtColor(np.asarray(current, dtype=np.uint8), cv2.COLOR_RGB2GRAY)
        flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, **self._params)
        return np.asarray(flow, dtype=np.float64)


def warp_with_flow(frame: np.ndarray, flow: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """`frame` 을 `flow` 만큼 이동시켜 다음 프레임 좌표계로 옮긴다(bilinear, 순수 numpy).

    Returns:
        `(워프된 프레임 float64, 유효 마스크 bool)` — 화면 밖에서 온 픽셀은 유효하지 않다.
        유효 마스크 없이 평균을 내면 경계 픽셀 때문에 잔차가 부풀려진다.
    """
    frame = np.asarray(frame, dtype=np.float64)
    height, width = frame.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float64)
    src_x = xx - flow[..., 0]
    src_y = yy - flow[..., 1]

    valid = (src_x >= 0) & (src_x <= width - 1) & (src_y >= 0) & (src_y <= height - 1)
    clipped_x = np.clip(src_x, 0, width - 1)
    clipped_y = np.clip(src_y, 0, height - 1)

    x0 = np.floor(clipped_x).astype(np.int64)
    y0 = np.floor(clipped_y).astype(np.int64)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)
    wx = (clipped_x - x0)[..., None] if frame.ndim == 3 else (clipped_x - x0)
    wy = (clipped_y - y0)[..., None] if frame.ndim == 3 else (clipped_y - y0)

    top = frame[y0, x0] * (1 - wx) + frame[y0, x1] * wx
    bottom = frame[y1, x0] * (1 - wx) + frame[y1, x1] * wx
    return top * (1 - wy) + bottom * wy, valid


class PerceptualMetric(ABC):
    """두 프레임의 지각 거리. 낮을수록 비슷하다."""

    name: str = "abstract"

    @abstractmethod
    def distance(self, a: np.ndarray, b: np.ndarray) -> float: ...


class L2PerceptualMetric(PerceptualMetric):
    """[0,1] 정규화 RMSE. **LPIPS 의 대체이며 지각적이지 않다.**

    같은 조건으로 두 방식을 비교하는 데는 쓸 수 있지만, 절대값을 LPIPS 수치와 비교하면 안 된다.
    """

    name = "l2"

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        diff = (np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)) / 255.0
        return float(np.sqrt((diff**2).mean()))


class LpipsPerceptualMetric(PerceptualMetric):
    """LPIPS. `lpips` + torch 가 있을 때만."""

    name = "lpips"

    def __init__(self, net: str = "alex", device: str = "cpu") -> None:
        try:
            import lpips
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "lpips 와 torch 가 필요합니다: pip install lpips "
                "(또는 eval.perceptual_backend=l2)"
            ) from exc
        self._torch = torch
        self._model = lpips.LPIPS(net=net).to(device).eval()
        self._device = device

    def _to_tensor(self, image: np.ndarray):
        array = np.asarray(image, dtype=np.float32)[..., :3] / 127.5 - 1.0
        tensor = self._torch.from_numpy(array).permute(2, 0, 1)[None]
        return tensor.to(self._device)

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        with self._torch.no_grad():
            value = self._model(self._to_tensor(a), self._to_tensor(b))
        return float(value.reshape(-1)[0])


def rotation_direction_flips(flows: list[np.ndarray], *, min_magnitude: float = 0.05) -> float:
    """회전 방향이 중간에 뒤집히는 비율.

    flow 의 평균 dx 부호가 다수 방향과 반대인 프레임쌍의 비율이다. **정답 방향을 모르는
    상태에서도 계산되는 게 요점** — 한 방향으로 꾸준히 도는지만 본다. 중간에 방향이 바뀌는 건
    I2V 의 전형적 실패다.

    `min_magnitude` 미만의 flow 는 방향 판정에서 제외한다(노이즈 부호로 오탐이 난다).
    `ZeroFlowEstimator` 를 쓰면 전부 제외돼 0.0 이 나온다 — "뒤집힘 없음"이 아니라 "판정 불가"다.
    """
    signs = []
    for flow in flows:
        mean_dx = float(np.asarray(flow)[..., 0].mean())
        if abs(mean_dx) >= min_magnitude:
            signs.append(1 if mean_dx > 0 else -1)
    if len(signs) < 2:
        return 0.0
    majority = 1 if sum(signs) >= 0 else -1
    return float(sum(1 for s in signs if s != majority) / len(signs))


def rotation_symmetry_error(frames: np.ndarray, *, offset: int = 0) -> float:
    """좌우 대칭 프레임쌍의 불일치.

    360° 한 바퀴 시퀀스에서 yaw `θ` 프레임과 yaw `-θ` 프레임은 **좌우 반전 관계**여야 한다.
    프레임 `k` 를 `(offset - k) mod T` 와 좌우 반전 비교해 평균 절대차를 [0,1] 로 낸다.

    ⚠️ **성립 조건이 좁다**: (1) 닫힌 360° 시퀀스, (2) 피사체가 좌우 대칭에 가까울 때. 의류
    단독 크롭은 대체로 만족하지만 로고·비대칭 디테일이 있으면 값이 커진다. 절대 판정에 쓰지 말고
    **turntable vs I2V 상대 비교**로만 읽는다.
    """
    frames = np.asarray(frames, dtype=np.float64)
    total = len(frames)
    if total < 2:
        raise ValueError("대칭 검사는 프레임이 2장 이상이어야 합니다")
    errors = []
    for k in range(total):
        j = (offset - k) % total
        if j == k:
            continue
        mirrored = frames[j][:, ::-1]
        errors.append(float(np.abs(frames[k] - mirrored).mean() / 255.0))
    return float(np.mean(errors)) if errors else 0.0


@dataclass(frozen=True)
class TextureMetrics:
    """텍스처 안정성. **전부 낮을수록 좋다.**"""

    #: flow 보정 후 잔차 평균([0,1] 정규화)
    flow_residual_mean: float
    #: 그 표준편차 — 특정 구간에서만 무너지는지
    flow_residual_std: float
    #: 인접 프레임 지각 거리 평균
    temporal_perceptual_mean: float
    #: 그 표준편차 = 플리커 지표
    temporal_perceptual_std: float
    #: 회전 방향이 뒤집힌 프레임쌍 비율
    direction_flip_ratio: float
    #: 좌우 대칭 불일치
    symmetry_error: float
    #: 어떤 백엔드로 쟀는지. **숫자 해석에 반드시 필요하다.**
    flow_backend: str
    perceptual_backend: str
    num_frames: int

    def as_row(self) -> dict[str, float]:
        return {
            "texture_flow_residual_mean": self.flow_residual_mean,
            "texture_flow_residual_std": self.flow_residual_std,
            "texture_perceptual_mean": self.temporal_perceptual_mean,
            "texture_perceptual_flicker": self.temporal_perceptual_std,
            "texture_direction_flip_ratio": self.direction_flip_ratio,
            "texture_symmetry_error": self.symmetry_error,
        }


def texture_metrics(
    frames: np.ndarray,
    *,
    flow_estimator: FlowEstimator | None = None,
    perceptual: PerceptualMetric | None = None,
    symmetry_offset: int | None = None,
) -> TextureMetrics:
    """텍스처 안정성 지표 묶음."""
    frames = np.asarray(frames)
    if len(frames) < 2:
        raise ValueError("텍스처 지표는 프레임이 2장 이상이어야 계산됩니다")

    flow_estimator = flow_estimator or ZeroFlowEstimator()
    perceptual = perceptual or L2PerceptualMetric()

    residuals: list[float] = []
    perceptual_distances: list[float] = []
    flows: list[np.ndarray] = []

    for t in range(1, len(frames)):
        previous, current = frames[t - 1], frames[t]
        flow = flow_estimator.estimate(previous, current)
        flows.append(flow)

        warped, valid = warp_with_flow(previous, flow)
        if valid.any():
            diff = np.abs(warped - np.asarray(current, dtype=np.float64))
            residuals.append(float(diff[valid].mean() / 255.0))
        perceptual_distances.append(perceptual.distance(previous, current))

    residual_array = np.asarray(residuals, dtype=np.float64)
    perceptual_array = np.asarray(perceptual_distances, dtype=np.float64)

    return TextureMetrics(
        flow_residual_mean=float(residual_array.mean()) if len(residual_array) else 0.0,
        flow_residual_std=float(residual_array.std()) if len(residual_array) else 0.0,
        temporal_perceptual_mean=float(perceptual_array.mean()),
        temporal_perceptual_std=float(perceptual_array.std()),
        direction_flip_ratio=rotation_direction_flips(flows),
        symmetry_error=rotation_symmetry_error(
            frames, offset=0 if symmetry_offset is None else symmetry_offset
        ),
        flow_backend=flow_estimator.name,
        perceptual_backend=perceptual.name,
        num_frames=int(len(frames)),
    )


def build_flow_estimator(backend: str) -> FlowEstimator:
    if backend == "dummy":
        return ZeroFlowEstimator()
    if backend == "opencv_farneback":
        return FarnebackFlowEstimator()
    raise ValueError(f"알 수 없는 flow 백엔드: {backend!r}")


def build_perceptual_metric(backend: str) -> PerceptualMetric:
    if backend == "l2":
        return L2PerceptualMetric()
    if backend == "lpips":
        return LpipsPerceptualMetric()
    raise ValueError(f"알 수 없는 perceptual 백엔드: {backend!r}")
