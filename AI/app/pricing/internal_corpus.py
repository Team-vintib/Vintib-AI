"""내부 CLIP 유사도 코퍼스 로더 + 검색 (`internal_clip` comps 백엔드, CH020).

`app/recommend/personalize/catalog.py`의 `get_catalog()` 패턴을 그대로 따른다 — 코퍼스는
`aihub_seed_pricing_corpus.py`(오프라인 스크립트)가 만든 `.npy`(임베딩) + `.json`(메타)
쌍을 프로세스당 1회 읽어 메모리에 유지한다. pgvector 대신 flat-file을 쓰는 이유는 CH020
문서 참고 — 코드베이스에 아직 pgvector 코사인 쿼리 전례가 없고, 코퍼스 크기가
(`--max-per-category`로) 통제되는 합성 데이터라 굳이 새 인프라를 만들 이유가 없다.

이번 라운드의 코퍼스는 **전부 합성 데이터**다(`CorpusItem.data_source == "synthetic_aihub"`)
— AI-Hub 분류기 학습 이미지 + 가상 가격. 실제 시세가 아니다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

VECTORS_FILENAME = "internal_clip_vectors.npy"
META_FILENAME = "internal_clip_meta.json"


class CorpusNotReady(Exception):
    """코퍼스 파일이 없거나 손상됨 — `aihub_seed_pricing_corpus.py`를 먼저 돌려야 한다."""


@dataclass(frozen=True)
class CorpusItem:
    """코퍼스 항목 1건의 메타. 벡터는 `Corpus.vectors`에 같은 인덱스로 정렬돼 있다."""

    aihub_category: str
    synthetic_price: int
    data_source: str  # 항상 "synthetic_aihub" — 실데이터와 절대 안 섞이게 하는 표식


@dataclass(frozen=True)
class Corpus:
    items: list[CorpusItem]
    vectors: np.ndarray  # shape (N, clip_embed.EMBEDDING_DIM), L2 정규화됨


def _item_from_row(row: dict) -> CorpusItem:
    return CorpusItem(
        aihub_category=row["aihub_category"],
        synthetic_price=row["synthetic_price"],
        data_source=row["data_source"],
    )


def load_corpus(corpus_dir: Path) -> Corpus:
    """`corpus_dir`에서 벡터+메타 쌍을 읽는다. 둘 다 없으면 `CorpusNotReady`."""
    vectors_path = corpus_dir / VECTORS_FILENAME
    meta_path = corpus_dir / META_FILENAME
    try:
        vectors = np.load(vectors_path)
        rows = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise CorpusNotReady(
            f"내부 CLIP 코퍼스를 읽을 수 없습니다: {corpus_dir} "
            "(aihub_seed_pricing_corpus.py를 먼저 돌릴 것)"
        ) from exc
    if len(rows) != len(vectors):
        raise CorpusNotReady(f"코퍼스 행 수 불일치: vectors={len(vectors)} vs meta={len(rows)}")
    if not rows:
        raise CorpusNotReady(f"내부 CLIP 코퍼스가 비어 있습니다: {corpus_dir}")
    items = [_item_from_row(row) for row in rows]
    return Corpus(items=items, vectors=vectors.astype(np.float32))


@lru_cache
def get_corpus(corpus_dir: str) -> Corpus:
    """서비스가 공유하는 코퍼스 싱글턴(로드 결과 캐시). `corpus_dir`은 `lru_cache` 키라
    문자열로 받는다(`Path`는 해시 가능하지만 호출부 일관성을 위해 문자열로 통일)."""
    return load_corpus(Path(corpus_dir))


def query_similar(
    embedding: list[float], corpus: Corpus, *, top_k: int, min_similarity: float
) -> list[tuple[CorpusItem, float]]:
    """코사인 유사도 top-K를 순수 함수로 계산한다.

    `embedding`과 `corpus.vectors`가 이미 L2 정규화돼 있다는 전제로 내적만 하면 코사인
    유사도와 같다 — 코퍼스 쪽은 `aihub_seed_pricing_corpus.py`가, 쿼리 쪽은
    `clip_embed.embed_image()`가 이미 정규화해서 넘긴다.
    """
    query = np.asarray(embedding, dtype=np.float32)
    scores = corpus.vectors @ query
    order = np.argsort(-scores)[:top_k]
    return [(corpus.items[i], float(scores[i])) for i in order if scores[i] >= min_similarity]
