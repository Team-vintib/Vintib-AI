"""동일 상품 텍스트 매칭용 후보 코퍼스 — AI 소유 postgres-vector, BE DB와 무관(CH030).

CH024의 `internal` 백엔드는 실시간으로 이미 계산된 임베딩(`product_garment_embedding`)만
조회하면 끝나지만, 텍스트 매칭(`internal_text`)은 비교 대상이 될 "다른 상품들"의 제목·브랜드·
카테고리를 알아야 후보를 추릴 수 있다. BE에 검색 API가 없으므로(`docs/plans/AI/
CH030-pricing-text-match.md`) 이 모듈이 `GET /api/products`를 카테고리별로 pull해 AI 자체
코퍼스로 캐시하고, 매칭 키(`app/pricing/product_match.py`)를 미리 계산해 같이 저장한다.

`embedding_store.py`와 같은 pgvector 인스턴스(`get_vector_engine()`)를 쓰지만 벡터 컬럼은
없다 — 순수 텍스트/정형 필드 캐시라 다이얼렉트 종속적인 `ON CONFLICT`(postgres 전용) 대신
"조회 후 갱신/삽입" 방식으로 upsert한다. 덕분에 `store.py`처럼 인메모리 SQLite로도 그대로
테스트할 수 있다.

브랜드 별칭 사전(`GET /api/brands`)은 `get_brand_alias_map()`이 프로세스 수명 동안 캐시한다
(21개 고정 마스터라 자주 안 바뀐다 — 바뀌면 `get_brand_alias_map.cache_clear()`로 강제 갱신).

설계: docs/plans/AI/CH030-pricing-text-match.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import DateTime, Integer, String, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.db import get_vector_engine
from app.pricing.attribute_extraction import build_attribute_extractor
from app.pricing.product_match import build_match_keys
from app.shared import be_client

__all__ = [
    "CorpusCandidate",
    "find_by_match_key",
    "get_brand_alias_map",
    "init_schema",
    "refresh_category",
]


class Base(DeclarativeBase):
    pass


class ProductCorpusItem(Base):
    """상품 하나의 최신 텍스트 매칭 스냅샷. `product_id`는 유니크 — 재pull 시 덮어쓴다."""

    __tablename__ = "product_corpus_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    brand_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category_id: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sale_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sale_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at_be: Mapped[str | None] = mapped_column(String(32), nullable=True)
    match_key_strict: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    match_key_relaxed: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


@dataclass(frozen=True)
class CorpusCandidate:
    """DAO 반환용 — `hedge.InternalCandidate`로 바꾸기 전 원본 필드."""

    product_id: int
    title: str
    price: int | None
    sale_type: str | None
    sale_status: str | None
    created_at: str | None


def init_schema() -> None:
    """테이블 생성. 이미 있으면 아무 것도 안 한다(멱등). 앱 기동에 묶지 않는다."""
    engine = get_vector_engine()
    with engine.begin() as conn:
        Base.metadata.create_all(conn)


@lru_cache
def get_brand_alias_map() -> dict[str, int]:
    """`GET /api/brands`를 `{정규화된 name/nameEn: brand_id}` 사전으로 캐시한다.

    조회 실패는 빈 사전 — 브랜드 파싱이 안 되는 것뿐이고 매칭 자체를 막지 않는다
    (`resolve_brand_id()`가 이 경우 `brand_id=None`으로 처리, `be_client.fetch_product()`와
    같은 관용 원칙). 21개 고정 마스터라 프로세스 수명 동안 재조회하지 않는다 — 강제 갱신은
    `get_brand_alias_map.cache_clear()`.
    """
    brands = be_client.fetch_brands()
    if brands is None:
        return {}
    alias_map: dict[str, int] = {}
    for brand in brands:
        if brand.name:
            alias_map[brand.name.strip().lower()] = brand.brand_id
        if brand.name_en:
            alias_map[brand.name_en.strip().lower()] = brand.brand_id
    return alias_map


def refresh_category(category_id: int, *, page_size: int = 100) -> int:
    """이 카테고리의 상품을 전부 pull해 코퍼스를 갱신한다. 갱신된 건수를 돌려준다.

    BE 조회가 실패하면(네트워크 오류 등) 0을 돌려주고 아무것도 갱신하지 않는다 — 호출부는
    다른 카테고리 갱신을 계속하면 된다(`be_client.fetch_products_page()`와 같은 관용 원칙).

    **1단계(속성 추출) 백엔드는 조회 시점(`comps.InternalTextCompsSource`)과 항상 같아야
    한다**(CH031) — 코퍼스가 regex 키로 채워져 있는데 조회는 llm 키로 하면(또는 반대) 같은
    상품이어도 `strict` 문자열이 달라져 절대 매칭되지 않는다. 둘 다
    `registry.ACTIVE_ATTRIBUTE_EXTRACTOR` 하나를 그대로 따르므로 저절로 일치한다.
    """
    alias_map = get_brand_alias_map()
    extractor = build_attribute_extractor()
    page = 0
    updated = 0
    while True:
        fetched = be_client.fetch_products_page(category_id, page=page, size=page_size)
        if fetched is None:
            break
        for item in fetched.items:
            extracted = extractor.extract(
                product_name=item.title, brand_id=item.brand_id, brand_alias_map=alias_map
            )
            keys = build_match_keys(
                tokens=extracted.tokens,
                brand_id=extracted.brand_id,
                category=str(item.category_id),
            )
            _upsert(item, keys.strict, keys.relaxed)
            updated += 1
        if not fetched.has_next:
            break
        page += 1
    return updated


def _upsert(item: be_client.BeProduct, match_key_strict: str, match_key_relaxed: str) -> None:
    """ "조회 후 갱신/삽입" 방식 upsert — postgres 전용 `ON CONFLICT` 없이 다이얼렉트 무관하게
    동작한다(`store.py`처럼 SQLite로도 테스트 가능)."""
    with Session(get_vector_engine()) as session:
        existing = session.execute(
            select(ProductCorpusItem).where(ProductCorpusItem.product_id == item.product_id)
        ).scalar_one_or_none()
        if existing is None:
            existing = ProductCorpusItem(product_id=item.product_id)
            session.add(existing)
        existing.title = item.title
        existing.brand_id = item.brand_id
        existing.category_id = item.category_id
        existing.price = item.price
        existing.sale_type = item.sale_type
        existing.sale_status = item.sale_status
        existing.created_at_be = item.created_at
        existing.match_key_strict = match_key_strict
        existing.match_key_relaxed = match_key_relaxed
        existing.cached_at = datetime.now(UTC)
        session.commit()


def find_by_match_key(
    match_key: str, *, exclude_product_id: int | None = None, limit: int = 20
) -> list[CorpusCandidate]:
    """이 매칭 키(strict 또는 relaxed)를 가진 다른 상품들을 코퍼스에서 찾는다.

    1차/2차 중 뭘 넘길지는 호출부(`comps.py`)가 정한다 — 이 함수는 키 하나로 조회만 한다.
    `exclude_product_id`로 자기 자신(방금 가격을 책정하려는 그 상품)을 제외한다.
    """
    with Session(get_vector_engine()) as session:
        query = select(ProductCorpusItem).where(
            (ProductCorpusItem.match_key_strict == match_key)
            | (ProductCorpusItem.match_key_relaxed == match_key)
        )
        if exclude_product_id is not None:
            query = query.where(ProductCorpusItem.product_id != exclude_product_id)
        rows = session.execute(query.limit(limit)).scalars()
        return [
            CorpusCandidate(
                product_id=row.product_id,
                title=row.title,
                price=row.price,
                sale_type=row.sale_type,
                sale_status=row.sale_status,
                created_at=row.created_at_be,
            )
            for row in rows
        ]
