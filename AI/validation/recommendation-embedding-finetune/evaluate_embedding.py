"""bge-m3 baseline vs 파인튜닝 버전(bge-m3-catalog-ft) 비교 평가.

Throwaway/spike code for AI/test/ — NOT production code. `Jira S15P11A108-292`의 결과물
5번("검증셋 기준 Recall@K/NDCG 평가")을 담당한다.

`AI/test/model_selection/recommendation_benchmark.py`를 그대로 import해서 재사용한다 —
로딩/임베딩/Recall·Precision·NDCG 계산 로직을 중복 작성하지 않기 위해서다. 이 스크립트가
새로 하는 일은 오직: (1) `dataset.py`의 val split으로 평가용 코퍼스/쿼리를 구성하고,
(2) baseline과 fine-tuned 두 후보를 **동일 코퍼스/쿼리로 나란히** 돌리는 것.

baseline과 fine-tuned를 반드시 같은 실행에서 나란히 비교해야 "파인튜닝이 실제로 효과가
있었는지"를 주장할 수 있다 — 이 스크립트 하나로 그 비교가 강제되도록 구성했다.

평가 코퍼스/쿼리 구성 — 트리비얼 매치 방지
--------------------------------------------
val 아이템을 그대로 코퍼스로 쓰면서 그 중 일부를 쿼리로도 쓰면, 쿼리 텍스트가 코퍼스에도
그대로 들어있어 "자기 자신과 매칭"되는 트리비얼 케이스가 생겨 지표가 부풀려진다. 이를
피하려고 `article_type`(카테고리) 그룹마다 일부 아이템을 쿼리 전용으로 떼어내고, 남은
아이템만 코퍼스로 쓴다(쿼리 아이템은 코퍼스에 없음) — recall/precision/NDCG가 "정말
카테고리가 다른 아이템들 사이에서 유사한 것을 찾아내는지"를 재도록.

주의: 코퍼스가 `ashraq/fashion-product-images-small` 플레이스홀더라는 점은
`recommendation_benchmark.py`와 동일하게 유효하다 — 실제 카탈로그가 아니다.

검증셋 기준 (Validation-set criteria)
--------------------------------------
1. **출처**: `dataset.py.load_catalog()`의 전체 아이템 중 `split_items()`가 나눈 val
   split만 사용한다(train은 절대 섞지 않음 — 파인튜닝이 학습 때 본 적 없는 데이터로만
   평가해야 "일반화"를 잰 게 된다).
2. **분리 기준**: `article_type`별 층화 샘플링, `val_ratio=0.2`, `seed=42`(둘 다
   `dataset.SEED`/`dataset.VAL_RATIO` 상수 — 재현 가능). 상품명 중복은 `load_catalog()`
   단계에서 이미 제거됨(같은 텍스트가 train/val 양쪽에 나타나는 리키지 방지, 실측 검증됨
   — `test_dataset.py::TestSplitThenBuildPairsIntegration`).
3. **쿼리/코퍼스 분리**: val 안에서도 `article_type`별로 `query_ratio=0.3`만큼을 쿼리
   전용으로 떼어내고, 코퍼스에는 넣지 않는다(트리비얼 자기매칭 방지, 위 섹션 참고).
4. **최소 표본 기준**: `article_type`당 val 아이템이 2개 미만이면(쿼리 1 + 코퍼스 1을
   못 만듦) 그 카테고리는 통째로 제외하고 경고를 출력한다.
5. **코퍼스 난이도**: `-180`이 5개 카테고리짜리 좁은 코퍼스에서 3개 모델 성능이 전부
   동일한 "천장 효과"로 결론을 못 냈다 — 이 스크립트는 `load_catalog()`가 스캔한
   범위의 **모든** `article_type`(수십 개)을 카테고리로 쓰기 때문에 구조적으로 더
   어렵다. 그래도 실행 시 `build_eval_corpus_and_queries()`가 출력하는 코퍼스/쿼리
   카테고리 수가 여전히 한 자릿수라면 결과를 신뢰하지 말 것(코퍼스가 너무 좁아 -180과
   같은 천장 효과가 재현될 수 있음).

성공 기준 / 결과 해석
----------------------
`print_report()` 표를 사람이 다음 기준으로 판단한다(자동 판정 없음 — 다른 벤치마크
모듈과 동일한 스탠스, `recommendation_benchmark.print_report` 참고):
- **회귀 없음이 최소 조건**: `bge_m3_catalog_ft`가 `bge_m3_baseline` 대비 recall@K/
  precision@K/NDCG@K 중 하나라도 뚜렷이 나빠지면(예: 5%p 이상 하락) 그 파인튜닝은
  채택 후보에서 제외한다.
- **개선 판단은 NDCG 우선**: recall/precision은 순서를 안 보므로 동점이 나올 수 있다
  (`test_recommendation_benchmark.py::test_rewards_higher_rank_more_than_recall_does`가
  이 차이를 보여준다) — NDCG@K가 baseline보다 뚜렷이 높으면(예: 5%p 이상) "파인튜닝이
  순위를 개선했다"는 증거로 본다.
- **`model_registry.ACTIVE_EMBEDDING` 승격 조건**: 위 두 조건을 만족하고, 4번 항목의
  코퍼스 난이도 경고가 없을 때만 승격을 검토한다 — `-180`이 걸어둔 "재검증 후 판단"
  조건을 그대로 계승한다.
"""

