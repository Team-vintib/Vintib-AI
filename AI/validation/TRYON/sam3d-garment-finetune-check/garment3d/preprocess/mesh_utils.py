"""메시 위생 검사 — watertight / manifold / 정규화 / 리메시.

**왜 필요한가**: SAM 3D 는 메시를 64³ occupancy 로 복셀화해서 감독 신호를 만든다. 그런데 의류
cloth 메시는 self-intersection 과 open surface(구멍 뚫린 표면)가 흔하고, 그 상태로 복셀화하면
occupancy 가 표면만 얇게 찍히거나 안팎이 뒤집힌다. 그래서 **복셀화 전에 무엇이 깨져 있는지
수치로 알아야 한다.**

순수 numpy 로 되는 것(검사·정규화·subdivide)과 라이브러리가 필요한 것(구멍 메우기·decimation)을
명확히 나눈다. 후자는 있으면 쓰고 없으면 **거짓 성공을 반환하지 않고 그렇다고 말한다.**
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..data import Mesh

# upstream `inference_utils.py::voxelize_mesh` 가 복셀화 직전에 적용하는 z-up → y-up 회전.
# 우리 쪽에서 미리 정규화해 둘 때도 같은 축 규약을 써야 결과가 어긋나지 않는다.
Z_UP_TO_Y_UP = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)


@dataclass(frozen=True)
class MeshHealth:
    """메시 위생 리포트. 숫자로 남겨서 데이터셋 전체 분포를 볼 수 있게 한다."""

    num_vertices: int
    num_faces: int
    #: 정확히 두 면이 공유하는 엣지 수 (정상)
    num_manifold_edges: int
    #: 한 면만 접한 엣지 수 → 열린 경계. cloth 메시에서 가장 흔한 문제.
    num_boundary_edges: int
    #: 세 면 이상이 공유하는 엣지 수 → non-manifold.
    num_nonmanifold_edges: int
    num_degenerate_faces: int
    num_duplicate_vertices: int

    @property
    def is_watertight(self) -> bool:
        """모든 엣지가 정확히 두 면을 갖는가."""
        return self.num_boundary_edges == 0 and self.num_nonmanifold_edges == 0

    @property
    def is_clean(self) -> bool:
        return self.is_watertight and self.num_degenerate_faces == 0

    def summary(self) -> str:
        state = "watertight" if self.is_watertight else "NOT watertight"
        return (
            f"{state}: V={self.num_vertices} F={self.num_faces} "
            f"boundary={self.num_boundary_edges} nonmanifold={self.num_nonmanifold_edges} "
            f"degenerate={self.num_degenerate_faces} dup_v={self.num_duplicate_vertices}"
        )


def _edge_counts(faces: np.ndarray) -> np.ndarray:
    """무향 엣지별 인접 면 수. (E,) int"""
    if len(faces) == 0:
        return np.zeros(0, dtype=np.int64)
    edges = np.concatenate(
        [faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]],
        axis=0,
    )
    edges = np.sort(edges, axis=1)  # 무향화
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return counts


def check_mesh(mesh: Mesh) -> MeshHealth:
    """순수 numpy 위생 검사. 라이브러리 없이 CI 에서 그대로 돈다."""
    faces = mesh.faces
    # 같은 정점을 두 번 이상 쓰는 면 = 면적 0 (degenerate)
    degenerate = 0
    if len(faces):
        degenerate = int(
            np.sum(
                (faces[:, 0] == faces[:, 1])
                | (faces[:, 1] == faces[:, 2])
                | (faces[:, 0] == faces[:, 2])
            )
        )

    counts = _edge_counts(faces)
    duplicate = 0
    if len(mesh.vertices):
        duplicate = int(len(mesh.vertices) - len(np.unique(mesh.vertices, axis=0)))

    return MeshHealth(
        num_vertices=int(len(mesh.vertices)),
        num_faces=int(len(faces)),
        num_manifold_edges=int(np.sum(counts == 2)),
        num_boundary_edges=int(np.sum(counts == 1)),
        num_nonmanifold_edges=int(np.sum(counts > 2)),
        num_degenerate_faces=degenerate,
        num_duplicate_vertices=duplicate,
    )


def normalize_mesh(mesh: Mesh) -> tuple[Mesh, float, np.ndarray]:
    """`[-0.5, 0.5]` 정규화. upstream `normalize_mesh_verts` 와 **같은 식**이다.

    최대 변 길이로 균일 스케일하므로 종횡비가 보존된다. 축별 정규화로 바꾸면 의류가 찌그러지고
    복셀 점유가 upstream 과 달라진다 — 바꾸지 말 것.

    Returns:
        (정규화된 메시, scale, center) — scale/center 는 역변환용.
    """
    verts = np.asarray(mesh.vertices, dtype=np.float64)
    if len(verts) == 0:
        return mesh, 1.0, np.zeros(3)
    vmin, vmax = verts.min(axis=0), verts.max(axis=0)
    center = (vmax + vmin) / 2.0
    max_extent = float(np.max(vmax - vmin))
    if max_extent == 0:
        return Mesh(verts - center, mesh.faces), 1.0, center
    scale = 1.0 / max_extent
    return Mesh((verts - center) * scale, mesh.faces), scale, center


def is_normalized(mesh: Mesh, tol: float = 1e-3) -> bool:
    """upstream 이 "이미 정규화됨"으로 판정하는 조건과 동일.

    `voxelize_mesh` 는 `abs(min + 0.5) < 1e-3 and abs(max - 0.5) < 1e-3` 이면 정규화를
    건너뛴다. 우리가 미리 정규화해 놓고 upstream 에 넘길 때 **이중 정규화를 피하려면** 같은
    조건을 알아야 한다.
    """
    verts = np.asarray(mesh.vertices)
    if len(verts) == 0:
        return False
    return bool(abs(verts.min() + 0.5) < tol and abs(verts.max() - 0.5) < tol)


def drop_degenerate_faces(mesh: Mesh) -> Mesh:
    """면적 0 삼각형 제거. 순수 numpy."""
    faces = mesh.faces
    if len(faces) == 0:
        return mesh
    keep = ~(
        (faces[:, 0] == faces[:, 1]) | (faces[:, 1] == faces[:, 2]) | (faces[:, 0] == faces[:, 2])
    )
    return Mesh(mesh.vertices, faces[keep])


def merge_duplicate_vertices(mesh: Mesh, tol: int = 8) -> Mesh:
    """좌표가 같은(반올림 기준) 정점을 병합한다.

    OBJ 왕복이나 여러 조각을 합친 메시는 같은 좌표의 정점이 중복되는데, 그러면 엣지가 공유되지
    않아 **멀쩡한 메시도 boundary 엣지로 잡힌다.** watertight 판정 전에 반드시 거쳐야 한다.
    """
    verts = np.asarray(mesh.vertices, dtype=np.float64)
    if len(verts) == 0:
        return mesh
    keys = np.round(verts, tol)
    _, first_index, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    # np.unique 는 정렬된 순서를 주므로 원래 순서를 유지하려면 재매핑이 필요하다.
    order = np.argsort(first_index)
    remap = np.empty(len(first_index), dtype=np.int64)
    remap[order] = np.arange(len(first_index))
    new_verts = verts[np.sort(first_index)]
    new_faces = remap[inverse.reshape(-1)][mesh.faces]
    return Mesh(new_verts, new_faces.astype(np.int64))


def subdivide(mesh: Mesh) -> Mesh:
    """엣지 중점 분할로 면 수를 4배로. 순수 numpy.

    decimation 과 달리 라이브러리 없이 되므로, `target_faces` 가 현재보다 클 때만 쓴다.
    """
    verts = list(np.asarray(mesh.vertices, dtype=np.float64))
    midpoint_cache: dict[tuple[int, int], int] = {}

    def _midpoint(a: int, b: int) -> int:
        key = (min(a, b), max(a, b))
        if key not in midpoint_cache:
            midpoint_cache[key] = len(verts)
            verts.append((verts[a] + verts[b]) / 2.0)
        return midpoint_cache[key]

    faces = []
    for a, b, c in mesh.faces:
        ab, bc, ca = _midpoint(a, b), _midpoint(b, c), _midpoint(c, a)
        faces += [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]]
    return Mesh(np.asarray(verts, dtype=np.float64), np.asarray(faces, dtype=np.int64))


class RepairUnavailableError(RuntimeError):
    """구멍 메우기/decimation 을 할 수 있는 라이브러리가 없다."""


def repair_watertight(mesh: Mesh) -> tuple[Mesh, MeshHealth]:
    """watertight 로 수선한다. **거짓 성공을 반환하지 않는다.**

    순서:
    1. 중복 정점 병합 + degenerate 면 제거 (순수 numpy). 이것만으로 해결되는 경우가 많다.
    2. 여전히 열려 있으면 `pymeshfix` → `trimesh.repair` 순으로 시도(lazy import).
    3. 둘 다 없으면 `RepairUnavailableError`. 호출자가 샘플을 버릴지 결정한다.

    `pymeshfix` 는 upstream `requirements.txt` 에 `pymeshfix==0.17.0` 으로 이미 들어 있다 —
    sam3d 환경에서는 3번으로 빠지지 않는다.
    """
    cleaned = drop_degenerate_faces(merge_duplicate_vertices(mesh))
    health = check_mesh(cleaned)
    if health.is_watertight:
        return cleaned, health

    try:
        import pymeshfix
    except ImportError:
        pass
    else:
        fixed_v, fixed_f = pymeshfix.clean_from_arrays(cleaned.vertices, cleaned.faces)
        repaired = Mesh(np.asarray(fixed_v, dtype=np.float64), np.asarray(fixed_f, dtype=np.int64))
        return repaired, check_mesh(repaired)

    try:
        import trimesh
    except ImportError as exc:
        raise RepairUnavailableError(
            "열린 메시를 수선할 수 없습니다 (boundary "
            f"{health.num_boundary_edges}개). pymeshfix 또는 trimesh 를 설치하세요."
        ) from exc

    tm = trimesh.Trimesh(vertices=cleaned.vertices, faces=cleaned.faces, process=False)
    trimesh.repair.fill_holes(tm)
    repaired = Mesh(np.asarray(tm.vertices, dtype=np.float64), np.asarray(tm.faces, dtype=np.int64))
    return repaired, check_mesh(repaired)


def remesh(mesh: Mesh, target_faces: int) -> Mesh:
    """면 수를 `target_faces` 근처로 맞춘다.

    - 늘리는 방향: 순수 numpy `subdivide()` 반복(4배씩).
    - 줄이는 방향: quadric decimation 이 필요하므로 **trimesh 없이는 불가**다.
      없으면 `RepairUnavailableError` 를 던진다 — 조용히 원본을 돌려주면 학습 데이터에
      의도하지 않은 해상도가 섞인다.
    """
    if target_faces <= 0:
        raise ValueError(f"target_faces 는 양수여야 합니다: {target_faces}")

    current = len(mesh.faces)
    if current == 0:
        return mesh

    if target_faces >= current:
        out = mesh
        while len(out.faces) * 4 <= target_faces:
            out = subdivide(out)
        return out

    try:
        import trimesh
    except ImportError as exc:
        raise RepairUnavailableError(
            f"면 수를 {current} → {target_faces} 로 줄이려면 trimesh 가 필요합니다."
        ) from exc

    tm = trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces, process=False)
    simplified = tm.simplify_quadric_decimation(face_count=target_faces)
    return Mesh(
        np.asarray(simplified.vertices, dtype=np.float64),
        np.asarray(simplified.faces, dtype=np.int64),
    )
