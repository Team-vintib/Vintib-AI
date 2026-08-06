"""렌더 — 합성 시퀀스가 결함에 실제로 반응하는지, 프레임 정규화, 저장 형식."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from garment3d.config import RenderConfig
from garment3d.render.synthetic import SyntheticDefects, frames_to_masks, synth_i2v, synth_turntable
from garment3d.render.turntable import (
    DummyTurntableRenderer,
    RenderError,
    _as_uint8_frames,
    build_renderer,
)
from garment3d.render.video import load_png_sequence, save_frames, write_gif, write_png_sequence


def test_synth_turntable_shape_and_dtype():
    frames = synth_turntable(num_frames=8, resolution=32)
    assert frames.shape == (8, 32, 32, 3)
    assert frames.dtype == np.uint8


def test_ideal_turntable_has_stable_vertical_extent():
    """세로 크기는 회전 불변이어야 한다 — 이게 스케일 드리프트 지표의 기준선이다."""
    masks = frames_to_masks(synth_turntable(num_frames=12, resolution=64))
    heights = [int(np.ptp(np.nonzero(m.any(axis=1))[0])) for m in masks]
    assert len(set(heights)) == 1


def test_ideal_turntable_width_varies_with_yaw():
    """얇은 의류라 정면이 넓고 측면이 좁아야 한다 — 안 변하면 회전을 모사하지 못한 것."""
    masks = frames_to_masks(synth_turntable(num_frames=12, resolution=64))
    widths = [int(m.any(axis=0).sum()) for m in masks]
    assert max(widths) > min(widths) * 1.5


def test_scale_drift_defect_grows_silhouette():
    clean = frames_to_masks(synth_turntable(num_frames=12, resolution=64))
    drifted = frames_to_masks(
        synth_turntable(num_frames=12, resolution=64, defects=SyntheticDefects(scale_drift=0.5))
    )

    def _height(mask):
        return int(np.ptp(np.nonzero(mask.any(axis=1))[0]))

    assert _height(drifted[-1]) > _height(drifted[0])
    assert _height(clean[-1]) == _height(clean[0])


def test_flicker_defect_increases_frame_to_frame_difference():
    clean = synth_turntable(num_frames=12, resolution=48).astype(np.float64)
    noisy = synth_turntable(
        num_frames=12, resolution=48, defects=SyntheticDefects(flicker=0.3)
    ).astype(np.float64)
    assert np.abs(np.diff(noisy, axis=0)).mean() > np.abs(np.diff(clean, axis=0)).mean()


def test_reverse_defect_flips_frame_order():
    forward = synth_turntable(num_frames=8, resolution=32)
    backward = synth_turntable(num_frames=8, resolution=32, defects=SyntheticDefects(reverse=True))
    # 첫 프레임(yaw=0)은 같고, 두 번째부터 회전 방향이 갈린다.
    assert np.array_equal(forward[0], backward[0])
    assert not np.array_equal(forward[1], backward[1])


def test_synth_turntable_is_deterministic():
    left = synth_turntable(num_frames=6, resolution=32, seed=7)
    right = synth_turntable(num_frames=6, resolution=32, seed=7)
    assert np.array_equal(left, right)


def test_frames_to_masks_threshold_effect():
    frames = synth_turntable(num_frames=4, resolution=32)
    assert frames_to_masks(frames, threshold=12).mean() > 0
    # 임계치를 최대로 올리면 전경이 사라진다 — 임계치 오설정을 감지하는 근거.
    assert frames_to_masks(frames, threshold=255).sum() == 0


def test_frames_to_masks_rejects_wrong_shape():
    with pytest.raises(ValueError):
        frames_to_masks(np.zeros((4, 8, 8)))


def test_synth_i2v_keeps_first_frame_identical():
    """I2V 는 첫 프레임을 입력으로 받는다 — 그 프레임은 그대로여야 한다."""
    first = synth_turntable(num_frames=4, resolution=32)[0]
    frames = synth_i2v(first, num_frames=6)
    assert frames.shape == (6, 32, 32, 3)
    assert np.array_equal(frames[0], first)


def test_dummy_renderer_honors_config():
    config = RenderConfig(num_frames=10, resolution=48)
    frames = DummyTurntableRenderer().render(0, config)
    assert frames.shape == (10, 48, 48, 3)


def test_dummy_renderer_seed_from_string_is_process_stable():
    """내장 hash() 를 쓰면 프로세스마다 그림이 달라져 재현이 깨진다 — sha256 이어야 한다."""
    import hashlib

    config = RenderConfig(num_frames=4, resolution=32)
    frames = DummyTurntableRenderer().render("sample_a", config)
    expected_seed = int.from_bytes(hashlib.sha256(b"sample_a").digest()[:4], "little")
    assert np.array_equal(
        frames, synth_turntable(4, 32, yaw_start_deg=config.yaw_start_deg, seed=expected_seed)
    )


def test_build_renderer_dummy_and_errors(tmp_path: Path):
    assert build_renderer(RenderConfig(backend="dummy")).name == "dummy"
    with pytest.raises(RenderError, match="sam3d_repo"):
        build_renderer(RenderConfig(backend="sam3d"), None)


def test_sam3d_renderer_import_failure_is_explicit(tmp_path: Path):
    """리포가 없으면 명확히 실패해야 한다 — 조용히 더미로 떨어지면 안 된다."""
    from garment3d.render.turntable import Sam3dTurntableRenderer

    renderer = Sam3dTurntableRenderer(tmp_path / "missing-repo")
    with pytest.raises(RenderError, match="notebook"):
        renderer.render({}, RenderConfig())


def test_as_uint8_frames_normalizes_float_zero_to_one():
    frames = _as_uint8_frames(np.ones((2, 4, 4, 3), dtype=np.float32))
    assert frames.dtype == np.uint8
    assert frames.max() == 255


def test_as_uint8_frames_keeps_float_already_in_255_range():
    source = np.full((2, 4, 4, 3), 128.0)
    assert _as_uint8_frames(source).max() == 128


def test_as_uint8_frames_transposes_channel_first():
    frames = _as_uint8_frames(np.zeros((2, 3, 8, 6), dtype=np.uint8))
    assert frames.shape == (2, 8, 6, 3)


def test_as_uint8_frames_drops_alpha():
    frames = _as_uint8_frames(np.zeros((2, 4, 4, 4), dtype=np.uint8))
    assert frames.shape[-1] == 3


def test_png_sequence_roundtrip(tmp_path: Path):
    frames = synth_turntable(num_frames=5, resolution=32)
    write_png_sequence(frames, tmp_path / "seq")
    restored = load_png_sequence(tmp_path / "seq")
    assert np.array_equal(restored, frames)


def test_load_png_sequence_missing_dir(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_png_sequence(tmp_path / "nope")


def test_write_gif_uses_pillow_only(tmp_path: Path):
    path = write_gif(synth_turntable(num_frames=4, resolution=32), tmp_path / "a.gif")
    assert path.is_file() and path.stat().st_size > 0


def test_write_gif_rejects_empty():
    with pytest.raises(ValueError):
        write_gif(np.zeros((0, 4, 4, 3), dtype=np.uint8), Path("x.gif"))


def test_save_frames_records_skipped_formats(tmp_path: Path):
    """mp4 는 imageio-ffmpeg 가 없으면 못 쓴다 — 조용히 넘기지 않고 남겨야 한다."""
    frames = synth_turntable(num_frames=4, resolution=32)
    result = save_frames(frames, tmp_path, "case", fps=8)

    assert result.png_dir is not None and result.png_dir.is_dir()
    assert result.gif_path is not None and result.gif_path.is_file()
    if result.mp4_path is None:
        assert any(note.startswith("mp4:") for note in result.skipped)
