"""의류 실측 라우터 — 큐 어댑터 동작 검증.

이 엔드포인트가 존재하는 이유는 **요청 검증**이다. 게이트웨이의 범용 `POST /ai/{feature}`는
payload가 `dict`라 카테고리 오타나 이미지 누락을 못 걸러내고, 잘못된 job이 큐에 들어가면
워커가 노트북을 잡고 나서야 실패한다. 그래서 여기서 막히는지를 고정한다.

Redis는 붙지 않는다 — `app.gateway.router.r`(모듈 전역 클라이언트)을 가짜로 갈아끼워
**큐에 실제로 무엇이 실리는지**를 본다. 진짜 Redis를 띄우면 CI에서 돌릴 수 없다.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.gateway import router as gateway_router
from app.main import app


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
        "image_url": "https://example.test/scan.jpg",
        "category": "TOP",
    }
    body.update(overrides)
    return body


def test_returns_job_id_instead_of_result(client, fake_redis):
    """접수증만 돌려준다 — 실측 결과가 여기 들어오면 비동기 큐가 무의미하다."""
    response = client.post("/measurement/scans", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == 1042
    assert body["job_id"]
    assert "measurements" not in body
    assert "landmarks" not in body


def test_job_lands_on_the_garment_measurement_queue(client, fake_redis):
    """시착·품질검수와 같은 큐 규약을 쓴다 — `queue:{feature}` 키에 Job JSON이 실린다."""
    client.post("/measurement/scans", json=_payload())

    assert len(fake_redis.pushed) == 1
    key, raw = fake_redis.pushed[0]
    assert key == "queue:garment_measurement"

    job = json.loads(raw)
    assert job["type"] == "garment_measurement"
    assert job["retry_count"] == 0
    assert job["payload"]["product_id"] == 1042


def test_payload_carries_everything_the_worker_needs(client, fake_redis):
    """워커는 payload만 보고 처리한다 — 여기서 빠지면 워커가 job을 처리할 수 없다."""
    client.post("/measurement/scans", json=_payload(category="BOTTOM"))

    payload = json.loads(fake_redis.pushed[0][1])["payload"]
    assert set(payload) == {"product_id", "image_url", "category", "reference_object"}
    # enum이 객체가 아니라 문자열로 직렬화돼야 워커가 그대로 파싱한다.
    assert payload["category"] == "BOTTOM"
    assert payload["reference_object"] == "A4_PAPER"


def test_defaults_are_filled_before_enqueue(client, fake_redis):
    """생략된 값은 게이트웨이가 채운다 — 워커가 기본값을 따로 알 필요가 없다."""
    client.post("/measurement/scans", json=_payload())

    payload = json.loads(fake_redis.pushed[0][1])["payload"]
    assert payload["reference_object"] == "A4_PAPER"


def test_job_status_is_seeded_as_queued(client, fake_redis):
    """접수 직후 폴링해도 404가 아니라 queued가 나와야 한다."""
    body = client.post("/measurement/scans", json=_payload()).json()

    stored = json.loads(fake_redis.stored[f"result:{body['job_id']}"])
    assert stored["status"] == "queued"


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"product_id": 0}, id="product_id는 1 이상"),
        pytest.param({"category": "DRESS"}, id="미등록 카테고리(v1 범위 밖)"),
        pytest.param({"reference_object": "CREDIT_CARD"}, id="미지원 기준 물체"),
    ],
)
def test_invalid_request_never_reaches_the_queue(client, fake_redis, overrides):
    """검증 실패는 422이고, **큐에 아무것도 실리지 않아야** 한다."""
    response = client.post("/measurement/scans", json=_payload(**overrides))

    assert response.status_code == 422
    assert fake_redis.pushed == []
