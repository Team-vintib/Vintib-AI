"""개인화 상품 추천 요청/응답 스키마.

FE 상품 카드 리스트가 그대로 렌더링할 수 있는 응답을 돌려준다. 필드명은 스키마 컬럼
기준의 잠정안이다(`product.title`/`product_image.image_url`/`brand.name` 매핑). 확정
스키마가 나오면 정렬한다. 설계: .claude/plans/ai/002-personalized-recommendation-mvp.md
"""

from enum import Enum

from pydantic import BaseModel


class Strategy(str, Enum):
    """추천에 사용된 콜드스타트 폴백 티어(응답으로 노출)."""

    popularity = "popularity"  # T0: 신호 없음 → 인기순
    onboarding = "onboarding"  # T1: 온보딩 관심 브랜드/카테고리
    interaction = "interaction"  # T2: 찜/구매 상호작용 로그


class ProductCard(BaseModel):
    """FE 상품 카드 한 장. 필드는 product/product_image/brand 컬럼 매핑(잠정)."""

    product_id: int
    title: str
    thumbnail: str | None = None
    price: int | None = None  # 경매 예정 등은 null 가능
    brand: str | None = None
    sale_type: str
    sale_status: str
    score: float  # 랭킹 점수(정렬 근거/디버그, FE 무시 가능)


class RecommendResponse(BaseModel):
    strategy: Strategy
    personalized: bool
    page: int
    size: int
    total: int
    items: list[ProductCard]
