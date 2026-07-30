"""더미 샘플 생성기 + 메시 I/O + 인덱스 실재 검증.

**데이터가 없는 지금 단계에서 파이프라인을 끝까지 돌리는 유일한 수단이다.** 실데이터가 들어오면
`make_dummy_index()` 를 쓰는 자리를 실제 인덱스 로더로 바꾸면 되고, 그 아래(전처리·학습·평가)는
손대지 않는다.

메시 I/O 는 **trimesh 없이도 동작**한다 — CI 에 trimesh 가 없어서 최소 OBJ 리더/라이터를
직접 둔다. trimesh 가 있으면 그쪽을 쓴다(ply/glb 등 다른 포맷 지원).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .contracts import (
    Camera,
    CameraExtrinsics,
    CameraIntrinsics,
    GarmentCategory,
    GarmentSample,
    GarmentSampleIndex,
)


@dataclass(frozen=True)
class Mesh:
    """최소 삼각 메시. trimesh 를 강제하지 않기 위한 자체 표현."""

    vertices: np.ndarray  # (V, 3) float64
    faces: np.ndarray  # (F, 3) int64

    def __post_init__(self) -> None:
        # 빈 배열은 통과시킨다 — 면이 없는 메시(점군만 있는 파일)도 위생검사 대상이다.
        if self.vertices.size and (self.vertices.ndim != 2 or self.vertices.shape[1] != 3):
            raise ValueError(f"vertices 형태가 (V, 3) 이 아닙니다: {self.vertices.shape}")
        if self.faces.size and (self.faces.ndim != 2 or self.faces.shape[1] != 3):
            raise ValueError(f"faces 형태가 (F, 3) 이 아닙니다: {self.faces.shape}")

    @property
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self.vertices.min(axis=0), self.vertices.max(axis=0)


def _rng(seed: int | str) -> np.random.Generator:
    """문자열 시드도 받는다 — sample_id 로 결정적 더미를 만들기 위해."""
    if isinstance(seed, str):
        digest = hashlib.sha256(seed.encode("utf-8")).digest()[:8]
        seed = int.from_bytes(digest, "little")
    return np.random.default_rng(seed)


# ── 메시 I/O ─────────────────────────────────────────────────────────────────


def write_obj(mesh: Mesh, path: Path) -> Path:
    """최소 OBJ 라이터. 面 인덱스는 1-based 다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in mesh.vertices]
    lines += [f"f {a + 1} {b + 1} {c + 1}" for a, b, c in mesh.faces]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _read_obj(path: Path) -> Mesh:
    """최소 OBJ 리더. `v` 와 삼각 `f` 만 읽는다(4각 이상은 팬 분할)."""
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append([float(v) for v in parts[1:4]])
        elif parts[0] == "f":
            # "f 1//1 2//2 3//3" 형태도 받아 준다.
            idx = [int(tok.split("/")[0]) - 1 for tok in parts[1:]]
            for i in range(1, len(idx) - 1):
                faces.append([idx[0], idx[i], idx[i + 1]])
    return Mesh(np.asarray(vertices, dtype=np.float64), np.asarray(faces, dtype=np.int64))


def load_mesh(path: Path) -> Mesh:
    """메시를 읽는다. trimesh 가 있으면 그걸로(포맷 넓음), 없으면 OBJ 만."""
    path = Path(path)
    try:
        import trimesh
    except ImportError:
        if path.suffix.lower() != ".obj":
            raise RuntimeError(
                f"{path.suffix} 를 읽으려면 trimesh 가 필요합니다: pip install trimesh"
            ) from None
        return _read_obj(path)

    loaded = trimesh.load(path, force="mesh")
    return Mesh(
        np.asarray(loaded.vertices, dtype=np.float64),
        np.asarray(loaded.faces, dtype=np.int64),
    )


# ── 더미 지오메트리 ──────────────────────────────────────────────────────────


def make_dummy_mesh(seed: int | str = 0, *, open_surface: bool = False) -> Mesh:
    """의류처럼 얇고 평평한 상자 메시. 12 삼각형.

    Args:
        open_surface: True 면 한 면을 빼서 **watertight 가 아닌** 메시를 만든다.
            cloth 메시의 현실(open surface 흔함)을 재현해 수선 로직을 테스트하기 위한 것.
    """
    rng = _rng(seed)
    # 상의처럼 x 가 넓고 z 가 얇은 비율 + 샘플별 약한 변형.
    half = np.array([0.30, 0.40, 0.06]) * (1.0 + 0.1 * rng.standard_normal(3))
    signs = np.array(
        [
            [-1, -1, -1],
            [1, -1, -1],
            [1, 1, -1],
            [-1, 1, -1],
            [-1, -1, 1],
            [1, -1, 1],
            [1, 1, 1],
            [-1, 1, 1],
        ],
        dtype=np.float64,
    )
    vertices = signs * half
    quads = [
        (0, 1, 2, 3),  # -z
        (4, 7, 6, 5),  # +z
        (0, 4, 5, 1),  # -y
        (2, 6, 7, 3),  # +y
        (0, 3, 7, 4),  # -x
        (1, 5, 6, 2),  # +x
    ]
    if open_surface:
        quads = quads[:-1]
    faces = []
    for a, b, c, d in quads:
        faces.append([a, b, c])
        faces.append([a, c, d])
    return Mesh(vertices, np.asarray(faces, dtype=np.int64))