from __future__ import annotations

import random
import sys
from functools import partial
from pathlib import Path

import dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model_selection"))
from loaders import load_bge_m3
from model_registry import EMBEDDING_MODELS
from recommendation_benchmark import (
    CorpusItem,
    RecommendationCandidate,
    RecommendationQuery,
    _embed_bge_m3,
    print_report,
    run_all_recommendations,
)

FT_CHECKPOINT_DIR = Path(__file__).parent / "checkpoints" / "bge-m3-catalog-ft"

QUERY_RATIO = 0.3  # 카테고리별 쿼리로 떼어낼 비율(나머지는 코퍼스)

CANDIDATES: dict[str, RecommendationCandidate] = {
    "bge_m3_baseline": RecommendationCandidate(
        name="bge_m3_baseline",
        model_id=EMBEDDING_MODELS["bge-m3"],
        note="파인튜닝 전 원본 bge-m3 — 비교 기준선.",
        corpus_modality="text",
        load=partial(load_bge_m3, EMBEDDING_MODELS["bge-m3"]),
        embed_query_fn=_embed_bge_m3,
        embed_corpus_fn=_embed_bge_m3,
    ),
    "bge_m3_catalog_ft": RecommendationCandidate(
        name="bge_m3_catalog_ft",
        model_id=str(FT_CHECKPOINT_DIR),
        note="상품 카탈로그 프록시 라벨로 파인튜닝한 버전(finetune_embedding.py 산출물). "
        "체크포인트가 없으면 이 후보는 로드 실패로 건너뛴다(run_all_recommendations 정책).",
        corpus_modality="text",
        load=partial(load_bge_m3, str(FT_CHECKPOINT_DIR)),
        embed_query_fn=_embed_bge_m3,
        embed_corpus_fn=_embed_bge_m3,
    ),
}


def build_eval_corpus_and_queries(
    *, query_ratio: float = QUERY_RATIO, seed: int = ds.SEED
) -> tuple[list[CorpusItem], list[RecommendationQuery]]:
    """`dataset.py`의 val split으로 평가용 코퍼스/쿼리를 만든다.

    학습에 쓰인 (anchor, positive) 쌍이 아니라 val 아이템 자체를 코퍼스/쿼리로 쓴다 —
    파인튜닝 손실이 아니라 "검색 품질"을 보는 게 목적이라 원본 텍스트 그대로가 맞다.
    """
    catalog_items = ds.load_catalog()
    _, val_items = ds.split_items(catalog_items)

    by_type: dict[str, list[ds.CatalogItem]] = {}
    for item in val_items:
        by_type.setdefault(item.article_type, []).append(item)

    rng = random.Random(seed)
    corpus_items: list[ds.CatalogItem] = []
    queries: list[RecommendationQuery] = []
    skipped = []
    for article_type, group in by_type.items():
        if len(group) < 2:
            skipped.append(article_type)
            continue  # 쿼리 1개 + 코퍼스 1개를 만들 최소 조건
        shuffled = group[:]
        rng.shuffle(shuffled)
        n_query = min(max(1, round(len(shuffled) * query_ratio)), len(shuffled) - 1)
        query_group, corpus_group = shuffled[:n_query], shuffled[n_query:]
        queries.extend((qi.text, qi.article_type) for qi in query_group)
        corpus_items.extend(corpus_group)

    if skipped:
        print(f"[build_eval_corpus_and_queries] 아이템 부족으로 제외된 article_type: {skipped}")

    corpus = [CorpusItem(text=ci.text, category=ci.article_type) for ci in corpus_items]
    return corpus, queries


if __name__ == "__main__":
    if not FT_CHECKPOINT_DIR.exists():
        print(
            f"[evaluate_embedding] 경고: {FT_CHECKPOINT_DIR}가 없습니다 — 먼저 "
            "`python finetune_embedding.py`를 실행하세요. baseline만 평가합니다."
        )

    eval_corpus, eval_queries = build_eval_corpus_and_queries()
    print(f"[evaluate_embedding] 평가 코퍼스 {len(eval_corpus)}건, 쿼리 {len(eval_queries)}건")

    results = run_all_recommendations(CANDIDATES, eval_corpus, eval_queries)
    print()
    print_report(results, k_values=(3, 5))
