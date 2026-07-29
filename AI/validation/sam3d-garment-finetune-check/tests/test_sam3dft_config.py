"""config — 기본값·병합·오버라이드 파싱, 그리고 "기본값은 무과금" 규율."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from garment3d.config import Config, PathsConfig, parse_overrides

_PROJECT_DIR = Path(__file__).resolve().parent.parent


def test_defaults_are_all_free_backends():
    """기본 config 로는 GPU·외부 API·무거운 의존성이 필요하지 않아야 한다.

    이게 깨지면 CI 와 `make smoke` 가 조용히 과금·설치 경로를 타게 된다.
    """
    config = Config()
    assert config.preprocess.voxelizer == "numpy"
    assert config.preprocess.latent_encoder == "dummy"
    assert config.render.backend == "dummy"
    assert config.i2v.backend == "dummy"
    assert config.eval.pose_backend == "dummy"
    assert config.eval.flow_backend == "dummy"
    assert config.eval.perceptual_backend == "l2"
    assert config.eval.face_backend == "dummy"


def test_lora_default_targets_exclude_sparse_linear_modules():
    """SparseLinear 타깃은 PEFT 를 깨뜨린다 (REPORT.md §10) — 기본값에 없어야 한다."""
    targets = set(Config().lora.target_modules)
    assert targets == {"to_qkv", "to_q", "to_kv", "to_out"}
    assert not targets & {"mlp", "input_layer", "out_layer"}


def test_unknown_key_is_rejected():
    with pytest.raises(ValidationError):
        Config.from_dict({"preprocess": {"voxeliser": "numpy"}})


def test_invalid_backend_literal_is_rejected():
    with pytest.raises(ValidationError):
        Config.from_dict({"render": {"backend": "blender"}})


def test_merged_is_deep_and_non_mutating():
    config = Config()
    merged = config.merged({"sft": {"max_steps": 7}})
    assert merged.sft.max_steps == 7
    # 같은 섹션의 다른 키는 유지된다(얕은 교체가 아니다).
    assert merged.sft.learning_rate == config.sft.learning_rate
    assert config.sft.max_steps != 7


def test_parse_overrides_types_and_nesting():
    parsed = parse_overrides(
        [
            "sft.max_steps=5",
            "render.backend=dummy",
            "report.plots=false",
            "eval.symmetry_offset=null",
        ]
    )
    assert parsed == {
        "sft": {"max_steps": 5},
        "render": {"backend": "dummy"},
        "report": {"plots": False},
        "eval": {"symmetry_offset": None},
    }


def test_parse_overrides_rejects_malformed_pair():
    with pytest.raises(ValueError):
        parse_overrides(["sft.max_steps"])


def test_parse_overrides_roundtrips_into_config():
    config = Config().merged(parse_overrides(["sft.max_steps=3", "lora.rank=8"]))
    assert (config.sft.max_steps, config.lora.rank) == (3, 8)


def test_paths_expanded_resolves_tilde():
    paths = PathsConfig(sam3d_repo=Path("~/somewhere")).expanded()
    assert "~" not in str(paths.sam3d_repo)


def test_paths_expanded_keeps_none():
    assert PathsConfig(sample_index=None).expanded().sample_index is None


def test_pipeline_config_path_joins_relative_to_repo():
    paths = PathsConfig(sam3d_repo=Path("/repo"), sam3d_pipeline_config=Path("checkpoints/x.yaml"))
    assert paths.pipeline_config_path() == Path("/repo") / "checkpoints" / "x.yaml"


def test_pipeline_config_path_keeps_absolute(tmp_path: Path):
    """체크포인트는 리포 클론 밖에 받는 경우가 흔하다 — 절대경로를 그대로 통과시켜야 한다."""
    absolute = (tmp_path / "checkpoints" / "hf" / "pipeline.yaml").resolve()
    paths = PathsConfig(sam3d_repo=Path("/repo"), sam3d_pipeline_config=absolute)
    assert paths.pipeline_config_path() == absolute


def test_pipeline_config_path_expands_tilde():
    paths = PathsConfig(sam3d_repo=Path("~/clone"), sam3d_pipeline_config=Path("a/b.yaml"))
    assert "~" not in str(paths.pipeline_config_path())


def test_default_yaml_matches_schema():
    """`configs/default.yaml` 이 스키마와 어긋나면 CLI 가 런타임에만 터진다."""
    yaml = pytest.importorskip("yaml")  # noqa: F841 - from_yaml 이 내부에서 쓴다
    config = Config.from_yaml(_PROJECT_DIR / "configs" / "default.yaml")
    assert config.render.num_frames == config.i2v.num_frames


def test_real_backends_yaml_matches_schema():
    pytest.importorskip("yaml")
    config = Config.from_yaml(_PROJECT_DIR / "configs" / "real_backends.yaml")
    assert config.render.backend == "sam3d"
    # 과금 경로여도 endpoint 는 비어 있어야 한다(실수로 호출되지 않게).
    assert config.i2v.endpoint is None
