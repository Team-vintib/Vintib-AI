"""V1 — GMS 프록시가 서버사이드 웹검색을 통과시키는지 점검한다.

가격 책정 파이프라인의 시세 수집(슬롯 B) 후보 중 "LLM 내장 웹검색"이 가능한지가 나머지
설계를 좌우한다. 이 스크립트는 그 판정만 한다 — comps 품질 측정은 V2(evaluate.py)의 몫이다.

설계: .claude/plans/ai/CH002-pricing-model-selection.md

세 층으로 나눠 확인한다. 층마다 실패 원인이 다르므로 결과도 따로 보고한다.

    1. 모델 노출   GMS가 그 ID를 받아주는가            → 실패 시 404
    2. 툴 통과     프록시가 서버툴 선언을 넘기는가       → 실패 시 400
    3. 검색 실행   상위 계정에 웹검색이 켜져 있는가      → 실패해도 HTTP 200

3층을 따로 두는 이유: **서버사이드 툴 오류는 예외로 올라오지 않는다.** HTTP 200 응답의
`web_search_tool_result` 블록에 담겨 오는데, 성공이면 `content`가 결과 리스트이고 실패면
`error_code`를 가진 객체다. 2층만 보고 "된다"고 판단하면 안 된다.

프롬프트도 판정에 관여한다. 모델이 학습 데이터만으로 답할 수 있는 질문을 주면 툴이
지원되더라도 호출하지 않아 **거짓 음성**이 난다. PROBE는 최신성이 필수인 질문이어야 한다.

실행:
    export GMS_API_KEY=...        # Windows PowerShell: $env:GMS_API_KEY = "..."
    python validation/pricing-model-check/smoke_gms.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from gms_client import GMS_GEMINI_BASE, anthropic_client, gemini_post, gms_key

# **기본 후보는 최저가 모델 하나뿐이다.** 상위 모델은 같은 질문에도 검색 라운드를 훨씬 많이
# 돌아 비용이 급증한다 — 후보 목록에 두지 않고 `--model` 로 명시할 때만 호출되게 한다
# (AI/CLAUDE.md 하드 룰: 후보 순회로 고가 모델이 자동 호출된 사고가 있었다).
ANTHROPIC_CANDIDATES = ["claude-haiku-4-5-20251001"]
GEMINI_CANDIDATES = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]

# 최신 변형(dynamic filtering)은 Opus 4.6+ / Sonnet 4.6+ 에서만 동작한다.
# 400이 나면 구형으로 폴백해야 하므로 순서대로 시도한다.
WEB_SEARCH_TOOL_TYPES = ["web_search_20260209", "web_search_20250305"]

# Gemini는 규격이 아예 다르다. 신버전이 google_search, 구버전이 google_search_retrieval.
GEMINI_TOOL_KEYS = ["google_search", "google_search_retrieval"]

# 학습 데이터로 답할 수 없어야 실제로 툴을 호출한다. 시세·등록일처럼 최신성이 필수인 질문.
PROBE = (
    "지금 번개장터와 당근마켓에서 거래 중인 '리바이스 501 빅E' 중고 시세를 웹에서 검색해서, "
    "최근 매물 3건의 가격과 등록일을 알려줘."
)


@dataclass
class Verdict:
    """한 (모델, 툴 규격) 조합의 판정 결과."""

    provider: str
    model: str
    tool: str
    layer: int  # 어느 층까지 통과했는지 (1=노출, 2=툴 통과, 3=검색 실행)
    detail: str
    results: int = 0

    @property
    def ok(self) -> bool:
        return self.layer >= 3 and self.results > 0

    def __str__(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        return f"[{mark}] L{self.layer} {self.provider}/{self.model} ({self.tool}) — {self.detail}"


def list_anthropic_models(api_key: str) -> list[str]:
    """GMS가 /v1/models 를 프록시하면 노출 목록을 그대로 돌려준다.

    프록시가 /v1/messages 만 화이트리스트했다면 404가 난다 — 그건 장애가 아니라 정상적인
    제약이므로, 그 경우 후보 ID를 직접 찔러 보는 것으로 대체한다(probe_anthropic).
    """
    import anthropic

    try:
        return [m.id for m in anthropic_client(api_key).models.list()]
    except anthropic.APIStatusError as exc:
        print(f"  models.list() 미지원({exc.status_code}) — 후보 ID를 직접 시도한다")
        return []
    except Exception as exc:  # 프록시가 비정형 응답을 줄 수 있다
        print(f"  models.list() 실패: {type(exc).__name__}: {exc}")
        return []


def list_gemini_models(api_key: str) -> list[str]:
    import httpx

    try:
        resp = httpx.get(
            f"{GMS_GEMINI_BASE}/models", headers={"x-goog-api-key": api_key}, timeout=30.0
        )
        resp.raise_for_status()
        return [m.get("name", "") for m in resp.json().get("models", [])]
    except Exception as exc:
        print(f"  Gemini models 목록 실패: {type(exc).__name__}: {exc}")
        return []


def probe_anthropic(api_key: str, model: str, tool_type: str) -> Verdict:
    """Claude 서버툴 web_search 를 선언하고 3층까지 판정한다."""
    import anthropic

    try:
        resp = anthropic_client(api_key).messages.create(
            model=model,
            max_tokens=2048,
            tools=[{"type": tool_type, "name": "web_search"}],
            messages=[{"role": "user", "content": PROBE}],
        )
    except anthropic.NotFoundError:
        return Verdict("anthropic", model, tool_type, 0, "모델 ID를 GMS가 모른다(404)")
    except anthropic.APIStatusError as exc:
        # 400이면 프록시나 상위 API가 툴 선언 자체를 거부한 것 — 2층 실패.
        return Verdict("anthropic", model, tool_type, 1, f"툴 선언 거부({exc.status_code}) {exc}")
    except Exception as exc:
        return Verdict("anthropic", model, tool_type, 0, f"{type(exc).__name__}: {exc}")

    called = False
    results = 0
    errors: list[str] = []

    for block in resp.content:
        btype = getattr(block, "type", "")
        if btype == "server_tool_use":
            called = True
        elif btype == "web_search_tool_result":
            content = block.content
            # 성공이면 list, 실패면 error_code 를 가진 단일 객체다. 반드시 타입으로 분기한다.
            if isinstance(content, list):
                results += len(content)
            else:
                errors.append(str(getattr(content, "error_code", content)))

    if errors:
        return Verdict("anthropic", model, tool_type, 2, f"툴은 통과, 검색 실패: {errors}")
    if not called:
        # 툴이 거부되진 않았지만 모델이 호출을 안 했다. PROBE가 약했거나 미지원이거나.
        return Verdict(
            "anthropic", model, tool_type, 2, "툴 선언은 통과했으나 호출 안 함(판정 보류)"
        )

    note = "" if resp.stop_reason != "pause_turn" else " (pause_turn — 이어받기 필요)"
    return Verdict("anthropic", model, tool_type, 3, f"검색 결과 {results}건{note}", results)


def probe_gemini(api_key: str, model: str, tool_key: str) -> Verdict:
    """Gemini grounding 을 선언하고 groundingMetadata 유무로 판정한다."""
    body = {
        "contents": [{"parts": [{"text": PROBE}]}],
        "tools": [{tool_key: {}}],
    }
    try:
        resp = gemini_post(api_key, model, "generateContent", body)
    except Exception as exc:
        return Verdict("gemini", model, tool_key, 0, f"{type(exc).__name__}: {exc}")

    if resp.status_code == 404:
        return Verdict("gemini", model, tool_key, 0, "모델 ID를 GMS가 모른다(404)")
    if resp.status_code != 200:
        return Verdict(
            "gemini", model, tool_key, 1, f"툴 선언 거부({resp.status_code}) {resp.text[:200]}"
        )

    candidates = resp.json().get("candidates", [])
    if not candidates:
        return Verdict("gemini", model, tool_key, 2, "응답에 candidates 없음")

    meta = candidates[0].get("groundingMetadata") or {}
    chunks = meta.get("groundingChunks") or []
    queries = meta.get("webSearchQueries") or []
    if not chunks and not queries:
        return Verdict(
            "gemini", model, tool_key, 2, "툴 선언은 통과했으나 grounding 미발생(판정 보류)"
        )

    return Verdict(
        "gemini", model, tool_key, 3, f"grounding {len(chunks)}건 / 쿼리 {queries}", len(chunks)
    )


def _probe_provider(candidates: list[str], tools: list[str], probe) -> list[Verdict]:
    """모델 × 툴 규격을 순회하되, **한 조합이라도 통과하면 즉시 멈춘다.**

    이 스크립트의 질문은 "이 provider로 웹검색이 되는가"이지 "어느 모델이 더 잘하는가"가
    아니다. 모델 비교는 `comps_sources.py --model` 로 사용자가 명시할 때만 한다.

    중단하지 않으면 앞 후보가 통과했는데도 뒤 후보까지 전부 호출된다 — 실제로 이 때문에
    의도치 않은 고가 모델 호출 사고가 있었다(AI/CLAUDE.md 하드 룰 참고).
    """
    verdicts: list[Verdict] = []
    for index, model in enumerate(candidates):
        for tool in tools:
            verdict = probe(model, tool)
            print(f"  {verdict}")
            verdicts.append(verdict)
            if verdict.ok:
                remaining = candidates[index + 1 :]
                if remaining:
                    print(f"  → 통과했으므로 나머지 후보는 호출하지 않는다: {remaining}")
                return verdicts
    return verdicts


def main() -> int:
    api_key = gms_key()
    if not api_key:
        print("GMS_API_KEY 가 없다. 키를 설정한 뒤 다시 실행할 것.")
        return 2

    print("\n[1층] GMS 노출 모델 목록")
    for name in list_anthropic_models(api_key):
        print(f"  anthropic: {name}")
    for name in list_gemini_models(api_key):
        print(f"  gemini: {name}")

    print("\n[2·3층] Anthropic web_search")
    verdicts = _probe_provider(
        ANTHROPIC_CANDIDATES,
        WEB_SEARCH_TOOL_TYPES,
        lambda m, t: probe_anthropic(api_key, m, t),
    )

    print("\n[2·3층] Gemini grounding")
    verdicts += _probe_provider(
        GEMINI_CANDIDATES,
        GEMINI_TOOL_KEYS,
        lambda m, t: probe_gemini(api_key, m, t),
    )

    passed = [v for v in verdicts if v.ok]
    print("\n=== 판정 ===")
    if passed:
        print("LLM 내장 웹검색 사용 가능. 아래 조합을 슬롯 B 후보로 레지스트리에 올린다:")
        for v in passed:
            print(f"  - {v.provider}/{v.model} ({v.tool})")
        return 0

    print("LLM 내장 웹검색 불가. 슬롯 B는 외부 검색 API(네이버 쇼핑 등)로 간다.")
    print("실패가 400/404가 아니라 '호출 안 함'이면 PROBE를 더 최신성 의존적으로 바꿔 재시도할 것.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
