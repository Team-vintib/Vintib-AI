# 상품 도메인 API 계약 보완 요청

## 요청자 파트 / 대상 파트

- 요청자: FE
- 대상: BE

## 배경/이유

BE 상품 API는 기본 상품 생성, 이미지 presigned 업로드, 이미지 등록/수정/삭제, 상시 판매 전환, 상품 목록/상세 조회까지 일부 구현되어 있다. FE 상품 상세와 상품 등록 플로우는 이미지 역할, 상세 표시 필드, 하자/AI 품질 분석, 가격 추천, 경매 연결 정보가 추가로 필요하다. 기존 BE에 붙일 수 있는 것은 그대로 두고 부족한 계약만 정리한다.

기존 `007-product-detail-view-contract.md`, `014-product-registration-api-contract.md`를 이 문서로 병합한다.

## 현재 BE에서 그대로 사용할 수 있는 계약

| 기능 | Method | Endpoint | 인증 | 현재 BE 구현 |
| --- | --- | --- | --- | --- |
| 브랜드 목록 | `GET` | `/api/brands` | 불필요 | 구현됨 |
| 카테고리 목록 | `GET` | `/api/categories` | 불필요 | 구현됨 |
| 상품 생성 | `POST` | `/api/products` | 필요 | 구현됨 |
| 상품 목록 | `GET` | `/api/products` | 필요로 문서화됨 | 구현됨 |
| 상품 상세 | `GET` | `/api/products/{id}` | 선택 | 구현됨 |
| 상시 판매 전환 | `PATCH` | `/api/products/{id}/status` | 필요 | 구현됨 |
| 이미지 업로드 URL 발급 | `POST` | `/api/products/{id}/images/upload-url` | 필요 | 구현됨 |
| 이미지 등록 | `POST` | `/api/products/{id}/images` | 필요 | 구현됨 |
| 이미지 수정 | `PATCH` | `/api/products/{id}/images/{imageId}` | 필요 | 구현됨 |
| 이미지 삭제 | `DELETE` | `/api/products/{id}/images/{imageId}` | 필요 | 구현됨 |

현재 상품 생성 요청:

```json
{
  "title": "빈티지 리바이스 데님 자켓",
  "description": "1990년대 리바이스 데님 자켓, 상태 양호",
  "categoryId": 1,
  "brandId": 1,
  "conditionGrade": "A",
  "sizeLabel": "M"
}
```

현재 상품 상세 응답 주요 필드:

| 필드 | 타입 |
| --- | --- |
| `id` | number |
| `sellerId` | number |
| `sellerNickname` | string |
| `categoryId` | number |
| `brandId` | number |
| `title` | string |
| `description` | string |
| `conditionGrade` | string |
| `sizeLabel` | string |
| `saleType` | `DIRECT_SALE`, `AUCTION` |
| `saleStatus` | `DRAFT`, `ON_SALE`, `AUCTION_SCHEDULED`, `AUCTION_IN_PROGRESS`, `AUCTION_FAILED`, `SOLD`, `PRIVATE` |
| `price` | number/null |
| `images` | `ProductImageResponse[]` |
| `createdAt` | string |
| `updatedAt` | string |

## 1. 상품 등록 요청/응답 계약 확장

FE 상품 등록 플로우는 아래 필드를 저장해야 한다.

```json
{
  "title": "90s 오버핏 데님 재킷",
  "brandId": 1,
  "brandName": "Levi's",
  "categoryId": 1,
  "categoryCode": "outer",
  "color": "indigo",
  "description": "상품 설명",
  "purchasedAt": "1990년대",
  "purchasedCountry": "미국",
  "sizeLabel": "M",
  "material": "면 100%",
  "measurements": {
    "shoulder": 45,
    "length": 68,
    "chest": 54,
    "sleeve": 61
  },
  "conditionGrade": "A",
  "hasDefect": true,
  "sellerDefectDescription": "왼쪽 소매 끝단 마모"
}
```

