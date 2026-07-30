"""전처리 오케스트레이션 — 더미 샘플 한 건이 latent 까지 가는지, 실패가 예외 대신 결과인지."""

from __future__ import annotations

from pathlib import Path

import pytest

from garment3d.config import Config
from garment3d.data import make_dummy_index, make_dummy_sample, verify_index
from garment3d.preprocess import preprocess_index, preprocess_sample, summarize


def _config(tmp_path: Path, **overrides) -> Config:
    payload = {
        "paths": {
            "data_root": str(tmp_path / "data"),
            "cache_dir": str(tmp_path / "cache"),
        }
    }
    payload.update(overrides)
    return Config.from_dict(payload)


def test_dummy_sample_files_exist(tmp_path: Path):
    index = make_dummy_index(tmp_path / "data", count=2)
    assert verify_index(index) == {}
    assert len(index.samples) == 2


def test_verify_index_reports_missing_files(tmp_path: Path):
    index = make_dummy_index(tmp_path / "data", count=1)
    (tmp_path / "data" / index.samples[0].mesh_path).unlink()
    missing = verify_index(index)
    assert list(missing) == ["dummy_000"]
    assert missing["dummy_000"][0].endswith(".obj")


def test_preprocess_sample_reaches_latent(tmp_path: Path):
    config = _config(tmp_path)
    sample = make_dummy_sample(tmp_path / "data", "s1").resolve_paths(tmp_path / "data")
    result = preprocess_sample(sample, config)

    assert result.ok
    assert result.health is not None and result.health.is_watertight
    assert result.occupancy is not None and result.occupancy.num_active > 0
    assert result.latent is not None and result.latent.stage == "geometry"
    assert result.occupancy_path is not None and result.occupancy_path.is_file()
    assert result.latent_path is not None and result.latent_path.is_file()


def test_preprocess_no_cache_writes_nothing(tmp_path: Path):
    config = _config(tmp_path)
    sample = make_dummy_sample(tmp_path / "data", "s1").resolve_paths(tmp_path / "data")
    result = preprocess_sample(sample, config, write_cache=False)

    assert result.ok
    assert result.occupancy_path is None
    assert not (tmp_path / "cache").exists()


def test_sample_without_mesh_is_skipped_with_reason(tmp_path: Path):
    """예외를 던지지 않는다 — 배치에서 한 건이 실패해도 나머지가 계속 가야 한다."""
    config = _config(tmp_path)
    sample = make_dummy_sample(tmp_path / "data", "nomesh", with_mesh=False).resolve_paths(
        tmp_path / "data"
    )
    result = preprocess_sample(sample, config)

    assert not result.ok
    assert result.occupancy is None
    assert any("mesh_path" in reason for reason in result.reasons)


def test_open_surface_sample_is_recorded(tmp_path: Path):
    """수선 라이브러리가 없어도 진행하지만, 무슨 일이 있었는지 남긴다."""
    config = _config(tmp_path)
    sample = make_dummy_sample(tmp_path / "data", "open", open_surface=True).resolve_paths(
        tmp_path / "data"
    )
    result = preprocess_sample(sample, config)

    assert result.ok
    assert result.reasons, "열린 메시였다는 기록이 남아야 한다"


def test_min_active_voxels_failure_is_a_result_not_an_exception(tmp_path: Path):
    config = _config(tmp_path, preprocess={"min_active_voxels": 10**9})
    sample = make_dummy_sample(tmp_path / "data", "s1").resolve_paths(tmp_path / "data")
    result = preprocess_sample(sample, config)

    assert not result.ok
    assert any("복셀화 실패" in reason for reason in result.reasons)


def test_summarize_counts_supervision_availability(tmp_path: Path):
    config = _config(tmp_path)
    root = tmp_path / "data"
    samples = [
        make_dummy_sample(root, "with_extrinsics").resolve_paths(root),
        make_dummy_sample(root, "no_extrinsics", with_extrinsics=False).resolve_paths(root),
        make_dummy_sample(root, "no_mesh", with_mesh=False).resolve_paths(root),
    ]
    summary = summarize(preprocess_index(samples, config))

    assert summary["total"] == 3
    assert summary["ok"] == 2
    assert summary["failed"] == 1
    assert summary["layout_supervisable"] == 1
    # SLat 인코더가 없으므로 texture 감독은 0 이어야 한다 (REPORT.md §5).
    assert summary["texture_supervisable"] == 0


def test_target_faces_upsamples(tmp_path: Path):
    config = _config(tmp_path, preprocess={"target_faces": 48})
    sample = make_dummy_sample(tmp_path / "data", "s1").resolve_paths(tmp_path / "data")
    result = preprocess_sample(sample, config, write_cache=False)
    assert result.ok
    assert result.occupancy is not None


def test_texture_stage_config_marks_availability(tmp_path: Path):
    """`latent_encoder=sam3d_slat` 로 두면 audit 은 texture 가능이라 보고, 인코딩에서 막힌다."""
    config = _config(tmp_path, preprocess={"latent_encoder": "sam3d_slat"})
    sample = make_dummy_sample(tmp_path / "data", "s1").resolve_paths(tmp_path / "data")
    with pytest.raises(NotImplementedError):
        preprocess_sample(sample, config, write_cache=False)
