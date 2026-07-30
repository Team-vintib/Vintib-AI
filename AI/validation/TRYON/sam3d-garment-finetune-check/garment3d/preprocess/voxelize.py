"""mesh → 64³ occupancy.

백엔드 2개다.

- `sam3d` — upstream `sam3d_objects.pipeline.inference_utils.voxelize_mesh` 위임.
  **학습 데이터 생성에는 이것만 쓴다.** open3d 표면 복셀화라 우리가 재현할 수 없다.
- `numpy` — 의존성 없는 삼각형 표면 샘플링. **테스트·CI 전용.**

두 백엔드는 축 규약·정규화·인덱싱을 맞췄지만(아래 참고) **동일 결과를 보장하지 않는다.**
같다고 가정하는 코드를 쓰지 말 것.

맞춘 것 (upstream `voxelize_mesh` 를 읽고 그대로 따랐다):
1. z-up → y-up 회전을 **정규화보다 먼저** 적용한다.
2. 이미 `[-0.5, 0.5]` 면 정규화를 건너뛴다(`is_normalized`, 허용오차 1e-3).
3. `[-0.5+eps, 0.5-eps]` 로 클립한다.
4. 복셀 인덱스는 `floor((p + 0.5) * resolution)` 이고 grid 는 `(1, R, R, R)` 이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..data import Mesh
from .mesh_utils import Z_UP_TO_Y_UP, is_normalized, normalize_mesh

_CLIP_EPS = 1e-6


class VoxelizeError(RuntimeError):
    """복셀화 결과가 학습에 쓸 수 없는 상태다."""


@dataclass(frozen=True)
class OccupancyGrid:
    """`(1, R, R, R)` occupancy + 역변환 정보.

    `scale`/`center` 는 원본 좌표계로 되돌리는 값이다. 입력이 이미 정규화돼 있었으면
    upstream 과 같이 `None` 이다 — "정규화를 하지 않았다"는 뜻이라 0/1 로 대체하면 안 된다.
    """

    grid: np.ndarray
    scale: float | None
    center: np.ndarray | None
    backend: str
    resolution: int

    @property
    def num_active(self) -> int:
        return int(self.grid.sum())

    @property
    def occupancy_ratio(self) -> float:
        return float(self.grid.mean())

    def active_coords(self) -> np.ndarray:
        """활성 복셀의 `(N, 3)` 인덱스. sparse structure 인코더 입력 좌표에 해당한다."""
        return np.stack(np.nonzero(self.grid[0]), axis=1).astype(np.int64)

    def save(self, path: Path) -> Path:
        """npz 로 저장. 활성 좌표만 담아 64³ 전체를 쓰지 않는다."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            coords=self.active_coords(),
            resolution=np.int64(self.resolution),
            scale=np.array([np.nan if self.scale is None else self.scale], dtype=np.float64),
            center=(
                np.full(3, np.nan) if self.center is None else np.asarray(self.center, np.float64)
            ),
            backend=np.array(self.backend),
        )
        return path

    @classmethod
    def load(cls, path: Path) -> OccupancyGrid:
        data = np.load(path, allow_pickle=False)
        resolution = int(data["resolution"])
        grid = np.zeros((1, resolution, resolution, resolution), dtype=np.int64)
        coords = data["coords"]
        if len(coords):
            grid[0, coords[:, 0], coords[:, 1], coords[:, 2]] = 1
        raw_scale = float(data["scale"][0])
        raw_center = data["center"]
        return cls(
            grid=grid,
            scale=None if np.isnan(raw_scale) else raw_scale,
            center=None if bool(np.isnan(raw_center).any()) else raw_center,
            backend=str(data["backend"]),
            resolution=resolution,
        )


def _prepare_vertices(mesh: Mesh) -> tuple[np.ndarray, float | None, np.ndarray | None]:
    """회전 → (필요하면) 정규화 → 클립. upstream 과 같은 순서."""
    verts = np.asarray(mesh.vertices, dtype=np.float64) @ Z_UP_TO_Y_UP.T
    rotated = Mesh(verts, mesh.faces)
    if is_normalized(rotated):
        scale: float | None = None
        center: np.ndarray | None = None
    else:
        rotated, scale, center = normalize_mesh(rotated)
        verts = rotated.vertices
    verts = np.clip(rotated.vertices, -0.5 + _CLIP_EPS, 0.5 - _CLIP_EPS)
    return verts, scale, center


