"""V2 — 슬롯 B(시세 수집) 백엔드 비교.

같은 쿼리를 여러 경로에 던져서 **어디서 중고 의류 comps를 실제로 얻을 수 있는지**를 잰다.
가격 정확도(V4)가 아니라 커버리지 측정이 목적이다 — 시세를 못 구하면 그 다음이 없다.

설계: .claude/plans/ai/CH002-pricing-model-selection.md

백엔드 3종. 전부 같은 `CompItem` 으로 정규화해서 downstream(pricer)이 출처를 몰라도 되게 한다.

    naver       네이버 쇼핑 오픈API — 구조화 필드로 가격이 바로 나온다. 다만 신품 위주
    anthropic   Claude 서버툴 web_search — GMS가 통과시키는지 자체가 미검증(smoke_gms.py)
    gemini      Gemini google_search grounding — 위와 규격이 완전히 다르다
    mock        키 없이 전 경로를 돌리기 위한 고정 응답

실행:
    python validation/pricing-model-check/comps_sources.py              # 기본 쿼리셋 전체
    python validation/pricing-model-check/comps_sources.py --source naver
    python validation/pricing-model-check/comps_sources.py --limit 3

**주의 — 중고 판별은 실측으로 확인한다.** 네이버 쇼핑 API의 `productType` 이 중고 여부를
구분한다고 알려져 있으나(4·5·6=중고), 문서 기준이지 우리 쿼리에서 실제로 그렇게 나오는지는
별개다. 그래서 이 스크립트는 중고 비율을 단정하지 않고 **관측된 productType 분포를 그대로
출력한다.** 분포를 눈으로 확인한 뒤 USED_PRODUCT_TYPES 를 확정할 것.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import sys
import time
from dataclasses import dataclass, field

from gms_client import NAVER_SHOP_URL, anthropic_client, gemini_post, gms_key, naver_keys

# LAB-21의 "카테고리별 정확도 차등(유명 브랜드 vs 니치)"을 재현하려면 둘을 섞어야 한다.
# 앞 5건이 식별 쉬운 유명 라인, 뒤 5건이 니치·모델명 불명확 케이스다.
DEFAULT_QUERIES = [
    "리바이스 501 빅E 데님",
    "나이키 빈티지 스우시 후드 집업",
    "폴로 랄프로렌 옥스포드 셔츠 빈티지",
    "칼하트 디트로이트 자켓 빈티지",
    "스톤아일랜드 니트 가디건",
    "90년대 무지 워시드 데님 자켓",
    "빈티지 체크 플란넬 셔츠 오버핏",
    "구제 코듀로이 와이드 팬츠",
    "빈티지 카레지 니트 베스트",
    "구제 워크웨어 헤링본 코트",
]

# 문서상 4·5·6이 중고다. 단정하지 말고 관측 분포로 검증한 뒤 확정할 것(모듈 docstring 참고).
USED_PRODUCT_TYPES = {"4", "5", "6"}

# 최신 변형은 Opus 4.6+ / Sonnet 4.6+ 전용이라 haiku 계열은 구형으로 폴백해야 한다.
ANTHROPIC_SEARCH_TOOLS = ["web_search_20260209", "web_search_20250305"]

_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class CompItem:
    """정규화된 비교 매물 1건. 어느 백엔드에서 왔든 같은 모양이 된다."""

    title: str
    price: int
    source: str
    url: str = ""
    mall: str = ""
    listed_at: str = ""  # 등록·판매일. 네이버 쇼핑은 제공하지 않는다 → 최신성 측정 불가
    is_used: bool | None = None  # 판별 불가면 None. False 로 뭉개지 않는다
    raw_type: str = ""  # 네이버 productType 등 판별 근거 원본값


@dataclass
class SourceResult:
    """한 (백엔드, 쿼리) 실행 결과."""

    source: str
    query: str
    items: list[CompItem] = field(default_factory=list)
    latency_ms: float = 0.0
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


# --- 백엔드 ----------------------------------------------------------------


def fetch_naver(query: str, display: int = 20) -> SourceResult:
    """네이버 쇼핑 오픈API. 가격이 구조화 필드(lprice)로 나와 파싱이 필요 없다."""
    import httpx

    client_id, client_secret = naver_keys()
    if not (client_id and client_secret):
        return SourceResult("naver", query, error="NAVER_CLIENT_ID/SECRET 없음")

    started = time.perf_counter()
    try:
        resp = httpx.get(
            NAVER_SHOP_URL,
            params={"query": query, "display": display, "sort": "sim"},
            headers={"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret},
            timeout=30.0,
        )
    except Exception as exc:
        return SourceResult("naver", query, error=f"{type(exc).__name__}: {exc}")
    elapsed = (time.perf_counter() - started) * 1000

    if resp.status_code != 200:
        return SourceResult(
            "naver", query, latency_ms=elapsed, error=f"HTTP {resp.status_code} {resp.text[:150]}"
        )

    items: list[CompItem] = []
    for raw in resp.json().get("items", []):
        price = raw.get("lprice") or "0"
        if not str(price).isdigit() or int(price) <= 0:
            continue
        product_type = str(raw.get("productType", ""))
        items.append(
            CompItem(
                title=html.unescape(_TAG_RE.sub("", raw.get("title", ""))),
                price=int(price),
                source="naver",
                url=raw.get("link", ""),
                mall=raw.get("mallName", ""),
                # 중고 여부는 productType 으로만 알 수 있고, 그 신뢰도는 아직 미검증이다.
                is_used=(product_type in USED_PRODUCT_TYPES) if product_type else None,
                raw_type=product_type,
            )
        )
    return SourceResult("naver", query, items=items, latency_ms=elapsed)


def _extract_json_array(text: str) -> list[dict]:
    """LLM 응답에서 첫 JSON 배열을 관대하게 건져낸다.

    structured output(`output_config.format`)을 쓰지 않는 이유: GMS 프록시가 그 파라미터를
    통과시키는지 미확인이라, 여기서 400이 나면 웹검색 지원 여부 판정까지 같이 오염된다.
    파싱 실패는 그 자체로 지표(파싱 실패율)이므로 관대하게 파싱하고 실패를 기록한다.
    """
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    return [row for row in parsed if isinstance(row, dict)]


def _comps_prompt(query: str) -> str:
    return (
        f"'{query}' 의 **중고** 거래 시세를 웹에서 검색해라. "
        "번개장터·당근마켓·중고나라 등 중고 거래 매물을 우선한다.\n"
        "찾은 매물을 JSON 배열로만 답해라. 설명 문장은 쓰지 마라.\n"
        '형식: [{"title": "상품명", "price": 숫자(원, 쉼표 없이), "url": "링크", '
        '"listed_at": "YYYY-MM-DD 또는 빈 문자열", "is_used": true/false}]\n'
        "가격을 확인할 수 없는 매물은 넣지 마라. 추측한 가격도 넣지 마라."
    )


def _rows_to_items(rows: list[dict], source: str) -> list[CompItem]:
    items: list[CompItem] = []
    for row in rows:
        price = row.get("price")
        if isinstance(price, str):
            price = re.sub(r"[^0-9]", "", price)
        try:
            price_int = int(price)
        except (TypeError, ValueError):
            continue
        if price_int <= 0:
            continue
        items.append(
            CompItem(
                title=str(row.get("title", ""))[:120],
                price=price_int,
                source=source,
                url=str(row.get("url", "")),
                listed_at=str(row.get("listed_at", "")),
                is_used=row.get("is_used") if isinstance(row.get("is_used"), bool) else None,
                raw_type="llm",
            )
        )
    return items


def fetch_anthropic(query: str, model: str) -> SourceResult:
    """Claude 서버툴 web_search. 툴 규격은 최신 → 구형 순으로 폴백한다."""
    import anthropic

    api_key = gms_key()
    if not api_key:
        return SourceResult("anthropic", query, error="GMS_API_KEY 없음")

    client = anthropic_client(api_key)
    last_error = ""
    for tool_type in ANTHROPIC_SEARCH_TOOLS:
        started = time.perf_counter()
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=4096,
                tools=[{"type": tool_type, "name": "web_search"}],
                messages=[{"role": "user", "content": _comps_prompt(query)}],
            )
        except anthropic.APIStatusError as exc:
            last_error = f"{tool_type}: HTTP {exc.status_code}"
            continue  # 이 규격을 프록시가 거부했다 — 구형으로 재시도
        except Exception as exc:
            return SourceResult("anthropic", query, error=f"{type(exc).__name__}: {exc}")
        elapsed = (time.perf_counter() - started) * 1000

        searched = any(getattr(b, "type", "") == "server_tool_use" for b in resp.content)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        items = _rows_to_items(_extract_json_array(text), "anthropic")

        if not searched:
            # 툴은 통과했는데 호출을 안 했다 — 검색 없이 지어낸 답일 수 있으니 신뢰하지 않는다.
            return SourceResult(
                "anthropic", query, latency_ms=elapsed, error="웹검색 미호출(응답 폐기)"
            )
        return SourceResult("anthropic", query, items=items, latency_ms=elapsed)

    return SourceResult("anthropic", query, error=last_error or "모든 web_search 규격 거부")


def fetch_gemini(query: str, model: str) -> SourceResult:
    """Gemini google_search grounding. Anthropic과 규격이 달라 별도 구현이 필요하다."""
    api_key = gms_key()
    if not api_key:
        return SourceResult("gemini", query, error="GMS_API_KEY 없음")

    body = {
        "contents": [{"parts": [{"text": _comps_prompt(query)}]}],
        "tools": [{"google_search": {}}],
    }
    started = time.perf_counter()
    try:
        resp = gemini_post(api_key, model, "generateContent", body)
    except Exception as exc:
        return SourceResult("gemini", query, error=f"{type(exc).__name__}: {exc}")
    elapsed = (time.perf_counter() - started) * 1000

    if resp.status_code != 200:
        return SourceResult(
            "gemini", query, latency_ms=elapsed, error=f"HTTP {resp.status_code} {resp.text[:150]}"
        )

    candidates = resp.json().get("candidates", [])
    if not candidates:
        return SourceResult("gemini", query, latency_ms=elapsed, error="candidates 없음")

    meta = candidates[0].get("groundingMetadata") or {}
    if not (meta.get("groundingChunks") or meta.get("webSearchQueries")):
        return SourceResult(
            "gemini", query, latency_ms=elapsed, error="grounding 미발생(응답 폐기)"
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    return SourceResult(
        "gemini",
        query,
        items=_rows_to_items(_extract_json_array(text), "gemini"),
        latency_ms=elapsed,
    )


def fetch_mock(query: str) -> SourceResult:
    """키 없이 downstream 전 경로를 돌리기 위한 고정 응답. 지표 계산 자체를 검증한다."""
    base = 40_000 + (abs(hash(query)) % 60_000)
    items = [
        CompItem(f"{query} 매물 {i + 1}", int(base * ratio), "mock", is_used=True, raw_type="mock")
        for i, ratio in enumerate((0.82, 0.95, 1.0, 1.12, 1.31))
    ]
    return SourceResult("mock", query, items=items, latency_ms=1.0)


SOURCES = {
    "naver": lambda q, m: fetch_naver(q),
    "anthropic": fetch_anthropic,
    "gemini": fetch_gemini,
    "mock": lambda q, m: fetch_mock(q),
}

DEFAULT_MODELS = {
    # GMS 확인된 호출 예시가 날짜 붙은 정식 ID였다. smoke_gms.py 결과로 갱신할 것.
    "anthropic": "claude-haiku-4-5-20251001",
    "gemini": "gemini-3.5-flash",
    "naver": "",
    "mock": "",
}


# --- 집계 ------------------------------------------------------------------


def summarize(results: list[SourceResult]) -> dict:
    """커버리지 지표. 가격 정확도가 아니라 '시세를 구할 수 있는가'만 본다."""
    ok = [r for r in results if r.ok]
    counts = [len(r.items) for r in ok]
    all_items = [item for r in ok for item in r.items]
    used = [i for i in all_items if i.is_used is True]
    unknown = [i for i in all_items if i.is_used is None]
    dated = [i for i in all_items if i.listed_at]

    type_dist: dict[str, int] = {}
    for item in all_items:
        type_dist[item.raw_type] = type_dist.get(item.raw_type, 0) + 1

    return {
        "쿼리": len(results),
        "성공": len(ok),
        "comps≥3": sum(1 for c in counts if c >= 3),
        "평균 comps": round(statistics.mean(counts), 1) if counts else 0.0,
        "중고 확인": len(used),
        "중고 불명": len(unknown),
        "날짜 있음": len(dated),
        "평균 ms": round(statistics.mean([r.latency_ms for r in ok]), 0) if ok else 0.0,
        "_type_dist": type_dist,
        "_errors": [r.error for r in results if not r.ok],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="슬롯 B(시세 수집) 백엔드 커버리지 비교")
    parser.add_argument("--source", action="append", choices=sorted(SOURCES), help="기본: 전부")
    parser.add_argument("--limit", type=int, default=0, help="쿼리 수 제한(빠른 확인용)")
    parser.add_argument("--model", default="", help="LLM 백엔드 모델 ID 오버라이드")
    args = parser.parse_args()

    queries = DEFAULT_QUERIES[: args.limit] if args.limit else DEFAULT_QUERIES
    sources = args.source or sorted(SOURCES)

    summaries: dict[str, dict] = {}
    for name in sources:
        model = args.model or DEFAULT_MODELS.get(name, "")
        print(f"\n=== {name} {f'({model})' if model else ''} ===")
        results = []
        for query in queries:
            result = SOURCES[name](query, model)
            results.append(result)
            status = f"{len(result.items)}건" if result.ok else f"실패: {result.error}"
            print(f"  {query} → {status}")
        summaries[name] = summarize(results)

    print("\n=== 커버리지 요약 ===")
    cols = [
        "쿼리",
        "성공",
        "comps≥3",
        "평균 comps",
        "중고 확인",
        "중고 불명",
        "날짜 있음",
        "평균 ms",
    ]
    print("  " + "source".ljust(11) + "".join(c.rjust(11) for c in cols))
    for name, s in summaries.items():
        print("  " + name.ljust(11) + "".join(str(s[c]).rjust(11) for c in cols))

    for name, s in summaries.items():
        if s["_type_dist"]:
            print(f"\n  [{name}] 관측된 raw_type 분포: {s['_type_dist']}")
        for err in dict.fromkeys(s["_errors"]):
            print(f"  [{name}] 오류: {err}")

    print(
        "\n판정 기준: comps≥3 비율이 낮거나 '중고 확인'이 0에 가까우면 그 백엔드로는"
        "\n중고 시세를 못 구하는 것이다. 네이버가 그렇게 나오면 CH002 §7의 대안으로 간다."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
