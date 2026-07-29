# HOME 홈 카드 응답 필드 보강 요청

## 요청자 파트 / 대상 파트

- 요청자 파트: FE
- 대상 파트: BE

## 배경/이유

FE 홈 화면은 현재 `GET /api/home`과 `GET /api/home/following`을 연결해 GuestHome/MemberHome에 표시하고 있습니다. 다만 BE 홈 응답이 아직 mock 중심이고 카드 표시용 일부 필드가 없어, FE에서 임시 기본값 또는 mock 보조값을 사용하고 있습니다.

홈 화면을 실제 DB 기준으로 완전히 표시하려면 BE 홈 응답에서 아래 카드 필드를 추가로 제공해야 합니다.

## 현재 FE 연동 상태

### 사용 중인 API

- `GET /api/home`
  - 비회원/회원 공통 홈 콘텐츠
  - FE에서는 `skipAuth`로 공개 호출합니다.
- `GET /api/home/following`
  - 로그인 회원 팔로잉 기반 콘텐츠
  - 실패 시 FE는 홈 전체 실패로 처리하지 않고 팔로잉 보강만 생략합니다.

### 현재 FE 매핑

- `liveNow`, `scheduledLives`는 `LiveCard`로 렌더링합니다.
- `onSaleProducts`, `upcomingAuctionProducts`는 `ProductCard`로 렌더링합니다.
- `/home/following.products`는 임시로 MemberHome의 `recommendedProducts`에 제한 매핑합니다.
- BE 미제공 필드는 FE mock 또는 기본값을 사용 중입니다.

## 요청 내용

### 1. `GET /api/home` 응답 구조 유지 및 mock 제거

현재 구조는 FE에서 사용 중이므로 유지 요청드립니다.

```ts
{
  liveNow: LiveCard[]
  scheduledLives: LiveCard[]
  onSaleProducts: ProductCard[]
  upcomingAuctionProducts: ProductCard[]
}
```

향후 `HomeService`의 mock 조립부를 실제 상품/라이브 DB 조회로 교체해 주세요.

### 2. 라이브 카드 응답 필드

현재 BE 응답에 있는 필드:

```ts
liveId: number
title: string
hostNickname: string
thumbnailUrl: string
broadcastStatus: 'LIVE' | 'SCHEDULED'
scheduledAt: string | null
viewerCount: number | null
productCount: number | null
```

추가 요청 필드:

```ts
startedAt?: string
reservationCount?: number
categoryName?: string
```

필드별 필요 이유:

| 필드 | 필요 이유 |
| --- | --- |
| `liveId` | 카드 key 및 `/lives/{id}` 이동 |
| `title` | 라이브 카드 제목 |
| `hostNickname` | `판매자 {hostNickname}` 표시 |
| `thumbnailUrl` | 카드 이미지. 실제 접근 가능한 URL 필요 |
| `broadcastStatus` | LIVE/예약 구분 |
| `scheduledAt` | 예약 라이브 일시 표시 |
| `startedAt` | 진행 중 라이브 시작 시간 표시. 현재 없어서 FE에서 `일정 확인` fallback 발생 |
| `viewerCount` | 진행 중 라이브 보조 정보 표시 가능 |
| `productCount` | 연결/예정 상품 수 표시 |
| `reservationCount` | 예약 라이브 알림/예약 수 표시 가능 |
| `categoryName` | 라이브 카테고리 표시 필요 시 사용 |

### 3. 상품 카드 응답 필드

현재 BE 응답에 있는 필드:

```ts
productId: number
name: string
brand: string
thumbnailUrl: string
sellType: 'NORMAL' | 'AUCTION_SCHEDULED'
sellStatus: 'ON_SALE' | 'RESERVED' | 'SOLD_OUT'
price: number | null
auctionScheduled: boolean
```

추가 요청 필드:

```ts
sellerName: string
categoryName?: string
isWished?: boolean
startingBid?: number
auctionStartsAt?: string
```

필드별 필요 이유:

