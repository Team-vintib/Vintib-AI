"""가격 분포 스파이크의 순수 로직 테스트.

**무거운 의존성 가드가 필요 없다** — `hist_metrics`/`harvest`의 순수 함수는 표준
라이브러리만 쓰므로 CI(`requirements-dev.txt`만 설치)에서 그대로 실행된다. 네트워크
호출은 `MockSearchBackend`로 대체하므로 GMS를 한 번도 부르지 않는다.

지표 자체를 먼저 검증해 두는 것이 목적이다 — 실측 라운드에서 이상한 숫자가 나왔을 때
"검색이 나쁜 건지 지표가 틀린 건지"를 구분할 수 없으면 실험 전체가 무의미해진다.
"""

from __future__ import annotations

import pytest
from harvest import (
    HarvestItem,
    MockSearchBackend,
    build_count_queries,
    build_specificity_ladder,
    classify_condition,
    dedup_items,
    extract_json_array,
    harvest,
    normalize_title,
    parse_count,
    retail_gate_mask,
    rows_to_items,
)
from hist_metrics import (
    bootstrap_ci,
    bucket_uniformity,
    freedman_diaconis_width,
    histogram,
    log_bucket_edges,
    mad,
    median,
    modified_z_scores,
    normalized_wasserstein,
    outlier_mask,
    quantile,
    spearman,
    wasserstein_distance,
)
from histogram_registry import ROUNDS, round_config

# --- 기초 통계 --------------------------------------------------------------


def test_quantile_interpolates_and_handles_edges():
    assert quantile([], 0.5) == 0.0
    assert quantile([7], 0.9) == 7.0
    assert quantile([0, 10], 0.5) == 5.0  # 보간 — 최근접 순위였다면 0 또는 10
    assert median([1, 2, 3, 4]) == 2.5


def test_mad_is_not_dragged_by_outlier():
    """표준편차와 달리 MAD는 이상치 자체에 오염되지 않는다."""
    clean = [10, 11, 12, 13, 14]
    dirty = [*clean, 10_000]
    assert mad(dirty) <= mad(clean) * 2


def test_modified_z_scores_fall_back_when_mad_is_zero():
    """표본 절반 이상이 같은 값이면 MAD가 0이다 — 0으로 나누지 않아야 한다."""
    scores = modified_z_scores([5, 5, 5, 5, 99])
    assert all(isinstance(s, float) for s in scores)
    assert scores[-1] != 0.0  # 99는 여전히 튀는 값으로 잡혀야 한다


def test_modified_z_scores_all_identical_is_all_zero():
    assert modified_z_scores([3, 3, 3]) == [0.0, 0.0, 0.0]


def test_outlier_mask_uses_log_scale():
    """로그 스케일이라 정상적인 고가 매물은 살아남고 자릿수 오탐만 걸린다."""
    prices = [30_000, 35_000, 40_000, 45_000, 50_000, 60_000, 3_000_000]
    flags = outlier_mask(prices)
    assert flags[-1] is True
    assert not any(flags[:-1])


def test_outlier_mask_falls_back_when_non_positive():
    """0 이하가 섞이면 로그 변환이 불가능하다 — 예외 대신 선형 폴백."""
    assert len(outlier_mask([0, 10, 20, 30])) == 4


# --- 버킷 (M4) --------------------------------------------------------------


def test_freedman_diaconis_zero_when_no_spread():
    assert freedman_diaconis_width([5, 5, 5, 5]) == 0.0
    assert freedman_diaconis_width([1]) == 0.0


def test_log_bucket_edges_empty_for_degenerate_samples():
    assert log_bucket_edges([]) == []
    assert log_bucket_edges([1000]) == []
    assert log_bucket_edges([1000, 1000, 1000]) == []  # 전부 같은 값


def test_log_bucket_edges_are_ascending_and_span_the_sample():
    prices = [10_000, 12_000, 15_000, 20_000, 28_000, 40_000, 65_000, 90_000]
    edges = log_bucket_edges(prices)
    assert len(edges) >= 2
    assert edges == sorted(edges)
    assert edges[0] == min(prices)
    assert edges[-1] == max(prices)


def test_histogram_counts_every_price_including_the_max():
    """마지막 버킷만 양끝을 포함한다 — 최댓값이 어디에도 안 들어가면 안 된다."""
    prices = [10_000, 12_000, 15_000, 20_000, 28_000, 40_000, 65_000, 90_000]
    buckets = histogram(prices, log_bucket_edges(prices))
    assert sum(b.count for b in buckets) == len(prices)


