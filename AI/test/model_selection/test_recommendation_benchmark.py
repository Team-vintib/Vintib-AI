"""`recommendation_benchmark.RecommendationResult`의 지표 계산(Recall@K/Precision@K/NDCG@K)
자체를 검증하는 단위 테스트.

Throwaway/spike code for AI/test/ — NOT production code. `Jira S15P11A108-292`(추천 알고리즘
모델 학습) 결과물 5번("검증셋 기준 Recall@K/NDCG 평가")이 신뢰할 수 있으려면, 평가에 쓰는
지표 계산 함수 자체가 맞다는 게 먼저 보장돼야 한다 — 이 파일은 모델/데이터 없이 순수하게
`QueryRanking` 합성 픽스처로 그 계산 로직만 검증한다(코퍼스 다운로드도, 모델 로딩도 없음).

CI 주의사항
-----------
`recommendation_benchmark.py`는 모듈 최상단에서 `torch`/`loaders`(transformers)를 import한다.
CI의 `ai-test` 잡은 `AI/requirements-dev.txt`만 설치하고 `AI/test/requirements-test.txt`(torch
등)는 설치하지 않는다(`.gitlab-ci.yml` 확인됨) — 그래서 `pytest.importorskip("torch")`로
torch가 없는 환경에서는 이 모듈 전체를 에러 없이 스킵되게 한다. torch가 설치된 로컬 환경
(예: `recommendation` conda env)에서는 정상적으로 전부 실행된다.
"""

import pytest

torch = pytest.importorskip("torch")

from recommendation_benchmark import QueryRanking, RecommendationResult  # noqa: E402


def _result(*rankings: QueryRanking) -> RecommendationResult:
    return RecommendationResult(model_name="test", load_time_s=0.0, query_rankings=list(rankings))


class TestRecallAtK:
    def test_all_relevant_within_topk(self):
        r = _result(QueryRanking(query="q", target_category="A", ranked_categories=["A", "A", "B"]))
        assert r.recall_at_k(3) == pytest.approx(1.0)

    def test_partial_recall(self):
        # 정답 카테고리 아이템이 코퍼스에 2개 있는데 top-2에는 1개만 들어옴 -> 0.5
        r = _result(
            QueryRanking(query="q", target_category="A", ranked_categories=["A", "B", "A", "C"])
        )
        assert r.recall_at_k(2) == pytest.approx(0.5)

    def test_no_relevant_items_excluded_from_average(self):
        # 코퍼스에 정답 카테고리가 아예 없는 쿼리는 분모 0이라 평균 계산에서 제외되어야 함
        r = _result(QueryRanking(query="q", target_category="Z", ranked_categories=["A", "B"]))
        assert r.recall_at_k(2) == 0.0

    def test_macro_average_across_queries(self):
        r = _result(
            QueryRanking(query="q1", target_category="A", ranked_categories=["A", "B", "C"]),  # 1.0
            QueryRanking(
                query="q2", target_category="B", ranked_categories=["A", "C", "B"]
            ),  # 0.0 (top-2 밖)
        )
        assert r.recall_at_k(2) == pytest.approx(0.5)


class TestPrecisionAtK:
    def test_all_correct(self):
        r = _result(QueryRanking(query="q", target_category="A", ranked_categories=["A", "A", "B"]))
        assert r.precision_at_k(2) == pytest.approx(1.0)

    def test_half_correct(self):
        r = _result(QueryRanking(query="q", target_category="A", ranked_categories=["A", "B", "C"]))
        assert r.precision_at_k(2) == pytest.approx(0.5)

    def test_k_larger_than_corpus_uses_actual_length(self):
        # k=10인데 코퍼스가 2개뿐이면 min(k, len)로 분모를 코퍼스 크기에 맞춰야 함
        r = _result(QueryRanking(query="q", target_category="A", ranked_categories=["A", "B"]))
        assert r.precision_at_k(10) == pytest.approx(0.5)

    def test_empty_ranking_excluded(self):
        r = _result(QueryRanking(query="q", target_category="A", ranked_categories=[]))
        assert r.precision_at_k(3) == 0.0


class TestNdcgAtK:
    def test_perfect_ranking_is_one(self):
        # 정답이 1등 -> DCG == IDCG -> NDCG == 1.0
        r = _result(QueryRanking(query="q", target_category="A", ranked_categories=["A", "B", "C"]))
        assert r.ndcg_at_k(3) == pytest.approx(1.0)

    def test_relevant_item_ranked_last_in_topk(self):
        # 정답이 top-3의 마지막(3위): DCG = 1/log2(4), IDCG(relevant=1개) = 1/log2(2)
        # NDCG = log2(2)/log2(4) = 0.5
        r = _result(QueryRanking(query="q", target_category="A", ranked_categories=["B", "C", "A"]))
        assert r.ndcg_at_k(3) == pytest.approx(0.5)

    def test_relevant_item_outside_topk_is_zero(self):
        r = _result(QueryRanking(query="q", target_category="A", ranked_categories=["B", "C", "A"]))
        assert r.ndcg_at_k(2) == pytest.approx(0.0)

    def test_no_relevant_items_excluded_from_average(self):
        r = _result(QueryRanking(query="q", target_category="Z", ranked_categories=["B", "C", "A"]))
        assert r.ndcg_at_k(3) == 0.0

    def test_multiple_relevant_items_ideal_ranking(self):
        # 정답이 2개(A) 있고 top-2가 전부 정답 -> 이상적 랭킹이므로 NDCG == 1.0
        r = _result(
            QueryRanking(query="q", target_category="A", ranked_categories=["A", "A", "B", "C"])
        )
        assert r.ndcg_at_k(2) == pytest.approx(1.0)

    def test_rewards_higher_rank_more_than_recall_does(self):
        # recall/precision은 순서를 안 보므로 두 랭킹이 동점이지만, NDCG는 순서를 반영해
        # 정답이 더 앞에 있는 랭킹에 더 높은 점수를 줘야 한다 — 이게 recall/precision만으로는
        # 못 잡는, NDCG를 추가한 이유 그 자체를 검증하는 테스트.
        better = _result(
            QueryRanking(query="q", target_category="A", ranked_categories=["A", "B", "C"])
        )
        worse = _result(
            QueryRanking(query="q", target_category="A", ranked_categories=["B", "C", "A"])
        )
        assert better.recall_at_k(3) == worse.recall_at_k(3) == pytest.approx(1.0)
        assert better.ndcg_at_k(3) > worse.ndcg_at_k(3)
