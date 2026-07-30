"""GMS(SSAFY 공용 LLM 게이트웨이) 호출 계층.

네트워크만 담당한다 — 프롬프트도 판정도 여기 없다. `comps.py`가 파싱·판정을 맡고, 그래서
그 함수들은 네트워크 없이 CI에서 그대로 테스트된다.

GMS는 `api.anthropic.com`으로 넘기는 얇은 프록시라 요청 본문이 Anthropic 규격 그대로다.
따라서 base URL만 갈아끼우고 공식 SDK를 쓴다. `validation/PRICE/pricing-model-check/gms_client.py`와
같은 값이지만 **import하지 않고 복사한다** — `validation/`을 프로덕션에서 참조하지 않는 규약.

⚠️ **timeout·max_retries를 반드시 명시한다.** SDK 기본값이 timeout 10분 / max_retries 2라,
그대로 두면 job 하나가 최악 30분간 백그라운드 스레드를 붙잡는다. 동시 실행 상한이 2뿐이라
그동안 가격 산정이 전면 정지한다.

설계: .claude/plans/ai/CH003-pricing-service-prototype.md
"""

from __future__ import annotations

from typing import Any

GMS_ANTHROPIC_BASE = "https://gms.ssafy.io/gmsapi/api.anthropic.com"

# SDK 기본 재시도(2회)는 429/5xx에만 걸리고 400에는 안 걸린다. 툴 규격 폴백은 우리가 하므로
# 재시도는 1회로 줄인다 — 웹검색은 호출마다 과금이라 자동 재시도를 늘릴 이유가 없다.
_MAX_RETRIES = 1


class GmsError(RuntimeError):
    """GMS 호출 실패. `status`는 HTTP 상태(네트워크 오류면 None).

    툴 규격 폴백이 400 여부로 갈리므로 상태 코드를 보존한다.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def messages_create(
    *,
    api_key: str,
    model: str,
    prompt: str,
    tools: list[dict[str, Any]] | None = None,
    max_tokens: int = 4096,
    timeout: float = 90.0,
) -> Any:
    """`POST /v1/messages` 1회. 응답 객체를 그대로 돌려준다.

    무거운 import를 함수 안에 두는 이유는 모듈 로딩 시점을 늦추기 위해서다 — comps 백엔드가
    mock이면 `anthropic`을 아예 건드리지 않는다.
    """
    import anthropic

    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=GMS_ANTHROPIC_BASE,
        timeout=timeout,
        max_retries=_MAX_RETRIES,
    )
    try:
        return client.messages.create(
            model=model,
            max_tokens=max_tokens,
            tools=tools or [],
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as exc:
        raise GmsError(f"GMS 응답 오류({exc.status_code})", status=exc.status_code) from exc
    except Exception as exc:  # 네트워크·타임아웃 등
        raise GmsError(f"GMS 호출 실패: {type(exc).__name__}") from exc
