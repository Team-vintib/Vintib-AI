"""평가 지표 — **지표가 결함에 실제로 반응하는지**를 결함 주입 시퀀스로 확인한다.

지표가 항상 같은 값을 뱉어도 "계산은 됐다" 수준의 테스트는 통과한다. 그래서 여기서는
결함 있는 시퀀스와 없는 시퀀스를 비교해 **부호와 방향**을 검증한다.
"""

from __future__ import annotations

import numpy as np
import pytest

from garment3d.config import EvalConfig
from garment3d.eval.harness import (
    METRIC_DIRECTIONS,
    aggregate,
    better,
    compare_case,
    evaluate_sequence,
)
from garment3d.eval.identity import PatchFaceEmbedder, cosine, identity_metrics
from garment3d.eval.pose_scale import (
    Keypoints2d,
    MaskPoseEstimator,
    build_pose_estimator,
    scale_drift_metrics,
)
from garment3d.eval.silhouette import edge_map, mask_iou, silhouette_metrics
from garment3d.eval.texture import (
    L2PerceptualMetric,
    ZeroFlowEstimator,
    rotation_direction_flips,
    rotation_symmetry_error,
    texture_metrics,
    warp_with_flow,
)
from garment3d.render.synthetic import SyntheticDefects, frames_to_masks, synth_turntable

_RES = 64
_FRAMES = 12


def _sequence(**defect_kwargs):
    defects = SyntheticDefects(**defect_kwargs) if defect_kwargs else None
    frames = synth_turntable(num_frames=_FRAMES, resolution=_RES, defects=defects)
    return frames, frames_to_masks(frames)


# ── 실루엣 ───────────────────────────────────────────────────────────────────


def test_mask_iou_basics():
    a = np.zeros((4, 4), dtype=bool)
    a[:2] = True
    assert mask_iou(a, a) == 1.0
    assert mask_iou(a, ~a) == 0.0
    # 둘 다 비면 "완전 일치"로 본다(0으로 나누지 않는다).
    assert mask_iou(np.zeros((4, 4), bool), np.zeros((4, 4), bool)) == 1.0


def test_edge_map_finds_boundary_and_ignores_flat():
    flat = np.zeros((16, 16, 3), dtype=np.uint8)
    assert edge_map(flat).sum() == 0

    block = np.zeros((16, 16, 3), dtype=np.uint8)
    block[4:12, 4:12] = 200
    edges = edge_map(block)
    assert edges.sum() > 0
    # 엣지는 경계에 있고 내부 중심에는 없어야 한다.
    assert not edges[8, 8]


def test_silhouette_metrics_shape_and_range():
    frames, masks = _sequence()
    metrics = silhouette_metrics(frames, masks)
    assert metrics.num_frames == _FRAMES
    assert 0.0 <= metrics.consecutive_iou_mean <= 1.0
    assert 0.0 < metrics.foreground_ratio_mean < 1.0
    assert set(metrics.as_row()) <= set(METRIC_DIRECTIONS)


def test_silhouette_area_cv_responds_to_scale_drift():
    _, clean = _sequence()
    _, drifted = _sequence(scale_drift=0.6)
    clean_frames, _ = _sequence()
    drift_frames, _ = _sequence(scale_drift=0.6)

    assert (
        silhouette_metrics(drift_frames, drifted).area_cv
        > silhouette_metrics(clean_frames, clean).area_cv
    )


def test_silhouette_metrics_reject_length_mismatch():
    frames, masks = _sequence()
    with pytest.raises(ValueError, match="프레임 수"):
        silhouette_metrics(frames, masks[:-1])


def test_silhouette_metrics_reject_single_frame():
    frames, masks = _sequence()
    with pytest.raises(ValueError, match="2장 이상"):
        silhouette_metrics(frames[:1], masks[:1])


# ── 스케일 드리프트 ──────────────────────────────────────────────────────────


def test_mask_pose_estimator_finds_extents():
    _, masks = _sequence()
    keypoints = MaskPoseEstimator().estimate(None, masks[0])
    assert keypoints.body_height is not None and keypoints.body_height > 0
    assert keypoints.shoulder_width is not None and keypoints.shoulder_width > 0


