"""가격 책정 라우터 — 접수 계약 검증.

**가장 중요한 것은 큐에 아무것도 실리지 않는다는 점이다.** 가격 책정은 워커가 없고 컨테이너가
직접 처리한다. 큐에 넣으면 아무도 꺼내가지 않는 job이 쌓이고 `/ai/workers/status`의 대기
건수만 부풀린다. `test_job_is_not_queued`가 그 설계의 회귀 방지선이다.

⚠️ `TestClient`는 백그라운드 작업을 **응답 반환 전에 동기 실행**한다. 그래서 아래 테스트에서
POST 직후 폴링하면 이미 `success`가 보이는데, 이건 진짜 비동기를 검증한 게 아니다. 실제
클라이언트는 `queued`/`processing`을 먼저 본다.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pricing.service import get_pricing_service


@pytest.fixture
def client(fake_redis):
    get_pricing_service.cache_clear()  # 세마포어 상태가 테스트 간에 새지 않게
    return TestClient(app)


def _payload(**overrides) -> dict:
    body = {
        "product_id": 1042,
        "product_name": "리바이스 501 빅E 데님",
        "condition_score": 82.0,
        "condition_grade": "A",
    }
    body.update(overrides)
    return body


def test_returns_receipt_not_result(client):
    """접수증만 돌려준다 — 가격이 여기 들어오면 비동기 전환이 무의미하다."""
    response = client.post("/pricing/estimates", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == 1042
    assert body["job_id"]
    assert "price_range" not in body
    assert "confidence" not in body


def test_job_is_not_queued(client, fake_redis):
    """★ 큐에 적재하지 않는다. 이걸 어기면 아무도 처리하지 않는 job이 쌓인다."""
    client.post("/pricing/estimates", json=_payload())

    assert fake_redis.pushed == []


def test_result_is_readable_through_the_shared_gateway_path(client, fake_redis):
    """결과 조회는 pricing 전용 경로가 아니라 게이트웨이 공통 경로를 쓴다."""
    job_id = client.post("/pricing/estimates", json=_payload()).json()["job_id"]

    response = client.get(f"/ai/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"  # TestClient가 백그라운드를 이미 돌렸다
    assert body["result"]["product_id"] == 1042
    assert body["result"]["model"]["comps_source"] == "mock"
    assert body["result"]["model"]["retail_source"] == "mock"


def test_retail_items_are_empty_by_default(client):
    """트리거 기준이 정해지기 전까지는 요청에 없어도(=false) 신상품가를 안 부른다."""
    job_id = client.post("/pricing/estimates", json=_payload()).json()["job_id"]
    body = client.get(f"/ai/jobs/{job_id}").json()

    assert body["result"]["retail_items"] == []
    assert body["result"]["retail_notes"]


def test_retail_items_are_populated_when_include_retail_is_true(client):
    """include_retail=true를 HTTP로 넣었을 때 라우터→서비스→mock retail까지 실제로 이어지는지."""
    job_id = client.post("/pricing/estimates", json=_payload(include_retail=True)).json()["job_id"]
    body = client.get(f"/ai/jobs/{job_id}").json()

    assert body["result"]["retail_items"] != []
    assert body["result"]["model"]["retail_source"] == "mock"


@pytest.mark.parametrize(
    "overrides",
    [
        {"product_id": 0},
        {"product_name": ""},
        {"condition_score": 101.0},
        {"condition_score": -1.0},
        {"condition_grade": "Z"},
        {"retail_price": -5},
    ],
)
def test_invalid_requests_are_rejected(client, fake_redis, overrides):
    """검증(422)이 이 엔드포인트의 존재 이유다 — 범용 `POST /ai/{feature}`는 dict라 못 거른다."""
    response = client.post("/pricing/estimates", json=_payload(**overrides))

    assert response.status_code == 422


def test_rejected_request_leaves_no_job_behind(client, fake_redis):
    """422면 result 키도 만들지 않는다 — 존재하지 않는 job을 폴링하게 만들면 안 된다."""
    client.post("/pricing/estimates", json=_payload(condition_score=999.0))

    assert fake_redis.stored == {}
    assert fake_redis.pushed == []


def test_busy_returns_503_without_creating_a_job(client, fake_redis, monkeypatch):
    """슬롯이 없으면 job_id를 발급하지 않는다 — 404와 '처리 중'을 구별할 수 없게 된다."""
    service = get_pricing_service()
    monkeypatch.setattr(service, "try_acquire_slot", lambda: False)

    response = client.post("/pricing/estimates", json=_payload())

    assert response.status_code == 503
    assert fake_redis.stored == {}
