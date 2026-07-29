"""평가 하네스 — **같은 케이스·같은 지표**로 turntable 과 I2V 를 둘 다 측정한다.

비교가 성립하려면 두 시퀀스가 같은 조건이어야 한다. 이 모듈이 그걸 강제한다:

- 프레임 수·해상도가 다르면 `warnings` 에 남긴다(조용히 리샘플하지 않는다 — 리샘플 자체가
  시간적 지표를 바꾼다).
- 실루엣 임계치·flow/perceptual 백엔드를 **양쪽에 동일하게** 적용한다.
- 각 지표가 "높을수록 좋은지 낮을수록 좋은지"를 `METRIC_DIRECTIONS` 한 곳에 모아 둔다 —
  방향을 리포트에서 다시 적으면 반드시 어긋난다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from ..config import EvalConfig
from ..render.synthetic import frames_to_masks
from .identity import IdentityMetrics, build_face_embedder, identity_metrics
from .pose_scale import ScaleDriftMetrics, build_pose_estimator, scale_drift_metrics
from .silhouette import SilhouetteMetrics, silhouette_metrics
from .texture import (
    TextureMetrics,
    build_flow_estimator,
    build_perceptual_metric,
    texture_metrics,
)

Method = Literal["turntable", "i2v"]

#: 지표 키 → 방향. `higher` = 클수록 좋다, `lower` = 작을수록 좋다.
#: `info` = 좋고 나쁨이 없는 신뢰도/진단 지표 — 승패 판정에서 제외한다.
METRIC_DIRECTIONS: dict[str, str] = {
    # 형태·핏 일관성
    "silhouette_iou_mean": "higher",
    "silhouette_iou_std": "lower",
    "silhouette_iou_min": "higher",
    "silhouette_area_cv": "lower",
    "edge_density_cv": "lower",
    "edge_iou_mean": "higher",
    "foreground_ratio_mean": "info",
    # 스케일 드리프트
    "scale_height_cv": "lower",
    "scale_height_drift": "lower",
    "scale_shoulder_ratio_cv": "lower",
    "scale_missing_ratio": "info",
    # 텍스처 안정성
    "texture_flow_residual_mean": "lower",
    "texture_flow_residual_std": "lower",
    "texture_perceptual_mean": "lower",
    "texture_perceptual_flicker": "lower",
    "texture_direction_flip_ratio": "lower",
    "texture_symmetry_error": "lower",
    # identity
    "identity_cosine_mean": "higher",
    "identity_cosine_min": "higher",
    "identity_vs_reference_mean": "higher",
    "identity_vs_reference_last": "higher",
    "identity_detect_ratio": "info",
}


@dataclass
class SequenceEvaluation:
    """한 시퀀스(방식 하나)의 전체 지표."""

    case_id: str
    method: str
    silhouette: SilhouetteMetrics
    scale: ScaleDriftMetrics
    texture: TextureMetrics
    identity: IdentityMetrics | None
    num_frames: int
    resolution: tuple[int, int]
    #: 임계치·백엔드·프레임수 불일치 등. **숫자를 읽기 전에 봐야 한다.**
    warnings: list[str] = field(default_factory=list)

    def as_row(self) -> dict[str, float]:
        """리포트 표 한 줄. identity 를 못 잰 경우 그 키들은 **빠진다**(0 이 아니다)."""
        row: dict[str, float] = {}
        row.update(self.silhouette.as_row())
        row.update(self.scale.as_row())
        row.update(self.texture.as_row())
        if self.identity is not None:
            row.update(self.identity.as_row())
        return row

    def backend_note(self) -> str:
        return (
            f"flow={self.texture.flow_backend}, "
            f"perceptual={self.texture.perceptual_backend}, "
            f"identity={'off' if self.identity is None else self.identity.backend}"
        )


def evaluate_sequence(
    frames: np.ndarray,
    config: EvalConfig,
    *,
    case_id: str,
    method: str,
    reference: np.ndarray | None = None,
) -> SequenceEvaluation:
    """프레임 시퀀스 하나를 전 지표로 측정한다."""
    frames = np.asarray(frames)
    if frames.ndim != 4:
        raise ValueError(f"frames 형태가 (T, H, W, 3) 이 아닙니다: {frames.shape}")

    warnings: list[str] = []
    masks = frames_to_masks(frames, threshold=config.background_threshold)
    foreground = float(masks.mean())
    if foreground < 0.01 or foreground > 0.99:
        warnings.append(
            f"전경 비율 {foreground:.3f} — background_threshold"
            f"({config.background_threshold}) 가 이 시퀀스에 맞지 않습니다. "
            "실루엣·스케일 지표를 신뢰하지 마세요."
        )

    silhouette = silhouette_metrics(frames, masks)

    pose = build_pose_estimator(config.pose_backend)
    keypoints = pose.estimate_sequence(frames, masks)
    scale = scale_drift_metrics(keypoints)
    if scale.missing_ratio > 0.2:
        warnings.append(f"keypoint 미검출 {scale.missing_ratio:.0%} — 스케일 지표 신뢰도 낮음")

    texture = texture_metrics(
        frames,
        flow_estimator=build_flow_estimator(config.flow_backend),
        perceptual=build_perceptual_metric(config.perceptual_backend),
        symmetry_offset=config.symmetry_offset,
    )
    if texture.flow_backend == "dummy":
        warnings.append(
            "flow_backend=dummy — flow_residual 은 raw 프레임 차분입니다"
            "(회전에 의한 변화가 제거되지 않았습니다)."
        )

    identity: IdentityMetrics | None = None
    if config.measure_identity:
        identity = identity_metrics(
            frames, embedder=build_face_embedder(config.face_backend), reference=reference
        )
        if identity is None:
            warnings.append("얼굴 임베딩을 얻지 못해 identity 지표를 생략했습니다")

    return SequenceEvaluation(
        case_id=case_id,
        method=method,
        silhouette=silhouette,
        scale=scale,
        texture=texture,
        identity=identity,
        num_frames=int(len(frames)),
        resolution=(int(frames.shape[1]), int(frames.shape[2])),
        warnings=warnings,
    )


def better(metric: str, left: float, right: float) -> int:
    """`left` 가 더 좋으면 1, `right` 가 더 좋으면 -1, 동일/판정불가면 0."""
    direction = METRIC_DIRECTIONS.get(metric, "info")
    if direction == "info" or left == right:
        return 0
    if direction == "higher":
        return 1 if left > right else -1
    return 1 if left < right else -1


@dataclass
class CaseComparison:
    """케이스 하나에 대한 turntable vs I2V."""

    case_id: str
    turntable: SequenceEvaluation
    i2v: SequenceEvaluation
    warnings: list[str] = field(default_factory=list)

    def metric_keys(self) -> list[str]:
        """양쪽 모두 값이 있는 지표만. 한쪽만 있는 지표로 비교하면 안 된다."""
        left, right = self.turntable.as_row(), self.i2v.as_row()
        return sorted(set(left) & set(right))

    def rows(self) -> dict[str, dict[str, float]]:
        """`{지표: {"turntable": v, "i2v": v, "delta": t - i}}`"""
        left, right = self.turntable.as_row(), self.i2v.as_row()
        return {
            key: {
                "turntable": left[key],
                "i2v": right[key],
                "delta": left[key] - right[key],
            }
            for key in self.metric_keys()
        }

    def winners(self) -> dict[str, str]:
        """지표별 승자. `info` 지표는 `"n/a"`."""
        left, right = self.turntable.as_row(), self.i2v.as_row()
        out = {}
        for key in self.metric_keys():
            verdict = better(key, left[key], right[key])
            out[key] = {1: "turntable", -1: "i2v", 0: "tie"}[verdict]
            if METRIC_DIRECTIONS.get(key, "info") == "info":
                out[key] = "n/a"
        return out

    def tally(self) -> dict[str, int]:
        """승자 집계. **동점·판정불가를 따로 세어** 표본이 얇은 걸 감춘다."""
        counts = {"turntable": 0, "i2v": 0, "tie": 0, "n/a": 0}
        for winner in self.winners().values():
            counts[winner] += 1
        return counts

    def verdict(self) -> str:
        counts = self.tally()
        if counts["turntable"] == counts["i2v"]:
            return "tie"
        return "turntable" if counts["turntable"] > counts["i2v"] else "i2v"


def compare_case(
    case_id: str,
    turntable_frames: np.ndarray,
    i2v_frames: np.ndarray,
    config: EvalConfig,
    *,
    reference: np.ndarray | None = None,
    extra_warnings: list[str] | None = None,
) -> CaseComparison:
    """같은 케이스의 두 시퀀스를 같은 설정으로 측정하고 비교한다."""
    turntable_frames = np.asarray(turntable_frames)
    i2v_frames = np.asarray(i2v_frames)

    warnings = list(extra_warnings or [])
    if len(turntable_frames) != len(i2v_frames):
        warnings.append(
            f"프레임 수가 다릅니다 (turntable={len(turntable_frames)}, i2v={len(i2v_frames)}) — "
            "시간적 지표(플리커·IoU 변동)는 프레임 수에 민감하니 config 를 맞추세요."
        )
    if turntable_frames.shape[1:3] != i2v_frames.shape[1:3]:
        warnings.append(
            f"해상도가 다릅니다 (turntable={turntable_frames.shape[1:3]}, "
            f"i2v={i2v_frames.shape[1:3]}) — 엣지·잔차 지표가 해상도에 의존합니다."
        )

    return CaseComparison(
        case_id=case_id,
        turntable=evaluate_sequence(
            turntable_frames, config, case_id=case_id, method="turntable", reference=reference
        ),
        i2v=evaluate_sequence(
            i2v_frames, config, case_id=case_id, method="i2v", reference=reference
        ),
        warnings=warnings,
    )


def aggregate(comparisons: list[CaseComparison]) -> dict[str, Any]:
    """여러 케이스를 합산한다. 케이스별 승자 집계 + 지표별 평균 델타."""
    if not comparisons:
        return {"cases": 0, "verdicts": {}, "mean_delta": {}}

    verdicts: dict[str, int] = {}
    for comparison in comparisons:
        verdicts[comparison.verdict()] = verdicts.get(comparison.verdict(), 0) + 1

    delta_sums: dict[str, list[float]] = {}
    for comparison in comparisons:
        for key, values in comparison.rows().items():
            delta_sums.setdefault(key, []).append(values["delta"])

    return {
        "cases": len(comparisons),
        "verdicts": verdicts,
        "mean_delta": {k: float(np.mean(v)) for k, v in sorted(delta_sums.items())},
    }
