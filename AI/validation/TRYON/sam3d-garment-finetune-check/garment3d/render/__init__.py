"""렌더 — 턴테이블 프레임 생성과 저장."""

from .synthetic import SyntheticDefects, frames_to_masks, synth_i2v, synth_turntable
from .turntable import (
    DummyTurntableRenderer,
    RenderError,
    Sam3dTurntableRenderer,
    TurntableRenderer,
    build_renderer,
)
from .video import (
    WriteResult,
    load_png_sequence,
    save_frames,
    write_gif,
    write_mp4,
    write_png_sequence,
)

__all__ = [
    "DummyTurntableRenderer",
    "RenderError",
    "Sam3dTurntableRenderer",
    "SyntheticDefects",
    "TurntableRenderer",
    "WriteResult",
    "build_renderer",
    "frames_to_masks",
    "load_png_sequence",
    "save_frames",
    "synth_i2v",
    "synth_turntable",
    "write_gif",
    "write_mp4",
    "write_png_sequence",
]
