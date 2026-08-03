"""가격 분포 스윕 실행 엔트리 — 축 A~D 리포트.

CH015의 실행 순서(R0 → R1 → R2 → R3)를 돌리고, 목표에 닿는 라운드에서 멈추기 위한
지표를 낸다. **격자 탐색을 하지 않는다** — 검색 라운드가 곧 비용이다.

실행:
    # 기본은 mock — 네트워크·과금 없이 지표 계산 경로 전체를 검증한다
    python validation/PRICE/pricing-histogram-check/run_histogram_sweep.py --round R0
    python .../run_histogram_sweep.py --round R3 --repeat 2

    # ⛔ 실호출 — 사용자만 실행한다(AI/CLAUDE.md 하드 룰)
    python .../run_histogram_sweep.py --round R1 --backend gemini

가장 먼저 확인할 것은 **S1(카운트 쿼리)** 이다. 검색이 플랫폼의 가격 필터별 "총 N개"를
읽어 오면 출력 A의 설계가 통째로 바뀐다(top-k 절단 편향이 사라진다).

    python .../run_histogram_sweep.py --round S1 --backend gemini --limit 3

라운드는 출력별로 나뉜다 — R0~R3은 **출력 A**(가격 분포), `B`는 **출력 B**(등급 단조성)다.
표본 요구가 달라서 한 라운드에 합치면 비용이 곱해지고 원인 구분도 안 된다(CH015 M9).

⚠️ **mock 백엔드로는 잴 수 없는 것이 둘 있다.** mock 결과를 실측으로 읽지 말 것.

- **축 B 재현성이 항상 0.0000이다.** mock은 결정적이라 매번 같은 값을 낸다. 재현성은
  실백엔드에서만 의미가 있다(그리고 캐시를 우회해야 한다 — CH015 S7).
- **등급 단조성이 낮게 나온다.** mock은 등급을 가격과 무관하게 순환 배정한다. 즉 이건
  "상태 신호가 잡음"이라는 발견이 아니라 **지표가 무신호를 제대로 잡아낸다는 음성 대조**다.

반대로 **가격 중립성은 mock에서도 유효하다** — 순위·가격 상관을 일부러 넣어 뒀고
(`MockSearchBackend(rank_bias=...)`), 지표가 그 왜곡을 잡아내는지 테스트로 고정해 뒀다.

설계: .claude/plans/ai/CH015-comps-price-distribution.md
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

from harvest import (
    GeminiSearchBackend,
    HarvestItem,
    HarvestOutcome,
    MockSearchBackend,
    SearchBackend,
    harvest,
)
from hist_metrics import (
    bootstrap_ci,
    bucket_uniformity,
    histogram,
    log_bucket_edges,
    median,
    normalized_wasserstein,
    spearman,
)
from histogram_registry import (
    ACTIVE_BACKEND,
    DEFAULT_MODELS,
    HIST_MIN_SAMPLES,
    NICHE_QUERY_OFFSET,
    QUERIES,
    SEED,
    HarvestConfig,
    round_config,
)

# 출력 A 판정: `price_neutrality`(무작위 귀무분포 대비 **초과분**)가 이 값을 넘으면
# "순위가 가격에 중립적이지 않다". 0이 중립이므로 원시 거리보다 임계가 훨씬 작다.
#
# ⚠️ 임의값이다. mock 스윕(쿼리 5건)에서 무작위 순위일 때도 ±0.03 정도가 관측됐다 —
#    쿼리당 관측 순서가 1개뿐이라 남는 유한표본 잡음이다. 임계를 그 위로 잡았다.
#    **실측에서는 고정 임계로 판정하지 말고 쿼리 수를 늘려 잡음 바닥을 먼저 재라.**
NEUTRALITY_ALERT = 0.05

# 등급을 나쁜 것 → 좋은 것 순으로. 단조성 Spearman의 x축이 된다.
_GRADE_ORDER = ("C", "B", "A", "S")


@dataclass
class QueryReport:
    """쿼리 1건의 축 A~D 원지표."""

    query: str
    niche: bool
    outcome: HarvestOutcome
    repeats: list[list[int]] = field(default_factory=list)  # 반복 실행별 가격 목록

    @property
    def prices(self) -> list[int]:
        return [item.price for item in self.outcome.items]

    @property
    def hist_ok(self) -> bool:
        return len(self.prices) >= HIST_MIN_SAMPLES


# --- 축 지표 ----------------------------------------------------------------


def price_neutrality(
    items: list[HarvestItem], k: int, *, trials: int = 30, seed: int = SEED
) -> float:
    """축 D — top-k 절단이 분포를 옮기는 정도 중 **순위 때문인 몫**. 순열검정 통계량.

    **출력 A 채택의 관문이다.** 값이 0보다 뚜렷이 크면 히스토그램은 시장이 아니라 우리
    검색의 순위 편향을 그리고 있다는 직접 증거다(CH015 M9). 표본을 늘려도 안 고쳐진다.

    ⚠️ **원시 Wasserstein을 그대로 쓰면 안 된다.** n건에서 k건만 뽑는 것 자체가 표집
    오차를 만들어서, 순위가 완전히 무작위여도 거리가 0이 아니다. 실제로 초기 구현이
    그랬고 mock 스윕에서 `rank_bias` 0과 0.95가 구분되지 않았다(2026-08-03).

    그래서 **같은 표본에서 무작위로 k건을 뽑은 귀무분포를 빼고 초과분만 돌려준다.**
    이러면 표집 잡음이 상쇄되고 남는 것은 순위가 만든 이동뿐이다.

    반환값 ≤ 0 이면 "순위가 가격에 중립적"이다.
    """
    if len(items) <= k:
        return 0.0
    full = [item.price for item in items]
    ranked = [item.price for item in sorted(items, key=lambda i: i.rank)[:k]]
    observed = normalized_wasserstein(full, ranked)

    rng = random.Random(seed)
    null = statistics.mean(normalized_wasserstein(full, rng.sample(full, k)) for _ in range(trials))
    return observed - null


def grade_monotonicity(items: list[HarvestItem]) -> tuple[float, dict[str, int]]:
    """축 D — 출력 B의 단조성. 등급별 중앙값이 C→S로 오르는가.

    **Spearman이 쓰이는 유일한 자리다**(CH015 M9). 상품 간 비교에는 쓰지 않는다 —
    개별 중고 의류에 "알려진 참 가격 순서"가 없기 때문이다.

    깨지면 결론은 "가격이 틀렸다"가 아니라 **"상태 신호가 잡음이다"** 이다.
    """
    by_grade: dict[str, list[int]] = {}
    for item in items:
        if item.grade:
            by_grade.setdefault(item.grade, []).append(item.price)

    medians = {g: int(median(by_grade[g])) for g in _GRADE_ORDER if by_grade.get(g)}
    if len(medians) < 3:  # 등급 3종 미만이면 순위상관이 의미 없다
        return 0.0, medians
    ranks = [_GRADE_ORDER.index(g) for g in medians]
    return round(spearman(ranks, list(medians.values())), 3), medians


def reproducibility(runs: list[list[int]]) -> float:
    """축 B — 반복 실행 간 분포 거리(정규화 Wasserstein)의 평균.

    판매자에게 보여줄 그래프가 실행할 때마다 모양이 바뀌면 표본이 아무리 많아도 못 쓴다.
    정답셋 없이 지금 잴 수 있는 유일한 정확도 프록시다(CH015 M7 — 재검사 신뢰도).
    """
    usable = [run for run in runs if run]
    if len(usable) < 2:
        return 0.0
    distances = [
        normalized_wasserstein(usable[i], usable[j])
        for i in range(len(usable))
        for j in range(i + 1, len(usable))
    ]
    return round(statistics.mean(distances), 4) if distances else 0.0


# --- 실행 -------------------------------------------------------------------


def build_backend(key: str, model: str, config: HarvestConfig) -> SearchBackend:
    """백엔드 조립. **실호출은 사용자가 명시할 때만 만들어진다.**"""
    if key == "mock":
        return MockSearchBackend()
    if key == "gemini":
        return GeminiSearchBackend(
            model or DEFAULT_MODELS["gemini"], follow_pause_turn=config.follow_pause_turn
        )
    raise ValueError(f"등록되지 않은 백엔드입니다: {key!r}")


def run_round(
    backend: SearchBackend, config: HarvestConfig, queries: list[str]
) -> list[QueryReport]:
    reports: list[QueryReport] = []
    for index, query in enumerate(queries):
        outcome = harvest(backend, config, query)
        report = QueryReport(
            query=query,
            niche=index >= NICHE_QUERY_OFFSET,
            outcome=outcome,
            repeats=[[item.price for item in outcome.items]],
        )
        # 축 B — 캐시를 우회해 매번 새로 던져야 의미가 있다(CH015 S7 주의).
        for _ in range(config.repeats - 1):
            report.repeats.append([item.price for item in harvest(backend, config, query).items])

        status = f"n={report.outcome.n_valid}" if outcome.ok else f"실패: {outcome.error}"
        print(f"  {query} → {status} (검색 {outcome.search_calls}회)")
        reports.append(report)
    return reports


def print_report(config: HarvestConfig, reports: list[QueryReport]) -> None:
    ok = [r for r in reports if r.outcome.ok]
    if not ok:
        print("\n  전부 실패 — 리포트를 낼 수 없습니다.")
        return

    print(f"\n=== {config.name} 리포트 — {config.note} ===")
    if config.levers:
        print(f"  적용 레버: {', '.join(config.levers)}")

    # --- 축 A: 수확량 ---
    print("\n[축 A] 수확량")
    _print_yield("전체", ok)
    _print_yield("유명", [r for r in ok if not r.niche])
    _print_yield("니치", [r for r in ok if r.niche])

    # S1 카운트 쿼리는 매물이 아니라 개수를 낸다 — 별도로 출력한다.
    counted = [r for r in ok if r.outcome.counts_by_stratum]
    if counted:
        print("\n[S1] 구간별 개수 (매물 파싱 없이 얻은 히스토그램)")
        for report in counted:
            bands = " ".join(f"{k}:{v}" for k, v in report.outcome.counts_by_stratum.items())
            print(f"  {report.query} → {bands}")
        return  # 카운트 라운드는 아래 분포 지표가 해당되지 않는다

    # --- 축 B: 재현성 ---
    if config.repeats > 1:
        distances = [reproducibility(r.repeats) for r in ok]
        print(f"\n[축 B] 재현성 — 반복 간 정규화 Wasserstein 평균 {statistics.mean(distances):.4f}")
        print("  (0에 가까울수록 안정. 크면 그래프가 실행마다 바뀐다는 뜻)")

    # --- 축 C: 비용 ---
    calls = [r.outcome.search_calls for r in ok]
    latency = [r.outcome.latency_ms for r in ok]
    print(
        f"\n[축 C] 비용 — 쿼리당 검색 {statistics.mean(calls):.1f}회, "
        f"평균 {statistics.mean(latency):.0f}ms"
    )

    # --- 축 D: 적합성·타당도 ---
    print("\n[축 D] 적합성·타당도")
    neutral = [price_neutrality(r.outcome.items, k=10) for r in ok if len(r.outcome.items) > 10]
    if neutral:
        worst = max(neutral)
        verdict = "⚠️ 편향 의심" if worst > NEUTRALITY_ALERT else "OK"
        print(
            f"  가격 중립성(top-10 절단 이동거리): 평균 {statistics.mean(neutral):.3f} / "
            f"최대 {worst:.3f} → {verdict}"
        )
        if worst > NEUTRALITY_ALERT:
            print("    → 히스토그램이 시장이 아니라 검색 순위 편향을 그리고 있다. S1/S2 필요.")
    else:
        print("  가격 중립성: 표본이 10건 이하라 판정 불가")

    monotone = [grade_monotonicity(r.outcome.items) for r in ok]
    scored = [rho for rho, medians in monotone if medians and len(medians) >= 3]
    if scored:
        print(
            f"  등급 단조성(Spearman ρ): 평균 {statistics.mean(scored):.3f} "
            f"({len(scored)}/{len(ok)} 쿼리에서 판정 가능)"
        )
        if statistics.mean(scored) < 0.5:
            print("    → 상태 신호가 잡음이다. 백분위 등급 밴드의 전제가 성립하지 않는다.")
    else:
        print("  등급 단조성: 등급 라벨이 3종 미만이라 판정 불가 (S3 상태축 층화 필요)")

    # --- 분포 산출물 ---
    print("\n[산출물] 히스토그램 (로그 스케일 + Freedman-Diaconis)")
    for report in ok[:3]:
        _print_histogram(report)


def _print_yield(label: str, reports: list[QueryReport]) -> None:
    if not reports:
        return
    valid = [r.outcome.n_valid for r in reports]
    hist_ok = sum(1 for r in reports if r.hist_ok)
    print(
        f"  {label:4s} n_raw {statistics.mean([r.outcome.n_raw for r in reports]):5.1f} / "
        f"n_dedup {statistics.mean([r.outcome.n_dedup for r in reports]):5.1f} / "
        f"n_valid {statistics.mean(valid):5.1f} | "
        f"hist_ok(n≥{HIST_MIN_SAMPLES}) {hist_ok}/{len(reports)}"
    )


def _print_histogram(report: QueryReport) -> None:
    prices = report.prices
    if len(prices) < 2:
        print(f"  {report.query}: 표본 {len(prices)}건 — 분포를 그리지 않는다")
        return
    edges = log_bucket_edges(prices)
    buckets = histogram(prices, edges)
    interval = bootstrap_ci([float(p) for p in prices])
    level = report.outcome.level or "-"
    print(f"  {report.query} [비교 수준: {level}]")
    for bucket in buckets:
        bar = "█" * bucket.count
        print(f"    {bucket.min:>8,}~{bucket.max:>8,}원 {bar} {bucket.count}")
    print(
        f"    중앙값 {interval.point:,.0f}원 "
        f"(95% CI {interval.low:,.0f}~{interval.high:,.0f}, 폭 {interval.width_ratio:.0%}) "
        f"/ 균일도 {bucket_uniformity(buckets):.2f}"
    )


def write_pool(reports: list[QueryReport], path: Path) -> None:
    """축 D의 풀링 적합성 판정용 시트(JSONL). 사람이 `relevant` 칸만 채운다.

    전수 정답이 없어도 실행 간 비교가 성립하는 TREC 방식이다(CH015 M7) — 여러 라운드의
    결과를 합쳐 그 풀만 판정한다.
    """
    with path.open("w", encoding="utf-8") as handle:
        for report in reports:
            for item in report.outcome.items:
                handle.write(
                    json.dumps(
                        {
                            "query": report.query,
                            "title": item.title,
                            "price": item.price,
                            "url": item.url,
                            "grade": item.grade,
                            "relevant": None,  # ← 사람이 true/false로 채운다
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    print(f"\n  적합성 판정 시트: {path} ({sum(len(r.outcome.items) for r in reports)}건)")


def main() -> int:
    parser = argparse.ArgumentParser(description="가격 분포 수집 레버 스윕 (CH015)")
    parser.add_argument("--round", default="R0", help="R0/R1/R2/R3/S1")
    parser.add_argument("--backend", default=ACTIVE_BACKEND, choices=["mock", "gemini"])
    parser.add_argument("--model", default="", help="LLM 모델 ID 오버라이드")
    parser.add_argument("--limit", type=int, default=0, help="쿼리 수 제한")
    parser.add_argument("--repeat", type=int, default=1, help="축 B 재현성 반복 횟수")
    parser.add_argument("--max-comps", type=int, default=None, help="수확 상한 오버라이드")
    parser.add_argument("--pool-out", default="", help="적합성 판정 시트 출력 경로(JSONL)")
    args = parser.parse_args()

    config = round_config(args.round, repeats=args.repeat, max_comps=args.max_comps)
    queries = QUERIES[: args.limit] if args.limit else QUERIES

    if args.backend != "mock":
        print(
            f"⚠️  실호출 백엔드({args.backend})입니다 — 검색 라운드마다 과금됩니다.\n"
            f"    쿼리 {len(queries)}건 × 반복 {config.repeats}회"
        )

    backend = build_backend(args.backend, args.model, config)
    print(f"\n=== {config.name} 실행 (backend={args.backend}) ===")
    reports = run_round(backend, config, queries)
    print_report(config, reports)

    if args.pool_out:
        write_pool(reports, Path(args.pool_out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
