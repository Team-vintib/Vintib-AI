"""턴테이블 렌더 — mesh/gaussian → N 시점 프레임 → 이미지 시퀀스/GIF/mp4.

백엔드 2개다.

- `sam3d` — upstream `notebook/inference.py::render_video` 위임. ⚠️ 그 모듈은 최상단에서
  `os.environ["CUDA_HOME"] = os.environ["CONDA_PREFIX"]` 를 실행하고 `kaolin`/`gradio`/
  `pytorch3d` 를 무조건 import 한다(`REPORT.md` §11). **conda 환경 밖에서는 import 자체가
  실패한다** — 그래서 함수 안에서 lazy import 한다.
- `dummy` — 합성 프레임(`synthetic.py`). 의존성 없이 평가 하네스를 끝까지 돌린다.

I2V 와 비교하려면 **프레임 수와 해상도를 맞춰야 한다** — `RenderConfig` 와 `I2vConfig` 의
`num_frames`/`resolution` 이 어긋나면 지표가 비교되지 않으므로 `harness` 가 확인한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

from ..config import RenderConfig
from .synthetic import SyntheticDefects, synth_turntable


class RenderError(RuntimeError):
    """렌더를 수행할 수 없다."""


class TurntableRenderer(ABC):
    """3D 산출물 → 프레임 시퀀스."""

    name: str = "abstract"

    @abstractmethod
    def render(self, model_output: Any, config: RenderConfig) -> np.ndarray:
        """`(T, H, W, 3) uint8` 프레임을 돌려준다."""


class DummyTurntableRenderer(TurntableRenderer):
    """합성 턴테이블. `model_output` 은 시드로만 쓰인다."""

    name = "dummy"

    def __init__(self, defects: SyntheticDefects | None = None, seed: int = 0) -> None:
        self.defects = defects
        self.seed = seed

    def render(self, model_output: Any, config: RenderConfig) -> np.ndarray:
        seed = self.seed
        if isinstance(model_output, (int, np.integer)):
            seed = int(model_output)
        elif isinstance(model_output, str):
            # 내장 hash() 는 프로세스마다 값이 달라 재현이 깨진다 — sha256 으로 고정한다.
            import hashlib

            digest = hashlib.sha256(model_output.encode("utf-8")).digest()[:4]
            seed = int.from_bytes(digest, "little")
        return synth_turntable(
            num_frames=config.num_frames,
            resolution=config.resolution,
            yaw_start_deg=config.yaw_start_deg,
            defects=self.defects,
            seed=seed,
        )


class Sam3dTurntableRenderer(TurntableRenderer):
    """upstream `render_video` 위임.

    `model_output` 은 `Inference.__call__` 의 반환 dict 다. upstream 데모와 같은 순서로
    `make_scene` → `ready_gaussian_for_video_rendering` → `render_video(...)["color"]` 를 쓴다.
    """

    name = "sam3d"

    def __init__(self, sam3d_repo: Path) -> None:
        self.sam3d_repo = Path(sam3d_repo).expanduser()

    def _import_inference(self) -> Any:
        import sys

        notebook_dir = self.sam3d_repo / "notebook"
        if not notebook_dir.is_dir():
            raise RenderError(f"{notebook_dir} 가 없습니다 — paths.sam3d_repo 를 확인하세요.")
        if str(notebook_dir) not in sys.path:
            sys.path.insert(0, str(notebook_dir))
        try:
            import inference as sam3d_inference
        except Exception as exc:  # kaolin/gradio/CUDA_HOME 등 다양하게 터진다
            raise RenderError(
                "upstream notebook/inference.py 를 import 하지 못했습니다 — "
                "sam3d-objects conda 환경에서 실행해야 합니다 "
                f"({type(exc).__name__}: {exc})"
            ) from exc
        return sam3d_inference

    def render(self, model_output: Any, config: RenderConfig) -> np.ndarray:
        module = self._import_inference()
        scene = module.make_scene(model_output)
        scene = module.ready_gaussian_for_video_rendering(scene)
        frames = module.render_video(
            scene,
            r=config.radius,
            fov=config.fov,
            pitch_deg=config.pitch_deg,
            yaw_start_deg=config.yaw_start_deg,
            resolution=config.resolution,
        )["color"]
        return _as_uint8_frames(frames)


def _as_uint8_frames(frames: Any) -> np.ndarray:
    """리스트/텐서/float 프레임을 `(T, H, W, 3) uint8` 로 정규화한다."""
    if hasattr(frames, "detach"):  # torch tensor
        frames = frames.detach().cpu().numpy()
    array = np.asarray(frames)
    if array.dtype != np.uint8:
        # float 프레임은 [0,1] 또는 [0,255] 둘 다 있어서 최댓값으로 판별한다.
        maximum = float(array.max()) if array.size else 1.0
        scale = 255.0 if maximum <= 1.0 + 1e-6 else 1.0
        array = np.clip(array * scale, 0, 255).astype(np.uint8)
    if array.ndim == 4 and array.shape[1] in (3, 4) and array.shape[-1] not in (3, 4):
        array = np.transpose(array, (0, 2, 3, 1))  # (T, C, H, W) -> (T, H, W, C)
    return array[..., :3]


def build_renderer(config: RenderConfig, sam3d_repo: Path | None = None) -> TurntableRenderer:
    """config 의 `render.backend` 로 렌더러를 만든다."""
    if config.backend == "dummy":
        return DummyTurntableRenderer()
    if config.backend == "sam3d":
        if sam3d_repo is None:
            raise RenderError("sam3d 백엔드는 paths.sam3d_repo 가 필요합니다.")
        return Sam3dTurntableRenderer(sam3d_repo)
    raise RenderError(f"알 수 없는 렌더 백엔드: {config.backend!r}")
