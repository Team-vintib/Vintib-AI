"""BE 공개 REST API 클라이언트 — 네트워크 미접촉, `httpx.get`을 monkeypatch로 대체한다.

`test_pricing_retail.py`의 `NaverRetailSource` 테스트와 같은 패턴 — 이 모듈도
`fetch_product()`가 절대 예외를 던지지 않는 계약이다.
"""

from app.shared.be_client import fetch_product


class _FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict:
        return self._body


def test_parses_successful_response(monkeypatch):
    import httpx

    body = {
        "data": {
            "id": 42,
            "title": "리메이크 Levi's 데님",
            "brand": "Levi's",
            "categoryId": 97,
            "conditionGrade": "A",
            "saleType": "DIRECT_SALE",
            "saleStatus": "ON_SALE",
            "price": 85000,
            "createdAt": "2026-07-29T12:00:00",
        }
    }
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(200, body))

    product = fetch_product(42)

    assert product is not None
    assert product.product_id == 42
    assert product.brand == "Levi's"
    assert product.category_id == 97
    assert product.sale_type == "DIRECT_SALE"
    assert product.sale_status == "ON_SALE"
    assert product.price == 85000


def test_returns_none_on_non_200(monkeypatch):
    import httpx

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(404))

    assert fetch_product(999) is None


def test_returns_none_on_network_exception(monkeypatch):
    import httpx

    def _explode(*args, **kwargs):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(httpx, "get", _explode)

    assert fetch_product(1) is None


def test_returns_none_on_malformed_body(monkeypatch):
    import httpx

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(200, {"unexpected": True}))

    assert fetch_product(1) is None


def test_missing_optional_fields_become_none(monkeypatch):
    import httpx

    body = {"data": {"id": 1, "title": "제목", "brand": None}}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(200, body))

    product = fetch_product(1)

    assert product is not None
    assert product.brand is None
    assert product.category_id is None
    assert product.sale_type is None


def test_warns_when_brand_field_missing_from_response(monkeypatch, caplog):
    """`brand` 키 자체가 없으면(값이 null인 것과 다르다) BE 계약 변경을 의심할 수 있게 경고한다."""
    import logging

    import httpx

    body = {"data": {"id": 1, "title": "제목"}}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(200, body))

    with caplog.at_level(logging.WARNING):
        product = fetch_product(1)

    assert product is not None
    assert product.brand is None
    assert any("brand" in record.message for record in caplog.records)


def test_no_warning_when_brand_field_present_but_null(monkeypatch, caplog):
    """브랜드를 안 적은 정상 케이스(키는 있고 값만 null)는 경고하지 않는다."""
    import logging

    import httpx

    body = {"data": {"id": 1, "title": "제목", "brand": None}}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(200, body))

    with caplog.at_level(logging.WARNING):
        fetch_product(1)

    assert not caplog.records
