"""프레임 시퀀스 저장 — PNG 시퀀스 / GIF / mp4.

PNG 시퀀스는 **Pillow 만으로** 항상 저장된다(CI 에서도 된다). GIF/mp4 는 `imageio` 가 있을 때만
저장하고, 없으면 조용히 건너뛰지 않고 **무엇을 못 썼는지 결과에 남긴다.**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class WriteResult:
    """무엇이 저장됐고 무엇이 안 됐는지."""

    png_dir: Path | None = None
    gif_path: Path | None = None
    mp4_path: Path | None = None
    skipped: list[str] = field(default_factory=list)


def write_png_sequence(frames: np.ndarray, out_dir: Path, *, prefix: str = "frame") -> Path:
    """`out_dir/{prefix}_0000.png` 형태로 전 프레임 저장."""
    from PIL import Image

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        Image.fromarray(np.asarray(frame, dtype=np.uint8)).save(
            out_dir / f"{prefix}_{index:04d}.png"
        )
    return out_dir


def write_gif(frames: np.ndarray, path: Path, fps: int = 12) -> Path:
    """Pillow 로 GIF 저장 — imageio 없이도 된다."""
    from PIL import Image

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    images = [Image.fromarray(np.asarray(f, dtype=np.uint8)) for f in frames]
    if not images:
        raise ValueError("프레임이 없습니다")
    images[0].save(
        path,
        save_all=True,
        append_images=images[1:],
        duration=int(1000 / max(1, fps)),
        loop=0,
    )
    return path


def write_mp4(frames: np.ndarray, path: Path, fps: int = 12) -> Path:
    """imageio(+ffmpeg) 로 mp4 저장. 없으면 ImportError 를 그대로 올린다."""
    import imageio.v2 as imageio

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(path, [np.asarray(f, dtype=np.uint8) for f in frames], fps=fps)
    return path


def save_frames(
    frames: np.ndarray,
    out_dir: Path,
    stem: str,
    *,
    fps: int = 12,
    png_sequence: bool = True,
    gif: bool = True,
    mp4: bool = True,
) -> WriteResult:
    """가능한 형식으로 다 저장하고, 못 쓴 건 `skipped` 에 남긴다."""
    out_dir = Path(out_dir)
    result = WriteResult()

    if png_sequence:
        result.png_dir = write_png_sequence(frames, out_dir / stem)

    if gif:
        try:
            result.gif_path = write_gif(frames, out_dir / f"{stem}.gif", fps=fps)
        except Exception as exc:
            result.skipped.append(f"gif: {type(exc).__name__}: {exc}")

    if mp4:
        try:
            result.mp4_path = write_mp4(frames, out_dir / f"{stem}.mp4", fps=fps)
        except Exception as exc:
            # imageio-ffmpeg 미설치가 가장 흔하다. GIF 가 있으면 치명적이지 않다.
            result.skipped.append(f"mp4: {type(exc).__name__}: {exc}")

    return result


def load_png_sequence(directory: Path, *, prefix: str = "frame") -> np.ndarray:
    """`write_png_sequence` 산출물을 되읽는다."""
    from PIL import Image

    paths = sorted(Path(directory).glob(f"{prefix}_*.png"))
    if not paths:
        raise FileNotFoundError(f"{directory} 에 {prefix}_*.png 가 없습니다")
    return np.stack([np.asarray(Image.open(p).convert("RGB")) for p in paths])
