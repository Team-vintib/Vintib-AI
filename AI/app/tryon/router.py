"""상품 등록 "AI 착용컷" 트리거 — 큐 어댑터 (S15P11A108-568).

**추론은 여기서 하지 않는다.** 기존 시착 워커(`worker/tryon_worker_example.py`)가 이미
프로덕션에서 처리하는 `type="tryon"` job을 그대로 재사용한다 — 이 라우터가 하는 일은
페르소나(희동이/도우너) 참조 사진 URL을 결정해 job payload를 조립하는 것뿐이다.

**페르소나 이미지는 AI가 자체 호스팅한다**(`app/static/personas/`, `AI/app/main.py`가
`/personas`로 정적 서빙). BE 쪽에 별도 업로드·호스팅을 요청하지 않는다 — job 호출·페르소나
관리 모두 AI 인프라 영역이라는 팀 결정에 따른 것이다(`docs/plans/AI/
CH021-registration-ai-model-tryon.md`).

결과 조회는 이 도메인 전용 엔드포인트가 없다 — 게이트웨이 공통 경로
`GET /ai/jobs/{job_id}`를 그대로 쓴다(일반 시착 job과 완전히 같은 결과 계약이므로).
"""

from fastapi import APIRouter

from app.core.config import settings
from app.gateway.router import enqueue_job
from app.tryon.schemas import (
    MaskFitType,
    PersonaGender,
    RegistrationModelCutEnqueued,
    RegistrationModelCutRequest,
)

router = APIRouter()

_PERSONA_FILENAME: dict[PersonaGender, str] = {
    PersonaGender.FEMALE: "dooner.png",
    PersonaGender.MALE: "heedongi.png",
}


@router.post("/registration-model-cut", response_model=RegistrationModelCutEnqueued)
def create_registration_model_cut(
    request: RegistrationModelCutRequest,
) -> RegistrationModelCutEnqueued:
    """일반 시착과 같은 `tryon` job을 페르소나 참조 사진으로 큐에 넣고 `job_id`를 돌려준다.

    **워커가 꺼져 있어도 200으로 접수된다** — 다른 job 생성 엔드포인트와 동일한 원칙
    (`GET /ai/workers/status`로 가용 여부 확인 가능).
    """
    persona_url = f"{settings.public_base_url}/personas/{_PERSONA_FILENAME[request.gender]}"

    enqueued = enqueue_job(
        "tryon",
        {
            "user_image_url": persona_url,
            "product_image_url": request.product_image_url,
            "mask_type": request.mask_type.value,
            "fit_type": MaskFitType.regular.value,
        },
    )
    return RegistrationModelCutEnqueued(job_id=enqueued["job_id"])