def test_mask_pose_estimator_handles_empty_mask():
    empty = np.zeros((16, 16), dtype=bool)
    keypoints = MaskPoseEstimator().estimate(None, empty)
    assert keypoints.body_height is None
    assert keypoints.shoulder_width is None


def test_mask_pose_estimator_requires_mask():
    with pytest.raises(ValueError, match="mask"):
        MaskPoseEstimator().estimate(np.zeros((4, 4, 3), dtype=np.uint8), None)


def test_height_cv_is_near_zero_for_ideal_turntable():
    """세로 스케일은 회전 불변 — 이상적 턴테이블에서 0 이어야 한다."""
    frames, masks = _sequence()
    estimator = MaskPoseEstimator()
    metrics = scale_drift_metrics(estimator.estimate_sequence(frames, masks))
    assert metrics.height_cv == pytest.approx(0.0, abs=1e-9)
    assert metrics.height_drift == pytest.approx(0.0, abs=1e-9)
    assert metrics.missing_ratio == 0.0


def test_height_drift_detects_growing_subject():
    frames, masks = _sequence(scale_drift=0.5)
    metrics = scale_drift_metrics(MaskPoseEstimator().estimate_sequence(frames, masks))
    assert metrics.height_drift > 0.2
    assert metrics.height_cv > 0.05


def test_shoulder_ratio_cv_normalizes_out_rotation():
    """어깨너비는 회전에 따라 실제로 변한다 — 키로 정규화한 비율의 변동만 본다.

    이상적 턴테이블에서도 이 값은 0 이 아니다(어깨너비가 실제로 변하니까). 대신 **드리프트가
    있을 때 더 커지지 않아야** 한다 — 스케일 드리프트는 비율에 영향을 주지 않으므로.
    """
    clean_frames, clean_masks = _sequence()
    drift_frames, drift_masks = _sequence(scale_drift=0.5)
    estimator = MaskPoseEstimator()

    clean = scale_drift_metrics(estimator.estimate_sequence(clean_frames, clean_masks))
    drifted = scale_drift_metrics(estimator.estimate_sequence(drift_frames, drift_masks))

    assert clean.shoulder_height_ratio_cv > 0
    assert drifted.shoulder_height_ratio_cv == pytest.approx(
        clean.shoulder_height_ratio_cv, rel=0.35
    )


def test_scale_metrics_report_missing_keypoints():
    keypoints = [
        Keypoints2d(None, None, None, None),
        Keypoints2d((0.0, 0.0), (10.0, 0.0), (5.0, 0.0), (5.0, 50.0)),
        Keypoints2d((0.0, 0.0), (10.0, 0.0), (5.0, 0.0), (5.0, 50.0)),
    ]
    metrics = scale_drift_metrics(keypoints)
    assert metrics.missing_ratio == pytest.approx(1 / 3)
    assert metrics.height_cv == 0.0


def test_scale_metrics_reject_single_frame():
    with pytest.raises(ValueError, match="2장 이상"):
        scale_drift_metrics([Keypoints2d(None, None, None, None)])


def test_build_pose_estimator_unknown():
    with pytest.raises(ValueError, match="pose 백엔드"):
        build_pose_estimator("vitpose")


# ── 텍스처 안정성 ────────────────────────────────────────────────────────────


def test_warp_with_zero_flow_is_identity():
    frame = synth_turntable(num_frames=1, resolution=16)[0]
    warped, valid = warp_with_flow(frame, np.zeros((16, 16, 2)))
    assert valid.all()
    assert np.allclose(warped, frame)


def test_warp_with_constant_flow_shifts_and_marks_invalid():
    frame = np.arange(16 * 16, dtype=np.float64).reshape(16, 16)
    flow = np.zeros((16, 16, 2))
    flow[..., 0] = 2.0  # dx = +2 → 소스는 왼쪽 2px
    warped, valid = warp_with_flow(frame, flow)

    assert np.allclose(warped[:, 5], frame[:, 3])
    # 왼쪽 2열은 화면 밖에서 왔으므로 유효하지 않다.
    assert not valid[:, 0].any()
    assert valid[:, 5].all()


def test_texture_metrics_flag_dummy_flow_backend():
    frames, _ = _sequence()
    metrics = texture_metrics(frames)
    assert metrics.flow_backend == "dummy"
    assert metrics.perceptual_backend == "l2"
    assert set(metrics.as_row()) <= set(METRIC_DIRECTIONS)


