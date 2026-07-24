"""`dataset.py`의 train/val 분리 및 (anchor, positive, negative) 쌍 생성 로직 검증.

Throwaway/spike code for AI/test/ — NOT production code. "검증셋에 대한 기준"이 실제로
지켜지는지(카테고리 리키지 없음, positive/negative가 올바른 카테고리에서 나옴)를 코드로
고정해두는 게 목적이다 — 이전에 실제 HF 데이터셋으로 手동 확인했던 것(오버랩 0건)을
합성 픽스처로 반복 가능하게 만든 버전이다.

네트워크 I/O 없음
------------------
`load_catalog()`(HF `datasets` 다운로드)는 테스트하지 않는다 — 이 파일은 순수 로직
(`split_items`/`build_pairs`)만 합성 `CatalogItem`으로 검증한다. `dataset.py` 자체는
모듈 최상단에서 `datasets`/`torch` 등 무거운 의존성을 import하지 않으므로(전부 함수
내부 지연 import), 이 테스트는 CI(`ai-test`, `AI/requirements-dev.txt`만 설치)에서도
추가 의존성 없이 그대로 돈다.
"""

from __future__ import annotations

from dataset import CatalogItem, build_pairs, split_items


def _make_items(article_type: str, master_category: str, count: int) -> list[CatalogItem]:
    return [
        CatalogItem(
            text=f"{article_type} item {i}",
            article_type=article_type,
            master_category=master_category,
        )
        for i in range(count)
    ]


class TestSplitItems:
    def test_no_text_overlap_between_train_and_val(self):
        items = (
            _make_items("Shirts", "Apparel", 10)
            + _make_items("Dresses", "Apparel", 8)
            + _make_items("Watches", "Accessories", 6)
        )
        train, val = split_items(items, val_ratio=0.3, seed=0)

        train_texts = {i.text for i in train}
        val_texts = {i.text for i in val}
        assert train_texts.isdisjoint(val_texts)
        # 전수 보존 확인 — 분리 과정에서 아이템이 사라지거나 중복되면 안 됨
        assert len(train) + len(val) == len(items)

    def test_val_ratio_roughly_respected_per_category(self):
        items = _make_items("Shirts", "Apparel", 20)
        train, val = split_items(items, val_ratio=0.25, seed=0)
        assert len(val) == 5
        assert len(train) == 15

    def test_small_category_keeps_at_least_one_train_item(self):
        # 아이템이 1개뿐인 카테고리는 val로 다 빠지면 train에서 positive 쌍을 못 만든다 —
        # split_items가 최소 1개는 train에 남겨야 한다.
        items = _make_items("Rare", "Apparel", 1)
        train, val = split_items(items, val_ratio=0.9, seed=0)
        assert len(train) == 1
        assert len(val) == 0


class TestBuildPairs:
    def test_positive_pair_comes_from_same_article_type(self):
        items = _make_items("Shirts", "Apparel", 5) + _make_items("Dresses", "Apparel", 5)
        pairs = build_pairs(items, num_negatives=2, seed=0)
        shirts_texts = {i.text for i in items if i.article_type == "Shirts"}
        for record in pairs:
            if record["query"] in shirts_texts:
                assert record["pos"][0] in shirts_texts

    def test_negative_never_same_article_type_as_query(self):
        items = (
            _make_items("Shirts", "Apparel", 5)
            + _make_items("Dresses", "Apparel", 5)
            + _make_items("Watches", "Accessories", 5)
        )
        pairs = build_pairs(items, num_negatives=3, seed=0)
        text_to_article_type = {i.text: i.article_type for i in items}
        for record in pairs:
            query_type = text_to_article_type[record["query"]]
            for neg_text in record["neg"]:
                assert text_to_article_type[neg_text] != query_type

    def test_category_with_single_item_is_skipped(self):
        # article_type당 최소 2개(MIN_ITEMS_PER_CATEGORY)가 없으면 positive를 못 만드므로
        # 그 카테고리의 아이템은 결과에서 빠져야 한다.
        items = _make_items("Rare", "Apparel", 1) + _make_items("Shirts", "Apparel", 3)
        pairs = build_pairs(items, num_negatives=1, seed=0)
        queries = {record["query"] for record in pairs}
        assert "Rare item 0" not in queries

    def test_every_item_with_enough_peers_produces_exactly_one_record(self):
        items = _make_items("Shirts", "Apparel", 4) + _make_items("Dresses", "Apparel", 4)
        pairs = build_pairs(items, num_negatives=2, seed=0)
        assert len(pairs) == len(items)


class TestSplitThenBuildPairsIntegration:
    def test_pairs_built_after_split_never_leak_across_splits(self):
        """실제 파이프라인 순서(먼저 split, 그다음 각 split 안에서만 build_pairs)를 그대로
        재현해, train 쪽 쌍이 val 텍스트를 전혀 참조하지 않는지 확인한다 — 이게 이번 검증셋
        기준의 핵심 불변식이다."""
        items = (
            _make_items("Shirts", "Apparel", 20)
            + _make_items("Dresses", "Apparel", 20)
            + _make_items("Watches", "Accessories", 20)
        )
        train, val = split_items(items, val_ratio=0.3, seed=0)
        val_texts = {i.text for i in val}

        train_pairs = build_pairs(train, num_negatives=3, seed=0)
        for record in train_pairs:
            assert record["query"] not in val_texts
            assert record["pos"][0] not in val_texts
            assert all(neg not in val_texts for neg in record["neg"])
