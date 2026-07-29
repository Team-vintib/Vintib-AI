"""신상품(정가) 수집 — mock 결정성·파싱·실패 계약 검증.

**`RetailSource.fetch()`는 절대 예외를 던지지 않는다.** `test_pricing_comps.py`의
`CompsUnavailable` 패턴과 다르다 — 여기서는 실패해도 빈 `RetailFetch`가 나오는지를 본다.
네트워크에도 절대 닿지 않는다(`AI/CLAUDE.md` 하드 룰: 네이버 호출은 사람이 직접 실행한다).
"""

import pytest

from app.pricing.retail import (
    MockRetailSource,
    NaverRetailSource,
    _parse_items,
    build_retail_source,
)

# --- mock 백엔드 ------------------------------------------------------------


def test_mock_is_deterministic_across_calls():
    first = MockRetailSource().fetch("리바이스 501")
    second = MockRetailSource().fetch("리바이스 501")

    assert [c.price for c in first.items] == [c.price for c in second.items]


def test_mock_differs_by_query():
    a = MockRetailSource().fetch("리바이스 501")
    b = MockRetailSource().fetch("나이키 후드")

    assert [c.price for c in a.items] != [c.price for c in b.items]


def test_mock_marks_itself_as_not_real():
    assert MockRetailSource().fetch("무엇이든").notes


def test_mock_items_are_marked_as_new():
    """신상품가는 '판별 불가'가 아니라 확실히 신품이다."""
    items = MockRetailSource().fetch("무엇이든").items
    assert items
    assert all(item.is_used is False for item in items)


def test_build_retail_source_rejects_unknown_key():
    with pytest.raises(ValueError, match="등록되지 않은"):
        build_retail_source("없는백엔드")


# --- 네이버 응답 → CompItem ---------------------------------------------------


def test_used_product_types_are_dropped():
    """4·5·6은 중고다 — 신상품가 소스에 섞이면 목적과 어긋난다."""
    rows = [
        {"title": "새 상품", "lprice": "10000", "productType": "1"},
        {"title": "중고 상품", "lprice": "5000", "productType": "5"},
    ]
    items = _parse_items(rows)

    assert len(items) == 1
    assert items[0].title == "새 상품"


def test_rows_without_usable_price_are_dropped():
    rows = [
        {"title": "가격없음"},
        {"title": "0원", "lprice": "0"},
        {"title": "음수", "lprice": "-100"},
        {"title": "정상", "lprice": "30000"},
    ]
    items = _parse_items(rows)

    assert len(items) == 1
    assert items[0].price == 30_000


def test_html_tags_and_entities_are_cleaned():
    rows = [{"title": "<b>리바이스</b> 501 &amp; 빅E", "lprice": "10000"}]
    items = _parse_items(rows)

    assert items[0].title == "리바이스 501 & 빅E"


def test_parsed_items_are_always_marked_as_new():
    rows = [{"title": "상품", "lprice": "10000", "productType": ""}]
    items = _parse_items(rows)

    assert items[0].is_used is False


# --- 네이버 백엔드 (네트워크 미접촉) -------------------------------------------


def test_naver_source_fails_before_touching_network_without_key(monkeypatch):
    """키가 없으면 fetch 시점에 즉시 빈 결과로 끊긴다. 예외를 던지지 않는다."""
    from app.core import config

    monkeypatch.setattr(config.settings, "naver_client_id", "")
    monkeypatch.setattr(config.settings, "naver_client_secret", "")

    def _explode(*args, **kwargs):  # pragma: no cover — 불려선 안 된다
        raise AssertionError("키가 없는데 네이버를 호출했다")

    import httpx

    monkeypatch.setattr(httpx, "get", _explode)

    result = NaverRetailSource().fetch("리바이스 501")

    assert result.items == []
    assert result.notes


def test_naver_source_swallows_network_exceptions(monkeypatch):
    """HTTP 예외가 나도 job을 죽이면 안 된다 — 빈 결과로 떨어진다."""
    from app.core import config

    monkeypatch.setattr(config.settings, "naver_client_id", "id")
    monkeypatch.setattr(config.settings, "naver_client_secret", "secret")

    import httpx

    def _explode(*args, **kwargs):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(httpx, "get", _explode)

    result = NaverRetailSource().fetch("리바이스 501")

    assert result.items == []
    assert result.notes


def test_naver_source_returns_empty_on_non_200(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "naver_client_id", "id")
    monkeypatch.setattr(config.settings, "naver_client_secret", "secret")

    class _FakeResponse:
        status_code = 500
        text = "internal error"

    import httpx

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: _FakeResponse())

    result = NaverRetailSource().fetch("리바이스 501")

    assert result.items == []
    assert result.notes