def test_flicker_increases_perceptual_variation():
    clean, _ = _sequence()
    noisy, _ = _sequence(flicker=0.35)
    assert (
        texture_metrics(noisy).temporal_perceptual_std
        > texture_metrics(clean).temporal_perceptual_std
    )


def test_flow_residual_increases_with_flicker():
    clean, _ = _sequence()
    noisy, _ = _sequence(flicker=0.35)
    assert texture_metrics(noisy).flow_residual_mean > texture_metrics(clean).flow_residual_mean


def test_symmetry_error_is_small_for_ideal_turntable():
    """좌우 대칭 관계는 이상적 턴테이블에서 성립하고, 정체성 붕괴가 있으면 깨진다."""
    clean, _ = _sequence()
    broken, _ = _sequence(identity_shift=1.0, jitter=3.0)
    assert rotation_symmetry_error(clean) < rotation_symmetry_error(broken)


def test_symmetry_error_rejects_single_frame():
    with pytest.raises(ValueError, match="2장 이상"):
        rotation_symmetry_error(synth_turntable(num_frames=1, resolution=8))


def test_direction_flips_undetermined_with_zero_flow():
    """ZeroFlow 로는 방향을 판정할 수 없다 — 0.0 은 "뒤집힘 없음"이 아니라 "판정 불가"다."""
    flows = [np.zeros((8, 8, 2)) for _ in range(4)]
    assert rotation_direction_flips(flows) == 0.0


def test_direction_flips_counts_minority_reversals():
    flows = [np.full((4, 4, 2), 1.0) for _ in range(3)]
    flows.append(np.full((4, 4, 2), -1.0))
    assert rotation_direction_flips(flows) == pytest.approx(0.25)


def test_direction_flips_ignores_subthreshold_noise():
    flows = [np.full((4, 4, 2), 0.001) for _ in range(4)]
    assert rotation_direction_flips(flows, min_magnitude=0.05) == 0.0


def test_l2_perceptual_is_zero_for_identical_frames():
    frame = synth_turntable(num_frames=1, resolution=16)[0]
    assert L2PerceptualMetric().distance(frame, frame) == 0.0


def test_zero_flow_estimator_shape():
    frame = synth_turntable(num_frames=2, resolution=16)
    flow = ZeroFlowEstimator().estimate(frame[0], frame[1])
    assert flow.shape == (16, 16, 2)


# ── identity ─────────────────────────────────────────────────────────────────


