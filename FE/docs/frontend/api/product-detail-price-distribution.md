# 상품 상세·유사 상품 가격 분포 API

확인 기준: 2026-07-30 로컬 Swagger UI (`/swagger-ui/index.html`, `/v3/api-docs`)

## 목적

상품 상세 화면과 구매 영역 아래의 유사 상품 가격 분포에 필요한 API를 정리한다.
Swagger에 없는 계약은 현재 제공되는 API처럼 사용하지 않고 `BE 확인 필요`로 구분한다.

## 현재 Swagger에서 사용 가능한 API

| 화면 기능 | Method | Endpoint | 인증 | 현재 상태 |
| --- | --- | --- | --- | --- |
| 상품 상세 기본 정보 | GET | `/api/products/{id}` | 비회원 가능 | 사용 가능 |
| 공개 상품 목록 | GET | `/api/products` | Swagger상 Bearer 표시 | 사용 가능, 유사 상품 조회 용도로는 부적합 |
| 상품 찜 | POST | `/api/users/{userId}/wishes` | 필요 | 사용 가능 |
| 상품 찜 해제 | DELETE | `/api/users/{userId}/wishes/{id}` | 필요 | 사용 가능 |
| 라이브 시청 정보 | GET | `/api/lives/{liveId}` | 비회원 가능 | `liveId`를 알고 있을 때 사용 가능 |
| 라이브 연결 상품 | GET | `/api/lives/{liveId}/products` | 필요 | 라이브에서 상품을 조회하는 방향만 가능 |

### 상품 상세 조회

```http
GET /api/products/{id}
```

`data`에서 확인되는 필드:

- `id`
- `sellerId`, `sellerNickname`
- `categoryId`, `brandId`
- `title`, `description`
- `conditionGrade`, `sizeLabel`
- `saleType`, `saleStatus`, `price`
- `images`
- `createdAt`, `updatedAt`

현재 상품 상세 화면에서 사용하는 아래 정보는 이 응답에 포함되지 않는다.

- 판매자 팔로워 수와 판매 상품 수
- 카테고리명과 브랜드명
- 현재 사용자의 찜 여부
- 상품에서 역방향으로 찾은 연결 라이브
- AI 품질 분석 결과
- 유사 상품 목록

### 공개 상품 목록 조회

```http
GET /api/products?page=0&size=20
```

현재 Swagger 설명상 공개 상품을 최신순으로만 반환하며, `sort` 파라미터는 무시된다.
카테고리·브랜드·가격·유사도 조건이 없으므로 FE가 이 목록을 받아 임의로 유사 상품처럼
필터링하지 않는다.

### 상품 찜·해제

```http
POST /api/users/{userId}/wishes
Authorization: Bearer {accessToken}
Content-Type: application/json

{
  "productId": 1
}
```

```http
DELETE /api/users/{userId}/wishes/{productId}
Authorization: Bearer {accessToken}
```

## 유사 상품 가격 분포에 필요한 API

현재 Swagger에는 특정 상품 기준 유사 상품 조회 API가 없다. 아래는 화면 연동에 필요한
최소 계약 제안이며, endpoint와 선별 정책 모두 `BE 확인 필요`이다.

```http
GET /api/products/{productId}/similar
```

응답 후보:

```json
{
  "success": true,
  "data": [
    {
      "id": 12,
      "title": "90s 오버핏 워싱 데님 재킷",
      "price": 29000,
      "thumbnailUrl": "https://...",
      "saleType": "DIRECT_SALE",
      "saleStatus": "ON_SALE"
    }
  ],
  "error": null
}
```

필수 필드:

| 필드 | 용도 |
| --- | --- |
| `id` | 상품 상세 `/products/{id}` 이동 |
| `title` | 점 선택 후 상품명 표시 |
| `price` | 가격 축 위치와 가격 표시 |
| `thumbnailUrl` | 추후 선택 정보에 이미지가 필요한 경우 사용 |
| `saleType`, `saleStatus` | 구매 가능한 상품만 노출하고 가격 의미를 구분 |

유사도 점수는 서버 내부 선별에는 사용할 수 있지만 현재 화면에는 표시하지 않는다.

## 현재 FE 처리

- `ProductDetailViewData.similarProducts`는 `Mock 전용` view model이다.
- 상품 점 선택과 `/products/{productId}` 이동은 FE에서 확인할 수 있다.
- 실제 API가 추가되면 `productDetailApi.ts`에서 응답을 view model로 매핑한다.
- 실제 API 연동 전까지 mock 데이터를 Swagger 응답이라고 설명하지 않는다.
