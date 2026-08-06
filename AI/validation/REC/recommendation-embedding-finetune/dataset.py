"""추천 임베딩 모델(bge-m3) 파인튜닝용 프록시 라벨 데이터셋 빌더.

Throwaway/spike code for AI/test/ — NOT production code. `Jira S15P11A108-292`(추천
알고리즘 모델 학습)의 결과물 1·2번("학습용 상품/쿼리 데이터셋 구축", "데이터 전처리 및
학습/검증 셋 분리")을 담당한다.

프록시 라벨 — 왜 필요한가
--------------------------
실제 상품 카탈로그도, 사용자 클릭/구매 로그도 아직 없다(FE/BE 도메인 데이터 미구축).
`AI/test/model_selection/recommendation_benchmark.py`가 이미 쓰고 있는 공개 데이터셋
`ashraq/fashion-product-images-small`(HF `datasets`)을 그대로 재사용해, 카테고리
메타데이터(`articleType`)를 "같은 카테고리 = 유사 상품"이라는 약지도(weak supervision)
신호로 취급한다. **실제 서비스 카탈로그가 아니다** — 실제 카탈로그/로그가 확보되면
`load_catalog()`의 데이터 소스만 교체하면 된다(파인튜닝/평가 스크립트는 그대로).

카테고리 리키지 방지가 핵심
----------------------------
반드시 **아이템(row) 단위로 먼저 train/val을 나누고, (anchor, positive) 쌍은 그 이후
각 split 내부에서만** 만든다. 순서를 반대로 하면(쌍을 먼저 만들고 나중에 나누면) 같은
상품이 양쪽 split에 걸쳐 등장할 수 있어 평가 지표가 부풀려진다.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SEED = 42
VAL_RATIO = 0.2

# 카테고리당 최소 이 개수는 있어야 (anchor, positive) 쌍을 만들 수 있다 — 미만이면 그 카테고리는
# 건너뛴다(경고 출력).
MIN_ITEMS_PER_CATEGORY = 2

# 쿼리 하나당 만들 명시적 negative 개수. FlagEmbedding 파인튜닝은 in-batch negative에도
# 의존하지만, 배치 내 우연히 전부 유사 카테고리만 뽑히는 경우를 막기 위해 최소한의 명시적
# negative를 함께 제공한다.
NUM_EXPLICIT_NEGATIVES = 4

_FASHION_DATASET_ID = "ashraq/fashion-product-images-small"

_DATA_DIR = Path(__file__).parent / "data"
TRAIN_JSONL = _DATA_DIR / "train.jsonl"
VAL_JSONL = _DATA_DIR / "val.jsonl"


@dataclass(frozen=True)
class CatalogItem:
    """카탈로그(프록시) 아이템 하나. `recommendation_benchmark.CorpusItem`과 달리 이미지는
    다루지 않는다 — 이번 파인튜닝은 텍스트 임베딩(bge-m3)만 스코프."""

    text: str
    article_type: str  # 세부 카테고리 (positive 쌍의 기준)
    master_category: str  # 상위 카테고리 (negative 후보 배제 기준)


def load_catalog(*, scan_rows: int = 20000, min_text_len: int = 3) -> list[CatalogItem]:
    """`ashraq/fashion-product-images-small`에서 카탈로그 아이템을 읽어온다.

    `recommendation_benchmark.load_sample_corpus()`와 달리 특정 카테고리로 좁히지 않고
    `scan_rows` 내 전체 `articleType` 범위를 그대로 쓴다 — 파인튜닝은 벤치마크보다 더 넓은
    다양성이 있어야 프록시 라벨의 노이즈(같은 카테고리인데 실제로는 안 유사한 경우)가
    희석된다.

    **네트워크 I/O 발생** — 명시적으로 호출해야만 실행된다(import 시점엔 실행 안 됨).

    Args:
        scan_rows: 앞에서부터 몇 행을 훑을지.
        min_text_len: 이보다 짧은 상품명은 노이즈로 보고 제외.

    Returns:
        `CatalogItem` 목록(카테고리 무관, 스캔한 범위 내 전부).
    """
    from datasets import load_dataset

    dataset = load_dataset(_FASHION_DATASET_ID, split=f"train[:{scan_rows}]")

    items: list[CatalogItem] = []
    seen_texts: set[str] = set()  # 중복 상품명 제거 — 실측 확인됨(500건 스캔 중 3건 중복).
    # 중복을 안 없애면 같은 텍스트가 train/val 양쪽에 걸쳐 등장할 수 있어(다른 row, 같은
    # productDisplayName) split_items()의 "아이템 단위 분리"가 무력화된다.
    for row in dataset:
        text = (row.get("productDisplayName") or "").strip()
        article_type = row.get("articleType")
        master_category = row.get("masterCategory")
        if not text or len(text) < min_text_len or not article_type or not master_category:
            continue
        if text in seen_texts:
            continue
        seen_texts.add(text)
        items.append(
            CatalogItem(text=text, article_type=article_type, master_category=master_category)
        )
    return items


def split_items(
    items: list[CatalogItem], *, val_ratio: float = VAL_RATIO, seed: int = SEED
) -> tuple[list[CatalogItem], list[CatalogItem]]:
    """`article_type`별 층화 샘플링으로 **아이템 단위** train/val 분리.

    (anchor, positive) 쌍은 이 함수가 반환한 각 리스트 안에서만(`build_pairs` 호출 시)
    만들어져야 한다 — 그래야 같은 상품이 train/val 양쪽에 걸쳐 지표를 부풀리는 리키지가
    생기지 않는다.
    """
    rng = random.Random(seed)
    by_category: dict[str, list[CatalogItem]] = {}
    for item in items:
        by_category.setdefault(item.article_type, []).append(item)

    train: list[CatalogItem] = []
    val: list[CatalogItem] = []
    for category_items in by_category.values():
        shuffled = category_items[:]
        rng.shuffle(shuffled)
        n_val = round(len(shuffled) * val_ratio)
        # 아이템이 너무 적어 val이 전부를 가져가면 그 카테고리는 train에서 쌍을 못 만든다 —
        # 최소 1개는 train에 남긴다(그래도 다음 build_pairs에서 MIN_ITEMS_PER_CATEGORY 체크로
        # 걸러질 수 있다).
        n_val = min(n_val, max(0, len(shuffled) - 1))
        val.extend(shuffled[:n_val])
        train.extend(shuffled[n_val:])
    return train, val


def build_pairs(
    items: list[CatalogItem], *, num_negatives: int = NUM_EXPLICIT_NEGATIVES, seed: int = SEED
) -> list[dict[str, Any]]:
    """`items`(train 또는 val 한쪽) 내부에서만 FlagEmbedding 파인튜닝 JSONL 스키마
    (`{"query": ..., "pos": [...], "neg": [...]}`)에 맞는 레코드를 만든다.

    - positive: 같은 `article_type` 내 다른 아이템 하나(랜덤).
    - negative: 다른 `master_category`(상위 카테고리 자체가 다른, 확실히 안 유사한 아이템)
      에서 `num_negatives`개 랜덤 샘플. `master_category`가 하나뿐이면 같은 `master_category`
      안의 다른 `article_type`으로 대체한다.
    - 같은 `article_type` 아이템이 1개뿐이면(positive를 못 만듦) 그 아이템은 건너뛴다.
    """
    rng = random.Random(seed)
    by_article_type: dict[str, list[CatalogItem]] = {}
    for item in items:
        by_article_type.setdefault(item.article_type, []).append(item)

    skipped = [cat for cat, group in by_article_type.items() if len(group) < MIN_ITEMS_PER_CATEGORY]
    if skipped:
        print(
            f"[build_pairs] positive를 만들 수 없어 건너뛰는 article_type "
            f"(아이템 {MIN_ITEMS_PER_CATEGORY}개 미만): {skipped}"
        )

    records: list[dict[str, Any]] = []
    for item in items:
        same_type = by_article_type[item.article_type]
        if len(same_type) < MIN_ITEMS_PER_CATEGORY:
            continue
        positive = rng.choice([other for other in same_type if other is not item])

        other_master = [
            other
            for other in items
            if other.master_category != item.master_category and other is not item
        ]
        if len(other_master) >= num_negatives:
            negatives = rng.sample(other_master, num_negatives)
        else:
            # master_category가 다양하지 않으면(스캔 범위가 좁을 때) 같은 상위 카테고리 내
            # 다른 article_type으로 대체 — 완전한 in-batch negative 의존보다는 낫다.
            fallback_pool = [
                other
                for other in items
                if other.article_type != item.article_type and other is not item
            ]
            negatives = rng.sample(fallback_pool, min(num_negatives, len(fallback_pool)))

        if not negatives:
            continue  # 후보 자체가 없으면(코퍼스가 너무 좁으면) 이 레코드는 제외

        records.append(
            {
                "query": item.text,
                "pos": [positive.text],
                "neg": [n.text for n in negatives],
            }
        )
    return records


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[write_jsonl] {len(records)}건 -> {path}")


# --------------------------------------------------------------------------
# CLI 단독 실행 (선택 사항) — `python dataset.py`로 직접 돌릴 때만 train/val JSONL을 생성한다.
# --------------------------------------------------------------------------
if __name__ == "__main__":
    catalog_items = load_catalog()
    print(f"[dataset] 카탈로그 아이템 {len(catalog_items)}건 로드")

    train_items, val_items = split_items(catalog_items)
    print(f"[dataset] train={len(train_items)}건, val={len(val_items)}건")

    write_jsonl(build_pairs(train_items), TRAIN_JSONL)
    write_jsonl(build_pairs(val_items), VAL_JSONL)
