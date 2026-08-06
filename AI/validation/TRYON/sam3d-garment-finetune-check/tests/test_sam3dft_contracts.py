"""데이터 컨트랙트 — 스키마 검증과 감독 가능성 판정.

무거운 의존성이 없다(pydantic 만 쓴다) → CI 에서 그대로 돈다.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from garment3d.contracts import (
    Camera,
    CameraExtrinsics,
    CameraIntrinsics,
    GarmentCategory,
    GarmentSample,
    GarmentSampleIndex,
    PreferencePair,
    audit_sample,
)


def _sample(**overrides) -> GarmentSample:
    payload = {
        "sample_id": "s001",
        "image_path": Path("images/s001.png"),
        "garment_mask_path": Path("masks/s001.png"),
        "mesh_path": Path("meshes/s001.obj"),
    }
    payload.update(overrides)
    return GarmentSample(**payload)


def test_sample_id_must_not_be_blank():
    with pytest.raises(ValidationError):
        _sample(sample_id="   ")


def test_unknown_field_is_rejected():
    """스키마 오타를 조용히 통과시키면 데이터 주입 단계에서 디버깅이 불가능해진다."""
    with pytest.raises(ValidationError):
        _sample(mesh_pathh=Path("x.obj"))


def test_intrinsics_reject_nonpositive_focal():
    with pytest.raises(ValidationError):
        CameraIntrinsics(fx=0.0, fy=100.0, cx=1.0, cy=1.0, width=10, height=10)


def test_extrinsics_reject_zero_quaternion():
    with pytest.raises(ValidationError):
        CameraExtrinsics(rotation_quat=[0.0, 0.0, 0.0, 0.0])


def test_resolve_paths_makes_absolute_and_keeps_none(tmp_path: Path):
    # 절대경로 판정은 플랫폼 의존이라(Windows 는 드라이브 문자가 필요) tmp_path 를 기준으로 쓴다.
    sample = _sample(mesh_path=None)
    resolved = sample.resolve_paths(tmp_path)
    assert resolved.image_path.is_absolute()
    assert resolved.image_path == tmp_path / "images" / "s001.png"
    assert resolved.mesh_path is None
    # 원본은 그대로여야 한다(model_copy 라서).
    assert not sample.image_path.is_absolute()


def test_resolve_paths_leaves_absolute_untouched(tmp_path: Path):
    absolute = (tmp_path / "already" / "img.png").resolve()
    sample = _sample(image_path=absolute)
    assert sample.resolve_paths(tmp_path / "other").image_path == absolute


def test_audit_full_supervision_requires_extrinsics_and_slat():
    sample = _sample(
        camera=Camera(
            intrinsics=CameraIntrinsics(fx=1.0, fy=1.0, cx=0.0, cy=0.0, width=4, height=4),
            extrinsics=CameraExtrinsics(),
        )
    )
    availability = audit_sample(sample, slat_encoder_available=True)
    assert (availability.geometry, availability.layout, availability.texture) == (True, True, True)
    assert availability.trainable


def test_audit_without_mesh_blocks_everything():
    availability = audit_sample(_sample(mesh_path=None))
    assert not availability.paired_image_mesh
    assert not availability.geometry
    assert not availability.trainable
    assert any("mesh_path" in note for note in availability.notes)


def test_audit_without_extrinsics_blocks_layout_only():
    availability = audit_sample(_sample(camera=Camera(intrinsics=None, extrinsics=None)))
    assert availability.geometry
    assert not availability.layout
    assert any("extrinsic" in note for note in availability.notes)


def test_audit_texture_blocked_by_default():
    """SLat 인코더가 릴리스에 없다 — 기본값이 '텍스처 감독 불가'여야 한다 (REPORT.md §5)."""
    availability = audit_sample(_sample())
    assert not availability.texture
    assert any("SLat" in note for note in availability.notes)


def test_index_jsonl_roundtrip(tmp_path: Path):
    index = GarmentSampleIndex(
        root=tmp_path,
        samples=[_sample(sample_id="a"), _sample(sample_id="b", category=GarmentCategory.OUTER)],
    )
    path = index.to_jsonl(tmp_path / "index.jsonl")
    restored = GarmentSampleIndex.from_jsonl(path, root=tmp_path)

    assert [s.sample_id for s in restored.samples] == ["a", "b"]
    assert restored.samples[1].category is GarmentCategory.OUTER
    assert all(s.image_path.is_absolute() for s in restored.resolved())


def test_index_jsonl_empty(tmp_path: Path):
    path = GarmentSampleIndex(root=tmp_path).to_jsonl(tmp_path / "empty.jsonl")
    assert GarmentSampleIndex.from_jsonl(path).samples == []


def test_preference_pair_margin_and_nan_guard(tmp_path: Path):
    pair = PreferencePair(
        sample_id="s",
        chosen_path=tmp_path / "a",
        rejected_path=tmp_path / "b",
        chosen_score=0.9,
        rejected_score=0.4,
    )
    assert pair.margin == pytest.approx(0.5)

    with pytest.raises(ValidationError):
        PreferencePair(
            sample_id="s",
            chosen_path=tmp_path / "a",
            rejected_path=tmp_path / "b",
            chosen_score=0.9,
            rejected_score=float("nan"),
        )