필드 규칙 확정 요청:

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `title` | string | 필수 | 상품명 |
| `brandId` | number/null | 조건부 | 기존 브랜드 선택 시 사용 |
| `brandName` | string/null | 조건부 | 신규/기타 브랜드 허용 시 사용 |
| `categoryId` | number | 필수 | BE 카테고리 ID |
| `categoryCode` | string/null | 선택 | FE 화면 코드와 매핑할지 확정 |
| `color` | string | 필수 | enum 또는 자유 문자열 정책 확정 |
| `description` | string | 필수 | 상품 설명 |
| `purchasedAt` | string/null | 선택 | 구매 시기 저장 여부 확정 |
| `purchasedCountry` | string/null | 선택 | 구매 국가 저장 여부 확정 |
| `sizeLabel` | string | 필수 | 표시 사이즈 |
| `material` | string/null | 선택 | 소재 |
| `measurements` | object/null | 선택 | cm 기준 단면 실측 JSON |
| `conditionGrade` | `S`, `A`, `B`, `C` | 필수 | 상태 등급 |
| `hasDefect` | boolean | 필수 | 판매자 고지 하자 여부 |
| `sellerDefectDescription` | string/null | 조건부 | `hasDefect=true`이면 필수 여부 확정 |

FE 실측 정책:

| 카테고리 | measurements key |
| --- | --- |
| 아우터/상의 | `shoulder`, `length`, `chest`, `sleeve` |
| 하의 | `waist`, `hip`, `totalLength`, `thigh`, `hem` |
| 원피스 | `shoulder`, `length`, `chest`, `waist`, `sleeveLength`, `hem` |
| 신발 | `size` |
| 액세서리/기타 | 없음 |

## 2. 이미지 역할 및 개수 정책

현재 BE 이미지 등록 요청은 `key`, `sortOrder`, `isPrimary`만 받으며 상품당 최대 10장이다. FE도 이미지 개수 제한은 BE 구현을 따른다. 따라서 상품 사진은 Front View 1장, Back View 1장을 포함해 전체 최대 10장이고, 추가 사진은 최대 8장까지 허용한다.

요청:

- 이미지 요청/응답에 `role` 추가 검토: `FRONT`, `BACK`, `ADDITIONAL`
- Front View/Back View 최소 1장 검증을 BE에서도 할지 확정
- 대표 이미지는 현재 `isPrimary` 유지 가능

이미지 등록 후보:

```json
{
  "key": "product-images/1/abc123.jpg",
  "sortOrder": 0,
  "isPrimary": true,
  "role": "FRONT"
}
```

## 3. 상품 상세 응답 보강

FE 상품 상세 화면에 필요한 추가 필드:

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `brandName` | string | 필수 | 상세 표시명 |
| `categoryName` | string | 필수 | 상세 표시명 |
| `color` | string/null | 선택 | 등록 확장 필드와 동일 |
| `material` | string/null | 선택 | 등록 확장 필드와 동일 |
| `isLiked` | boolean | 필수 | 로그인 사용자 기준 찜 여부, 비로그인 false |
| `seller.followerCount` | number | 필수 | 판매자 정보 |
| `seller.productCount` | number | 필수 | 판매자 정보 |
| `linkedLive` | object/null | 선택 | 연결 라이브 정보 |
| `similarProducts` | array | 선택 | 가격 비교/추천 상품 |
| `sellerDisclosedDefects` | array | 선택 | 판매자 직접 고지 하자 |
| `aiQualityAnalysis` | object | 선택 | AI 품질 분석 결과 |

`saleType`만으로는 상시 판매 상품의 라이브 연결 여부를 판단할 수 없으므로 `linkedLive`를 명시해 달라.

## 4. 상시 판매/경매 등록 흐름

상시 판매는 현재 `PATCH /api/products/{id}/status`로 연결 가능하다.

경매 선택 시 추가 확정 요청:

- 상품 상태를 `AUCTION_SCHEDULED`로 만들 endpoint 필요 여부
- 경매 라이브 미선택 상태로 경매 예정 상품 등록 가능 여부
- 경매 라이브 선택 시 FE가 따라야 할 순서 문서화
  1. 상품 생성
  2. 이미지 등록
  3. 라이브 상품 연결 `POST /api/lives/{liveId}/products`
  4. 경매 조건 설정 `POST /api/lives/{liveId}/auctions`

