"""`app/gateway/router._ingest_quality_embedding_result()` 검증 — 품질검수 워커가 실어
보낸 `garment_embedding`을 pgvector(`embedding_store`)에 upsert하는 진입점.

실제 DB 왕복(`embedding_store.save_garment_embedding`)은 monkeypatch로 대체한다 —
`_ingest_stt_result`/`_ingest_chat_rag_result` 테스트와 같은 스타일.
"""

from app.gateway import router as gateway_router
from app.recommend.personalize import embedding_store


def test_saves_embedding_when_present(monkeypatch):
    calls = []
    monkeypatch.setattr(
        embedding_store, "save_garment_embedding", lambda **kwargs: calls.append(kwargs)
    )

    gateway_router._ingest_quality_embedding_result(
        {
            "product_id": 42,
            "garment_embedding": [0.1, 0.2],
            "garment_embedding_model_id": "patrickjohncyh/fashion-clip",
        }
    )

    assert calls == [
        {"product_id": 42, "embedding": [0.1, 0.2], "model_id": "patrickjohncyh/fashion-clip"}
    ]


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

    gateway_router._ingest_quality_embedding_result(
        {"product_id": 42, "garment_embedding": [0.1, 0.2], "garment_embedding_model_id": "m"}
    )  # 예외가 밖으로 나오면 여기서 터진다
