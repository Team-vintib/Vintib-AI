"""
게이트웨이 업로드/다운로드 HTTP 유틸.

워커(노트북)는 자기 디스크에 결과를 직접 쓰지 않는다 — 외부에서 접근 불가능하기 때문이다.
대신 게이트웨이의 `/workers/upload-image`로 전송하면 EC2 디스크에 저장되고 공개 URL이
돌아온다(S3 권한이 없어 대체한 경로, AI/docs/infra-architecture.md §3.5).

`base_worker.py`와 달리 클래스가 아니라 함수형이다 — 각 워커의 `run_inference()`에서
바로 호출해 쓰는 짧은 유틸이라 상태를 가질 필요가 없다.
"""

import io
import os

import requests
from PIL import Image

_GATEWAY_URL = os.getenv("GATEWAY_URL", "").rstrip("/")
_API_KEY = os.getenv("WORKER_API_KEY")


def _headers() -> dict[str, str]:
    return {"X-API-Key": _API_KEY} if _API_KEY else {}


def download_image(url: str, timeout: float = 30.0) -> Image.Image:
    """상품/사용자 이미지 URL을 내려받는다."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content))


def download_bytes(url: str, timeout: float = 60.0) -> bytes:
    """오디오/영상처럼 PIL로 열 수 없는 원본을 그대로 내려받는다(STT 워커용).

    타임아웃을 이미지보다 길게 잡은 이유: 방송 녹화 청크는 이미지보다 용량이 크다.
    """
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def upload_image(image: Image.Image, prefix: str, timeout: float = 30.0) -> str:
    """결과 이미지를 PNG로 인코딩해 게이트웨이에 올리고 공개 URL을 받는다."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    resp = requests.post(
        f"{_GATEWAY_URL}/workers/upload-image",
        params={"prefix": prefix},
        files={"file": ("result.png", buffer, "image/png")},
        headers=_headers(),
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["url"]
