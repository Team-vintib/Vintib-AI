"""품질 검수 API 레이어.

요청 검증·응답 변환만 담당하고 로직은 service에 위임한다. 검수는 **동기**다 — 상품 등록은
판매자가 화면에서 기다리는 흐름이라 job 폴링을 끼우지 않는다.

에러 매핑(설계 문서 §API 스펙):

| 상황 | 응답 |
| --- | --- |
| 요청 필드 누락 / 미등록 카테고리 | 422 (FastAPI 기본 검증 + enum) |
| 활성 백엔드 준비 안 됨(torch 미설치·워커 미연결) | 503 |
| 이미지 다운로드 실패 | 502 |
| 검수 id 없음 / TTL 만료 | 404 |

기존 도메인과 동일하게 `{success,data,error}` 봉투로 감싸지 않는다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.quality.schemas import InspectionRequest, InspectionResponse, QualityConfigResponse
from app.quality.service import (
    ImageFetchFailed,
    InspectionNotFound,
    QualityInspectionService,
    SegmenterNotReady,
    get_quality_service,
)

router = APIRouter()


@router.post("/inspections", response_model=InspectionResponse)
def create_inspection(
    request: InspectionRequest,
    service: QualityInspectionService = Depends(get_quality_service),
) -> InspectionResponse:
    try:
        return service.inspect(request)
    except SegmenterNotReady as exc:
        # 기동 실패가 아니라 가용성 문제다 — 백엔드를 목업으로 되돌리면 즉시 복구된다.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "segmenter backend not ready"
        ) from exc
    except ImageFetchFailed as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "failed to fetch product image") from exc


@router.get("/inspections/{inspection_id}", response_model=InspectionResponse)
def get_inspection(
    inspection_id: str,
    service: QualityInspectionService = Depends(get_quality_service),
) -> InspectionResponse:
    try:
        return service.get_inspection(inspection_id)
    except InspectionNotFound as exc:
        # 없는 id와 TTL 만료를 구분하지 않는다 — 호출자가 할 일은 둘 다 재검수로 같다.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "inspection not found or expired") from exc


@router.get("/prompt-sets", response_model=QualityConfigResponse)
def get_config(
    service: QualityInspectionService = Depends(get_quality_service),
) -> QualityConfigResponse:
    """활성 백엔드·임계치·프롬프트·하자 분류 체계를 노출한다(디버그·데모용).

    "모델을 갈아끼웠다"를 API로 확인하고, 어떤 값이 아직 미확정인지 드러내는 용도다.
    """
    return service.describe_config()
