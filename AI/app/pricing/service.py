"""가격 책정 오케스트레이션.

**두 진입점이 있고 책임이 다르다.**

- `estimate()` — 순수 산정. Redis도 job도 모른다. 예외를 그대로 올린다.
- `run_job()` — 백그라운드 진입점. `result:{job_id}`에 상태를 기록하고 **예외를 절대 밖으로
  내보내지 않는다.** 백그라운드 스레드에서 터진 예외는 응답이 이미 나간 뒤라 아무도 못 보고,
  job은 `queued`인 채 TTL까지 남아 BE가 "워커 없음"과 구별하지 못한다.

동시 실행 상한을 세마포어로 건다. 백그라운드가 도는 스레드풀을 게이트웨이 엔드포인트
(`GET /ai/jobs/{id}` 폴링 포함)와 공유하기 때문에, 상한이 없으면 가격 job이 풀을 채워
폴링 자체가 굶는다. **초과분은 대기시키지 않고 접수 단계에서 거절한다**(라우터가 503).

설계: .claude/plans/ai/CH003-pricing-service-prototype.md
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from functools import lru_cache

from app.gateway.router import store_job_result
from app.pricing import registry
from app.pricing.comps import CompsSource, CompsUnavailable, build_comps_source, build_query
from app.pricing.pricer import Pricer, build_pricer
from app.pricing.retail import RetailSource, build_retail_source
from app.pricing.schemas import (
    CompItem,
    CompsSourceKey,
    ConditionEcho,
    PricingModelInfo,
    PricingRequest,
    PricingResult,
    RetailSourceKey,
)

__all__ = ["PricingService", "CompsUnavailable", "get_pricing_service"]

logger = logging.getLogger(__name__)


class PricingService:
    """comps 수집 → 가격 산정 → 결과 조립."""

    def __init__(
        self,
        comps_source: CompsSource,
        pricer: Pricer,
        retail_source: RetailSource,
        *,
        comps_model_id: str | None = None,
        max_concurrent: int = registry.MAX_CONCURRENT_JOBS,
    ) -> None:
        self._comps_source = comps_source
        self._pricer = pricer
        self._retail_source = retail_source
        self._comps_model_id = comps_model_id
        self._slots = threading.BoundedSemaphore(max_concurrent)

    # --- 접수 제어 ---------------------------------------------------------

    def try_acquire_slot(self) -> bool:
        """실행 슬롯을 잡는다. 실패하면 라우터가 503으로 끊는다(대기시키지 않는다)."""
        return self._slots.acquire(blocking=False)

    def release_slot(self) -> None:
        self._slots.release()

    # --- 산정 -------------------------------------------------------------

    def estimate(self, request: PricingRequest) -> PricingResult:
        """가격을 산정한다. **comps를 못 구하면 `CompsUnavailable`을 올린다.**

        반대로 comps가 부족한 것(0건·파싱 실패)은 예외가 아니라 `priced=false` 결과다.
        """
        started = time.perf_counter()
        query = build_query(request.product_name, request.brand, request.category)
        fetched = self._comps_source.fetch(query)
        retail_items, retail_notes = (
            self._fetch_retail(query)
            if request.include_retail
            else ([], ["신상품가 조회를 요청하지 않았습니다(include_retail=false)."])
        )

        outcome = self._pricer.price(
            fetched.items,
            condition_score=request.condition_score,
            condition_grade=request.condition_grade,
            retail_price=request.retail_price,
        )
        # comps가 비어 있던 사유(검색 미호출·파싱 실패)가 있으면 그쪽이 더 구체적이다.
        reason_code = (
            fetched.reason if (fetched.reason and not outcome.priced) else outcome.reason_code
        )

        return PricingResult(
            estimate_id=f"price_{request.product_id}_{uuid.uuid4().hex[:4]}",
            product_id=request.product_id,
            priced=outcome.priced,
            reason_code=reason_code,
            price_range=outcome.price_range,
            confidence=outcome.confidence,
            confidence_level=outcome.confidence_level,
            rationale=outcome.rationale,
            comps_used=outcome.comps_used,
            comps_stats=outcome.comps_stats,
            condition=ConditionEcho(
                score=request.condition_score,
                grade=request.condition_grade,
                coefficient=outcome.coefficient,
            ),
            model=PricingModelInfo(
                comps_source=CompsSourceKey(self._comps_source.key),
                comps_model_id=self._comps_model_id,
                pricer=self._pricer.key,
                retail_source=RetailSourceKey(self._retail_source.key),
            ),
            notes=list(fetched.notes),
            retail_items=retail_items,
            retail_notes=retail_notes,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
        )

    def _fetch_retail(self, query: str) -> tuple[list[CompItem], list[str]]:
        """신상품가 수집. **여기서 나는 예외는 가격 산정을 막지 않는다.**

        `RetailSource.fetch()` 자체가 예외를 던지지 않는 게 계약이지만, 구현 버그로
        어긴 경우까지 대비한 이중 방어다 — 신상품가는 부가 정보일 뿐 필수 입력이 아니다.
        """
        try:
            fetched = self._retail_source.fetch(query)
        except Exception:  # noqa: BLE001 — 신상품가 실패가 job을 죽이면 안 된다
            logger.exception("신상품가 수집 실패 (query=%s)", query)
            return [], ["신상품가 조회 중 오류가 발생했습니다."]
        return fetched.items, list(fetched.notes)

    # --- 백그라운드 진입점 --------------------------------------------------

    def run_job(self, job_id: str, request: PricingRequest) -> None:
        """`BackgroundTasks`가 부른다. **어떤 경우에도 예외를 올리지 않는다.**

        동기 함수인 것이 중요하다 — Starlette는 코루틴이 아닌 백그라운드 콜백을 스레드풀에서
        돌리므로, 블로킹 HTTP 호출이 이벤트 루프를 막지 않는다.
        """
        try:
            store_job_result(job_id, "processing")
            result = self.estimate(request)
            store_job_result(
                job_id,
                "success",
                result=result.model_dump(mode="json"),
                worker_id=registry.WORKER_ID,
            )
        except Exception as exc:  # noqa: BLE001 — 백그라운드 밖으로 나가면 아무도 못 본다
            logger.exception("가격 산정 실패 (job_id=%s)", job_id)
            self._store_failed(job_id, exc)
        finally:
            self.release_slot()

    def _store_failed(self, job_id: str, exc: Exception) -> None:
        # 예외 원문을 그대로 싣지 않는다 — `GET /ai/jobs/{job_id}`는 무인증이고 값이
        # BE를 거쳐 FE까지 흘러갈 수 있다. GMS 응답 본문이나 키 흔적이 섞이면 그대로 노출된다.
        message = f"{type(exc).__name__}: {str(exc)[:200]}"
        try:
            store_job_result(job_id, "failed", error=message, worker_id=registry.WORKER_ID)
        except Exception:  # noqa: BLE001 — Redis까지 죽었으면 남길 곳이 없다
            logger.exception("실패 상태 기록마저 실패 (job_id=%s)", job_id)


@lru_cache
def get_pricing_service() -> PricingService:
    """유일한 조립 지점. 백엔드 스왑은 `registry.ACTIVE_*` 한 줄로 끝난다."""
    config = registry.comps_config()
    return PricingService(
        build_comps_source(),
        build_pricer(min_comps=config["min_comps_for_pricing"]),
        build_retail_source(),
        comps_model_id=config["model_id"],
    )
