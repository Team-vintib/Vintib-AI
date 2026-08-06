"""유사 상품 조회(item-to-item) API 레이어 테스트.

DB(pgvector)는 붙이지 않는다 — `get_similar_product_service` 의존성을 가짜로 갈아끼워
서비스가 받은 인자와 라우터가 돌려준 응답만 검증한다(`test_personalize_service.py`의
`test_api_503_when_catalog_not_ready` 스타일).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.recommend.similar.schemas import SimilarProduct, SimilarProductsResponse
from app.recommend.similar.service import SimilarProductService, get_similar_product_service


class _FakeService(SimilarProductService):
    def __init__(self, response: SimilarProductsResponse) -> None:
        self.calls: list[tuple[int, int, str | None]] = []
        self._response = response

    def get_similar(self, product_id, k, category=None):
        self.calls.append((product_id, k, category))
        return self._response


@pytest.fixture
def client():
    return TestClient(app)


def _override(fake: _FakeService):
    app.dependency_overrides[get_similar_product_service] = lambda: fake


def test_returns_items_from_service(client):
    fake = _FakeService(
        SimilarProductsResponse(
            product_id=42,
            items=[
                SimilarProduct(product_id=7, score=0.91),
                SimilarProduct(product_id=8, score=0.5),
            ],
        )
    )
    _override(fake)
    try:
        resp = client.get("/recommend/products/42/similar")
        assert resp.status_code == 200
        body = resp.json()
        assert body["product_id"] == 42
        assert body["items"] == [
            {"product_id": 7, "score": 0.91},
            {"product_id": 8, "score": 0.5},
        ]
        assert fake.calls == [(42, 10, None)]  # k 기본값 10
    finally:
        app.dependency_overrides.clear()


def test_passes_k_and_category_query_params(client):
    fake = _FakeService(SimilarProductsResponse(product_id=42, items=[]))
    _override(fake)
    try:
        resp = client.get("/recommend/products/42/similar", params={"k": 3, "category": "TOP_KNIT"})
        assert resp.status_code == 200
        assert fake.calls == [(42, 3, "TOP_KNIT")]
    finally:
        app.dependency_overrides.clear()


def test_empty_when_no_embedding_yet(client):
    """대상 상품에 임베딩이 없으면(품질검수 미완료 등) 빈 리스트 — 에러가 아니다."""
    fake = _FakeService(SimilarProductsResponse(product_id=999999, items=[]))
    _override(fake)
    try:
        resp = client.get("/recommend/products/999999/similar")
        assert resp.status_code == 200
        assert resp.json()["items"] == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("params", [{"k": 0}, {"k": 101}])
def test_422_invalid_k(client, params):
    resp = client.get("/recommend/products/42/similar", params=params)
    assert resp.status_code == 422


def test_does_not_shadow_entity_graph_similar_route(client):
    """`/recommend/{entity}/{entity_id}/similar`(브랜드/셀러 그래프, `recommend/router.py`)와
    이 라우터의 `/recommend/products/{product_id}/similar`는 세그먼트 수가 같아(3개) 등록
    순서에 따라 서로를 가로챌 수 있다 — `app/main.py`가 이 라우터를 먼저 등록해야 한다.
    `entity=brand`(유효 값)로 확인 — 이 값이 422(enum 검증 실패)로 오면 그래프 경로가
    similar_router에 가로채인 것이다."""
    resp = client.get("/recommend/brand/1/similar")
    assert resp.status_code != 422
