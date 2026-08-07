"""상품 정보 분류 라우터 — 큐 어댑터 동작 검증.

`test/measurement/test_measurement_router.py`와 같은 목적·같은 기법이다 — 요청 검증이
이 엔드포인트의 존재 이유이므로 잘못된 요청이 큐 앞에서 막히는지를 고정하고, 진짜 Redis
대신 `app.gateway.router.r`을 가짜로 갈아끼워 큐에 실제로 무엇이 실리는지 본다.
"""

import json

import pytest
from app.gateway import router as gateway_router
from app.main import app
from fastapi.testclient import TestClient


class _FakeRedis:
    """rpush/set만 흉내내는 최소 스텁. 큐에 실린 값을 그대로 보관한다."""

    def __init__(self) -> None:
        self.pushed: list[tuple[str, str]] = []
        self.stored: dict[str, str] = {}

    def rpush(self, key: str, value: str) -> int:
        self.pushed.append((key, value))
        return len(self.pushed)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.stored[key] = value
        return True


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(gateway_router, "r", fake)
    return fake


@pytest.fixture
def client():
    return TestClient(app)


def _payload(**overrides) -> dict:
    body = {
        "product_id": 1042,
        "image_url": "https://example.test/front.jpg",
    }
    body.update(overrides)
    return body


def test_returns_job_id_instead_of_result(client, fake_redis):
    """접수증만 돌려준다 — 분류 결과가 여기 들어오면 비동기 큐가 무의미하다."""
    response = client.post("/product-classifier/classify", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == 1042
    assert body["job_id"]
    assert "fields" not in body


def test_job_lands_on_the_product_classifier_queue(client, fake_redis):
    """품질검수·실측과 같은 큐 규약을 쓴다 — `queue:{feature}` 키에 Job JSON이 실린다."""
    client.post("/product-classifier/classify", json=_payload())

    assert len(fake_redis.pushed) == 1
    key, raw = fake_redis.pushed[0]
    assert key == "queue:product_classifier"

    job = json.loads(raw)
    assert job["type"] == "product_classifier"
    assert job["retry_count"] == 0
    assert job["payload"]["product_id"] == 1042


def test_payload_carries_everything_the_worker_needs(client, fake_redis):
    """워커는 payload만 보고 처리한다 — 여기서 빠지면 워커가 job을 처리할 수 없다."""
    client.post("/product-classifier/classify", json=_payload())

    payload = json.loads(fake_redis.pushed[0][1])["payload"]
    assert set(payload) == {"product_id", "image_url", "taxonomy_version"}


def test_taxonomy_version_defaults_before_enqueue(client, fake_redis):
    """생략된 값은 게이트웨이가 채운다 — 워커가 기본값을 따로 알 필요가 없다."""
    client.post("/product-classifier/classify", json=_payload())

    payload = json.loads(fake_redis.pushed[0][1])["payload"]
    assert payload["taxonomy_version"] == "v2-be-seed-2026-08-03"


def test_product_id_is_optional_for_pre_upload_trigger(client, fake_redis):
    """상품 생성 전 사전업로드 단계(방향 B)는 아직 진짜 상품 id가 없다 — 생략해도 접수돼야 한다."""
    payload = {"image_url": "https://example.test/front.jpg"}

    response = client.post("/product-classifier/classify", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] is None
    assert body["job_id"]


def test_job_status_is_seeded_as_queued(client, fake_redis):
    """접수 직후 폴링해도 404가 아니라 queued가 나와야 한다."""
    body = client.post("/product-classifier/classify", json=_payload()).json()

    stored = json.loads(fake_redis.stored[f"result:{body['job_id']}"])
    assert stored["status"] == "queued"


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"product_id": 0}, id="product_id는 1 이상"),
        pytest.param({"image_url": None}, id="image_url 누락"),
    ],
)
def test_invalid_request_never_reaches_the_queue(client, fake_redis, overrides):
    """검증 실패는 422이고, **큐에 아무것도 실리지 않아야** 한다."""
    response = client.post("/product-classifier/classify", json=_payload(**overrides))

    assert response.status_code == 422
    assert fake_redis.pushed == []
