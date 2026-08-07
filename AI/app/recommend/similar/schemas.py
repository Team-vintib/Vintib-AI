"""유사 상품 조회(item-to-item) 응답 스키마.

`personalize/schemas.py`의 `ProductCard`와 달리 상품 메타(제목/썸네일/가격 등)를 안 채운다
— `catalog.py`가 아직 목업이라 AI 쪽엔 실제 상품 메타 소스가 없다. `product_id`+점수만
돌려주고, 화면에 필요한 카드 정보는 (BE 통합 시) 그 id로 BE가 채운다.
"""

from pydantic import BaseModel


class SimilarProduct(BaseModel):
    product_id: int
    score: float  # 코사인 유사도(1에 가까울수록 유사)


class SimilarProductsResponse(BaseModel):
    product_id: int
    items: list[SimilarProduct]
