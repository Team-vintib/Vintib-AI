eck# HOME 홈 화면 API 응답 계약 확인 요청

- 요청자 파트: FE
- 대상 파트: BE

## 배경/이유

FE 홈 화면은 현재 `HomeViewData` view model과 mock adapter(`FE/src/domains/home/api/homeViewApi.ts`)로 동작합니다. 실제 서비스 데이터로 전환하려면 BE 응답 계약과 API 제공 방식이 확정되어야 하므로, 아래 필드와 엔드포인트 구성 가능 여부 확인을 요청합니다.

## 관련 기능/Jira

- `S15P11A108-283` 홈 페이지 기본 레이아웃 구현
- `S15P11A108-287` 홈 화면 Mock 데이터 렌더링 및 반응형 구현
- `S15P11A108-284` 진행 중·예약 라이브 카드 및 목록 UI 구현
- `S15P11A108-285` 상시 판매·경매 예정 상품 카드 및 목록 UI 구현
- `S15P11A108-286` 홈 콘텐츠 UI 구현
- `S15P11A108-396` 로그인 홈 섹션 레이아웃 구현
- `S15P11A108-398` 비로그인 홈 진입 화면 구현

## 현재 FE view model

FE는 현재 아래 구조로 화면을 렌더링합니다. API 계약 확정 전 임시 구조이며, BE 응답이 정리되면 adapter에서 매핑할 예정입니다.

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

- `id`
- `status`: `LIVE` 또는 `SCHEDULED`
- `title`
- `thumbnailUrl`
- `hostName`
- `scheduledAt`: 예약 라이브에서 사용
- `startedAt`: 진행 중 라이브에서 사용
- `scheduledProductCount`: 예약 라이브 예정 상품 수
- `viewerCount`: 진행 중 라이브 시청자 수를 제공할 수 있으면 사용 가능
- `reservationCount`: 예약 라이브 알림/예약 수를 제공할 수 있으면 사용 가능
- `categoryName`: 카테고리 노출이 가능하면 사용 가능

### 상품 카드

- `id`
- `title`
- `saleType`: `DIRECT_SALE` 또는 `AUCTION`
- `saleStatus`: `ON_SALE` 또는 `AUCTION_SCHEDULED`
- `primaryImageUrl`
- `sellerName`
- `price`
- `startingBid`: 경매 상품에서 사용
- `auctionStartsAt`: 경매 예정 시각 제공 가능하면 사용 가능
- `brandName`: 브랜드 제공 가능하면 사용
- `categoryName`: 카테고리 제공 가능하면 사용
- `isWished`: 로그인 회원의 찜 상태 제공 가능하면 사용

### 로그인 홈 전용 팔로잉 판매자 카드

- `id`
- `liveId`
- `name`
- `profileImageUrl`
- `coverImageUrl`
- `specialty`
- `followerCount`
- `newProductCount`
- `liveStatus`: `LIVE` 또는 `SCHEDULED`
- `liveTitle`
- `liveAt`

### 추천 상품

상품 카드 필드에 더해 아래 값을 제공할 수 있으면 사용합니다.

- `recommendationReason`

## 요청 내용

1. HOME 전용 집계 API가 필요한지, 기존 라이브/상품/팔로잉 API 조합으로 처리하는 것이 적절한지 판단 부탁드립니다.
2. 위 후보 필드 중 BE에서 제공 가능한 필드와 제공하지 않을 필드를 구분해 주세요.
3. `viewerCount`, `reservationCount`, `isWished`, `followerCount`처럼 집계/회원별 상태가 필요한 값이 HOME 응답에서 바로 제공 가능한지 확인 부탁드립니다.
4. 비로그인 홈과 로그인 홈을 같은 응답으로 처리할지, 인증 여부에 따라 다른 응답을 제공할지 확인 부탁드립니다.
5. 각 섹션의 기본 노출 개수와 정렬 기준을 정해 주세요. FE 현재 mock은 섹션당 2~3개 카드 기준입니다.
6. 응답이 빈 배열일 수 있는 섹션을 알려 주세요. FE는 각 섹션 empty 상태를 이미 처리할 수 있습니다.

## FE 반영 예정

- BE 계약 확정 전까지는 `homeViewApi.ts`에서 mock 데이터를 반환합니다.
- BE 계약 확정 후 `homeViewApi.ts` 내부를 HTTP 호출과 `HomeViewData` 매핑 로직으로 교체합니다.
- 화면 컴포넌트(`GuestHome`, `MemberHome`)는 API 응답에 직접 묶지 않고 `HomeViewData`만 받도록 유지합니다.
