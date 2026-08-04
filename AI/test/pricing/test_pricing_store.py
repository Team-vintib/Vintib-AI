"""관측 로그 DAO — 인메모리 SQLite로 검증한다(CH017). 라이브 postgres 불필요.

`app.pricing.store`는 `app.core.db.get_vector_engine()`(AI 전용 postgres-vector)을 쓰지만,
저장 모델에 pgvector 전용 타입(Vector 컬럼)이 없어 SQLite로도 스키마·쿼리를 그대로 검증할 수
있다. `StaticPool`로 커넥션을 하나만 유지해야 세션 간에 같은 인메모리 DB를 본다.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.pricing import store
from app.pricing.schemas import CompItem


@pytest.fixture
def sqlite_store(monkeypatch):
    """`store.get_vector_engine`을 인메모리 SQLite로 갈아끼운다."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    store.Base.metadata.create_all(engine)
    monkeypatch.setattr(store, "get_vector_engine", lambda: engine)
    return store


def _comp(title: str, price: int, *, is_used: bool | None = True) -> CompItem:
    return CompItem(title=title, price=price, source="llm_web_search", is_used=is_used)


def test_save_then_fetch_round_trips(sqlite_store):
    saved = sqlite_store.save_observations(
        "리바이스 501", "llm_web_search", [_comp("리바이스 501", 45_000)]
    )

    observations = sqlite_store.fetch_recent("리바이스 501")

    assert saved == 1
    assert len(observations) == 1
    assert observations[0].item.price == 45_000
    assert observations[0].item.title == "리바이스 501"


def test_save_empty_items_is_a_noop(sqlite_store):
    assert sqlite_store.save_observations("무엇이든", "llm_web_search", []) == 0
    assert sqlite_store.fetch_recent("무엇이든") == []


def test_fetch_only_matches_exact_query(sqlite_store):
    """지금은 완전 일치만 본다 — 유사 쿼리 매칭은 CH016의 몫이다."""
    sqlite_store.save_observations("리바이스 501", "llm_web_search", [_comp("a", 10_000)])

    assert sqlite_store.fetch_recent("리바이스 501 빅E") == []


def test_fetch_orders_newest_first(sqlite_store):
    sqlite_store.save_observations("q", "llm_web_search", [_comp("먼저", 1_000)])
    sqlite_store.save_observations("q", "llm_web_search", [_comp("나중", 2_000)])

    titles = [obs.item.title for obs in sqlite_store.fetch_recent("q")]

    assert titles == ["나중", "먼저"]


def test_fetch_respects_limit(sqlite_store):
    for price in range(5):
        sqlite_store.save_observations("q", "llm_web_search", [_comp("t", price)])

    assert len(sqlite_store.fetch_recent("q", limit=2)) == 2


def test_is_used_none_round_trips_as_none(sqlite_store):
    """판별 불가(None)를 False로 뭉개면 신품과 구별이 사라진다 — DB를 거쳐도 유지돼야 한다."""
    sqlite_store.save_observations("q", "llm_web_search", [_comp("판별불가", 10_000, is_used=None)])

    assert sqlite_store.fetch_recent("q")[0].item.is_used is None
