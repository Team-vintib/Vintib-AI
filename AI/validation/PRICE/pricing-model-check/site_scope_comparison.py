"""V3 (CH017) — 슬롯 B 사이트별 비교: 후르츠패밀리 vs 번개장터 vs 당근마켓.

`comps.py`(프로덕션)의 프롬프트는 "후르츠패밀리·번개장터·중고나라"를, `comps_sources.py`
(실측 스크립트)는 "번개장터·당근마켓·중고나라"를 우선한다고 적어 뒀다 — **근거 없이 갈렸고**
어느 사이트가 실제로 comps를 만들어 주는지 측정된 적이 없다(`-494` 점검 B4).

한 프롬프트에 여러 사이트를 뭉쳐 넣으면 어느 사이트가 기여했는지 알 수 없다. 그래서 사이트
하나당 **별도 쿼리**를 던져 A(후르츠패밀리)/B(번개장터)/C(당근마켓) 세 비교군을 만든다.
`comps_sources.py`의 정규화·집계 로직(`CompItem`/`_rows_to_items`/`summarize`)을 그대로
재사용한다 — 지표를 두 번 구현하지 않는다.

설계: .claude/plans/ai/CH017-pricing-cheap-wins.md

⚠️ **쿼리 1건당 GMS 호출이 3회다**(사이트 3개). 기본 쿼리 수를 3건으로 제한했다 — 필요하면
`--limit`으로 늘리되, 늘어난 만큼 호출 수가 그대로 늘어난다는 걸 인지할 것.

**GMS 호출 스크립트는 사람이 직접 실행한다**(`AI/CLAUDE.md` 하드 룰). Claude는 이 파일을
작성만 하고 실행하지 않는다.

실행:
    python validation/PRICE/pricing-model-check/site_scope_comparison.py           # 기본 3쿼리
    python validation/PRICE/pricing-model-check/site_scope_comparison.py --limit 1  # 최소 확인
"""

from __future__ import annotations

import argparse
import sys
import time

from comps_sources import (
    DEFAULT_QUERIES,
    SourceResult,
    _extract_json_array,
    _rows_to_items,
    summarize,
)
from gms_client import gemini_post, gms_key

# A/B/C 비교군. 사이트 표기는 검색 쿼리에 그대로 들어가므로 실제 도메인/서비스명을 쓴다.
SITES: dict[str, str] = {
    "A_fruits": "후르츠패밀리(fruitsfamily.com)",
    "B_bunjang": "번개장터(bunjang.co.kr)",
    "C_daangn": "당근마켓(daangn.com 중고거래)",
}

# comps_sources.py의 gemini 기본값과 동일한 최저가 모델. 상위 모델로 올리지 말 것
# (AI/CLAUDE.md 하드 룰 — 검색 라운드가 늘어날수록 비용이 급증한다, CH002 V1 실측).
DEFAULT_MODEL = "gemini-3.5-flash"


def _site_scoped_prompt(query: str, site_label: str) -> str:
    return (
        f"'{query}' 의 **중고** 거래 시세를 {site_label} 에서만 검색해라. "
        "다른 사이트의 결과는 쓰지 마라.\n"
        "찾은 매물을 JSON 배열로만 답해라. 설명 문장은 쓰지 마라.\n"
        '형식: [{"title": "상품명", "price": 숫자(원, 쉼표 없이), "url": "링크", '
        '"listed_at": "YYYY-MM-DD 또는 빈 문자열", "is_used": true/false}]\n'
        "가격을 확인할 수 없는 매물은 넣지 마라. 추측한 가격도 넣지 마라."
    )


def fetch_site(query: str, site_key: str, site_label: str, model: str) -> SourceResult:
    """사이트 하나에 한정한 검색 1회. `comps_sources.py`의 `fetch_gemini()`와 판정 로직이
    같다 — grounding이 없으면 그 자체를 실패로 본다(검색 없이 지어낸 답일 수 있으므로)."""
    body = {
        "contents": [{"parts": [{"text": _site_scoped_prompt(query, site_label)}]}],
        "tools": [{"google_search": {}}],
    }
    started = time.perf_counter()
    try:
        resp = gemini_post(gms_key() or "", model, "generateContent", body)
    except Exception as exc:
        return SourceResult(site_key, query, error=f"{type(exc).__name__}: {exc}")
    elapsed = (time.perf_counter() - started) * 1000

    if resp.status_code != 200:
        return SourceResult(
            site_key, query, latency_ms=elapsed, error=f"HTTP {resp.status_code} {resp.text[:150]}"
        )

    candidates = resp.json().get("candidates", [])
    if not candidates:
        return SourceResult(site_key, query, latency_ms=elapsed, error="candidates 없음")

    meta = candidates[0].get("groundingMetadata") or {}
    if not (meta.get("groundingChunks") or meta.get("webSearchQueries")):
        return SourceResult(
            site_key, query, latency_ms=elapsed, error="grounding 미발생(응답 폐기)"
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    return SourceResult(
        site_key,
        query,
        items=_rows_to_items(_extract_json_array(text), site_key),
        latency_ms=elapsed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="사이트별(A/B/C) comps 비교 — 쿼리 1건당 GMS 호출 3회"
    )
    parser.add_argument("--limit", type=int, default=3, help="쿼리 수 제한(기본 3 — 비용 방어)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini 모델 ID")
    args = parser.parse_args()

    if not gms_key():
        print("GMS_API_KEY 가 없다. AI/.env 또는 환경변수에 설정한 뒤 다시 실행할 것.")
        return 2

    queries = DEFAULT_QUERIES[: args.limit] if args.limit else DEFAULT_QUERIES
    print(f"⚠️  쿼리 {len(queries)}건 × 사이트 3개 = GMS 호출 {len(queries) * 3}회 예정\n")

    summaries: dict[str, dict] = {}
    for site_key, site_label in SITES.items():
        print(f"=== {site_key} ({site_label}) ===")
        results = []
        for query in queries:
            result = fetch_site(query, site_key, site_label, args.model)
            results.append(result)
            status = f"{len(result.items)}건" if result.ok else f"실패: {result.error}"
            print(f"  {query} → {status}")
        summaries[site_key] = summarize(results)
        print()

    print("=== 사이트별 커버리지 요약 ===")
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
    print("  " + "site".ljust(11) + "".join(c.rjust(11) for c in cols))
    for site_key, s in summaries.items():
        print("  " + site_key.ljust(11) + "".join(str(s[c]).rjust(11) for c in cols))

    for site_key, s in summaries.items():
        for err in dict.fromkeys(s["_errors"]):
            print(f"  [{site_key}] 오류: {err}")

    print(
        "\n판정 기준: comps≥3 비율·평균 comps가 가장 높은 사이트가 실제로 comps를 만들어 주는"
        "\n사이트다. 이 결과로 app/pricing/comps.py의 프롬프트 사이트 목록(B4)을 확정한다 —"
        "\n지금은 후르츠패밀리·번개장터·중고나라를 프로덕션 기준으로 뭉쳐 두고 있지만 실측 근거는"
        "\n없었다."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
