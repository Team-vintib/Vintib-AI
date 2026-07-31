"""품질 검수 라우터 — 큐 어댑터 동작 검증.

이 엔드포인트가 존재하는 이유는 **요청 검증**이다. 게이트웨이의 범용 `POST /ai/{feature}`는
payload가 `dict`라 카테고리 오타나 이미지 누락을 못 걸러내고, 잘못된 job이 큐에 들어가면
워커가 GPU를 잡고 나서야 실패한다. 그래서 여기서 막히는지를 고정한다.

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
        "image_urls": ["https://example.test/front.jpg"],
        "category": "TOP_KNIT",
    }
    body.update(overrides)
    return body


def test_returns_job_id_instead_of_result(client, fake_redis):
    """접수증만 돌려준다 — 판정 결과가 여기 들어오면 비동기 전환이 무의미하다."""
    response = client.post("/quality/inspections", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == 1042
    assert body["job_id"]
    assert "condition_score" not in body
    assert "findings" not in body


def test_job_lands_on_the_quality_check_queue(client, fake_redis):
    """시착과 같은 큐 규약을 쓴다 — `queue:{feature}` 키에 Job JSON이 실린다."""
    client.post("/quality/inspections", json=_payload())

    assert len(fake_redis.pushed) == 1
    key, raw = fake_redis.pushed[0]
    assert key == "queue:quality_check"

    job = json.loads(raw)
    assert job["type"] == "quality_check"
    assert job["retry_count"] == 0
    assert job["payload"]["product_id"] == 1042


def test_payload_carries_everything_the_worker_needs(client, fake_redis):
    """워커는 payload만 보고 추론한다 — 여기서 빠지면 워커가 job을 처리할 수 없다."""
    client.post(
        "/quality/inspections",
        json=_payload(base_color="PATTERNED", include_attention_maps=True),
    )

    payload = json.loads(fake_redis.pushed[0][1])["payload"]
    assert set(payload) == {
        "product_id",
        "image_urls",
        "category",
        "base_color",
        "include_attention_maps",
        "include_descriptions",
    }
    # enum이 객체가 아니라 문자열로 직렬화돼야 워커가 그대로 파싱한다.
    assert payload["category"] == "TOP_KNIT"
    assert payload["base_color"] == "PATTERNED"
    assert payload["include_attention_maps"] is True


def test_defaults_are_filled_before_enqueue(client, fake_redis):
    """생략된 값은 게이트웨이가 채운다 — 워커가 기본값을 따로 알 필요가 없다."""
    client.post("/quality/inspections", json=_payload())

    payload = json.loads(fake_redis.pushed[0][1])["payload"]
    assert payload["base_color"] == "LIGHT"
    assert payload["include_attention_maps"] is False
    assert payload["include_descriptions"] is False


def test_job_status_is_seeded_as_queued(client, fake_redis):
    """접수 직후 폴링해도 404가 아니라 queued가 나와야 한다."""
    body = client.post("/quality/inspections", json=_payload()).json()

    stored = json.loads(fake_redis.stored[f"result:{body['job_id']}"])
    assert stored["status"] == "queued"


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"product_id": 0}, id="product_id는 1 이상"),
        pytest.param({"image_urls": []}, id="이미지 최소 1장"),
        pytest.param({"category": "SOCKS"}, id="미등록 카테고리"),
        pytest.param({"base_color": "NEON"}, id="미등록 기본색"),
    ],
)
def test_invalid_request_never_reaches_the_queue(client, fake_redis, overrides):
    """검증 실패는 422이고, **큐에 아무것도 실리지 않아야** 한다.

    이게 이 엔드포인트를 범용 `POST /ai/quality_check` 대신 두는 이유다 — 잘못된 job이
    큐에 들어가면 워커가 모델을 로드하고 나서야 실패한다.
    """
    response = client.post("/quality/inspections", json=_payload(**overrides))

    assert response.status_code == 422
    assert fake_redis.pushed == []
