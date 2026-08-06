"""유사 상품 조회(item-to-item) 서빙 로직.

`personalize/`(유저 취향 대 카탈로그)나 최상위 `recommend/`(브랜드/셀러 오프라인 그래프)와
데이터 접근 패턴이 다르다 — 여기는 상품이 등록될 때마다 늘어나는 라이브 pgvector 코퍼스를
그때그때 조회한다. 실제 코사인 검색은 `embedding_store.find_similar()`가 한다(이 모듈은
DB를 직접 만지지 않는다).

설계: `.claude/plans/serialized-nibbling-mango.md`(유사 상품 조회 API 절)
"""

from __future__ import annotations

from app.recommend.personalize import embedding_store
from app.recommend.similar.schemas import SimilarProduct, SimilarProductsResponse


class SimilarProductService:
    def get_similar(
        self, product_id: int, k: int, category: str | None = None
    ) -> SimilarProductsResponse:
        """대상 상품의 임베딩이 없으면(품질검수 미완료·옷 미검출) `items=[]` — 에러가 아니다,
        `personalize`의 "필터 0건은 200" 관례와 동일하게 정상 응답으로 처리한다."""
        matches = embedding_store.find_similar(product_id, k, category=category)
        return SimilarProductsResponse(
            product_id=product_id,
            items=[SimilarProduct(product_id=m.product_id, score=m.score) for m in matches],
        )


def get_similar_product_service() -> SimilarProductService:
    """FastAPI 의존성 주입용 프로바이더. 상태가 없어 매 요청 새 인스턴스라도 무해하지만,
    `personalize`의 `get_personalize_service()`와 시그니처를 맞춰 둔다."""
    return SimilarProductService()
