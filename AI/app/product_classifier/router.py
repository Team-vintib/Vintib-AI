"""상품 정보 분류 API 레이어 — 큐 어댑터.

**추론은 여기서 하지 않는다.** 요청을 검증해 게이트웨이 큐에 적재하고 `job_id`만 돌려준다.
실제 처리(카테고리 분류 + 색상 추출)는 팀원 노트북에서 도는 워커
(`worker/product_classifier_worker_example.py`)가 맡는다.

**왜 비동기인가**: `quality_check`/`garment_measurement`와 같은 이유 — EC2 `ai` 컨테이너에는
GPU도 torch도 없고(`mem_limit: 1g`), 추론은 노트북이 하는데 노트북은 인바운드 접속이
불가능하다(`AI/docs/infra-architecture.md` §2·§6).

**품질검수와 병렬로 돈다.** 상품 사진이 올라오면 이 엔드포인트와 `POST /quality/inspections`가
동시에 호출된다(BE/FE가 각자의 job_id로 독립 폴링) — 카테고리·색상은 가벼워서 먼저 끝나 폼을
프리필하고, 무거운 품질검수는 그동안 별도로 진행된다(CH012 §1.1/§3).

결과 조회는 이 도메인이 아니라 게이트웨이 공통 경로를 쓴다 — `GET /ai/jobs/{job_id}`.

설계: `.claude/plans/ai/CH012-~2.MD`
"""

from fastapi import APIRouter

from app.gateway.router import enqueue_job
from app.product_classifier.schemas import ProductClassifyEnqueued, ProductClassifyRequest

router = APIRouter()


@router.post("/classify", response_model=ProductClassifyEnqueued)
def create_classification(request: ProductClassifyRequest) -> ProductClassifyEnqueued:
    """분류 job을 큐에 넣고 `job_id`를 돌려준다.

    요청 검증(422)을 여기서 하는 게 이 엔드포인트의 존재 이유다 — 게이트웨이의 범용
    `POST /ai/{feature}`는 payload가 `dict`라 이미지 누락 같은 걸 걸러내지 못한다.

    **워커가 꺼져 있어도 200으로 접수된다.** 그 경우 job은 `queued`로 남아 있다가 TTL(1시간)에
    만료된다 — 워커 가용 여부는 `GET /ai/workers/status`로 미리 확인할 수 있다.
    """
    enqueued = enqueue_job("product_classifier", request.model_dump(mode="json"))
    return ProductClassifyEnqueued(job_id=enqueued["job_id"], product_id=request.product_id)