def test_histogram_empty_without_edges():
    assert histogram([1, 2, 3], []) == []


def test_bucket_uniformity_bounds():
    edges = [0, 10, 20, 30]
    spread = histogram([5, 15, 25], edges)
    piled = histogram([5, 6, 7], edges)
    assert bucket_uniformity(spread) == pytest.approx(1.0)
    assert bucket_uniformity(piled) == 0.0


# --- 불확실성 (M6) ----------------------------------------------------------


def test_bootstrap_ci_is_deterministic_and_brackets_the_point():
    values = [30_000.0, 35_000.0, 40_000.0, 45_000.0, 50_000.0, 60_000.0]
    first = bootstrap_ci(values, iterations=200)
    second = bootstrap_ci(values, iterations=200)
    assert first == second  # 시드 고정 — 재현성 도구가 흔들리면 안 된다
    assert first.low <= first.point <= first.high
    assert first.point == median(values)


def test_bootstrap_ci_degenerate_samples():
    assert bootstrap_ci([]).point == 0.0
    single = bootstrap_ci([42.0])
    assert single.low == single.point == single.high == 42.0


def test_ci_width_ratio_shrinks_with_more_samples():
    """표본이 늘면 구간이 좁아진다 — 신뢰도의 해석 가능한 표현(M6)."""
    narrow = bootstrap_ci([100.0 + i for i in range(40)], iterations=300)
    wide = bootstrap_ci([100.0, 140.0, 180.0], iterations=300)
    assert narrow.width_ratio < wide.width_ratio


# --- 분포 비교 (M7) ---------------------------------------------------------


def test_wasserstein_zero_for_identical_and_equals_shift():
    assert wasserstein_distance([1, 2, 3], [1, 2, 3]) == 0.0
    assert wasserstein_distance([1, 2, 3], [2, 3, 4]) == 1.0


def test_normalized_wasserstein_is_scale_free():
    """상품마다 가격대가 달라 원본 거리는 비교가 안 된다."""
    small = normalized_wasserstein([100, 200, 300], [200, 300, 400])
    large = normalized_wasserstein([1000, 2000, 3000], [2000, 3000, 4000])
    assert abs(small - large) < 1e-9


def test_spearman_monotonic_and_tied():
    assert spearman([0, 1, 2, 3], [10, 20, 30, 40]) == 1.0
    assert spearman([0, 1, 2, 3], [40, 30, 20, 10]) == -1.0
    assert spearman([1, 1, 1], [1, 2, 3]) == 0.0  # 분산 0 → 정의되지 않음, 0으로


# --- harvest 순수 함수 -------------------------------------------------------


def test_extract_json_array_is_lenient_but_safe():
    assert extract_json_array('앞말 [{"price": 1}] 뒷말') == [{"price": 1}]
    assert extract_json_array("배열 없음") == []
    assert extract_json_array("[깨진 json") == []
    assert extract_json_array('{"a": 1}') == []


def test_parse_count_returns_minus_one_when_unknown():
    assert parse_count('{"count": 12, "basis": "번개장터"}') == (12, "번개장터")
    assert parse_count('{"count": -1}')[0] == -1
    assert parse_count("숫자 없음")[0] == -1
    assert parse_count('{"count": true}')[0] == -1  # bool은 int가 아니다


def test_rows_to_items_preserves_rank_and_drops_unpriced():
    rows = [
        {"title": "A", "price": "45,000원"},
        {"title": "B", "price": None},
        {"title": "C", "price": 30_000},
    ]
    items = rows_to_items(rows, query="q")
    assert [i.title for i in items] == ["A", "C"]
    assert [i.price for i in items] == [45_000, 30_000]
    assert [i.rank for i in items] == [0, 2]  # 원래 순위를 보존한다


def test_normalize_title_and_dedup_prefers_earlier_rank():
    assert normalize_title("리바이스 501 (빅E)") == normalize_title("리바이스501빅e")
    items = [
        HarvestItem(title="같은 매물", price=1000, rank=3),
        HarvestItem(title="같은  매물", price=1000, rank=1),
        HarvestItem(title="다른 매물", price=2000, rank=2),
    ]
    kept = dedup_items(items)
    assert len(kept) == 2
    assert kept[0].rank == 1  # 순위가 앞선 쪽이 남는다


