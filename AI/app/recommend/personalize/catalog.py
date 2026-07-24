"""상품 카탈로그 + 아이템 임베딩 로더 (개인화 추천의 데이터 입력부).

**실데이터 전환 시 바뀌는 건 이 모듈뿐이다.** MVP는 목업 카탈로그(data/mock_catalog.json)를
읽고, 아이템 임베딩을 numpy로 **결정적으로 생성**한다(torch/임베딩 모델 불필요 — 서빙 경로는
경량 의존성만). 실데이터 전환 시에는 오프라인 파이프라인(pipeline/embed_catalog.py)이 만든
item_vectors.npy(kanana 임베딩) + item_meta.json 캐시를 읽도록 `load_catalog`만 교체한다.

목업 벡터 규칙: `정규화( 카테고리_basis + 0.6·브랜드_basis + 0.15·상품_noise )`.
각 basis는 키로 시드한 np.random.default_rng로 생성 → 같은 카테고리/브랜드끼리 가깝게
배치되어 취향 벡터 재정렬 효과가 드러난다.

설계: .claude/plans/ai/002-personalized-recommendation-mvp.md
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

_DATA_DIR = Path(__file__).resolve().parent / "data"
_MOCK_CATALOG_FILE = _DATA_DIR / "mock_catalog.json"

# 목업 임베딩 차원(결정적 생성용). 실데이터(kanana) 전환 시 실제 임베딩 차원으로 대체된다.
_EMBED_DIM = 32
_BRAND_WEIGHT = 0.6
_NOISE_WEIGHT = 0.15

# 후보로 노출 가능한 판매 상태(가시성 필터). DRAFT/PRIVATE/SOLD 는 제외한다.
VISIBLE_SALE_STATUS = frozenset({"ON_SALE", "AUCTION_SCHEDULED", "AUCTION_IN_PROGRESS"})


class CatalogNotReady(Exception):
    """아이템 임베딩/카탈로그 아티팩트를 읽지 못함(실데이터 경로 대비 계약)."""


@dataclass(frozen=True)
class CatalogItem:
    """카탈로그 상품 한 건. 응답 카드 필드 + 랭킹/필터용 메타(brand_id/category_id/view_count)."""

    product_id: int
    title: str
    thumbnail: str | None
    price: int | None
    brand: str | None
    brand_id: int | None
    category_id: int | None
    sale_type: str
    sale_status: str
    view_count: int

    @property
    def is_visible(self) -> bool:
        return self.sale_status in VISIBLE_SALE_STATUS


@dataclass(frozen=True)
class Catalog:
    """카탈로그 + 아이템 벡터. 벡터는 items 순서와 index로 정렬되며 L2 정규화돼 있다."""

    items: list[CatalogItem]
    vectors: np.ndarray  # shape (N, D), L2 정규화
    _index_by_pid: dict[int, int]

    def index_of(self, product_id: int) -> int | None:
        return self._index_by_pid.get(product_id)


def _seeded_vector(key: str, dim: int) -> np.ndarray:
    """키를 시드로 한 결정적 표준정규 벡터. 같은 키는 항상 같은 벡터를 준다."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()[:8]
    seed = int.from_bytes(digest, "little")
    return np.random.default_rng(seed).standard_normal(dim)


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm == 0.0:
        return vec
    return vec / norm


def _mock_vector(item: CatalogItem) -> np.ndarray:
    """카테고리/브랜드/상품 basis를 합성해 결정적 아이템 벡터를 만든다."""
    category_basis = _seeded_vector(f"category:{item.category_id}", _EMBED_DIM)
    brand_basis = _seeded_vector(f"brand:{item.brand_id}", _EMBED_DIM)
    product_noise = _seeded_vector(f"product:{item.product_id}", _EMBED_DIM)
    raw = category_basis + _BRAND_WEIGHT * brand_basis + _NOISE_WEIGHT * product_noise
    return _normalize(raw)


def _item_from_row(row: dict) -> CatalogItem:
    return CatalogItem(
        product_id=row["product_id"],
        title=row["title"],
        thumbnail=row.get("thumbnail"),
        price=row.get("price"),
        brand=row.get("brand"),
        brand_id=row.get("brand_id"),
        category_id=row.get("category_id"),
        sale_type=row["sale_type"],
        sale_status=row["sale_status"],
        view_count=row.get("view_count", 0),
    )


def load_mock_catalog(path: Path = _MOCK_CATALOG_FILE) -> Catalog:
    """목업 카탈로그 JSON을 읽어 아이템 + 결정적 임베딩 벡터로 Catalog를 만든다."""
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogNotReady(f"목업 카탈로그를 읽을 수 없습니다: {path}") from exc
    if not rows:
        raise CatalogNotReady(f"목업 카탈로그가 비어 있습니다: {path}")

    items = [_item_from_row(row) for row in rows]
    vectors = np.stack([_mock_vector(item) for item in items]).astype(np.float32)
    index_by_pid = {item.product_id: i for i, item in enumerate(items)}
    return Catalog(items=items, vectors=vectors, _index_by_pid=index_by_pid)


@lru_cache
def get_catalog() -> Catalog:
    """서비스가 공유하는 카탈로그 싱글턴(로드 결과 캐시)."""
    return load_mock_catalog()
