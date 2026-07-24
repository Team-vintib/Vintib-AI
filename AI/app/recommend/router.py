"""추천 도메인 API 레이어.

엔드포인트는 요청 검증·응답 변환만 담당하고 실제 로직은 service에 위임한다.
현재는 스캐폴드라 로직 미구현 구간은 501을 반환한다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.recommend.schemas import EntityType, GraphResponse, SimilarResponse
from app.recommend.service import RecommendService, get_recommend_service

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
    except NotImplementedError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(exc)) from exc


@router.get("/{entity}/{entity_id}/similar", response_model=SimilarResponse)
def get_similar(
    entity: EntityType,
    entity_id: str,
    k: int = Query(10, ge=1, le=50, description="반환할 유사 엔티티 수"),
    service: RecommendService = Depends(get_recommend_service),
) -> SimilarResponse:
    try:
        return service.get_similar(entity, entity_id, k)
    except NotImplementedError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(exc)) from exc
