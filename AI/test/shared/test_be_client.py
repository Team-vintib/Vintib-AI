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
            "brandId": 3,
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
    assert product.brand_id == 3
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

    body = {"data": {"id": 1, "title": "제목"}}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(200, body))

    product = fetch_product(1)

    assert product is not None
    assert product.brand_id is None
    assert product.category_id is None
    assert product.sale_type is None
