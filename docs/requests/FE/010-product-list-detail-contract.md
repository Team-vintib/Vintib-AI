# 상품 목록 필터·상세 응답 보강 — 확정 계약

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

`docs/requests/BE/006-product-contract.md` §3.1(목록 필터), §3.2(상세 응답 보강)를 구현 완료했다.
필드 이름·구조가 요청과 일부 달라진 부분이 있어 FE가 참고할 수 있게 확정 계약을 정리한다.

## 요청 내용

### 1. 상품 목록 필터 — `GET /api/products`

요청한 파라미터명 그대로 구현했다(변경 없음).

| Query | 타입 | 설명 |
| --- | --- | --- |
| `categoryIds` | number[] | 복수 가능. 미입력 시 전체 |
| `conditionGrades` | string[] | 복수 가능(`S`,`A` 등). 미입력 시 전체 |
| `saleType` | `DIRECT_SALE` \| `AUCTION` | 미입력 시 전체 |
| `minPrice` / `maxPrice` | number | 미입력 시 하한/상한 없음 |
| `sort` | `LATEST`(기본) \| `PRICE_ASC` \| `PRICE_DESC` | |

응답은 기존 `PageResponse<ProductResponse>` 그대로다. **`keyword`(검색어)는 아직 없다** — 통합 검색(`docs/requests/BE/005-search-contract.md`, `GET /api/search`)이 아직 미구현이라 그쪽에서 다룰 예정이다. 목록 화면에서 검색어가 당장 급하면 별도로 알려달라.

### 2. 상품 상세 응답 보강 — `GET /api/products/{id}` (`ProductDetailResponse`)

요청 문서 대비 **이름·구조가 달라진 필드**가 있다:

| 요청했던 이름 | 실제 필드 | 비고 |
| --- | --- | --- |
| `seller.followerCount`(중첩 객체) | `sellerFollowerCount`(최상위 평탄 필드) | 기존 `sellerNickname`과 같은 레벨에 둠 |
| `seller.productCount`(중첩 객체) | `sellerProductCount`(최상위 평탄 필드) | 판매 중인 상품 수(DRAFT 제외) |
| `relatedLive` | `linkedLive` | 이름만 다름, 구조는 아래와 동일 |

전체 응답 예시:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "sellerId": 1,
    "sellerNickname": "vintagelover",
    "categoryId": 1,
    "categoryName": "자켓",
    "brandId": 1,
    "brandName": "리바이스",
    "title": "빈티지 리바이스 데님 자켓",
    "measurements": { "총장": 70, "어깨너비": 45 },
    "defects": ["소매 끝 실밥 풀림"],
    "images": [],
    "isWished": false,
    "sellerFollowerCount": 120,
    "sellerProductCount": 45,
    "linkedLive": {
      "liveId": 10,
      "title": "빈티지 리바이스 특가전",
      "status": "SCHEDULED",
      "scheduledAt": "2026-07-29T12:00:00",
      "startedAt": null,
      "thumbnailUrl": "https://example.com/thumbnail.jpg"
    }
  },
  "error": null
}
```

`linkedLive`는 연결된 라이브가 없으면 `null`이다. `isWished`는 비회원 요청이면 `false`(006에서 이미 확정 — `null` 아님).

**이번 범위 밖(아직 없음)**: `similarProducts`(유사 상품), `priceDistribution`(가격 분포), `images[].role`(FRONT/BACK/ADDITIONAL). AI 품질 분석/가격 추천도 별도 계약 확정 전이라 아직 없다.

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "상품(Products)" 태그
- `BE/src/main/java/com/ssafy/backend/product/dto/response/ProductDetailResponse.java`

## 처리 결과

(FE 반영 후 기입)
