"""추천 도메인 API 레이어.

엔드포인트는 요청 검증·응답 변환만 담당하고 실제 로직은 service에 위임한다.
아티팩트 미생성은 503, 없는 엔티티 id는 404로 매핑한다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.recommend.schemas import EntityType, GraphResponse, SimilarResponse
from app.recommend.service import (
    ArtifactNotFound,
    EntityItemNotFound,
    RecommendService,
    get_recommend_service,
)

router = APIRouter()


@router.get("/graph", response_model=GraphResponse)
def get_graph(
    entity: EntityType = Query(EntityType.brand, description="유사도 대상 엔티티"),
    focus: str | None = Query(None, description="중심 엔티티 id(없으면 전체 맵)"),
    k: int = Query(10, ge=1, le=50, description="focus 이웃 수"),
    service: RecommendService = Depends(get_recommend_service),
) -> GraphResponse:
    try:
        return service.get_graph(entity, focus, k)
    except ArtifactNotFound as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except EntityItemNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/{entity}/{entity_id}/similar", response_model=SimilarResponse)
def get_similar(
    entity: EntityType,
    entity_id: str,
    k: int = Query(10, ge=1, le=50, description="반환할 유사 엔티티 수"),
    service: RecommendService = Depends(get_recommend_service),
) -> SimilarResponse:
    try:
        return service.get_similar(entity, entity_id, k)
    except ArtifactNotFound as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except EntityItemNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
