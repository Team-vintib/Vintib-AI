"""개인화 상품 추천 API 레이어.

요청 검증·응답 변환만 담당하고 로직은 service에 위임한다. 익명/신규/필터 0건은 정상 경로
(200, 폴백)이며, 카탈로그(아이템 임베딩) 미생성만 503으로 매핑한다. 기존 graph 엔드포인트
(/recommend/graph, /recommend/{entity}/{id}/similar)와 경로 충돌이 없다.

설계: .claude/plans/ai/002-personalized-recommendation-mvp.md
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.recommend.personalize.schemas import RecommendResponse
from app.recommend.personalize.service import (
    CatalogNotReady,
    PersonalizeService,
    get_personalize_service,
)

router = APIRouter()


@router.get("/products", response_model=RecommendResponse)
def get_personalized_products(
    # TODO(BE): 인증 방식 확정 전 잠정으로 쿼리 수신. 확정 시 헤더/BE 주입으로 이전.
    user_id: int | None = Query(None, description="유저 id(없으면 익명 → T0 인기순)"),
    category_id: int | None = Query(None, description="카테고리 필터"),
    brand_id: int | None = Query(None, description="브랜드 필터"),
    page: int = Query(1, ge=1, description="1-base 페이지"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기(1~100)"),
    service: PersonalizeService = Depends(get_personalize_service),
) -> RecommendResponse:
    try:
        return service.recommend(user_id, category_id, brand_id, page, size)
    except CatalogNotReady as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "item embedding artifact not built",
        ) from exc
