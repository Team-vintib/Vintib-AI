"""가격 책정 서비스 — 오케스트레이션과 job 상태 기록 검증.

`run_job`은 백그라운드 스레드에서 도는 함수라 **예외가 밖으로 나가면 아무도 못 본다.**
그 경우 job이 `queued`인 채 TTL까지 남아 BE가 "워커 없음"과 구별하지 못한다. 그래서 여기서
"어떤 실패든 `failed`로 기록된다"를 고정한다.
"""

import json

import pytest

from app.pricing import registry
from app.pricing.comps import CompsFetch, CompsSource, CompsUnavailable
from app.pricing.pricer import RuleBaselinePricer
from app.pricing.retail import RetailFetch, RetailSource
from app.pricing.schemas import CompItem, ConditionGrade, PricingRequest, ReasonCode
from app.pricing.service import PricingService


class _StubSource(CompsSource):
    key = "mock"

    def __init__(self, fetch_result=None, error: Exception | None = None) -> None:
        self._fetch_result = fetch_result
        self._error = error

    def fetch(self, query: str) -> CompsFetch:
        if self._error is not None:
            raise self._error
        return self._fetch_result


class _StubRetailSource(RetailSource):
    key = "mock"

    def __init__(self, fetch_result=None, error: Exception | None = None) -> None:
        self._fetch_result = fetch_result if fetch_result is not None else RetailFetch(items=[])
        self._error = error

    def fetch(self, query: str) -> RetailFetch:
        if self._error is not None:
            raise self._error
        return self._fetch_result


def _comps(*prices: int) -> CompsFetch:
    return CompsFetch(
        items=[CompItem(title="t", price=p, source="mock", is_used=True) for p in prices]
    )


def _retail(*prices: int) -> RetailFetch:
    return RetailFetch(
        items=[CompItem(title="새 상품", price=p, source="mock", is_used=False) for p in prices]
    )


def _service(
    source: CompsSource,
    *,
    retail_source: RetailSource | None = None,
    max_concurrent: int = 2,
) -> PricingService:
    return PricingService(
        source,
        RuleBaselinePricer(min_comps=1),
        retail_source or _StubRetailSource(),
        max_concurrent=max_concurrent,
    )


def _request(**overrides) -> PricingRequest:
    body = {
        "product_id": 7,
        "product_name": "리바이스 501 빅E",
        "condition_score": 82.0,
        "condition_grade": ConditionGrade.a,
    }
    body.update(overrides)
    return PricingRequest(**body)


def _stored_result(fake_redis, job_id: str) -> dict:
    return json.loads(fake_redis.stored[f"result:{job_id}"])


# --- estimate (순수) --------------------------------------------------------


def test_estimate_returns_priced_result():
    result = _service(_StubSource(_comps(10_000, 20_000, 30_000))).estimate(_request())

    assert result.priced is True
    assert result.reason_code is ReasonCode.priced
    assert result.price_range is not None
    assert result.product_id == 7
    assert result.condition.grade is ConditionGrade.a
    assert result.model.pricer == "rule_baseline"


def test_estimate_propagates_fetch_reason_when_unpriced():
    """comps가 왜 비었는지(검색 미호출)가 산정기의 일반 사유보다 구체적이다."""
    fetch = CompsFetch(items=[], notes=["검색 안 함"], reason=ReasonCode.no_search_performed)
    result = _service(_StubSource(fetch)).estimate(_request())

    assert result.priced is False
    assert result.reason_code is ReasonCode.no_search_performed
    assert result.notes == ["검색 안 함"]


def test_estimate_raises_on_infrastructure_failure():
    """인프라 오류는 결과가 아니라 예외다 — job을 failed로 만들어야 하기 때문."""
    service = _service(_StubSource(error=CompsUnavailable("GMS_API_KEY가 설정되지 않았습니다")))

    with pytest.raises(CompsUnavailable):
        service.estimate(_request())


# --- 신상품가(retail) — comps와 완전히 분리, include_retail로 조건부 호출 --------


