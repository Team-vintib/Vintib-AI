"""`app/gateway/router._ingest_quality_embedding_result()` 검증 — 품질검수 워커가 실어
보낸 `garment_embedding`을 pgvector(`embedding_store`)에 upsert하는 진입점.

실제 DB 왕복(`embedding_store.save_garment_embedding`)과 BE 조회(`be_client.fetch_product`)는
monkeypatch로 대체한다 — `_ingest_stt_result`/`_ingest_chat_rag_result` 테스트와 같은 스타일.

**CH024부터 `category`는 워커가 보낸 `garment_category`(품질검수의 6종 `GarmentCategory`,
BE 체계와 무관)가 아니라 BE `categoryId`를 그대로 쓴다(Q4) — `garment_category` 필드는
더 이상 이 경로에서 읽지 않는다.
"""

from app.gateway import router as gateway_router
from app.recommend.personalize import embedding_store
from app.shared.be_client import BeProduct


def _be_product(category_id: int | None) -> BeProduct:
    return BeProduct(
        product_id=42,
        title="t",
        brand="테스트브랜드",
        category_id=category_id,
        condition_grade="A",
        sale_type="DIRECT_SALE",
        sale_status="ON_SALE",
        price=10_000,
        created_at="2026-08-06T00:00:00",
    )


def test_saves_embedding_with_be_category_id(monkeypatch):
    calls = []
    monkeypatch.setattr(
        embedding_store, "save_garment_embedding", lambda **kwargs: calls.append(kwargs)
    )
    monkeypatch.setattr(
        gateway_router.be_client, "fetch_product", lambda product_id: _be_product(97)
    )

    gateway_router._ingest_quality_embedding_result(
        {
            "product_id": 42,
            "garment_embedding": [0.1, 0.2],
            "garment_embedding_model_id": "patrickjohncyh/fashion-clip",
            "garment_category": "TOP_KNIT",  # 더 이상 category로 쓰이지 않는다는 걸 확인
        }
    )

    assert calls == [
        {
            "product_id": 42,
            "embedding": [0.1, 0.2],
            "model_id": "patrickjohncyh/fashion-clip",
            "category": "97",
        }
    ]


def test_saves_embedding_with_category_none_when_be_unreachable(monkeypatch):
    """BE 조회 실패(다운·상품 없음 등)여도 임베딩 저장 자체는 그대로 진행돼야 한다."""
    calls = []
    monkeypatch.setattr(
        embedding_store, "save_garment_embedding", lambda **kwargs: calls.append(kwargs)
    )
    monkeypatch.setattr(gateway_router.be_client, "fetch_product", lambda product_id: None)

    gateway_router._ingest_quality_embedding_result(
        {
            "product_id": 42,
            "garment_embedding": [0.1, 0.2],
            "garment_embedding_model_id": "patrickjohncyh/fashion-clip",
        }
    )

    assert calls == [
        {
            "product_id": 42,
            "embedding": [0.1, 0.2],
            "model_id": "patrickjohncyh/fashion-clip",
            "category": None,
        }
    ]


def test_saves_embedding_with_category_none_when_be_category_id_missing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        embedding_store, "save_garment_embedding", lambda **kwargs: calls.append(kwargs)
    )
    monkeypatch.setattr(
        gateway_router.be_client, "fetch_product", lambda product_id: _be_product(None)
    )

    gateway_router._ingest_quality_embedding_result(
        {
            "product_id": 42,
            "garment_embedding": [0.1, 0.2],
            "garment_embedding_model_id": "patrickjohncyh/fashion-clip",
        }
    )

    assert calls[0]["category"] is None


def test_skips_when_embedding_missing(monkeypatch):
    """mock 세그멘터·의류 미검출·임베딩 계산 실패 — 전부 이 케이스로 수렴한다."""
    calls = []
    monkeypatch.setattr(
        embedding_store, "save_garment_embedding", lambda **kwargs: calls.append(kwargs)
    )

    gateway_router._ingest_quality_embedding_result({"product_id": 42})

    assert calls == []


def test_save_failure_does_not_raise(monkeypatch):
    """저장 실패가 job 제출 자체를 실패로 만들면 안 된다 — 검수는 이미 끝난 일이다."""

    def _explode(**kwargs):
        raise RuntimeError("DB 연결 실패")

    monkeypatch.setattr(embedding_store, "save_garment_embedding", _explode)
    monkeypatch.setattr(gateway_router.be_client, "fetch_product", lambda product_id: None)

    gateway_router._ingest_quality_embedding_result(
        {"product_id": 42, "garment_embedding": [0.1, 0.2], "garment_embedding_model_id": "m"}
    )  # 예외가 밖으로 나오면 여기서 터진다