경매 설정은 현재 BE의 `POST /api/lives/{liveId}/auctions`를 우선 재사용할 수 있다. 다만 상품 상태가 `AUCTION_SCHEDULED`로 반영되는지, 상품 상세/목록에서 경매 시작가가 노출되는지 확인 필요하다.

## 5. AI 품질 검증 저장/조회 계약

FE는 AI 품질 검증 결과를 상품 상세의 AI 분석 결과로 노출해야 한다.

endpoint 후보:

```http
POST /api/products/{id}/quality-inspections
PATCH /api/products/{id}/quality-inspections/{inspectionId}/confirm
GET /api/products/{id}/quality-inspections
```

저장 데이터 후보:

```json
{
  "photoId": 10,
  "status": "CONFIRMED",
  "findings": [
    {
      "labelNumber": 1,
      "description": "소매 끝단 마모 의심",
      "box": {
        "x": 12.5,
        "y": 42.1,
        "width": 18.0,
        "height": 10.4
      },
      "isActualDefect": true
    }
  ],
  "maskedImageUrl": "https://..."
}
```

확정 필요:

- AI 호출 주체가 FE인지 BE인지
- 상태 enum: `NOT_REQUESTED`, `ANALYZING`, `COMPLETED`, `NO_FINDINGS`, `FAILED`
- bounding box 좌표 단위: `%` 또는 pixel
- 사용자가 실제 하자 여부를 수정한 결과 저장 방식
- 상품 상세 조회에 포함할지 별도 endpoint로 조회할지

## 6. AI 가격 추천 API

가격 단계에서 사용할 추천 데이터 조회 endpoint가 필요하다.

```http
POST /api/products/price-recommendations
Authorization: Bearer {accessToken}
Content-Type: application/json
```

요청 후보:

```json
{
  "title": "90s 오버핏 데님 재킷",
  "brandId": 1,
  "categoryId": 1,
  "conditionGrade": "A",
  "sizeLabel": "M",
  "color": "indigo"
}
```

응답 후보:

```json
{
  "buckets": [
    {
      "label": "5~7만",
      "minPrice": 50000,
      "maxPrice": 70000,
      "productCount": 24
    }
  ],
  "recommendedPrices": [
    {
      "grade": "A",
      "price": 92000
    }
  ]
}
```

## FE 관련 파일

- `FE/src/domains/product/pages/ProductRegistrationPage.vue`
- `FE/src/domains/product/api/productRegistrationApi.ts`
- `FE/src/domains/product/types/productRegistration.types.ts`
- `FE/src/domains/product/pages/ProductDetailView.vue`
- `FE/src/domains/product/api/productDetailApi.ts`
- `FE/src/domains/product/types/productDetail.types.ts`
- `FE/docs/frontend/api/product-detail-price-distribution.md`
- `FE/docs/frontend/screens/PROD-001/requirements.md`
- `FE/docs/frontend/screens/PROD-006/requirements.md`

## 7. 상품 API 연동 전 추가 확인 요청

FE에서 다음 작업으로 상품 목록/상세/등록/찜 API를 실제 연동할 예정이다. 현재 BE에 구현된 API 중 바로 붙일 수 있는 부분과 화면 구현상 부족한 부분을 아래 기준으로 추가 확인 요청한다.

### 7.1 상품 목록 조회 계약

현재 `GET /api/products`는 `Pageable`만 받고 최신순 고정으로 동작한다. 상품 목록 화면은 아래 상태를 가지고 있어 query 계약이 필요하다.

