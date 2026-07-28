"""품질 검수 API 레이어 — 큐 어댑터.

**추론은 여기서 하지 않는다.** 요청을 검증해 게이트웨이 큐에 적재하고 `job_id`만 돌려준다.
실제 판정(CLIPSeg 추론 + 하자 항목화 + 점수 + 오버레이)은 팀원 노트북에서 도는 워커
(`worker/quality_check_worker_example.py`)가 맡는다.

**왜 비동기인가**: EC2 `ai` 컨테이너에는 GPU가 없고 torch도 설치돼 있지 않다(`mem_limit: 1g`).
추론은 노트북 GPU가 하는데, 노트북은 공유기 뒤라 인바운드 접속이 불가능하다 —
**인바운드가 안 되는 자원은 동기 호출 대상이 될 수 없다.** 시착(CatVTON)이 같은 이유로 이미
큐를 쓴다(`AI/docs/infra-architecture.md` §2·§6).

한때 이 파일은 동기 REST였다. 목업 백엔드로는 즉시 응답이 가능했지만 **실모델을 붙이는 순간
배포 환경에서 동작할 수 없는 구조**였다. 목업 역시 워커로 옮겨서(`QUALITY_BACKEND=mock`)
GPU 없이도 전 경로를 검증할 수 있다.

결과 조회는 이 도메인이 아니라 게이트웨이 공통 경로를 쓴다 — `GET /ai/jobs/{job_id}`.
시착과 같은 형식이라 BE가 폴링 로직을 하나만 유지하면 된다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md
BE 계약: .claude/requests/be/001-quality-inspection-async.md
"""

from fastapi import APIRouter

from app.gateway.router import enqueue_job
from app.quality.schemas import InspectionEnqueued, InspectionRequest

router = APIRouter()


@router.post("/inspections", response_model=InspectionEnqueued)
def create_inspection(request: InspectionRequest) -> InspectionEnqueued:
    """검수 job을 큐에 넣고 `job_id`를 돌려준다.

    요청 검증(422)을 여기서 하는 게 이 엔드포인트의 존재 이유다 — 게이트웨이의 범용
    `POST /ai/{feature}`는 payload가 `dict`라 카테고리 오타나 이미지 누락을 걸러내지 못한다.
    잘못된 job이 큐에 들어가면 워커가 GPU를 잡고 나서야 실패한다.

    **워커가 꺼져 있어도 202로 접수된다.** 그 경우 job은 `queued`로 남아 있다가 TTL(1시간)에
    만료된다 — 워커 가용 여부는 `GET /ai/workers/status`로 미리 확인할 수 있다.
    """
    enqueued = enqueue_job("quality_check", request.model_dump(mode="json"))
    return InspectionEnqueued(job_id=enqueued["job_id"], product_id=request.product_id)