def test_dedup_uses_url_when_present():
    items = [
        HarvestItem(title="제목 다름 1", price=1000, url="https://x.invalid/1", rank=0),
        HarvestItem(title="제목 다름 2", price=2000, url="https://x.invalid/1", rank=1),
    ]
    assert len(dedup_items(items)) == 1


def test_classify_condition_takes_the_worse_grade():
    """'A급이지만 오염 있음'은 C로 본다 — 낙관적으로 라벨링하면 단조성이 부풀려진다."""
    assert classify_condition("리바이스 A급 상태좋음") == "A"
    assert classify_condition("미사용 새제품 택포") == "S"
    assert classify_condition("A급이지만 오염 있음") == "C"
    assert classify_condition("그냥 청바지") == ""


def test_retail_gate_drops_only_out_of_range():
    items = [
        HarvestItem(title="정상", price=50_000),
        HarvestItem(title="자릿수 오탐", price=500),
        HarvestItem(title="정가보다 비쌈", price=300_000),
    ]
    assert retail_gate_mask(items, 100_000) == [False, True, True]
    assert retail_gate_mask(items, None) == [False, False, False]  # 정가 없으면 통과


def test_specificity_ladder_widens_and_labels():
    ladder = build_specificity_ladder("501 빅E 데님", brand="리바이스", category="팬츠")
    assert [level for level, _ in ladder] == ["모델 일치", "브랜드 유사", "카테고리 평균"]
    assert ladder[0][1].startswith("리바이스")


def test_specificity_ladder_without_brand_or_category():
    ladder = build_specificity_ladder("빈티지 데님 자켓")
    assert len(ladder) == 1
    assert ladder[0][0] == "모델 일치"


def test_count_queries_cover_every_stratum():
    labels = [label for label, _ in build_count_queries("리바이스 501")]
    assert len(labels) == len(set(labels))
    assert labels[-1].endswith("+")  # 최상단 층은 상한이 없다


# --- 레지스트리 -------------------------------------------------------------


def test_round_config_overrides_without_mutating_registry():
    tuned = round_config("R0", repeats=3, max_comps=50)
    assert tuned.repeats == 3
    assert tuned.max_comps == 50
    assert ROUNDS["R0"].repeats == 1  # 원본은 그대로여야 한다
    assert ROUNDS["R0"].max_comps == 10


def test_round_config_rejects_unknown_round():
    try:
        round_config("R99")
    except ValueError as exc:
        assert "R99" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("알 수 없는 라운드는 ValueError여야 한다")


def test_baseline_round_has_no_levers():
    """R0는 현행 프로덕션과 같아야 대조군 역할을 한다."""
    baseline = ROUNDS["R0"]
    assert baseline.levers == ()
    assert baseline.fanout == 1
    assert not baseline.mad_filter
    assert not baseline.stratified


# --- 순위 편향 재현 (축 D의 핵심) ---------------------------------------------


def test_mock_backend_reproduces_rank_price_bias():
    """**이 테스트가 축 D 지표의 존재 이유다.**

    순위검색 결과를 top-k로 자르면 분포가 왜곡된다는 것(CH015 M9)을 GMS 호출 없이
    재현하고, 가격 중립성 지표가 그 왜곡을 실제로 잡아내는지 확인한다. 편향을 끄면
    (`rank_bias=0`) 지표가 내려가야 한다 — 안 내려가면 지표가 다른 걸 재고 있는 것이다.
    """
    from run_histogram_sweep import price_neutrality

    config = round_config("R0", max_comps=40)
    biased = harvest(MockSearchBackend(rank_bias=0.95), config, "리바이스 501 빅E")
    neutral = harvest(MockSearchBackend(rank_bias=0.0), config, "리바이스 501 빅E")

    assert len(biased.items) > 10 and len(neutral.items) > 10
    assert price_neutrality(biased.items, k=10) > price_neutrality(neutral.items, k=10)


def test_harvest_reports_search_calls_for_cost_axis():
    """축 C — 검색 호출 수가 곧 비용이라 정확히 세어야 한다."""
    single = harvest(MockSearchBackend(), round_config("R0"), "쿼리")
    fanned = harvest(MockSearchBackend(), round_config("R3"), "쿼리")
    assert single.search_calls == 1
    assert fanned.search_calls > single.search_calls


def test_count_round_returns_counts_not_items():
    outcome = harvest(MockSearchBackend(), round_config("S1"), "리바이스 501")
    assert outcome.counts_by_stratum
    assert not outcome.items  # 매물을 파싱하지 않는다