def _sample_triangle_points(triangle: np.ndarray, step: float) -> np.ndarray:
    """삼각형 하나를 `step` 간격 격자로 채운 점들. 표면 복셀화용.

    barycentric 격자 밀도를 삼각형의 최대 변 길이에서 정한다 — 큰 삼각형에서 복셀이 비는 걸
    막고, 작은 삼각형에 과도한 점을 만들지 않는다.
    """
    a, b, c = triangle
    longest = max(
        float(np.linalg.norm(b - a)), float(np.linalg.norm(c - b)), float(np.linalg.norm(a - c))
    )
    divisions = max(1, int(np.ceil(longest / step)))
    # u + v <= 1 인 barycentric 격자
    idx = np.arange(divisions + 1)
    uu, vv = np.meshgrid(idx, idx, indexing="ij")
    keep = (uu + vv) <= divisions
    u = uu[keep] / divisions
    v = vv[keep] / divisions
    return a + u[:, None] * (b - a) + v[:, None] * (c - a)


def voxelize_numpy(mesh: Mesh, resolution: int = 64) -> OccupancyGrid:
    """의존성 없는 표면 복셀화. **테스트용이며 upstream 과 값이 같지 않다.**"""
    verts, scale, center = _prepare_vertices(mesh)
    grid = np.zeros((1, resolution, resolution, resolution), dtype=np.int64)
    if len(mesh.faces) == 0:
        return OccupancyGrid(grid, scale, center, "numpy", resolution)

    # 복셀 한 칸의 절반 간격으로 샘플링 — 대각선 방향에서 칸이 비는 걸 막는다.
    step = 0.5 / resolution
    for face in mesh.faces:
        points = _sample_triangle_points(verts[face], step)
        coords = np.floor((points + 0.5) * resolution).astype(np.int64)
        np.clip(coords, 0, resolution - 1, out=coords)
        grid[0, coords[:, 0], coords[:, 1], coords[:, 2]] = 1
    return OccupancyGrid(grid, scale, center, "numpy", resolution)


def voxelize_sam3d(mesh: Mesh, resolution: int = 64) -> OccupancyGrid:
    """upstream `voxelize_mesh` 위임. open3d + sam3d_objects 가 필요하다.

    upstream 은 **open3d TriangleMesh** 를 받는다(`mesh.vertices` 에
    `o3d.utility.Vector3dVector` 를 대입한다) — trimesh 객체를 그대로 넘기면 깨진다.
    그래서 여기서 o3d 메시로 변환해 넘긴다.
    """
    try:
        import open3d as o3d
        from sam3d_objects.pipeline.inference_utils import voxelize_mesh
    except ImportError as exc:
        raise VoxelizeError(
            "sam3d 백엔드는 sam3d_objects + open3d 환경에서만 동작합니다 "
            "(REPORT.md §0 의 sam3d-objects conda 환경). preprocess.voxelizer=numpy 로 두세요."
        ) from exc

    o3d_mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(np.asarray(mesh.vertices, dtype=np.float64)),
        o3d.utility.Vector3iVector(np.asarray(mesh.faces, dtype=np.int32)),
    )
    grid_tensor, scale, center = voxelize_mesh(o3d_mesh, resolution=resolution)
    grid = np.asarray(grid_tensor.cpu().numpy(), dtype=np.int64)
    return OccupancyGrid(
        grid=grid,
        scale=None if scale is None else float(scale),
        center=None if center is None else np.asarray(center, dtype=np.float64),
        backend="sam3d",
        resolution=resolution,
    )


_BACKENDS = {"numpy": voxelize_numpy, "sam3d": voxelize_sam3d}


def voxelize(
    mesh: Mesh,
    *,
    backend: str = "numpy",
    resolution: int = 64,
    min_active_voxels: int = 0,
) -> OccupancyGrid:
    """백엔드 이름으로 복셀화한다.

    Raises:
        VoxelizeError: 알 수 없는 백엔드거나, 활성 복셀이 `min_active_voxels` 미만일 때.
            후자는 빈 메시·정규화 실패·축 규약 오류를 조용히 통과시키지 않기 위한 방어다.
    """
    if backend not in _BACKENDS:
        raise VoxelizeError(f"알 수 없는 백엔드: {backend!r} (가능: {sorted(_BACKENDS)})")

    grid = _BACKENDS[backend](mesh, resolution)
    if grid.num_active < min_active_voxels:
        raise VoxelizeError(
            f"활성 복셀 {grid.num_active}개 < 최소 {min_active_voxels}개 — "
            "메시가 비었거나 정규화/축 규약이 어긋났을 수 있습니다."
        )
    return grid
