"""I2V 어댑터 구현 — 더미 하나 + HTTP stub 하나.

⚠️ **비용 규율**: 외부 VideoGen API 는 호출당 과금이다. `AI/CLAUDE.md` 의 하드 룰에 따라
`HttpStubAdapter` 는 **기본 비활성**이고, 실제 전송 코드는 의도적으로 미구현이다. 테스트는
`DummyI2vAdapter` 만 쓴다. 실호출은 사용자가 제공자 규격을 채운 뒤 직접 켠다.
"""

from __future__ import annotations

import base64
import io
import time
from typing import Any

import numpy as np

from ..config import I2vConfig
from ..render.synthetic import SyntheticDefects, synth_i2v
from .base import I2vError, I2vRequest, I2vResponse, VideoGenAdapter, resolve_api_key


class DummyI2vAdapter(VideoGenAdapter):
    """합성 I2V 출력. **첫 프레임은 입력과 동일**하고 뒤로 갈수록 흐트러진다.

    실제 I2V 의 전형적 실패 모드를 흉내내므로, "turntable 이 I2V 보다 형태 일관성이 높다"는
    비교 결과가 하네스에서 실제로 재현되는지 확인할 수 있다.
    """

    name = "dummy"
    supports = frozenset({"end_keyframe", "depth"})

    def __init__(self, defects: SyntheticDefects | None = None, seed: int = 0) -> None:
        self.defects = defects
        self.seed = seed

    def generate(self, request: I2vRequest) -> I2vResponse:
        started = time.perf_counter()
        frames = synth_i2v(
            np.asarray(request.image[..., :3], dtype=np.uint8),
            num_frames=request.num_frames,
            defects=self.defects,
            seed=request.seed if request.seed is not None else self.seed,
        )
        return I2vResponse(
            frames=frames,
            backend=self.name,
            latency_sec=time.perf_counter() - started,
            warnings=self.check_unsupported(request),
            raw={"synthetic": True},
        )


def encode_png_base64(image: np.ndarray) -> str:
    """이미지를 base64 PNG 문자열로. 대부분의 VideoGen API 가 이 형식을 받는다."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.fromarray(np.asarray(image[..., :3], dtype=np.uint8)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class HttpStubAdapter(VideoGenAdapter):
    """일반적인 HTTP VideoGen API 어댑터 **stub**.

    `build_payload()` 와 키 확인은 실제로 동작하고 테스트된다. 전송·폴링·응답 파싱은
    제공자마다 다르므로 **추측으로 채우지 않았다**.

    TODO(제공자 확정 후):
    - `submit()`: `POST {endpoint}` 로 payload 를 보내고 job id 를 받는다.
    - `poll()`: job 상태를 폴링해 완료 시 비디오 URL/바이트를 얻는다.
    - `decode()`: mp4 바이트 → `(T, H, W, 3) uint8` (imageio 로 디코드).
    - 실패 코드(쿼터·안전필터·해상도 제한)를 `I2vError` 로 매핑한다.
    """

    name = "http_stub"
    #: 제공자가 지원한다고 확인되면 여기에 추가한다. 지금은 아무것도 보장하지 않는다.
    supports = frozenset()

    def __init__(self, config: I2vConfig) -> None:
        self.config = config
        # 키 존재 확인만 먼저 한다 — payload 를 다 만들고 401 을 받는 낭비를 막는다.
        self.api_key = resolve_api_key(config, required=False)

    def build_payload(self, request: I2vRequest) -> dict[str, Any]:
        """전송 payload. 제공자 공통으로 보이는 필드만 담고, 조건 입력은 있으면 넣는다.

        키 이름은 제공자에 맞춰 바꿔야 한다 — 이 함수가 그 **한 곳**이다.
        """
        payload: dict[str, Any] = {
            "model": self.config.model,
            "prompt": request.prompt,
            "image": encode_png_base64(request.image),
            "num_frames": request.num_frames,
            "fps": request.fps,
            "resolution": request.resolution,
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.end_keyframe is not None:
            payload["end_image"] = encode_png_base64(request.end_keyframe)
        if request.depth is not None:
            payload["depth_image"] = encode_png_base64(request.depth)
        return payload

    def generate(self, request: I2vRequest) -> I2vResponse:
        if not self.config.endpoint:
            raise I2vError(
                "i2v.endpoint 가 비어 있습니다 — HttpStubAdapter 는 제공자 확정 후에만 씁니다."
            )
        if not self.api_key:
            raise I2vError(f"환경변수 {self.config.api_key_env} 가 비어 있습니다.")
        _payload = self.build_payload(request)
        raise NotImplementedError(
            "HTTP 전송·폴링·디코딩은 제공자 규격 확정 후 구현합니다 "
            "(adapters.py::HttpStubAdapter 의 TODO 참고). "
            "외부 API 는 호출당 과금이라 추측 구현을 두지 않았습니다."
        )


def build_i2v_adapter(config: I2vConfig) -> VideoGenAdapter:
    """config 의 `i2v.backend` 로 어댑터를 만든다. 기본은 `dummy`(무과금)."""
    if config.backend == "dummy":
        return DummyI2vAdapter()
    if config.backend == "http_stub":
        return HttpStubAdapter(config)
    raise I2vError(f"알 수 없는 i2v 백엔드: {config.backend!r}")
