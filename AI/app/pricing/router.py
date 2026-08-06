"""가격 책정 API 레이어.

**품질검수와 달리 워커 큐를 쓰지 않는다.** `app/quality/router.py`가 큐로 간 이유는 추론이
팀원 노트북 GPU에서 돌고 그 노트북이 공유기 뒤라 인바운드가 불가능하기 때문이다. 가격 책정은
GPU도 torch도 필요 없고 GMS로 나가는 **아웃바운드 HTTPS 호출**뿐이라 그 제약이 없다.

비동기인 유일한 이유는 **느려서**다 — 가장 싼 모델·가장 적은 검색 라운드에서도 7.7초가
걸린다(CH002 V2 실측). 상품 등록 화면을 그만큼 세울 수 없다. 그래서 접수만 하고
백그라운드에서 처리한다.

**결과 조회는 게이트웨이 공통 경로를 쓴다** — `GET /ai/jobs/{job_id}`. 품질검수·시착과 같은
형식이라 BE가 폴링 로직을 하나만 유지하면 된다. 이게 가능한 이유는 그 엔드포인트가
`result:{job_id}`만 읽고 `JobResult`에 job 종류 필드가 없어서, 폴링 계약이 이미
feature와 무관하기 때문이다.

설계: .claude/plans/ai/CH003-pricing-service-prototype.md
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.gateway.router import new_local_job_id
from app.pricing.schemas import PricingEnqueued, PricingRequest
from app.pricing.service import PricingService, get_pricing_service

router = APIRouter()


@router.post("/estimates", response_model=PricingEnqueued)
def create_estimate(
    request: PricingRequest,
    background: BackgroundTasks,
    service: PricingService = Depends(get_pricing_service),  # noqa: B008
) -> PricingEnqueued:
    """가격 산정을 접수하고 `job_id`를 돌려준다.

    요청 검증(422)을 여기서 하는 게 이 엔드포인트의 존재 이유다 — 게이트웨이의 범용
    `POST /ai/{feature}`는 payload가 `dict`라 상태 점수 범위나 상품명 누락을 걸러내지 못한다.

    **`POST /ai/pricing`으로 넣지 말 것.** 그 경로는 큐에 적재하는데 가격 책정에는 큐를 읽는
    워커가 없어서 job이 아무에게도 처리되지 않고 TTL까지 남는다.

    동시 실행 상한을 넘으면 **503**이다. 대기시키지 않는 이유는, 대기 스레드가 게이트웨이와
    공유하는 스레드풀을 점유해 결과 폴링까지 굶기기 때문이다.
    """
    if not service.try_acquire_slot():
        # 슬롯을 못 잡았으면 job_id도 발급하지 않는다 — 존재하지 않는 job을 폴링하게 만들면
        # BE가 404와 "아직 처리 중"을 구별하지 못한다.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "pricing is busy, retry shortly")

    try:
        job_id = new_local_job_id()
    except Exception:
        service.release_slot()
        raise

    background.add_task(service.run_job, job_id, request)
    return PricingEnqueued(job_id=job_id, product_id=request.product_id)
