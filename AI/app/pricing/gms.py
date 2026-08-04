"""GMS(SSAFY 공용 LLM 게이트웨이) 호출 계층.

네트워크만 담당한다 — 프롬프트도 판정도 여기 없다. `comps.py`가 파싱·판정을 맡고, 그래서
그 함수들은 네트워크 없이 CI에서 그대로 테스트된다.

**메인 시세 검색 모델을 Gemini로 전환**(2026-07-31). 이전에는 Claude(`claude-haiku-4-5`)를
Anthropic Messages API로 호출했으나, 이번 라운드부터 Gemini(`gemini-3.5-flash`)를
`generateContent` + `google_search` 그라운딩으로 호출한다. Anthropic Messages API와는
엔드포인트(`v1beta`)·인증 헤더(`x-goog-api-key`)·요청 바디(`contents`+`tools.google_search`)가
전부 달라 공식 SDK 대신 `httpx.post()`를 직접 쓴다 — SDK가 굳이 필요 없을 만큼 요청이
단순하다. `validation/PRICE/pricing-model-check/gms_client.py`의 `gemini_post()`와 같은
값이지만 **import하지 않고 복사한다** — `validation/`을 프로덕션에서 참조하지 않는 규약.

⚠️ Gemini 쪽은 아직 comps 커버리지(V2 스타일 실측)가 없다 — LAB-47(웹검색 테스트)이 확인한
건 "GMS가 `google_search` 그라운딩을 통과시킨다"(V1, 쿼리 1건 grounding 9건)뿐이고, Claude
haiku처럼 여러 쿼리로 평균 comps 건수·중고 비율을 잰 적은 없다. `registry.py`의
`min_comps_for_pricing`이 보수적인 이유.

설계: .claude/plans/ai/CH003-pricing-service-prototype.md
"""

from __future__ import annotations

GMS_GEMINI_BASE = "https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta"


class GmsError(RuntimeError):
    """GMS 호출 실패. `status`는 HTTP 상태(네트워크 오류면 None)."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def generate_content(
    *,
    api_key: str,
    model: str,
    prompt: str,
    timeout: float = 90.0,
    max_output_tokens: int = 0,
) -> dict:
    """`POST /models/{model}:generateContent` 1회, `google_search` 그라운딩 포함.

    응답 JSON을 그대로 돌려준다 — 그라운딩 여부 판정(`groundingMetadata`)과 텍스트 추출은
    `comps.py`가 한다. 무거운 import(`httpx`)를 함수 안에 두는 이유는 모듈 로딩 시점을 늦추기
    위해서다 — comps 백엔드가 mock이면 이 함수 자체가 호출되지 않는다.

    `max_output_tokens`(0이면 지정 안 함)를 CH017에서 추가했다 — 이전에는 상한이 없어 응답이
    중간에 잘려도 알 방법이 없었다. `finishReason`(`STOP`/`MAX_TOKENS` 등)은 응답 JSON에
    그대로 들어 있으므로 이 함수에서 추출하지 않는다 — 판정은 `comps.py`의 몫이다.
    """
    import httpx

    body: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
    }
    if max_output_tokens > 0:
        body["generationConfig"] = {"maxOutputTokens": max_output_tokens}
    try:
        response = httpx.post(
            f"{GMS_GEMINI_BASE}/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=body,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 — 네트워크·타임아웃 등, 원인 그대로 감싸 올린다
        raise GmsError(f"GMS 호출 실패: {type(exc).__name__}") from exc

    if response.status_code != 200:
        raise GmsError(f"GMS 응답 오류({response.status_code})", status=response.status_code)
    return response.json()
