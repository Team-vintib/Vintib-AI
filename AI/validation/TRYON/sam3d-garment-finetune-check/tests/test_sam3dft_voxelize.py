"""복셀화 — 형태·인덱싱 규약, 최소 활성 복셀 방어, npz 왕복, sam3d 백엔드 가드."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from garment3d.data import Mesh, make_dummy_mesh
from garment3d.preprocess.mesh_utils import Z_UP_TO_Y_UP
from garment3d.preprocess.voxelize import (
    OccupancyGrid,
    VoxelizeError,
    voxelize,
    voxelize_numpy,
    voxelize_sam3d,
)


def test_grid_shape_and_dtype_match_upstream():
    """upstream `voxelize_mesh` 는 `(1, R, R, R)` long 을 돌려준다 — 형태를 맞춘다."""
    grid = voxelize_numpy(make_dummy_mesh(seed=1), resolution=32)
    assert grid.grid.shape == (1, 32, 32, 32)
    assert grid.grid.dtype == np.int64
    assert set(np.unique(grid.grid)) <= {0, 1}
    assert grid.resolution == 32
    assert grid.backend == "numpy"


def test_surface_voxelization_is_not_solid():
    """표면 복셀화다 — 내부가 채워지면 안 된다(upstream 도 표면만 찍는다)."""
    grid = voxelize_numpy(make_dummy_mesh(seed=2), resolution=32)
    assert 0 < grid.occupancy_ratio < 0.5


def test_active_coords_are_within_bounds():
    grid = voxelize_numpy(make_dummy_mesh(seed=3), resolution=16)
    coords = grid.active_coords()
    assert coords.shape[1] == 3
    assert coords.min() >= 0
    assert coords.max() <= 15
    assert len(coords) == grid.num_active


def test_normalized_input_skips_normalization():
    """이미 `[-0.5, 0.5]` 면 upstream 처럼 정규화를 건너뛰고 scale/center 가 None 이다."""
    # 회전 후에도 [-0.5, 0.5] 를 유지하는 정육면체를 만든다.
    signs = np.array(
        [[x, y, z] for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5)],
        dtype=np.float64,
    )
    rotated_back = signs @ np.linalg.inv(Z_UP_TO_Y_UP.T)
    mesh = Mesh(rotated_back, np.array([[0, 1, 2]], dtype=np.int64))
    grid = voxelize_numpy(mesh, resolution=16)
    assert grid.scale is None
    assert grid.center is None


def test_unnormalized_input_reports_scale_and_center():
    grid = voxelize_numpy(make_dummy_mesh(seed=4), resolution=16)
    assert grid.scale is not None and grid.scale > 0
    assert grid.center is not None and grid.center.shape == (3,)


def test_axis_convention_rotation_is_applied():
    """z-up → y-up 회전이 실제로 걸리는지 — 긴 축의 복셀 범위로 확인한다.

    y 로 길쭉한(원래 좌표계) 판을 넣으면 회전 후에는 **z 축**이 가장 길어야 한다.
    회전을 빼먹으면 y 가 그대로 가장 길다.
    """
    long_y = Mesh(
        np.array(
            [[-0.05, -0.5, -0.01], [0.05, -0.5, -0.01], [0.05, 0.5, 0.01], [-0.05, 0.5, 0.01]]
        ),
        np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64),
    )
    coords = voxelize_numpy(long_y, resolution=32).active_coords()
    spans = coords.max(axis=0) - coords.min(axis=0)
    assert spans[2] == spans.max()


def test_min_active_voxels_guards_empty_mesh():
    empty = Mesh(np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64))
    grid = voxelize(empty, backend="numpy", resolution=8)
    assert grid.num_active == 0
    with pytest.raises(VoxelizeError, match="활성 복셀"):
        voxelize(empty, backend="numpy", resolution=8, min_active_voxels=1)


def test_unknown_backend_raises():
    with pytest.raises(VoxelizeError, match="알 수 없는 백엔드"):
        voxelize(make_dummy_mesh(seed=5), backend="open3d")


def test_sam3d_backend_fails_loudly_without_deps():
    """sam3d 환경이 아니면 명확한 에러여야 한다 — 조용히 numpy 로 폴백하면 안 된다."""
    try:
        import open3d  # noqa: F401
        import sam3d_objects  # noqa: F401
    except ImportError:
        with pytest.raises(VoxelizeError, match="sam3d_objects"):
            voxelize_sam3d(make_dummy_mesh(seed=6), resolution=16)
    else:
        pytest.skip("sam3d_objects 환경이라 실백엔드가 동작한다 — 이 가드는 검사 대상이 아니다")


def test_npz_roundtrip_preserves_grid_and_layout(tmp_path: Path):
    grid = voxelize_numpy(make_dummy_mesh(seed=7), resolution=16)
    restored = OccupancyGrid.load(grid.save(tmp_path / "occ.npz"))

    assert np.array_equal(restored.grid, grid.grid)
    assert restored.resolution == grid.resolution
    assert restored.backend == grid.backend
    assert restored.scale == pytest.approx(grid.scale)
    assert np.allclose(restored.center, grid.center)


def test_npz_roundtrip_preserves_none_layout(tmp_path: Path):
    """`scale=None` 은 "정규화하지 않았다"는 정보다 — 0 이나 1 로 바뀌면 역변환이 틀어진다."""
    grid = OccupancyGrid(
        grid=np.zeros((1, 4, 4, 4), dtype=np.int64),
        scale=None,
        center=None,
        backend="numpy",
        resolution=4,
    )
    restored = OccupancyGrid.load(grid.save(tmp_path / "none.npz"))
    assert restored.scale is None
    assert restored.center is None
