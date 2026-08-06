"""VideoGen(image-to-video) 어댑터 인터페이스.

턴테이블과 **같은 계약**으로 프레임을 내놓게 해서, 평가 하네스가 둘을 구분 없이 측정하게 한다.
`(T, H, W, 3) uint8` 이 그 계약이다.

start/end 키프레임과 depth 조건은 요청 스키마에 **자리를 만들어 둔다** — 제공자마다 지원 여부가
달라서, 어댑터가 `supports` 로 스스로 신고하고 하네스가 미지원 옵션을 조용히 무시하지 않도록
`I2vResponse.warnings` 에 남긴다.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..config import I2vConfig


class I2vError(RuntimeError):
    """I2V 생성을 수행할 수 없다."""


@dataclass
class I2vRequest:
    """I2V 요청. 이미지는 배열로 담고, 인코딩은 어댑터가 한다."""

    image: np.ndarray
    prompt: str = ""
    num_frames: int = 24
    fps: int = 12
    resolution: int = 256
    #: 끝 키프레임. 턴테이블은 한 바퀴가 닫히지만 I2V 는 안 닫히는 경우가 많아 필요하다.
    end_keyframe: np.ndarray | None = None
    #: depth 조건. 형태 변형을 억제하려는 목적.
    depth: np.ndarray | None = None
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.image.ndim != 3 or self.image.shape[-1] not in (3, 4):
            raise ValueError(f"image 형태가 (H, W, 3|4) 이 아닙니다: {self.image.shape}")
        if self.num_frames < 2:
            raise ValueError(f"num_frames 는 2 이상이어야 합니다: {self.num_frames}")


@dataclass
class I2vResponse:
    frames: np.ndarray
    backend: str
    latency_sec: float = 0.0
    #: 미지원 옵션·잘린 프레임 등. **빈 리스트가 아니면 지표 비교 전에 읽어야 한다.**
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class VideoGenAdapter(ABC):
    """image-to-video 제공자 어댑터."""

    name: str = "abstract"
    #: 이 어댑터가 실제로 지원하는 옵션 이름 집합.
    supports: frozenset[str] = frozenset()

    @abstractmethod
    def generate(self, request: I2vRequest) -> I2vResponse:
        """프레임을 만든다."""

    def check_unsupported(self, request: I2vRequest) -> list[str]:
        """요청에 담겼지만 이 어댑터가 못 쓰는 옵션 목록."""
        unsupported = []
        if request.end_keyframe is not None and "end_keyframe" not in self.supports:
            unsupported.append("end_keyframe 를 지원하지 않아 무시됩니다")
        if request.depth is not None and "depth" not in self.supports:
            unsupported.append("depth 조건을 지원하지 않아 무시됩니다")
        return unsupported


def resolve_api_key(config: I2vConfig, *, required: bool = True) -> str | None:
    """환경변수에서 API 키를 읽는다. **키를 config/코드에 적지 않는다.**

    Raises:
        I2vError: `required` 인데 환경변수가 비어 있을 때. 키 없이 호출해 402/401 을 받는
            것보다 먼저 죽는 게 낫다.
    """
    value = os.environ.get(config.api_key_env, "").strip()
    if not value and required:
        raise I2vError(
            f"환경변수 {config.api_key_env} 가 비어 있습니다 — "
            "I2V 어댑터는 키를 코드에 두지 않습니다."
        )
    return value or None


def request_from_config(
    image: np.ndarray,
    config: I2vConfig,
    *,
    end_keyframe: np.ndarray | None = None,
    depth: np.ndarray | None = None,
    seed: int | None = None,
) -> I2vRequest:
    """config 의 값으로 요청을 만든다. 옵션 플래그가 꺼져 있으면 조건 입력을 버린다."""
    return I2vRequest(
        image=image,
        prompt=config.prompt,
        num_frames=config.num_frames,
        fps=config.fps,
        resolution=config.resolution,
        end_keyframe=end_keyframe if config.use_end_keyframe else None,
        depth=depth if config.use_depth_condition else None,
        seed=seed,
    )
