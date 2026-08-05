# 011 상품 상세 — 유사 상품 가격대(가격 분포) 데이터 요청

**요청자 파트**: FE
**대상 파트**: BE

## 배경/이유
상품 상세에 "유사 상품 가격대 그래프"(FE `S15P11A108-408`, SALE-001)가 구현돼 있는데, mock → 실 API 전환 후 상세 응답에 유사 상품 데이터가 없어 `similarProducts`가 빈 배열이 된다. 그래프는 데이터가 있을 때만 렌더되므로 현재 화면에서 사라진 상태다. 실데이터가 응답에 담기면 그래프가 자동으로 다시 표시된다.

## 요청 내용
- 상품 상세 응답 `GET /api/products/{id}`에 **유사 상품 목록**을 포함해 달라(또는 별도 엔드포인트 `GET /api/products/{id}/similar` — 방식은 BE 판단).
- FE가 필요한 최소 필드(현재 컴포넌트 기준, `SimilarProductPricePoint`):
  ```json
  "similarProducts": [
    { "id": 12, "title": "빈티지 데님 자켓", "price": 89000 }
  ]
  ```
  - `id`(그래프에서 상품 클릭 이동), `title`(표시), `price`(가격 분포 계산). 이 3개면 충분.
- **"유사" 판정 기준**(같은 카테고리/브랜드/상태 등)은 **BE에서 결정**. FE는 목록만 받으면 됨. 현재 상품(`{id}`)은 포함돼도 되고(FE가 자체 제외) 빼도 됨.
- 개수 상한은 BE 판단(그래프상 수 개~수십 개면 충분).

## 일정
- FE는 그래프 구현 완료 상태. **BE 데이터가 응답에 담기는 시점(예정: 2026-08-05(수) 경)부터** 추가 FE 작업 없이 그래프 자동 표시.

## 관련 자료
- FE: `FE/src/domains/product/components/ProductPriceDistribution.vue`, `FE/src/domains/product/api/productApi.ts`(현재 `similarProducts: []` 하드코딩, `toProductDetailViewData`), 타입 `SimilarProductPricePoint { id, title, price }`
- 기능: SALE-001 상품 상세·검수 / FE 이슈 `S15P11A108-408`

## 처리 결과
(BE 반영 후 기입)
