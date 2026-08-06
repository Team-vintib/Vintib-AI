"""latent 인코더 — 더미 결정성, stage 2 stub, 백엔드 팩토리, npz 왕복."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from garment3d.data import make_dummy_mesh
from garment3d.preprocess.latent import (
    DummyLatentEncoder,
    Latent,
    LatentEncodeError,
    Sam3dSlatEncoder,
    build_latent_encoder,
)
from garment3d.preprocess.voxelize import voxelize_numpy

_PROJECT_DIR = Path(__file__).resolve().parent.parent


def _grid(seed: int = 1, resolution: int = 16):
    return voxelize_numpy(make_dummy_mesh(seed=seed), resolution=resolution)


def test_dummy_encoder_shape_and_stage():
    latent = DummyLatentEncoder(latent_channels=8, downsample=4).encode(_grid(resolution=16))
    assert latent.array.shape == (1, 8, 4, 4, 4)
    assert latent.array.dtype == np.float32
    assert latent.stage == "geometry"
    assert latent.meta["source_backend"] == "numpy"


def test_dummy_encoder_is_deterministic_within_process():
    encoder = DummyLatentEncoder()
    grid = _grid()
    assert np.array_equal(encoder.encode(grid).array, encoder.encode(grid).array)


def test_dummy_encoder_differs_for_different_geometry():
    encoder = DummyLatentEncoder()
    left = encoder.encode(_grid(seed=1)).array
    right = encoder.encode(_grid(seed=99)).array
    assert not np.array_equal(left, right)


def test_dummy_encoder_is_deterministic_across_processes():
    """내장 `hash()` 를 쓰면 PYTHONHASHSEED 때문에 프로세스마다 값이 달라진다.

    체크포인트 재현·회귀 비교가 이 성질에 의존하므로 별도 프로세스로 확인한다.
    """
    script = (
        "import sys; sys.path.insert(0, r'%s');"
        "import numpy as np;"
        "from garment3d.data import make_dummy_mesh;"
        "from garment3d.preprocess.voxelize import voxelize_numpy;"
        "from garment3d.preprocess.latent import DummyLatentEncoder;"
        "g = voxelize_numpy(make_dummy_mesh(seed=1), resolution=16);"
        "print(float(DummyLatentEncoder().encode(g).array.sum()))" % _PROJECT_DIR
    )
    runs = [
        subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=True
        ).stdout.strip()
        for _ in range(2)
    ]
    assert runs[0] == runs[1]
    assert runs[0] == str(float(DummyLatentEncoder().encode(_grid()).array.sum()))


def test_slat_encoder_is_an_explicit_stub():
    """stage 2 는 릴리스에 없다 (REPORT.md §5) — 조용히 뭔가 반환하면 안 된다."""
    with pytest.raises(NotImplementedError, match="REPORT.md"):
        Sam3dSlatEncoder().encode(_grid())
    assert Sam3dSlatEncoder().stage == "texture"


def test_build_latent_encoder_dummy():
    assert build_latent_encoder("dummy").name == "dummy"


def test_build_latent_encoder_ss_requires_injection():
    """실인코더는 파이프라인 모듈 주입이 필요하다 — 스스로 수 GB 를 로드하지 않는다."""
    with pytest.raises(LatentEncodeError, match="ss_encoder"):
        build_latent_encoder("sam3d_ss")


def test_build_latent_encoder_unknown():
    with pytest.raises(LatentEncodeError, match="알 수 없는"):
        build_latent_encoder("vqvae")


def test_latent_npz_roundtrip(tmp_path: Path):
    latent = DummyLatentEncoder().encode(_grid())
    restored = Latent.load(latent.save(tmp_path / "l.npz"))
    assert np.array_equal(restored.array, latent.array)
    assert (restored.backend, restored.stage) == (latent.backend, latent.stage)


def test_sam3d_ss_encoder_accepts_tensor_and_dict_outputs():
    """upstream 에는 텐서를 돌려주는 인코더와 `{"z": ...}` 를 돌려주는 래퍼가 둘 다 있다."""
    torch = pytest.importorskip("torch")

    from garment3d.preprocess.latent import Sam3dSparseStructureEncoder

    grid = _grid(resolution=8)

    class TensorEncoder:
        def __call__(self, dense):
            assert dense.shape == (1, 1, 8, 8, 8), dense.shape
            assert dense.dtype == torch.float32
            return dense.mean(dim=(2, 3, 4), keepdim=True)

    class DictEncoder(TensorEncoder):
        def __call__(self, dense):
            return {"z": super().__call__(dense)}

    for encoder in (TensorEncoder(), DictEncoder()):
        latent = Sam3dSparseStructureEncoder(encoder).encode(grid)
        assert latent.backend == "sam3d_ss"
        assert latent.array.shape == (1, 1, 1, 1, 1)


def test_sam3d_ss_encoder_rejects_dict_without_z():
    pytest.importorskip("torch")

    from garment3d.preprocess.latent import Sam3dSparseStructureEncoder

    class BadEncoder:
        def __call__(self, dense):
            return {"latent": dense}

    with pytest.raises(LatentEncodeError, match="'z'"):
        Sam3dSparseStructureEncoder(BadEncoder()).encode(_grid(resolution=8))