def test_retail_is_skipped_by_default():
    """트리거 기준(BE/FE 협의 중)이 정해지기 전까지는 기본이 꺼짐이다 — 쿼터를 안 쓴다."""
    service = _service(
        _StubSource(_comps(10_000, 20_000, 30_000)),
        retail_source=_StubRetailSource(_retail(45_000, 47_000)),
    )

    result = service.estimate(_request())  # include_retail 생략 → False

    assert result.retail_items == []
    assert result.retail_notes  # 왜 비었는지(호출 안 함)는 밝힌다


def test_retail_items_are_included_when_requested():
    service = _service(
        _StubSource(_comps(10_000, 20_000, 30_000)),
        retail_source=_StubRetailSource(_retail(45_000, 47_000)),
    )

    result = service.estimate(_request(include_retail=True))

    assert [item.price for item in result.retail_items] == [45_000, 47_000]
    assert result.model.retail_source == "mock"


def test_retail_failure_does_not_break_estimate():
    """신상품가는 부가 정보다 — 실패해도 comps 기반 가격 산정은 그대로 나와야 한다."""
    service = _service(
        _StubSource(_comps(10_000, 20_000, 30_000)),
        retail_source=_StubRetailSource(error=RuntimeError("네이버 터짐")),
    )

    result = service.estimate(_request(include_retail=True))

    assert result.priced is True
    assert result.retail_items == []
    assert result.retail_notes


def test_retail_failure_does_not_fail_the_job(fake_redis):
    """④의 회귀 방지선 — retail 소스가 예외를 던져도 run_job은 success로 끝나야 한다."""
    service = _service(
        _StubSource(_comps(10_000, 20_000, 30_000)),
        retail_source=_StubRetailSource(error=RuntimeError("네이버 터짐")),
    )
    service.try_acquire_slot()

    service.run_job("job-retail-fail", _request(include_retail=True))

    stored = _stored_result(fake_redis, "job-retail-fail")
    assert stored["status"] == "success"
    assert stored["result"]["priced"] is True


# --- run_job (job 상태 기록) -------------------------------------------------


def test_run_job_records_success(fake_redis):
    service = _service(_StubSource(_comps(10_000, 20_000, 30_000)))
    service.try_acquire_slot()

    service.run_job("job-1", _request())

    stored = _stored_result(fake_redis, "job-1")
    assert stored["status"] == "success"
    assert stored["worker_id"] == registry.WORKER_ID
    assert stored["result"]["priced"] is True


def test_run_job_records_failure_without_raising(fake_redis):
    service = _service(_StubSource(error=CompsUnavailable("키 없음")))
    service.try_acquire_slot()

    service.run_job("job-2", _request())  # 예외가 밖으로 나오면 여기서 터진다

    stored = _stored_result(fake_redis, "job-2")
    assert stored["status"] == "failed"
    assert "CompsUnavailable" in stored["error"]


def test_run_job_swallows_unexpected_errors_too(fake_redis):
    """예상 못 한 예외도 job을 failed로 남겨야 한다 — 안 그러면 queued로 방치된다."""
    service = _service(_StubSource(error=RuntimeError("무언가 터짐")))
    service.try_acquire_slot()

    service.run_job("job-3", _request())

    assert _stored_result(fake_redis, "job-3")["status"] == "failed"


def test_error_message_is_truncated(fake_redis):
    """`GET /ai/jobs/{id}`는 무인증이라 원문이 FE까지 흘러갈 수 있다 — 길이를 자른다."""
    service = _service(_StubSource(error=RuntimeError("x" * 500)))
    service.try_acquire_slot()

    service.run_job("job-4", _request())

    assert len(_stored_result(fake_redis, "job-4")["error"]) < 300


def test_run_job_releases_the_slot(fake_redis):
    """실패해도 슬롯이 반납돼야 한다 — 안 그러면 몇 번 실패 후 영구 503이 된다."""
    service = _service(_StubSource(error=RuntimeError("boom")), max_concurrent=1)

    for index in range(3):
        assert service.try_acquire_slot() is True
        service.run_job(f"job-loop-{index}", _request())

    assert service.try_acquire_slot() is True


def test_slot_is_exhausted_at_the_limit():
    service = _service(_StubSource(_comps(10_000)), max_concurrent=1)

    assert service.try_acquire_slot() is True
    assert service.try_acquire_slot() is False