def test_cosine_edge_cases():
    assert cosine(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == pytest.approx(1.0)
    assert cosine(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(0.0)
    assert cosine(np.zeros(3), np.ones(3)) == 0.0


def test_identity_metrics_high_for_stable_face():
    frames, _ = _sequence()
    metrics = identity_metrics(frames)
    assert metrics is not None
    assert metrics.detect_ratio == 1.0
    assert metrics.consecutive_cosine_mean > 0.9
    assert set(metrics.as_row()) <= set(METRIC_DIRECTIONS)


def test_identity_metrics_drop_when_face_region_changes():
    stable, _ = _sequence()
    shifting, _ = _sequence(identity_shift=1.0)
    stable_metrics = identity_metrics(stable)
    shifting_metrics = identity_metrics(shifting)
    assert stable_metrics is not None and shifting_metrics is not None
    assert shifting_metrics.consecutive_cosine_mean < stable_metrics.consecutive_cosine_mean


def test_identity_metrics_return_none_when_no_embedding():
    """0 으로 채우면 "정체성이 완전히 무너졌다"로 오독된다 — None 이어야 한다."""

    class NeverEmbeds(PatchFaceEmbedder):
        def embed(self, frame):
            return None

    frames, _ = _sequence()
    assert identity_metrics(frames, embedder=NeverEmbeds()) is None


def test_patch_embedder_handles_tiny_frames():
    """작은 프레임에서 8x8 그리드를 강행하면 nan 이 섞여 코사인이 조용히 0 이 된다."""
    tiny = np.full((6, 6, 3), 100, dtype=np.uint8)
    embedding = PatchFaceEmbedder().embed(tiny)
    assert embedding is None or np.isfinite(embedding).all()


# ── 하네스 ───────────────────────────────────────────────────────────────────


def test_metric_directions_cover_every_reported_key():
    """지표를 추가하고 방향을 등록하지 않으면 승패 판정에서 조용히 빠진다."""
    frames, _ = _sequence()
    evaluation = evaluate_sequence(frames, EvalConfig(), case_id="c", method="turntable")
    assert set(evaluation.as_row()) <= set(METRIC_DIRECTIONS)
    assert set(evaluation.as_row())  # 비어 있지 않다


def test_better_respects_direction():
    assert better("silhouette_iou_mean", 0.9, 0.5) == 1  # higher
    assert better("silhouette_area_cv", 0.01, 0.2) == 1  # lower
    assert better("silhouette_area_cv", 0.2, 0.01) == -1
    assert better("foreground_ratio_mean", 0.9, 0.1) == 0  # info
    assert better("silhouette_iou_mean", 0.5, 0.5) == 0


def test_evaluate_sequence_warns_on_bad_threshold():
    frames, _ = _sequence()
    evaluation = evaluate_sequence(
        frames, EvalConfig(background_threshold=254), case_id="c", method="i2v"
    )
    assert any("전경 비율" in warning for warning in evaluation.warnings)


def test_evaluate_sequence_rejects_wrong_dims():
    with pytest.raises(ValueError, match=r"\(T, H, W, 3\)"):
        evaluate_sequence(np.zeros((4, 8, 8)), EvalConfig(), case_id="c", method="i2v")


def test_evaluate_sequence_can_disable_identity():
    frames, _ = _sequence()
    evaluation = evaluate_sequence(
        frames, EvalConfig(measure_identity=False), case_id="c", method="turntable"
    )
    assert evaluation.identity is None
    assert "identity_cosine_mean" not in evaluation.as_row()


def test_compare_case_prefers_turntable_over_degraded_i2v():
    """이 하네스의 존재 이유 — 결함이 많은 쪽이 실제로 지는지.

    ⚠️ `flicker` 는 여기서 일부러 빼 뒀다. 밝기 잡음이 세면 밝기 임계치 마스크가 배경까지
    전경으로 잡아 **실루엣 면적이 오히려 안정돼 보이는** 역전이 생긴다(그 상황은
    `foreground_ratio` 경고로 따로 감지한다). 형태·스케일·정체성 축만 두고 비교한다.
    """
    turntable, _ = _sequence()
    degraded, _ = _sequence(scale_drift=0.5, identity_shift=1.0, jitter=2.0)
    comparison = compare_case("case1", turntable, degraded, EvalConfig())

    tally = comparison.tally()
    assert tally["turntable"] > tally["i2v"]
    assert comparison.verdict() == "turntable"
    # 스케일 드리프트는 낮을수록 좋다 → 턴테이블이 더 작아야 하므로 델타가 음수다.
    assert comparison.rows()["scale_height_drift"]["delta"] < 0
    assert comparison.winners()["scale_height_drift"] == "turntable"


def test_compare_case_warns_on_frame_count_mismatch():
    turntable, _ = _sequence()
    short = synth_turntable(num_frames=6, resolution=_RES)
    comparison = compare_case("case1", turntable, short, EvalConfig())
    assert any("프레임 수" in warning for warning in comparison.warnings)


def test_compare_case_warns_on_resolution_mismatch():
    turntable, _ = _sequence()
    small = synth_turntable(num_frames=_FRAMES, resolution=32)
    comparison = compare_case("case1", turntable, small, EvalConfig())
    assert any("해상도" in warning for warning in comparison.warnings)


def test_winners_marks_info_metrics_as_na():
    turntable, _ = _sequence()
    degraded, _ = _sequence(flicker=0.3)
    winners = compare_case("c", turntable, degraded, EvalConfig()).winners()
    assert winners["foreground_ratio_mean"] == "n/a"


def test_aggregate_empty_and_populated():
    assert aggregate([])["cases"] == 0

    turntable, _ = _sequence()
    degraded, _ = _sequence(flicker=0.3)
    comparisons = [
        compare_case("a", turntable, degraded, EvalConfig()),
        compare_case("b", turntable, degraded, EvalConfig()),
    ]
    summary = aggregate(comparisons)
    assert summary["cases"] == 2
    assert sum(summary["verdicts"].values()) == 2
    assert "silhouette_area_cv" in summary["mean_delta"]
