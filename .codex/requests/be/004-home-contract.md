# 홈 도메인 API 계약 보완 요청

## 요청자 파트 / 대상 파트

- 요청자: FE
- 대상: BE

## 배경/이유

FE 홈 화면은 실제 `/api/home`, `/api/home/following`에 일부 연동되어 있다. BE 홈 구현은 현재 mock 응답 중심이고 카드 표시용 일부 필드가 부족하므로, 홈 도메인 계약을 한 문서로 정리한다.

기존 `006-home-api-contract.md`, `009-home-card-response-fields.md`를 이 문서로 병합한다.

## 현재 BE에서 그대로 사용할 수 있는 홈 계약

| 기능 | Method | Endpoint | 인증 | 현재 BE 구현 |
| --- | --- | --- | --- | --- |
| 홈 콘텐츠 조회 | `GET` | `/api/home` | 선택/불필요 | 구현됨, 현재 mock 응답 |
| 팔로잉 콘텐츠 조회 | `GET` | `/api/home/following` | 필요 | 구현됨, 현재 mock 응답 |

현재 홈 응답 DTO:

```json
{
  "liveNow": [],
  "scheduledLives": [],
  "onSaleProducts": [],
  "upcomingAuctionProducts": []
}
```

현재 `LiveCardResponse` 필드:

| 필드 | 타입 |
| --- | --- |
| `liveId` | number |
| `title` | string |
| `hostNickname` | string |
| `thumbnailUrl` | string |
| `broadcastStatus` | `LIVE`, `SCHEDULED` |
| `scheduledAt` | string/null |
| `viewerCount` | number/null |
| `productCount` | number/null |

현재 `ProductCardResponse` 필드:

| 필드 | 타입 |
| --- | --- |
| `productId` | number |
| `name` | string |
| `brand` | string |
| `thumbnailUrl` | string |
| `sellType` | `NORMAL`, `AUCTION_SCHEDULED` |
| `sellStatus` | `ON_SALE`, `RESERVED`, `SOLD_OUT` |
| `price` | number/null |
| `auctionScheduled` | boolean |

## 홈 필수 보완 요청

FE 홈 화면은 아래 필드를 추가로 사용한다. BE가 실데이터로 전환할 때 응답 보강을 요청한다.

### 라이브 카드 추가 필드

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `hostId` | number | 권장 | 판매자/호스트 상세 이동용 |
| `startedAt` | string/null | 선택 | 진행 중 방송 시작 시각 |
| `reservationCount` | number/null | 선택 | 예약 방송 알림/예약 수 |
| `categoryId` | number/null | 선택 | 카테고리 필터/표시용 |
| `categoryName` | string/null | 선택 | 카드 표시용 |

### 상품 카드 추가 필드

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `sellerId` | number | 권장 | 판매자 상세 이동용 |
| `sellerName` | string | 필수 | 현재 FE는 fallback 사용 중 |
| `categoryId` | number/null | 선택 | 카테고리 섹션용 |
| `categoryName` | string/null | 선택 | 카드 표시용 |
| `isWished` | boolean | 선택 | 로그인 사용자 기준 찜 여부, 비로그인 false |
| `startingBid` | number/null | 경매 상품 | 경매 예정 시작가 |
| `auctionStartsAt` | string/null | 경매 상품 | 예정 경매 시작 시각 |

현재 FE는 `sellerName`과 `isWished`를 임시값으로 처리한다. BE에서 붙일 수 있는 기존 필드는 그대로 쓰고 위 필드만 추가 보강하면 된다.

## 카테고리별 상품 섹션 요청

현재 FE의 `카테고리별 상품` 섹션은 `homeMockData.categoryProductSections`를 사용한다. BE 실데이터로 전환하려면 `GET /api/home` 응답에 카테고리별 상품 섹션을 추가하거나, 별도 endpoint를 제공해야 한다.

권장 응답 필드:

```json
{
  "categoryProductSections": [
    {
      "categoryId": "outer",
      "categoryName": "아우터",
      "title": "아우터",
      "products": []
    }
  ]
}
```

`products`는 기존 `ProductCardResponse`를 재사용하되, 카드 표시 품질을 위해 `sellerName`, `categoryName`, `isWished` 보강이 필요하다.

## 팔로잉 홈 응답 보강 요청

현재 FE는 로그인 상태에서만 `GET /api/home/following`을 호출한다. 이 요청이 실패하면 홈 전체를 실패 처리하지 않고 공개 홈 데이터와 FE 보조값으로 화면을 유지한다.

실데이터 전환 시 HOME-002 요구사항을 제대로 표시하려면 아래 구조 보강이 필요하다.

- `empty`: 팔로잉 기반 콘텐츠가 없는지 여부
- `lives`: 팔로우한 판매자/회원의 라이브 목록. 현재 FE는 이 값을 라이브 섹션에 섞지 않고, 추후 `followedSellers` 카드 구성에 사용할 예정
- `products`: 팔로우한 판매자/회원의 상품 목록
- `followedSellers`: 팔로우한 판매자 카드 목록. 현재 FE는 mock 유지 중
- `recommendedProducts` 또는 추천 회원/상품 대체 섹션. `empty=true`일 때 표시할 콘텐츠

`lives`, `products`는 HOME-001의 카드 DTO를 재사용해도 된다. 단, 판매자 카드와 추천/대체 섹션은 현재 BE 응답에 없어서 FE가 완전한 HOME-002 화면으로 전환하지 못한다.

## Mock 이미지 리소스 요청

BE mock 응답의 `thumbnailUrl`은 현재 `https://cdn.example.com/...` 형태라 브라우저에서 실제 이미지로 확인하기 어렵다. 첨부된 placeholder 이미지를 BE 정적 리소스로 두고 mock 응답에서 같은 URL을 재사용하는 방식을 요청한다.

권장 위치:

- `BE/src/main/resources/static/mock/home/product-placeholder.png`

권장 응답 URL:

- `/mock/home/product-placeholder.png`

Spring Security에서 정적 mock 이미지를 막지 않도록 `/mock/**`는 `permitAll`에 추가가 필요하다.

## 페이지 응답 규격 정합성 요청

현재 BE `PageResponse<T>`는 아래 구조다.

```json
{
  "content": [],
  "page": 0,
  "size": 20,
  "totalElements": 0,
  "totalPages": 0,
  "hasNext": false
}
```

현재 FE 공통 타입은 아래 구조를 기대한다.

```json
{
  "items": [],
  "meta": {
    "page": 1,
    "size": 20,
    "totalElements": 0,
    "totalPages": 0
  }
}
```

BE 전체 페이지 응답을 바꾸지 않는다면 FE가 adapter에서 `content -> items`, 나머지 필드 -> `meta`로 매핑할 수 있다. 다만 신규 API 문서에는 실제 BE 응답 구조를 명확히 표기해 달라.

## FE 관련 파일

- `FE/src/domains/home/api/homeViewApi.ts`
- `FE/src/domains/home/types/homeView.types.ts`
- `FE/docs/frontend/api/api-index.md`
