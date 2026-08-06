"""GMS(SSAFY 공용 게이트웨이)·네이버 오픈API 접속 헬퍼.

가격 책정 검증 스파이크가 공유하는 얇은 계층이다. 키 로딩과 base URL만 담당하고
판정 로직은 갖지 않는다.

설계: .claude/plans/ai/CH002-pricing-model-selection.md

**GMS 모델 ID는 날짜 접미사가 붙은 정식 ID다.** 팀이 확인한 실제 호출 예시가
`claude-haiku-4-5-20251001` 이었다 — alias(`claude-haiku-4-5`)도 받는지는 미확인이므로
후보를 시도할 때 양쪽을 다 넣는다.

키는 환경변수 또는 `AI/.env` 에서 읽는다. python-dotenv를 의존성에 추가하지 않으려고
최소 파서를 직접 둔다(스파이크에서 라이브러리 하나 늘릴 이유가 없다).
"""

from __future__ import annotations

import os
from pathlib import Path

# provider마다 경로도 인증 헤더도 다르다. Anthropic은 x-api-key, Gemini는 x-goog-api-key.
GMS_ANTHROPIC_BASE = "https://gms.ssafy.io/gmsapi/api.anthropic.com"
GMS_GEMINI_BASE = "https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta"
GMS_OPENAI_BASE = "https://gms.ssafy.io/gmsapi/api.openai.com/v1"

NAVER_SHOP_URL = "https://openapi.naver.com/v1/search/shop.json"

# AI/.env — 이 파일 기준 세 단계 위(validation/PRICE/pricing-model-check/ → PRICE/ → validation/ → AI/)
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"

_env_loaded = False


def _load_env_file() -> None:
    """AI/.env 의 KEY=VALUE 줄을 os.environ 에 채운다(이미 있는 값은 덮지 않는다)."""
    global _env_loaded
    if _env_loaded or not _ENV_PATH.exists():
        _env_loaded = True
        return
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    _env_loaded = True


def get_key(name: str) -> str | None:
    _load_env_file()
    value = os.environ.get(name, "").strip()
    return value or None


def gms_key() -> str | None:
    return get_key("GMS_API_KEY")


def naver_keys() -> tuple[str | None, str | None]:
    return get_key("NAVER_CLIENT_ID"), get_key("NAVER_CLIENT_SECRET")


def anthropic_client(api_key: str):
    """공식 SDK에 GMS base_url만 갈아끼운다. 무거운 import는 호출 시점으로 미룬다."""
    import anthropic

    return anthropic.Anthropic(api_key=api_key, base_url=GMS_ANTHROPIC_BASE)


def gemini_post(api_key: str, model: str, method: str, body: dict, timeout: float = 90.0):
    """`{base}/models/{model}:{method}` 로 POST. method 예: generateContent, embedContent."""
    import httpx

    return httpx.post(
        f"{GMS_GEMINI_BASE}/models/{model}:{method}",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=timeout,
    )