| 필드 | 필요 이유 |
| --- | --- |
| `productId` | 카드 key 및 `/products/{id}` 이동 |
| `name` | 상품 카드 제목 |
| `brand` | 브랜드 표시 |
| `thumbnailUrl` | 카드 이미지. 실제 접근 가능한 URL 필요 |
| `sellType` | 상시 판매/경매 예정 구분 |
| `sellStatus` | 판매중/예약/품절 등 상태 표시 |
| `price` | 상시 판매 상품 가격 표시 |
| `auctionScheduled` | 경매 예정 badge 및 경매 카드 구분 |
| `sellerName` | `판매자 {sellerName}` 표시. 현재 FE는 `판매자 정보 확인 중` 기본값 사용 |
| `categoryName` | 상품 카테고리 표시 |
| `isWished` | 로그인 회원 찜 상태 표시 필요 시 사용 |
| `startingBid` | 경매 예정 상품 시작가 표시. 현재 없어서 `시작가 미정` 표시 |
| `auctionStartsAt` | 경매 시작 예정 시간 표시 |

### 4. `GET /api/home/following` 응답 보강

현재 BE 응답:

```ts
{
  empty: boolean
  lives: LiveCard[]
  products: ProductCard[]
}
```

MemberHome의 `내가 팔로우한 판매자` 섹션을 실제 데이터로 표시하려면 아래 구조가 추가로 필요합니다.

```ts
followedSellers: FollowedSellerCard[]
```

필요 필드:

```ts
sellerId: number
sellerName: string
profileImageUrl: string
coverImageUrl: string
followerCount: number
newProductCount: number
liveId?: number
liveStatus?: 'LIVE' | 'SCHEDULED'
liveTitle?: string
liveAt?: string
```

필드별 필요 이유:

| 필드 | 필요 이유 |
| --- | --- |
| `sellerId` | 판매자 카드 key |
| `sellerName` | 판매자명 표시 |
| `profileImageUrl` | 판매자 아바타 |
| `coverImageUrl` | 판매자 카드 커버 이미지 |
| `followerCount` | 팔로워 수 표시 |
| `newProductCount` | 판매 상품 수 표시 |
| `liveId` | 라이브 이동 |
| `liveStatus` | LIVE/예약 상태 표시 |
| `liveTitle` | 판매자 진행/예약 라이브 제목 |
| `liveAt` | 라이브 시작/예약 일시 |

참고: 기존 FE mock에는 `specialty`가 있었지만 화면에서 제거했으므로 BE 응답에 필요하지 않습니다.

### 5. 추천 상품과 팔로잉 상품 구분 필요

현재 FE는 `/home/following.products`를 MemberHome의 `recommendedProducts`로 임시 표시합니다. 실제 서비스에서는 아래 중 하나로 계약을 확정해 주세요.

- `following.products`: 팔로우한 판매자의 상품
- `recommendedProducts`: 사용자 취향 추천 상품

추천 상품으로 제공한다면 선택 필드로 아래 값을 받을 수 있습니다.

```ts
recommendationReason?: string
```

### 6. 콘텐츠 카드/배너 처리 방식 확인

GuestHome/MemberHome 하단 콘텐츠 카드는 현재 FE 상수로 유지 중입니다.

```ts
contentCards: {
  id: number
  title: string
  description: string
  imageUrl: string
  ctaLabel: string
  targetPath: string
  audience: 'guest' | 'member' | 'all'
}[]
```

운영 배너/홈 콘텐츠를 BE에서 관리할 계획이면 `/api/home` 응답에 포함하거나 별도 배너 API 제공 여부를 확인 부탁드립니다. BE 관리 계획이 없다면 FE 상수로 유지하겠습니다.

## 관련 FE 파일

- `FE/src/domains/home/api/homeViewApi.ts`
- `FE/src/domains/home/types/homeView.types.ts`
- `FE/src/domains/home/components/GuestHome.vue`
- `FE/src/domains/home/components/MemberHome.vue`
- `FE/src/domains/home/components/LiveCard.vue`
- `FE/src/domains/home/components/ProductCard.vue`

## FE 임시 처리 현황

- `sellerName` 미제공 → `판매자 정보 확인 중` 기본값 사용
- 경매 예정 상품 `price: null`, `startingBid` 미제공 → `시작가 미정` 표시
- `startedAt` 미제공 → 진행 중 라이브 시작 시간 표시 불가
- `followedSellers` 미제공 → FE mock 유지
- `contentCards` 미제공 → FE 상수 유지
- BE mock 이미지 `cdn.example.com`은 실제 이미지 서버가 아니므로 콘솔에 이미지 로드 실패가 발생할 수 있음. 실제 접근 가능한 이미지 URL이 들어오면 해결됩니다.
