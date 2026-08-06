"""occupancy → latent 인코딩.

**이 모듈이 이 프로젝트에서 가장 크게 막혀 있는 지점이다** (`REPORT.md` §4·5).

| stage | 감독 타깃 | 릴리스 상태 | 여기서의 구현 |
| --- | --- | --- | --- |
| 1 (geometry) | sparse structure latent | ✅ `models["ss_encoder"]` 로 연결돼 있다 | `Sam3dSparseStructureEncoder` — 실호출 |
| 2 (texture) | structured latent (SLat) | ⚠️ `SLatEncoder` 클래스만 있고 파이프라인 미연결, 특징 생성 코드 없음 | `Sam3dSlatEncoder` — **stub + TODO** |

stage 2 를 추측으로 구현하지 않는다. 채워야 할 것이 무엇인지만 코드에 못박아 둔다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .voxelize import OccupancyGrid


class LatentEncodeError(RuntimeError):
    """인코딩을 수행할 수 없다."""


@dataclass(frozen=True)
class Latent:
    """인코딩 결과. numpy 로 담아 torch 없는 환경에서도 다룰 수 있게 한다.

    `array` 형태는 백엔드마다 다르다 —
    - `sam3d_ss`: `(B, latent_channels, R/f, R/f, R/f)` dense
    - `dummy`: `(B, C, r, r, r)` dense (모양만 흉내)
    - `sam3d_slat`: `(N, latent_channels)` + 좌표 (미구현)
    """

    array: np.ndarray
    backend: str
    #: 학습 타깃이 무엇인지. sft.stage 와 맞아야 한다.
    stage: str
    meta: dict[str, Any]

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path, array=self.array, backend=np.array(self.backend), stage=np.array(self.stage)
        )
        return path

    @classmethod
    def load(cls, path: Path) -> Latent:
        data = np.load(path, allow_pickle=False)
        return cls(
            array=data["array"], backend=str(data["backend"]), stage=str(data["stage"]), meta={}
        )


class LatentEncoder(ABC):
    """occupancy → latent. 백엔드 교체 지점."""

    name: str = "abstract"
    stage: str = "geometry"

    @abstractmethod
    def encode(self, grid: OccupancyGrid) -> Latent:
        """occupancy 하나를 latent 로."""

    def encode_batch(self, grids: list[OccupancyGrid]) -> list[Latent]:
        """기본 구현은 순차 처리. GPU 백엔드는 배치로 오버라이드하면 된다."""
        return [self.encode(grid) for grid in grids]


class DummyLatentEncoder(LatentEncoder):
    """결정적 난수 latent. **CI·스모크 테스트 전용.**

    occupancy 를 해시해서 시드로 쓰므로 같은 메시는 항상 같은 latent 를 준다 — 학습 루프의
    결정성 테스트가 성립한다. 값 자체에는 의미가 없다.
    """

    name = "dummy"
    stage = "geometry"

    def __init__(self, latent_channels: int = 8, downsample: int = 4) -> None:
        self.latent_channels = latent_channels
        self.downsample = downsample

    def encode(self, grid: OccupancyGrid) -> Latent:
        import hashlib

        resolution = grid.resolution // self.downsample
        coords = grid.active_coords()
        # 내장 hash() 는 PYTHONHASHSEED 로 프로세스마다 달라진다 — 프로세스 간 결정성이
        # 필요하므로(체크포인트/재현 테스트) sha256 을 쓴다.
        digest = hashlib.sha256(coords.tobytes()).digest()[:4]
        rng = np.random.default_rng(int.from_bytes(digest, "little"))
        array = rng.standard_normal(
            (1, self.latent_channels, resolution, resolution, resolution)
        ).astype(np.float32)
        return Latent(
            array=array,
            backend=self.name,
            stage=self.stage,
            meta={"num_active": grid.num_active, "source_backend": grid.backend},
        )


class Sam3dSparseStructureEncoder(LatentEncoder):
    """stage 1 실인코더. `pipeline.models["ss_encoder"]` 를 그대로 쓴다.

    `SparseStructureEncoder.forward(x, sample_posterior=False, return_raw=False)` 는 dense
    `(B, in_channels, R, R, R)` 를 받아 `x.float()` 로 캐스팅한다(`sparse_structure_vae.py:84`).
    occupancy 는 `(1, R, R, R)` 이므로 **채널 축을 하나 넣어야 한다.**

    `SparseStructureEncoderTdfyWrapper` 는 같은 forward 를 감싸 `{"z": ...}` dict 를 돌려준다
    (`sparse_structure_vae.py:135`). 파이프라인이 어느 쪽을 로드하는지에 따라 반환형이 달라지므로
    **둘 다 받는다** — 추측이 아니라 두 클래스가 실제로 그렇게 생겼다.
    """

    name = "sam3d_ss"
    stage = "geometry"

    def __init__(self, encoder: Any, device: str = "cpu") -> None:
        """
        Args:
            encoder: `pipeline.models["ss_encoder"]`. 모듈을 직접 주입받는다 —
                파이프라인 로딩(수 GB)을 이 클래스가 책임지지 않게.
        """
        self.encoder = encoder
        self.device = device

    def encode(self, grid: OccupancyGrid) -> Latent:
        try:
            import torch
        except ImportError as exc:
            raise LatentEncodeError("sam3d_ss 백엔드는 torch 가 필요합니다.") from exc

        # (1, R, R, R) -> (1, 1, R, R, R)
        dense = torch.from_numpy(grid.grid.astype(np.float32))[:, None].to(self.device)
        with torch.no_grad():
            out = self.encoder(dense)
        if isinstance(out, dict):  # TdfyWrapper 경로
            if "z" not in out:
                raise LatentEncodeError(f"인코더 출력에 'z' 가 없습니다: {sorted(out)}")
            out = out["z"]
        return Latent(
            array=out.detach().float().cpu().numpy(),
            backend=self.name,
            stage=self.stage,
            meta={"num_active": grid.num_active, "source_backend": grid.backend},
        )


class Sam3dSlatEncoder(LatentEncoder):
    """stage 2 (SLat) 인코더 — **미구현 stub.**

    **가중치는 있다.** `checkpoints/hf/slat_encoder.ckpt` (173 MB) + `slat_encoder.yaml`:
    `SLatEncoderTdfyWrapper(resolution=64, model_channels=768, latent_channels=8,
    in_channels=1024, num_blocks=12, num_heads=12)`. 파이프라인이 instantiate 하지 않을 뿐
    hydra 로 직접 만들 수 있다.

    **없는 것은 입력을 만드는 단계다.** `in_channels=1024` 가 말해 주듯 이 인코더의 입력은
    occupancy 가 아니라 **활성 복셀별 1024차 시각 특징**이고, 1024 는 DINOv2 ViT-L 의
    embed_dim 이다(릴리스의 조건 임베더가 `dino.Dino(dino_model="dinov2_vitl14_reg")` 를 쓴다).
    특징 추출기 자체는 릴리스에 있지만, **GT 메시를 멀티뷰로 렌더해 그 특징을 복셀에 집계하는
    코드**(TRELLIS 계열 데이터 엔진)가 없다. 근거는 `REPORT.md` §4·5·6.

    TODO(집계 규약 확정 후):
    - 규약을 먼저 정한다 — **뷰 개수, 카메라 분포, DINOv2 어느 레이어의 출력, 복셀당 집계
      방식(평균/가시성 가중)**. 릴리스에 문서가 없어 추측하면 인코더 입력 분포가 학습 시와
      어긋나고, 그러면 latent 가 조용히 쓰레기가 된다.
    - 그다음: 멀티뷰 렌더 → `Dino` 특징 추출 → 복셀 집계 → `sp.SparseTensor` 구성 →
      `SLatEncoder(pretrained_ckpt_path=".../slat_encoder.ckpt")` 의 `forward()` 호출.
      ⚠️ 확장자가 `.safetensors` 면 `load_file()` 경로를 타는데 릴리스의
      `ss_encoder.safetensors` 가 0 바이트로 관측됐다 — `.ckpt` 를 쓰는 편이 안전하다.
    - 규약을 확정하지 못하면 stage 2 는 **범위에서 제외**하고 stage 1(기하)만 LoRA 학습한다.
      그 판단이 `configs/default.yaml` 의 `lora.target_models` 와 `sft.stage` 에 반영된다.
    """

    name = "sam3d_slat"
    stage = "texture"

    def encode(self, grid: OccupancyGrid) -> Latent:
        raise NotImplementedError(
            "SLat 인코딩 경로는 릴리스에 없습니다 (REPORT.md §4·5·6). 가중치는 있지만 "
            "입력 특징(멀티뷰 DINOv2 특징의 복셀 집계) 생성 규약이 공개되지 않았습니다 — "
            "추측 구현을 두지 않았습니다."
        )


def build_latent_encoder(backend: str, **kwargs) -> LatentEncoder:
    """config 의 `preprocess.latent_encoder` 로 인코더를 만든다."""
    if backend == "dummy":
        return DummyLatentEncoder(**kwargs)
    if backend == "sam3d_ss":
        if "encoder" not in kwargs:
            raise LatentEncodeError(
                "sam3d_ss 백엔드는 encoder=pipeline.models['ss_encoder'] 주입이 필요합니다."
            )
        return Sam3dSparseStructureEncoder(**kwargs)
    if backend == "sam3d_slat":
        return Sam3dSlatEncoder()
    raise LatentEncodeError(f"알 수 없는 latent 백엔드: {backend!r}")
