# S15P11A108-283 홈 화면 API 응답 계약 확인 요청

## 요청 배경

FE의 홈 화면 기본 레이아웃, 비로그인/로그인 홈 섹션, 라이브·상품 카드 UI가 구현되어
현재 `HomeViewData` view model과 mock adapter로 동작한다.

실제 서비스 데이터로 전환하려면 HOME 전용 API 제공 방식과 응답 필드 계약이 확정되어야
하므로 아래 FE 선행 구조에 맞춘 BE 계약 확인을 요청한다.

## 요청 API

HOME 전용 집계 API가 필요하다면 아래 형태를 우선 후보로 요청한다.

```http
GET /api/home
Authorization: Bearer {accessToken} 선택
```

로그인 회원의 팔로잉 기반 홈 콘텐츠를 별도 조회해야 한다면 아래 형태를 우선 후보로 요청한다.

```http
GET /api/home/following
Authorization: Bearer {accessToken}
```

- 비회원 홈은 인증 없이 접근 가능해야 한다.
- 로그인 홈은 인증 여부에 따라 회원별 상태와 팔로잉 콘텐츠를 포함할 수 있어야 한다.
- 단일 API로 비회원/로그인 홈을 모두 처리할지, 공통 홈과 팔로잉 홈을 분리할지 확정이 필요하다.

## 현재 FE view model

FE는 현재 아래 구조로 화면을 렌더링한다. API 계약 확정 후 adapter에서 BE 응답을
`HomeViewData`로 매핑할 예정이다.

```ts
interface HomeViewData {
  liveNow: HomeLiveCardItem[]
  scheduledLives: HomeLiveCardItem[]
  directSaleProducts: HomeProductCardItem[]
  upcomingAuctionProducts: HomeProductCardItem[]
  followedSellers: HomeFollowedSellerItem[]
  recommendedProducts: HomeRecommendedProductItem[]
  contentCards: HomeContentCardItem[]
}
```

## 필요한 응답 후보

### 라이브 카드

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | number/string | 필수 | 라이브 상세 이동과 카드 key에 사용 |
| `status` | enum | 필수 | `LIVE`, `SCHEDULED` |
| `title` | string | 필수 | 라이브 제목 |
| `thumbnailUrl` | string | 필수 | 접근 가능한 대표 이미지 URL |
| `hostName` | string | 필수 | 판매자/호스트 표시명 |
| `scheduledAt` | string/null | 예약 라이브 필수 | ISO 8601 일시 |
| `startedAt` | string/null | 진행 중 라이브 요청 | ISO 8601 일시 |
| `scheduledProductCount` | number/null | 선택 | 예약 라이브 예정 상품 수 |
| `viewerCount` | number/null | 선택 | 진행 중 라이브 시청자 수 |
| `reservationCount` | number/null | 선택 | 예약/알림 수 |
| `categoryName` | string/null | 선택 | 카테고리 노출 가능 시 사용 |

### 상품 카드

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | number/string | 필수 | 상품 상세 이동과 카드 key에 사용 |
| `title` | string | 필수 | 상품명 |
| `saleType` | enum | 필수 | `DIRECT_SALE`, `AUCTION` |
| `saleStatus` | enum | 필수 | `ON_SALE`, `AUCTION_SCHEDULED` |
| `primaryImageUrl` | string | 필수 | 접근 가능한 대표 이미지 URL |
| `sellerName` | string | 필수 | 판매자 표시명 |
| `price` | number/null | 상시 판매 필수 | 판매가 |
| `startingBid` | number/null | 경매 상품 요청 | 경매 시작가 |
| `auctionStartsAt` | string/null | 선택 | 경매 예정 시각 |
| `brandName` | string/null | 선택 | 브랜드명 |
| `categoryName` | string/null | 선택 | 카테고리명 |
| `isWished` | boolean/null | 로그인 시 선택 | 회원별 찜 상태 |

### 로그인 홈 전용 팔로잉 판매자 카드

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | number/string | 필수 | 판매자 카드 key |
| `liveId` | number/string/null | 선택 | 진행/예약 라이브 이동 |
| `name` | string | 필수 | 판매자 표시명 |
| `profileImageUrl` | string | 필수 | 접근 가능한 프로필 이미지 URL |
| `coverImageUrl` | string | 필수 | 접근 가능한 커버 이미지 URL |
| `specialty` | string/null | 선택 | 판매자 전문 분야 또는 소개 |
| `followerCount` | number/null | 선택 | 팔로워 수 |
| `newProductCount` | number/null | 선택 | 신규/판매 상품 수 |
| `liveStatus` | enum/null | 선택 | `LIVE`, `SCHEDULED` |
| `liveTitle` | string/null | 선택 | 라이브 제목 |
| `liveAt` | string/null | 선택 | 라이브 시작 또는 예약 일시 |

### 추천 상품

상품 카드 필드에 더해 아래 값을 제공할 수 있으면 사용한다.

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `recommendationReason` | string/null | 선택 | 추천 이유. 현재 카드에는 직접 표시하지 않음 |

## 응답 규격

성공:

```http
200 OK
```

```json
{
  "success": true,
  "data": {
    "liveNow": [],
    "scheduledLives": [],
    "directSaleProducts": [],
    "upcomingAuctionProducts": [],
    "followedSellers": [],
    "recommendedProducts": [],
    "contentCards": []
  },
  "error": null
}
```

- 각 섹션은 빈 배열을 허용한다.
- 섹션별 기본 노출 개수와 정렬 기준을 BE에서 확정해 공유해야 한다.
- `viewerCount`, `reservationCount`, `isWished`, `followerCount`처럼 집계/회원별 상태가 필요한 값은 제공 가능 여부 확인이 필요하다.

## FE 처리

- BE 계약 확정 전까지 `homeViewApi.ts`에서 mock 데이터를 반환한다.
- BE 계약 확정 후 `homeViewApi.ts`를 HTTP 호출과 `HomeViewData` 매핑 로직으로 교체한다.
- 화면 컴포넌트(`GuestHome`, `MemberHome`)는 API 응답 DTO에 직접 묶지 않고 `HomeViewData`만 받도록 유지한다.
- 비회원과 로그인 회원의 응답 차이는 adapter에서 흡수한다.
- 빈 배열 섹션은 FE에서 섹션 숨김 또는 empty 상태로 처리할 수 있다.

## BE 확인 필요

1. HOME 전용 집계 API가 필요한지, 기존 라이브/상품/팔로잉 API 조합으로 처리하는 것이 적절한지 확정해야 한다.
2. 비회원 홈과 로그인 홈을 같은 응답으로 처리할지, 인증 여부에 따라 다른 응답을 제공할지 확정해야 한다.
3. 후보 필드 중 BE에서 제공 가능한 필드와 제공하지 않을 필드를 구분해야 한다.
4. 집계값과 회원별 상태값을 HOME 응답에서 바로 제공할 수 있는지 확인해야 한다.
5. 각 섹션의 기본 노출 개수와 정렬 기준을 확정해야 한다.
6. 구현 후 Swagger에 HOME 응답 DTO, 인증 정책, 빈 배열 가능 섹션을 문서화해야 한다.

## FE 관련 파일

- `FE/src/domains/home/api/homeViewApi.ts`
- `FE/src/domains/home/types/homeView.types.ts`
- `FE/src/domains/home/components/GuestHome.vue`
- `FE/src/domains/home/components/MemberHome.vue`
- `FE/src/domains/home/components/LiveCard.vue`
- `FE/src/domains/home/components/ProductCard.vue`