| FE 화면 상태 | 요청 query 제안 | 비고 |
| --- | --- | --- |
| 검색어 | `keyword` | 상품명/브랜드명 검색 범위 확인 필요 |
| 카테고리 | `categoryIds` | 다중 선택 가능 여부 확인 필요 |
| 상태 등급 | `conditionGrades` | `S`, `A`, `B`, `C` |
| 판매 방식 | `saleType` | `DIRECT`, `AUCTION`, `ALL` 중 BE enum과 매핑 필요 |
| 가격 범위 | `minPrice`, `maxPrice` | 원 단위 number |
| 정렬 | `sort` | `LATEST`, `PRICE_ASC`, `PRICE_DESC` |
| 페이지 | `page`, `size` | Spring `Pageable` 기준 |

목록 카드에 필요한 응답 필드:

| 필드 | 타입 | 필요 이유 |
| --- | --- | --- |
| `id` | number | 상세 이동 |
| `brandName` | string | 카드 상단 브랜드 표시 |
| `title` | string | 상품명 |
| `price` | number/null | 가격 표시 |
| `conditionGrade` | `S`/`A`/`B`/`C` | 상태 배지 |
| `saleType` | `DIRECT_SALE`/`AUCTION` | 탭/배지 |
| `primaryImageUrl` | string/null | 카드 썸네일 |
| `isWished` | boolean | 로그인 사용자 기준 찜 상태. 비로그인 false |

현재 `ProductResponse`에는 `brandId`만 있고 `brandName`, `primaryImageUrl`, `isWished`가 없어 FE에서 카드 품질이 떨어진다. 목록 응답에 포함 가능 여부 확인을 요청한다.

### 7.2 상품 목록 인증 정책

`ProductController#getProductList`는 Swagger 설명상 `401 인증 필요`와 `bearerAuth`가 붙어 있다. 화면상 상품 목록은 비회원도 볼 수 있는 공개 탐색 화면으로 쓰는 것이 자연스럽다.

요청:

- `GET /api/products`를 비회원 조회 가능으로 열 수 있는지 확인
- 비회원 조회가 가능하다면 `isWished=false`로 응답
- 로그인 사용자가 access token을 보낸 경우에만 `isWished` 계산

### 7.3 상품 상세 화면 필드

현재 상세 UI가 필요로 하는 필드 중 BE `ProductDetailResponse`에 없는 항목:

| 필드 | 타입 | 필요 이유 |
| --- | --- | --- |
| `brandName` | string | 상세 기본 정보 |
| `categoryName` | string | 상세 기본 정보 |
| `color` | string/null | 등록 정보 표시 |
| `material` | string/null | 등록 정보 표시 |
| `measurements` | object/null | 실측 정보 표시 |
| `purchasedAt` | string/null | 빈티지 구매/연식 정보 표시 |
| `purchasedCountry` | string/null | 구매 국가 표시 |
| `isWished` | boolean | 상세 찜 초기 상태 |
| `seller.followerCount` | number | 판매자 요약 |
| `seller.productCount` | number | 판매자 요약 |
| `linkedLive` | object/null | 해당 상품이 예정/진행 라이브에 연결된 경우 표시 |
| `sellerDisclosedDefects` | array | 판매자 고지 하자 |
| `aiQualityAnalysis` | object/null | AI 품질 분석 결과 |
| `similarProducts` 또는 `priceDistribution` | object/array | 유사 상품 가격 분포 |

FE는 우선 BE가 제공하는 기본 상세와 images만 붙이고, 위 항목은 BE 계약이 생기기 전까지 빈 상태 또는 기존 목업 fallback으로 처리할 예정이다.

### 7.4 찜 API와 상품 응답의 관계

찜 생성/삭제 API는 구현되어 있으나 목록/상세 응답에 현재 사용자의 찜 여부가 없다.

요청:

- `GET /api/products`, `GET /api/products/{id}` 응답에 `isWished` 포함 가능 여부 확인
- 어렵다면 `GET /api/users/{userId}/wishes`로 FE가 초기 찜 Set을 구성해도 되는지 확인
- `DELETE /api/users/{userId}/wishes/{id}`의 `{id}`는 찜 PK가 아니라 상품 ID라는 점을 Swagger/문서에 계속 명시

### 7.5 상품 등록 플로우 확정

현재 바로 가능한 직접 판매 등록 흐름:

