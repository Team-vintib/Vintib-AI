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
"""

from __future__ import annotations

import random
import sys
from functools import partial
from pathlib import Path

import dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model_selection"))
from loaders import load_bge_m3  # noqa: E402 — sys.path 조정 이후 import
from model_registry import EMBEDDING_MODELS  # noqa: E402
from recommendation_benchmark import (  # noqa: E402
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
