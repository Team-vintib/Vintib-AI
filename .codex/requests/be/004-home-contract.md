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
