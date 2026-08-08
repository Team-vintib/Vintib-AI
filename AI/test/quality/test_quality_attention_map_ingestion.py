"""`app/gateway/router._ingest_quality_attention_maps()` 검증 — 품질검수 워커가 실어 보낸
`attention_maps[]`를 로그 테이블(`attention_map_store`)에 append하는 진입점.

실제 DB 왕복(`attention_map_store.save_attention_maps`)은 monkeypatch로 대체한다 —
`test_embedding_gateway_ingestion.py`와 같은 스타일.
"""

from app.gateway import router as gateway_router
from app.quality import attention_map_store


def test_saves_attention_maps_when_present(monkeypatch):
    calls = []
    monkeypatch.setattr(
        attention_map_store, "save_attention_maps", lambda **kwargs: calls.append(kwargs)
    )

    gateway_router._ingest_quality_attention_maps(
        {
            "product_id": 42,
            "inspection_id": "insp_42_abc",
            "attention_maps": [
                {"image_index": 0, "defect_type": "STAIN", "url": "https://.../a.png"},
                {"image_index": 1, "defect_type": "HOLE_TEAR", "url": "https://.../b.png"},
            ],
        }
    )

    assert calls == [
        {
            "product_id": 42,
            "inspection_id": "insp_42_abc",
            "attention_maps": [
                {"image_index": 0, "defect_type": "STAIN", "url": "https://.../a.png"},
                {"image_index": 1, "defect_type": "HOLE_TEAR", "url": "https://.../b.png"},
            ],
        }
    ]


def test_skips_when_attention_maps_missing_or_empty(monkeypatch):
    """`include_attention_maps=false`(기본값)면 빈 리스트라 저장을 아예 시도하지 않는다."""
    calls = []
    monkeypatch.setattr(
        attention_map_store, "save_attention_maps", lambda **kwargs: calls.append(kwargs)
    )

    gateway_router._ingest_quality_attention_maps({"product_id": 42})
    gateway_router._ingest_quality_attention_maps({"product_id": 42, "attention_maps": []})

    assert calls == []


def test_save_failure_does_not_raise(monkeypatch):
    """저장 실패가 job 제출 자체를 실패로 만들면 안 된다 — 검수는 이미 끝난 일이다."""

    def _explode(**kwargs):
        raise RuntimeError("DB 연결 실패")

    monkeypatch.setattr(attention_map_store, "save_attention_maps", _explode)

    gateway_router._ingest_quality_attention_maps(
        {
            "product_id": 42,
            "inspection_id": "insp_42_abc",
            "attention_maps": [
                {"image_index": 0, "defect_type": "STAIN", "url": "https://.../a.png"}
            ],
        }
    )  # 예외가 밖으로 나오면 여기서 터진다
