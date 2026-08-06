"""등록 시 AI 착용컷 트리거(`POST /ai/tryon/registration-model-cut`) — 큐 어댑터 동작 검증.

`test/product_classifier/test_product_classifier_router.py`와 같은 기법이다 — 진짜
Redis 대신 `app.gateway.router.r`을 가짜로 갈아끼워, 큐에 실제로 어떤 job payload가
실리는지(특히 페르소나 URL이 gender에 맞게 골라졌는지)를 확인한다.
"""

import json

import pytest
from app.gateway import router as gateway_router
from app.main import app
from fastapi.testclient import TestClient


class _FakeRedis:
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
        "product_image_url": "https://example.test/product.jpg",
        "gender": "MALE",
    }
    body.update(overrides)
    return body


def test_returns_job_id_instead_of_result(client, fake_redis):
    """접수증만 돌려준다 — 다른 job 생성 엔드포인트와 같은 원칙."""
    response = client.post("/ai/tryon/registration-model-cut", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"]


def test_enqueues_onto_shared_tryon_queue(client, fake_redis):
    """새 feature 큐를 만들지 않는다 — 기존 시착 워커가 그대로 소비해야 하므로
    `queue:tryon`에 실려야 한다."""
    client.post("/ai/tryon/registration-model-cut", json=_payload())

    assert len(fake_redis.pushed) == 1
    key, raw_job = fake_redis.pushed[0]
    assert key == "queue:tryon"
    job = json.loads(raw_job)
    assert job["type"] == "tryon"


def test_male_resolves_to_heedongi_persona(client, fake_redis):
    client.post("/ai/tryon/registration-model-cut", json=_payload(gender="MALE"))

    _, raw_job = fake_redis.pushed[0]
    job = json.loads(raw_job)
    assert job["payload"]["user_image_url"].endswith("/personas/heedongi.png")


def test_female_resolves_to_dooner_persona(client, fake_redis):
    client.post("/ai/tryon/registration-model-cut", json=_payload(gender="FEMALE"))

    _, raw_job = fake_redis.pushed[0]
    job = json.loads(raw_job)
    assert job["payload"]["user_image_url"].endswith("/personas/dooner.png")


def test_product_image_url_and_mask_type_pass_through(client, fake_redis):
    client.post(
        "/ai/tryon/registration-model-cut",
        json=_payload(product_image_url="https://example.test/lower.jpg", mask_type="lower"),
    )

    _, raw_job = fake_redis.pushed[0]
    job = json.loads(raw_job)
    assert job["payload"]["product_image_url"] == "https://example.test/lower.jpg"
    assert job["payload"]["mask_type"] == "lower"


def test_mask_type_defaults_to_upper(client, fake_redis):
    client.post("/ai/tryon/registration-model-cut", json=_payload())

    _, raw_job = fake_redis.pushed[0]
    job = json.loads(raw_job)
    assert job["payload"]["mask_type"] == "upper"


def test_fit_type_is_fixed_to_regular(client, fake_redis):
    client.post("/ai/tryon/registration-model-cut", json=_payload())

    _, raw_job = fake_redis.pushed[0]
    job = json.loads(raw_job)
    assert job["payload"]["fit_type"] == "regular"


def test_rejects_invalid_gender(client, fake_redis):
    response = client.post(
        "/ai/tryon/registration-model-cut", json=_payload(gender="UNISEX")
    )

    assert response.status_code == 422
    assert not fake_redis.pushed


def test_rejects_missing_product_image_url(client, fake_redis):
    response = client.post(
        "/ai/tryon/registration-model-cut", json={"gender": "MALE"}
    )

    assert response.status_code == 422
    assert not fake_redis.pushed


def test_still_accepts_when_worker_offline(client, fake_redis):
    """워커가 꺼져 있어도 200으로 접수된다 — 다른 job 생성 엔드포인트와 동일 원칙."""
    response = client.post("/ai/tryon/registration-model-cut", json=_payload())

    assert response.status_code == 200