1. `POST /api/products`로 DRAFT 생성
2. 이미지마다 `POST /api/products/{id}/images/upload-url`
3. 발급받은 presigned URL로 `PUT` 업로드
4. `POST /api/products/{id}/images`로 이미지 등록
5. 직접 판매라면 `PATCH /api/products/{id}/status`로 가격 설정 및 `ON_SALE` 전환

추가 확인 요청:

- `PATCH /api/products/{id}/status`가 직접 판매 전용인지, 다른 상태 전환에도 재사용할 예정인지
- 경매 상품 등록 시 상품 상태를 `AUCTION_SCHEDULED`로 만드는 API 또는 플로우
- `POST /api/lives/{liveId}/products`와 경매 생성 API를 상품 등록 완료 시점에 같이 호출해도 되는지
- 이미지 업로드 중 일부 실패 시 FE가 이미 생성된 DRAFT 상품/이미지를 정리할 수 있는 삭제 API가 필요한지

## 2026-07-31 최신 BE 확인 결과

상품 기본 API는 일부 연동 가능하지만, FE 목록/상세 화면 전체를 mock 없이 대체하기에는 응답 필드와 query가 부족하다.

### 반영 확인

| 항목 | 현재 BE 상태 |
| --- | --- |
| 브랜드/카테고리 조회 | `GET /api/brands`, `GET /api/categories` 구현됨 |
| 상품 생성 | `POST /api/products` 구현됨. 기본 필드만 저장 |
| 직접 판매 전환 | `PATCH /api/products/{id}/status` 구현됨. `price` 필수 |
| 경매 예정 전환 | `PATCH /api/products/{id}/auction-schedule` 추가 구현됨 |
| 상품 목록 | `GET /api/products` 구현됨. Spring `Pageable`, 최신순 고정 |
| 상품 상세 | `GET /api/products/{id}` 구현됨. 비회원 조회 가능 |
| 상품 이미지 | presigned URL 발급, 등록, 수정, 삭제 구현됨 |
| 찜 API | `POST/DELETE/GET /api/users/{userId}/wishes` 구현됨 |

### FE 연동 시 주의

- BE `PageResponse`는 `content/page/size/totalElements/totalPages/hasNext` 구조다. FE 공통 `items/meta` 구조와 다르므로 adapter 변환이 필요하다.
- `GET /api/products`는 현재 검색어, 카테고리, 상태등급, 판매방식, 가격, 정렬 query를 실질적으로 처리하지 않는다. FE 필터 UI와 직접 연결하면 화면과 응답이 불일치한다.
- 목록/상세 응답에는 `brandName`, `categoryName`, `primaryImageUrl`, `isWished`가 없다. FE는 브랜드/카테고리 master 매핑과 이미지 fallback을 유지해야 한다.
- 상세 응답에는 `color`, `material`, `measurements`, `purchasedAt`, `purchasedCountry`, `linkedLive`, `sellerDisclosedDefects`, `aiQualityAnalysis`, `similarProducts`, `priceDistribution`이 없다.
- `DELETE /api/users/{userId}/wishes/{id}`의 `{id}`는 찜 row ID가 아니라 `productId`다.

### 추가 요청

- `GET /api/products` query 계약을 확정하고 구현해 달라: `keyword`, `categoryIds`, `conditionGrades`, `saleType`, `minPrice`, `maxPrice`, `sort`, `page`, `size`.
- 상품 목록 응답에 최소 `brandName`, `categoryName`, `primaryImageUrl`, 로그인 사용자 기준 `isWished`를 포함해 달라. 비회원은 `isWished=false` 또는 `null` 중 하나로 문서화한다.
- 상품 상세 응답에 상세 UI 필드(`brandName`, `categoryName`, `color`, `material`, `measurements`, 판매자 요약, 연결 라이브, 가격분포/유사상품)를 단계적으로 보강해 달라.
- 상품 이미지 `role`(`FRONT`, `BACK`, `ADDITIONAL`) 저장 여부를 확정해 달라.
- AI 품질 분석과 가격 추천 API는 별도 endpoint로 구현 여부와 AI 파트 연동 주체를 확정해 달라.
