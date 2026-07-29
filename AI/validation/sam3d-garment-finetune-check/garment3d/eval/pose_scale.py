"""체형 스케일 드리프트 — 2D keypoint 로 어깨너비·키 스케일의 프레임 간 분산을 본다.

**측정 대상**: 회전하는 동안 사람의 크기가 변하는가. 턴테이블은 카메라만 도니 세로 스케일이
변할 이유가 없다. I2V 는 프레임을 생성하므로 사람이 커지거나 작아지는 드리프트가 흔하다.

**어깨너비는 회전에 따라 실제로 변한다**(정면에서 최대, 측면에서 최소). 그래서 어깨너비는
*분산 그대로*가 아니라 **키(세로 스케일)로 정규화한 비율**의 변동을 본다 — 세로는 회전
불변이므로 그 비율이 흔들리면 형태가 변한 것이다. 이 구분이 이 모듈의 핵심이다.

백엔드는 인터페이스로 분리한다. `dummy` 는 마스크에서 근사 keypoint 를 뽑아 CI 에서 돌고,
`mediapipe` 는 실제 추정기를 쓴다(설치돼 있을 때만).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Keypoints2d:
    """프레임 하나의 필요한 keypoint 만. 전체 골격이 필요하지 않다.

    좌표는 픽셀 `(x, y)` 이고, 못 찾은 점은 `None` 이다 — 0 으로 채우면 지표가 조용히 망가진다.
    """

    left_shoulder: tuple[float, float] | None
    right_shoulder: tuple[float, float] | None
    #: 세로 스케일용. 머리 최상단과 발 최하단.
    top: tuple[float, float] | None
    bottom: tuple[float, float] | None

    @property
    def shoulder_width(self) -> float | None:
        if self.left_shoulder is None or self.right_shoulder is None:
            return None
        return float(abs(self.left_shoulder[0] - self.right_shoulder[0]))

    @property
    def body_height(self) -> float | None:
        if self.top is None or self.bottom is None:
            return None
        return float(abs(self.bottom[1] - self.top[1]))


class PoseEstimator(ABC):
    """프레임 → keypoint."""

    name: str = "abstract"

    @abstractmethod
    def estimate(self, frame: np.ndarray, mask: np.ndarray | None = None) -> Keypoints2d: ...

    def estimate_sequence(
        self, frames: np.ndarray, masks: np.ndarray | None = None
    ) -> list[Keypoints2d]:
        return [
            self.estimate(frames[t], None if masks is None else masks[t])
            for t in range(len(frames))
        ]


class MaskPoseEstimator(PoseEstimator):
    """마스크 기하로 keypoint 를 근사한다. **CI·스모크 전용 프록시.**

    - `top`/`bottom`: 마스크의 최상단/최하단 행.
    - 어깨: 상단에서 `shoulder_ratio` 만큼 내려온 행의 마스크 좌우 끝.

    실제 어깨가 아니라 **실루엣 폭**이다. 그래도 "프레임 간 스케일이 흔들리는가"라는 질문에는
    답한다 — 이 지표의 목적이 절대 치수가 아니라 **프레임 간 변동**이라서 성립한다.
    실측 비교에는 `mediapipe`/vitpose 백엔드를 써야 한다.
    """

    name = "dummy"

    def __init__(self, shoulder_ratio: float = 0.18) -> None:
        self.shoulder_ratio = shoulder_ratio

    def estimate(self, frame: np.ndarray, mask: np.ndarray | None = None) -> Keypoints2d:
        if mask is None:
            raise ValueError("MaskPoseEstimator 는 mask 가 필요합니다")
        mask = np.asarray(mask, dtype=bool)
        rows = np.nonzero(mask.any(axis=1))[0]
        if len(rows) == 0:
            return Keypoints2d(None, None, None, None)

        top_row, bottom_row = int(rows[0]), int(rows[-1])
        height = bottom_row - top_row
        shoulder_row = min(bottom_row, top_row + int(height * self.shoulder_ratio))
        columns = np.nonzero(mask[shoulder_row])[0]
        if len(columns) == 0:
            left = right = None
        else:
            left = (float(columns[0]), float(shoulder_row))
            right = (float(columns[-1]), float(shoulder_row))

        center_columns = np.nonzero(mask[top_row])[0]
        center_x = float(center_columns.mean()) if len(center_columns) else 0.0
        return Keypoints2d(
            left_shoulder=left,
            right_shoulder=right,
            top=(center_x, float(top_row)),
            bottom=(center_x, float(bottom_row)),
        )


class MediapipePoseEstimator(PoseEstimator):
    """mediapipe Pose 백엔드. 설치돼 있을 때만 동작한다.

    vitpose 를 쓰려면 같은 인터페이스로 어댑터를 하나 더 만들면 된다 — 지표 코드는 손대지 않는다.
    """

    name = "mediapipe"
    #: mediapipe Pose landmark 인덱스 (BlazePose 33점 규약)
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    NOSE = 0
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self) -> None:
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError(
                "mediapipe 가 없습니다: pip install mediapipe (또는 eval.pose_backend=dummy)"
            ) from exc
        self._pose = mp.solutions.pose.Pose(static_image_mode=True)

    def estimate(self, frame: np.ndarray, mask: np.ndarray | None = None) -> Keypoints2d:
        frame = np.asarray(frame, dtype=np.uint8)
        height, width = frame.shape[:2]
        result = self._pose.process(frame[..., :3])
        landmarks = getattr(result, "pose_landmarks", None)
        if landmarks is None:
            return Keypoints2d(None, None, None, None)

        points = landmarks.landmark

        def _xy(index: int) -> tuple[float, float]:
            return (float(points[index].x * width), float(points[index].y * height))

        ankles = [_xy(self.LEFT_ANKLE), _xy(self.RIGHT_ANKLE)]
        bottom = (
            float(np.mean([a[0] for a in ankles])),
            float(np.max([a[1] for a in ankles])),
        )
        return Keypoints2d(
            left_shoulder=_xy(self.LEFT_SHOULDER),
            right_shoulder=_xy(self.RIGHT_SHOULDER),
            top=_xy(self.NOSE),
            bottom=bottom,
        )


@dataclass(frozen=True)
class ScaleDriftMetrics:
    """스케일 드리프트. **전부 낮을수록 좋다.**"""

    #: 세로 스케일(키)의 변동계수 — 회전 불변량이므로 0 이어야 정상
    height_cv: float
    #: 첫 프레임 대비 마지막 프레임의 키 비율 - 1 — 단조 드리프트를 잡는다
    height_drift: float
    #: 어깨너비/키 비율의 변동계수 — 회전에 따른 어깨너비 변화를 정규화해 제거한 뒤의 변동
    shoulder_height_ratio_cv: float
    #: keypoint 를 못 찾은 프레임 비율 — 높으면 위 숫자들을 신뢰하지 말 것
    missing_ratio: float
    num_frames: int

    def as_row(self) -> dict[str, float]:
        return {
            "scale_height_cv": self.height_cv,
            "scale_height_drift": self.height_drift,
            "scale_shoulder_ratio_cv": self.shoulder_height_ratio_cv,
            "scale_missing_ratio": self.missing_ratio,
        }


def _cv(values: list[float]) -> float:
    if not values:
        return 0.0
    array = np.asarray(values, dtype=np.float64)
    mean = float(array.mean())
    if abs(mean) < 1e-12:
        return 0.0
    return float(array.std() / mean)


def scale_drift_metrics(keypoints: list[Keypoints2d]) -> ScaleDriftMetrics:
    """keypoint 시퀀스에서 스케일 드리프트를 계산한다. 순수 함수."""
    if len(keypoints) < 2:
        raise ValueError("스케일 드리프트는 프레임이 2장 이상이어야 계산됩니다")

    heights = [kp.body_height for kp in keypoints]
    ratios = [
        kp.shoulder_width / kp.body_height
        for kp in keypoints
        if kp.shoulder_width is not None and kp.body_height not in (None, 0)
    ]
    valid_heights = [h for h in heights if h not in (None, 0)]
    missing = sum(1 for h in heights if h in (None, 0))

    drift = 0.0
    if len(valid_heights) >= 2 and valid_heights[0] > 0:
        drift = float(valid_heights[-1] / valid_heights[0] - 1.0)

    return ScaleDriftMetrics(
        height_cv=_cv(valid_heights),
        height_drift=drift,
        shoulder_height_ratio_cv=_cv(ratios),
        missing_ratio=float(missing / len(keypoints)),
        num_frames=len(keypoints),
    )


def build_pose_estimator(backend: str) -> PoseEstimator:
    if backend == "dummy":
        return MaskPoseEstimator()
    if backend == "mediapipe":
        return MediapipePoseEstimator()
    raise ValueError(f"알 수 없는 pose 백엔드: {backend!r}")
