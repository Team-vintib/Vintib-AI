"""의류 실측(cm) 측정 API 레이어 — 큐 어댑터.

**추론은 여기서 하지 않는다.** 요청을 검증해 게이트웨이 큐에 적재하고 `job_id`만 돌려준다.
실제 처리(기준 물체 검출 + 원단 분할 + 랜드마크 검출 + cm 환산)는 팀원 노트북에서 도는 워커
(`worker/garment_measurement_worker_example.py`)가 맡는다.

**왜 비동기인가**: `quality_check`와 같은 이유 — EC2 `ai` 컨테이너에는 GPU도 torch도 없고
(`mem_limit: 1g`), 추론은 노트북 GPU가 하는데 노트북은 인바운드 접속이 불가능하다. 인바운드가
안 되는 자원은 동기 호출 대상이 될 수 없다(`AI/docs/infra-architecture.md` §2·§6).

결과 조회는 이 도메인이 아니라 게이트웨이 공통 경로를 쓴다 — `GET /ai/jobs/{job_id}`.
품질검수·시착과 같은 형식이라 BE가 폴링 로직을 하나만 유지하면 된다.

설계: .claude/plans/ai/010-garment-measurement-scan.md
BE 계약: .claude/requests/be/004-garment-measurement-scan.md
"""

from fastapi import APIRouter

from app.gateway.router import enqueue_job
from app.measurement.schemas import MeasurementScanEnqueued, MeasurementScanRequest

router = APIRouter()


@router.post("/scans", response_model=MeasurementScanEnqueued)
def create_scan(request: MeasurementScanRequest) -> MeasurementScanEnqueued:
    """실측 job을 큐에 넣고 `job_id`를 돌려준다.

    요청 검증(422)을 여기서 하는 게 이 엔드포인트의 존재 이유다 — 게이트웨이의 범용
    `POST /ai/{feature}`는 payload가 `dict`라 카테고리 오타나 이미지 누락을 걸러내지 못한다.

    **워커가 꺼져 있어도 202로 접수된다.** 그 경우 job은 `queued`로 남아 있다가 TTL(1시간)에
    만료된다 — 워커 가용 여부는 `GET /ai/workers/status`로 미리 확인할 수 있다.
    """
    enqueued = enqueue_job("garment_measurement", request.model_dump(mode="json"))
    return MeasurementScanEnqueued(job_id=enqueued["job_id"], product_id=request.product_id)
