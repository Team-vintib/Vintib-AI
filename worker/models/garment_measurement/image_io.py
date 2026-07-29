"""이미지 다운로드 — 실측 파이프라인 공용.

**워커 공용 `storage_utils.download_image`를 쓰지 않는다.** `worker/models/garment_measurement/`는
AI의 pytest 세션에도 import된다(순수 로직 커버용, `AI/test/conftest.py` 참고). `storage_utils`는
`worker/` 최상단에 있어서 그 경로가 sys.path에 없는 테스트 환경에서는 import가 깨진다 —
`worker/models/clipseg/segmenter.py`의 `load_source_image()`가 같은 이유로 독자 구현해 둔 선례를
그대로 따른다(다만 이쪽은 기준물체 검출/원단 분할/랜드마크 검출 세 단계가 전부 이 로더를 쓰므로
중복하지 않고 공용 모듈로 뺐다).
"""

from __future__ import annotations

import io
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

_FETCH_TIMEOUT_SECONDS = 10.0
_FETCH_MAX_BYTES = 20 * 1024 * 1024


class ImageFetchFailed(Exception):
    """실측 대상 이미지를 가져오지 못함."""


def load_image(url: str) -> Image.Image:
    """실측 대상 이미지를 RGB로 읽는다. HTTP(S) URL과 로컬 경로를 모두 받는다."""
    try:
        if url.startswith(("http://", "https://")):
            request = urllib.request.Request(
                url, headers={"User-Agent": "vintib-ai-measurement/0.1"}
            )
            with urllib.request.urlopen(  # noqa: S310 - BE가 준 상품 이미지 URL을 대신 가져온다
                request, timeout=_FETCH_TIMEOUT_SECONDS
            ) as response:
                payload = response.read(_FETCH_MAX_BYTES + 1)
            if len(payload) > _FETCH_MAX_BYTES:
                raise ImageFetchFailed(f"이미지가 너무 큽니다(>{_FETCH_MAX_BYTES}B): {url}")
            return Image.open(io.BytesIO(payload)).convert("RGB")
        return Image.open(Path(url)).convert("RGB")
    except ImageFetchFailed:
        raise
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise ImageFetchFailed(f"이미지를 읽을 수 없습니다: {url} ({exc})") from exc
