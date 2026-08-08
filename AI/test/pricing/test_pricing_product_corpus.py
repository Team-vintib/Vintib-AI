"""동일 상품 텍스트 매칭 후보 코퍼스(CH030) — 인메모리 SQLite로 검증한다. 라이브 postgres/
네트워크 불필요 — `be_client` 호출은 monkeypatch로 갈아끼운다.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.pricing import product_corpus
from app.shared import be_client


@pytest.fixture
def sqlite_corpus(monkeypatch):
    """`product_corpus.get_vector_engine`을 인메모리 SQLite로 갈아끼운다."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    product_corpus.Base.metadata.create_all(engine)
    monkeypatch.setattr(product_corpus, "get_vector_engine", lambda: engine)
    product_corpus.get_brand_alias_map.cache_clear()
    yield product_corpus
    product_corpus.get_brand_alias_map.cache_clear()


def _product(**overrides) -> be_client.BeProduct:
    base = {
        "product_id": 1,
        "title": "리바이스 501 빈티지",
        "brand": None,
        "category_id": 40,
        "condition_grade": "A",
        "sale_type": "DIRECT_SALE",
        "sale_status": "ON_SALE",
        "price": 45_000,
        "created_at": "2026-08-01T00:00:00",
    }
    base.update(overrides)
    return be_client.BeProduct(**base)


def _page(items: list[be_client.BeProduct], *, has_next: bool = False) -> be_client.BeProductPage:
    return be_client.BeProductPage(items=items, has_next=has_next)


# --- get_brand_alias_map ------------------------------------------------------


def test_brand_alias_map_indexes_by_name_and_name_en(sqlite_corpus, monkeypatch):
    monkeypatch.setattr(
        be_client,
        "fetch_brands",
        lambda **_: [be_client.BeBrand(brand_id=1, name="리바이스", name_en="Levi's")],
    )

    alias_map = sqlite_corpus.get_brand_alias_map()

    assert alias_map["리바이스"] == 1
    assert alias_map["levi's"] == 1


def test_brand_alias_map_empty_when_be_unavailable(sqlite_corpus, monkeypatch):
    monkeypatch.setattr(be_client, "fetch_brands", lambda **_: None)

    assert sqlite_corpus.get_brand_alias_map() == {}


# --- refresh_category ----------------------------------------------------------


def test_refresh_category_upserts_products_and_computes_match_keys(sqlite_corpus, monkeypatch):
    monkeypatch.setattr(be_client, "fetch_brands", lambda **_: [])
    monkeypatch.setattr(
        be_client, "fetch_products_page", lambda category_id, **_: _page([_product(product_id=1)])
    )

    updated = sqlite_corpus.refresh_category(40)

    assert updated == 1
    candidates = sqlite_corpus.find_by_match_key("unknown:40", limit=10)
    assert len(candidates) == 1
    assert candidates[0].product_id == 1


def test_refresh_category_paginates_until_no_next(sqlite_corpus, monkeypatch):
    monkeypatch.setattr(be_client, "fetch_brands", lambda **_: [])
    pages = {
        0: _page([_product(product_id=1)], has_next=True),
        1: _page([_product(product_id=2)], has_next=False),
    }
    monkeypatch.setattr(
        be_client, "fetch_products_page", lambda category_id, *, page, size: pages[page]
    )

    updated = sqlite_corpus.refresh_category(40)

    assert updated == 2


def test_refresh_category_returns_zero_when_be_unavailable(sqlite_corpus, monkeypatch):
    monkeypatch.setattr(be_client, "fetch_brands", lambda **_: [])
    monkeypatch.setattr(be_client, "fetch_products_page", lambda category_id, **_: None)

    assert sqlite_corpus.refresh_category(40) == 0


def test_refresh_category_upsert_overwrites_existing_row(sqlite_corpus, monkeypatch):
    monkeypatch.setattr(be_client, "fetch_brands", lambda **_: [])
    monkeypatch.setattr(
        be_client,
        "fetch_products_page",
        lambda category_id, **_: _page([_product(product_id=1, price=45_000)]),
    )
    sqlite_corpus.refresh_category(40)

    monkeypatch.setattr(
        be_client,
        "fetch_products_page",
        lambda category_id, **_: _page([_product(product_id=1, price=39_000, sale_status="SOLD")]),
    )
    sqlite_corpus.refresh_category(40)

    candidates = sqlite_corpus.find_by_match_key("unknown:40", limit=10)
    assert len(candidates) == 1
    assert candidates[0].price == 39_000
    assert candidates[0].sale_status == "SOLD"


# --- find_by_match_key ----------------------------------------------------------


def test_find_by_match_key_matches_either_strict_or_relaxed(sqlite_corpus, monkeypatch):
    monkeypatch.setattr(be_client, "fetch_brands", lambda **_: [])
    monkeypatch.setattr(
        be_client,
        "fetch_products_page",
        lambda category_id, **_: _page([_product(product_id=1, title="리바이스 501 빈티지")]),
    )
    sqlite_corpus.refresh_category(40)

    by_relaxed = sqlite_corpus.find_by_match_key("unknown:40")
    by_strict = sqlite_corpus.find_by_match_key("unknown:501-리바이스:40")

    assert len(by_relaxed) == 1
    assert len(by_strict) == 1


def test_find_by_match_key_excludes_given_product_id(sqlite_corpus, monkeypatch):
    monkeypatch.setattr(be_client, "fetch_brands", lambda **_: [])
    monkeypatch.setattr(
        be_client, "fetch_products_page", lambda category_id, **_: _page([_product(product_id=1)])
    )
    sqlite_corpus.refresh_category(40)

    candidates = sqlite_corpus.find_by_match_key("unknown:40", exclude_product_id=1)

    assert candidates == []


def test_find_by_match_key_respects_limit(sqlite_corpus, monkeypatch):
    monkeypatch.setattr(be_client, "fetch_brands", lambda **_: [])
    monkeypatch.setattr(
        be_client,
        "fetch_products_page",
        lambda category_id, **_: _page(
            [_product(product_id=i, title=f"상품 {i} 빈티지") for i in range(5)]
        ),
    )
    sqlite_corpus.refresh_category(40)

    candidates = sqlite_corpus.find_by_match_key("unknown:40", limit=2)

    assert len(candidates) == 2
