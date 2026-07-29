"""V1 — GMS 프록시가 서버사이드 웹검색을 통과시키는지 점검한다.

가격 책정 파이프라인의 시세 수집(슬롯 B) 후보 중 "LLM 내장 웹검색"이 가능한지가 나머지
설계를 좌우한다. 이 스크립트는 그 판정만 한다 — comps 품질 측정은 V2(evaluate.py)의 몫이다.

설계: .claude/plans/ai/CH002-pricing-model-selection.md

네 층으로 나눠 확인한다. 층마다 실패 원인이 다르므로 결과도 따로 보고한다.

    0. 연결       키와 게이트웨이가 살아 있는가         → 실패 시 401/403
    1. 모델 노출   GMS가 그 ID를 받아주는가            → 실패 시 404
    2. 툴 통과     프록시가 서버툴 선언을 넘기는가       → 실패 시 400
    3. 검색 실행   상위 계정에 웹검색이 켜져 있는가      → 실패해도 HTTP 200

**0층을 따로 두는 이유**: 웹검색이 실패했을 때 그게 키 문제인지 툴 문제인지 구분해야 한다.
provider마다 인증 헤더가 다르므로(Anthropic `x-api-key` / Gemini `x-goog-api-key`) 양쪽을
각각 가장 단순한 호출로 찔러 본다 — Anthropic은 툴 없는 messages 1건, Gemini는 embedContent.

> **임베딩 모델은 웹검색 후보가 아니다.** `gemini-embedding-2` 는 텍스트를 벡터로 바꿔
> 돌려줄 뿐 검색·답변·툴 호출을 하지 못한다. 여기서는 **Gemini 쪽 인증이 사는지 확인하는
> 최소 호출**로만 쓴다. 이 모델의 진짜 용도는 슬롯 D(comps 유사도 필터)다.

**3층을 따로 두는 이유**: 서버사이드 툴 오류는 예외로 올라오지 않는다. HTTP 200 응답의
`web_search_tool_result` 블록에 담겨 오는데, 성공이면 `content`가 결과 리스트이고 실패면
`error_code`를 가진 객체다. 2층만 보고 "된다"고 판단하면 안 된다.

프롬프트도 판정에 관여한다. 모델이 학습 데이터만으로 답할 수 있는 질문을 주면 툴이
지원되더라도 호출하지 않아 **거짓 음성**이 난다. PROBE는 최신성이 필수인 질문이어야 한다.

실행:
    # 키는 AI/.env 의 GMS_API_KEY 를 자동으로 읽는다
    python validation/pricing-model-check/smoke_gms.py --quick   # 0층만 (연결 확인)
    python validation/pricing-model-check/smoke_gms.py           # 전체
    python validation/pricing-model-check/smoke_gms.py --model claude-haiku-4-5-20251001
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from gms_client import GMS_GEMINI_BASE, anthropic_client, gemini_post, gms_key

# 0층 연결 확인용. 팀이 실제로 호출해 본 두 엔드포인트를 그대로 쓴다.
CONNECT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
CONNECT_GEMINI_EMBEDDING = "gemini-embedding-2"

# **기본 후보는 최저가 모델 하나뿐이다.** 상위 모델은 같은 질문에도 검색 라운드를 훨씬 많이
# 돌아 비용이 급증한다 — 후보 목록에 두지 않고 `--model` 로 명시할 때만 호출되게 한다
# (AI/CLAUDE.md 하드 룰: 후보 순회로 고가 모델이 자동 호출된 사고가 있었다).
ANTHROPIC_CANDIDATES = ["claude-haiku-4-5-20251001"]

# GMS의 Gemini 세대 표기가 섞여 있다 — `gemini-3.5-flash` 는 동작했고
# `gemini-3.5-flash-lite` 는 400(`not available in Model`)이었는데, lite 계열의 실제 이름은
# `gemini-2.5-flash-lite` 다. 싼 것부터 시도한다.
GEMINI_CANDIDATES = [
    "gemini-2.5-flash-lite",  # 미검증 — grounding 지원 여부를 이번에 확인한다
    "gemini-3.5-flash",  # grounding 실측 확인됨(9건)
]

# Anthropic **서버사이드 툴의 타입 식별자**다. GMS 문서에 없는 이유는 GMS가 단순 프록시라
# 요청 본문이 Anthropic 규격 그대로이기 때문 — 출처는 Anthropic API 쪽이다.
# 날짜는 릴리스 버전이며(도구 스키마가 바뀌어도 기존 연동이 안 깨지도록 날짜로 고정),
# `text_editor_20250728` `bash_20250124` 처럼 서버툴 전반이 같은 규칙을 쓴다.
#
#   web_search_20250305   기본형. 검색 결과가 그대로 컨텍스트에 들어온다.
#   web_search_20260209   신형. 결과를 컨텍스트에 넣기 전에 모델이 코드를 돌려 걸러낸다
#                         (dynamic filtering). 이 코드 실행 때문에 programmatic tool calling을
#                         지원하는 상위 모델에서만 동작하고, haiku 는 400이 난다(실측).
#
# 신형 → 기본형 순으로 시도한다. haiku 에서는 첫 시도가 반드시 400이지만 거절된 요청은
# 추론 전에 끊겨 과금되지 않는다. 순서를 뒤집지 않는 이유는, 상위 모델로 바꿨을 때
# 조용히 기본형으로 떨어지지 않게 하기 위해서다.
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


def check_anthropic_connect(api_key: str, model: str) -> tuple[bool, str]:
    """0층 — 툴 없는 최소 messages 호출. Anthropic 쪽 인증·모델 ID가 사는지만 본다."""
    import anthropic

    try:
        resp = anthropic_client(api_key).messages.create(
            model=model,
            max_tokens=32,
            messages=[{"role": "user", "content": "핑. '퐁'이라고만 답해."}],
        )
    except anthropic.AuthenticationError:
        return False, "인증 실패(401) — GMS_API_KEY 확인"
    except anthropic.NotFoundError:
        return False, f"모델 ID를 GMS가 모른다(404): {model}"
    except anthropic.APIStatusError as exc:
        return False, f"HTTP {exc.status_code}: {exc}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    return True, f"응답 {resp.usage.output_tokens}토큰: {text[:40]!r}"


def check_gemini_connect(api_key: str, model: str) -> tuple[bool, str]:
    """0층 — embedContent 1건. **검색 능력과 무관하고**, Gemini 쪽 인증만 확인한다."""
    body = {"content": {"parts": [{"text": "연결 확인용 텍스트."}]}}
    try:
        resp = gemini_post(api_key, model, "embedContent", body, timeout=30.0)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}: {resp.text[:150]}"

    values = (resp.json().get("embedding") or {}).get("values") or []
    if not values:
        return False, "embedding.values 비어 있음"
    return True, f"{len(values)}차원 벡터 수신"


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
    parser = argparse.ArgumentParser(description="GMS 웹검색 지원 여부 점검")
    parser.add_argument("--quick", action="store_true", help="0층(연결 확인)만 하고 종료")
    parser.add_argument("--model", default="", help="Anthropic 후보를 이 ID 하나로 고정")
    args = parser.parse_args()

    api_key = gms_key()
    if not api_key:
        print("GMS_API_KEY 가 없다. AI/.env 또는 환경변수에 설정한 뒤 다시 실행할 것.")
        return 2

    print("\n[0층] 연결 확인 — 키가 사는지, provider별 인증이 통과하는지")
    connect_model = args.model or CONNECT_ANTHROPIC_MODEL
    a_ok, a_detail = check_anthropic_connect(api_key, connect_model)
    print(f"  [{'PASS' if a_ok else 'FAIL'}] anthropic/{connect_model} — {a_detail}")
    g_ok, g_detail = check_gemini_connect(api_key, CONNECT_GEMINI_EMBEDDING)
    print(f"  [{'PASS' if g_ok else 'FAIL'}] gemini/{CONNECT_GEMINI_EMBEDDING} — {g_detail}")
    print("  (임베딩은 검색 능력과 무관하다 — Gemini 쪽 인증 확인용이다)")

    if not (a_ok or g_ok):
        print("\n양쪽 다 실패했다. 웹검색 이전에 키·게이트웨이 문제다. 여기서 멈춘다.")
        return 2
    if args.quick:
        return 0 if (a_ok and g_ok) else 1

    print("\n[1층] GMS 노출 모델 목록")
    for name in list_anthropic_models(api_key):
        print(f"  anthropic: {name}")
    for name in list_gemini_models(api_key):
        print(f"  gemini: {name}")

    print("\n[2·3층] Anthropic web_search")
    verdicts = _probe_provider(
        [args.model] if args.model else ANTHROPIC_CANDIDATES,
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
