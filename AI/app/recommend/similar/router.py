"""유사 상품 조회(item-to-item) API 레이어.

경로를 `docs/requests/BE/023-product-similar-list.md`(FE→BE, `/api/products/{id}/similar`)와
최대한 맞춰 둔다 — 지금은 AI 내부 검증/사용 목적이고 BE와 조율은 별도 논의지만, 나중에
통합 논의가 쉬워지도록. 기존 `personalize_router`(`/products`, path param 없음)와 경로
충돌 없음.
"""

from fastapi import APIRouter, Depends, Query

from app.recommend.similar.schemas import SimilarProductsResponse
from app.recommend.similar.service import SimilarProductService, get_similar_product_service

router = APIRouter()


@router.get("/products/{product_id}/similar", response_model=SimilarProductsResponse)
def get_similar_products(
    product_id: int,
    k: int = Query(10, ge=1, le=100, description="반환할 유사 상품 수"),
    category: str | None = Query(None, description="카테고리로 후보를 좁힘(선택)"),
    service: SimilarProductService = Depends(get_similar_product_service),
) -> SimilarProductsResponse:
    return service.get_similar(product_id, k, category=category)