def make_dummy_image(size: tuple[int, int] = (128, 96), seed: int | str = 0) -> np.ndarray:
    """(H, W, 3) uint8. 밝은 배경 위 어두운 의류 실루엣 — 마스크와 짝이 맞는다."""
    width, height = size
    rng = _rng(seed)
    image = np.full((height, width, 3), 235, dtype=np.uint8)
    mask = make_dummy_mask(size, seed)
    color = rng.integers(20, 90, size=3)
    image[mask] = color.astype(np.uint8)
    # 약한 노이즈 — 완전 균일 이미지는 엣지/플로우 지표를 0 으로 만들어 테스트가 무의미해진다.
    noise = rng.integers(-6, 7, size=image.shape)
    return np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def make_dummy_mask(size: tuple[int, int] = (128, 96), seed: int | str = 0) -> np.ndarray:
    """(H, W) bool. 가운데 사각형 실루엣."""
    width, height = size
    rng = _rng(seed)
    mask = np.zeros((height, width), dtype=bool)
    half_w = int(width * rng.uniform(0.18, 0.26))
    half_h = int(height * rng.uniform(0.26, 0.34))
    cx, cy = width // 2, height // 2
    mask[cy - half_h : cy + half_h, cx - half_w : cx + half_w] = True
    return mask


def _save_png(array: np.ndarray, path: Path) -> Path:
    """PNG 로 저장. bool 은 0/255 L 모드로."""
    from PIL import Image

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if array.dtype == bool:
        Image.fromarray(array.astype(np.uint8) * 255).save(path)
    else:
        Image.fromarray(array.astype(np.uint8)).save(path)
    return path


def make_dummy_camera(seed: int | str = 0, *, with_extrinsics: bool = True) -> Camera:
    """더미 카메라. `with_extrinsics=False` 로 "extrinsic 없는 데이터"를 재현한다."""
    rng = _rng(seed)
    intrinsics = CameraIntrinsics(fx=120.0, fy=120.0, cx=64.0, cy=48.0, width=128, height=96)
    if not with_extrinsics:
        return Camera(intrinsics=intrinsics, extrinsics=None)
    quat = rng.standard_normal(4)
    quat = quat / np.linalg.norm(quat)
    return Camera(
        intrinsics=intrinsics,
        extrinsics=CameraExtrinsics(
            rotation_quat=[float(v) for v in quat],
            translation=[0.0, 0.0, float(rng.uniform(1.5, 2.5))],
            scale=1.0,
        ),
    )


def make_dummy_sample(
    root: Path,
    sample_id: str,
    *,
    with_mesh: bool = True,
    with_camera: bool = True,
    with_extrinsics: bool = True,
    open_surface: bool = False,
    category: GarmentCategory = GarmentCategory.TOP,
) -> GarmentSample:
    """파일까지 실제로 쓰는 더미 샘플. 경로는 `root` 기준 **상대경로**로 담는다."""
    root = Path(root)
    rel_image = Path("images") / f"{sample_id}.png"
    rel_mask = Path("masks") / f"{sample_id}.png"
    _save_png(make_dummy_image(seed=sample_id), root / rel_image)
    _save_png(make_dummy_mask(seed=sample_id), root / rel_mask)

    rel_mesh: Path | None = None
    if with_mesh:
        rel_mesh = Path("meshes") / f"{sample_id}.obj"
        write_obj(make_dummy_mesh(sample_id, open_surface=open_surface), root / rel_mesh)

    camera = make_dummy_camera(sample_id, with_extrinsics=with_extrinsics) if with_camera else None
    return GarmentSample(
        sample_id=sample_id,
        image_path=rel_image,
        garment_mask_path=rel_mask,
        mesh_path=rel_mesh,
        camera=camera,
        category=category,
        meta={"source": "dummy", "license": "N/A (합성 더미)"},
    )


def make_dummy_index(root: Path, count: int = 3, **sample_kwargs) -> GarmentSampleIndex:
    """더미 샘플 `count` 개로 인덱스를 만든다."""
    samples = [make_dummy_sample(root, f"dummy_{i:03d}", **sample_kwargs) for i in range(count)]
    return GarmentSampleIndex(root=Path(root), samples=samples)


# ── 실재 검증 (데이터 의존) ──────────────────────────────────────────────────


def verify_index(index: GarmentSampleIndex) -> dict[str, list[str]]:
    """인덱스가 가리키는 파일이 실제로 있는지 본다.

    `audit_sample()`(데이터 비의존, 스키마만 봄)과 **일부러 분리**했다. 이쪽은 디스크를 만진다.

    Returns:
        `{sample_id: [없는 경로, ...]}` — 전부 정상이면 빈 dict.
    """
    missing: dict[str, list[str]] = {}
    for sample in index.resolved():
        gaps = [
            str(path)
            for path in (sample.image_path, sample.garment_mask_path, sample.mesh_path)
            if path is not None and not Path(path).exists()
        ]
        if gaps:
            missing[sample.sample_id] = gaps
    return missing
