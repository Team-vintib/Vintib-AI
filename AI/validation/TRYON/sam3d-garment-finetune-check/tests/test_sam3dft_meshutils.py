"""메시 위생 — watertight 판정, 중복 정점, 정규화(upstream 식과 일치), subdivide/remesh."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from garment3d.data import Mesh, load_mesh, make_dummy_mesh, write_obj
from garment3d.preprocess.mesh_utils import (
    RepairUnavailableError,
    check_mesh,
    drop_degenerate_faces,
    is_normalized,
    merge_duplicate_vertices,
    normalize_mesh,
    remesh,
    subdivide,
)


def test_closed_box_is_watertight():
    health = check_mesh(make_dummy_mesh(seed=1))
    assert health.num_faces == 12
    assert health.is_watertight
    assert health.num_boundary_edges == 0
    assert health.is_clean


def test_open_surface_is_detected():
    """cloth 메시의 현실 — 한 면이 빠지면 경계 엣지가 생긴다."""
    health = check_mesh(make_dummy_mesh(seed=1, open_surface=True))
    assert not health.is_watertight
    assert health.num_boundary_edges == 4
    assert "NOT watertight" in health.summary()


def test_duplicate_vertices_cause_false_boundaries_and_merge_fixes_it():
    """정점이 중복되면 엣지가 공유되지 않아 멀쩡한 메시도 열린 것으로 잡힌다."""
    mesh = make_dummy_mesh(seed=2)
    # 모든 면을 자기 정점 복사본으로 재작성 → 위상적으로 완전히 분리된 삼각형 12개
    vertices = []
    faces = []
    for face in mesh.faces:
        base = len(vertices)
        vertices.extend(mesh.vertices[i] for i in face)
        faces.append([base, base + 1, base + 2])
    exploded = Mesh(np.asarray(vertices), np.asarray(faces, dtype=np.int64))

    assert not check_mesh(exploded).is_watertight
    assert check_mesh(exploded).num_duplicate_vertices > 0

    merged = merge_duplicate_vertices(exploded)
    assert check_mesh(merged).is_watertight
    assert len(merged.vertices) == 8
    assert len(merged.faces) == 12


def test_degenerate_faces_counted_and_dropped():
    mesh = make_dummy_mesh(seed=3)
    with_degenerate = Mesh(
        mesh.vertices, np.concatenate([mesh.faces, np.array([[0, 0, 1]], dtype=np.int64)])
    )
    assert check_mesh(with_degenerate).num_degenerate_faces == 1
    assert len(drop_degenerate_faces(with_degenerate).faces) == len(mesh.faces)


def test_normalize_matches_upstream_formula():
    """upstream `normalize_mesh_verts` 와 같은 식이어야 한다 — 최대 변 기준 균일 스케일."""
    vertices = np.array([[0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 2.0]])
    mesh = Mesh(vertices, np.array([[0, 1, 2]], dtype=np.int64))
    normalized, scale, center = normalize_mesh(mesh)

    assert scale == pytest.approx(1.0 / 4.0)
    assert center == pytest.approx([2.0, 0.5, 1.0])
    # 최대 변(x)은 정확히 [-0.5, 0.5] 를 채우고, 나머지 축은 그보다 좁다(종횡비 보존).
    assert normalized.vertices[:, 0].min() == pytest.approx(-0.5)
    assert normalized.vertices[:, 0].max() == pytest.approx(0.5)
    assert np.ptp(normalized.vertices[:, 1]) == pytest.approx(0.25)


def test_normalize_of_degenerate_extent_does_not_divide_by_zero():
    mesh = Mesh(np.zeros((3, 3)), np.array([[0, 1, 2]], dtype=np.int64))
    normalized, scale, _ = normalize_mesh(mesh)
    assert scale == 1.0
    assert np.allclose(normalized.vertices, 0.0)


def test_is_normalized_matches_upstream_skip_condition():
    cube = Mesh(
        np.array(
            [
                [-0.5, -0.5, -0.5],
                [0.5, 0.5, 0.5],
                [0.0, 0.0, 0.0],
            ]
        ),
        np.array([[0, 1, 2]], dtype=np.int64),
    )
    assert is_normalized(cube)
    assert not is_normalized(make_dummy_mesh(seed=4))


def test_subdivide_quadruples_faces():
    mesh = make_dummy_mesh(seed=5)
    finer = subdivide(mesh)
    assert len(finer.faces) == len(mesh.faces) * 4
    # 중점이 공유돼야 한다 — 캐시가 없으면 정점이 3배로 늘어난다.
    assert len(finer.vertices) == 8 + 18


def test_subdivide_preserves_bounds():
    mesh = make_dummy_mesh(seed=6)
    finer = subdivide(mesh)
    assert np.allclose(finer.vertices.min(axis=0), mesh.vertices.min(axis=0))
    assert np.allclose(finer.vertices.max(axis=0), mesh.vertices.max(axis=0))


def test_remesh_up_uses_subdivide():
    mesh = make_dummy_mesh(seed=7)
    assert len(remesh(mesh, 48).faces) == 48
    # 4배 단위로만 늘어난다 — 50 을 요구해도 48 에서 멈춘다.
    assert len(remesh(mesh, 50).faces) == 48


def test_remesh_down_requires_trimesh():
    """decimation 은 라이브러리 없이 불가 — 조용히 원본을 돌려주면 안 된다."""
    mesh = make_dummy_mesh(seed=8)
    try:
        import trimesh  # noqa: F401
    except ImportError:
        with pytest.raises(RepairUnavailableError):
            remesh(mesh, 4)
    else:
        assert len(remesh(mesh, 4).faces) <= len(mesh.faces)


def test_remesh_rejects_nonpositive_target():
    with pytest.raises(ValueError):
        remesh(make_dummy_mesh(seed=9), 0)


def test_obj_roundtrip(tmp_path: Path):
    mesh = make_dummy_mesh(seed=10)
    path = write_obj(mesh, tmp_path / "m.obj")
    restored = load_mesh(path)
    assert np.allclose(restored.vertices, mesh.vertices, atol=1e-6)
    assert np.array_equal(restored.faces, mesh.faces)
