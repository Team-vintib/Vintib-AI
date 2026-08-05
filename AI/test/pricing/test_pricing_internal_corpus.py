"""내부 CLIP 유사도 코퍼스 — 순수 함수(`query_similar`) + 로딩 계약 검증.

실제 `.npy`/`.json` 파일 I/O는 `load_corpus`/`get_corpus`에서만 하고, 검색 로직
(`query_similar`)은 순수 함수라 손으로 만든 `Corpus`로 torch/실제 코퍼스 없이 검증한다.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from app.pricing.internal_corpus import (
    Corpus,
    CorpusItem,
    CorpusNotReady,
    load_corpus,
    query_similar,
)

# --- query_similar (순수 함수) ------------------------------------------------


def _item(category: str, price: int) -> CorpusItem:
    return CorpusItem(aihub_category=category, synthetic_price=price, data_source="synthetic_aihub")


def _corpus() -> Corpus:
    items = [_item("JACKET", 100_000), _item("JACKET", 90_000), _item("SHIRT", 40_000)]
    vectors = np.array(
        [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]],
        dtype=np.float32,
    )
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    return Corpus(items=items, vectors=vectors)


def test_query_similar_orders_by_descending_similarity():
    query = [1.0, 0.0]
    matches = query_similar(query, _corpus(), top_k=3, min_similarity=-1.0)

    assert [item.aihub_category for item, _ in matches][:2] == ["JACKET", "JACKET"]
    assert matches[0][1] >= matches[1][1] >= matches[2][1]


def test_query_similar_respects_top_k():
    query = [1.0, 0.0]
    matches = query_similar(query, _corpus(), top_k=1, min_similarity=-1.0)

    assert len(matches) == 1


def test_query_similar_filters_below_min_similarity():
    """SHIRT 벡터는 JACKET 쿼리와 직교라 유사도가 낮다 — 하한 위로 걸러진다."""
    query = [1.0, 0.0]
    matches = query_similar(query, _corpus(), top_k=3, min_similarity=0.5)

    assert all(item.aihub_category == "JACKET" for item, _ in matches)


def test_query_similar_returns_empty_when_nothing_meets_the_floor():
    """코사인 유사도의 최댓값은 1.0이다 — 1.0보다 큰 하한을 주면 무조건 다 걸러진다."""
    query = [1.0, 0.0]
    matches = query_similar(query, _corpus(), top_k=3, min_similarity=1.5)

    assert matches == []


# --- load_corpus (파일 I/O) ---------------------------------------------------


def _write_corpus(tmp_path, rows: list[dict], vectors: np.ndarray) -> None:
    np.save(tmp_path / "internal_clip_vectors.npy", vectors)
    (tmp_path / "internal_clip_meta.json").write_text(
        json.dumps(rows, ensure_ascii=False), encoding="utf-8"
    )


def test_load_corpus_reads_matching_vectors_and_meta(tmp_path):
    rows = [
        {"aihub_category": "JACKET", "synthetic_price": 100_000, "data_source": "synthetic_aihub"}
    ]
    _write_corpus(tmp_path, rows, np.array([[1.0, 0.0]], dtype=np.float32))

    corpus = load_corpus(tmp_path)

    assert len(corpus.items) == 1
    assert corpus.items[0].aihub_category == "JACKET"
    assert corpus.vectors.shape == (1, 2)


def test_load_corpus_missing_files_raises_not_ready(tmp_path):
    with pytest.raises(CorpusNotReady):
        load_corpus(tmp_path)


def test_load_corpus_row_count_mismatch_raises_not_ready(tmp_path):
    rows = [
        {"aihub_category": "JACKET", "synthetic_price": 100_000, "data_source": "synthetic_aihub"},
        {"aihub_category": "SHIRT", "synthetic_price": 40_000, "data_source": "synthetic_aihub"},
    ]
    _write_corpus(tmp_path, rows, np.array([[1.0, 0.0]], dtype=np.float32))  # 벡터는 1행뿐

    with pytest.raises(CorpusNotReady, match="행 수 불일치"):
        load_corpus(tmp_path)


def test_load_corpus_empty_meta_raises_not_ready(tmp_path):
    _write_corpus(tmp_path, [], np.zeros((0, 2), dtype=np.float32))

    with pytest.raises(CorpusNotReady):
        load_corpus(tmp_path)
