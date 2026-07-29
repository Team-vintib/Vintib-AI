# S15P11A108-396 홈 카드 응답 필드 보강 요청

## 요청 배경

FE 홈 화면은 `GET /api/home`과 `GET /api/home/following`을 연결해 GuestHome/MemberHome에
표시하고 있다. 현재 BE 홈 응답은 mock 중심이고 카드 표시용 일부 필드가 없어 FE에서 임시
기본값 또는 mock 보조값을 사용 중이다.

홈 화면을 실제 DB 기준으로 표시하려면 BE 홈 응답에 아래 카드 필드 보강이 필요하다.

## 요청 API

```http
GET /api/home
Authorization: Bearer {accessToken} 선택
```

```http
GET /api/home/following
Authorization: Bearer {accessToken}
```

- `GET /api/home`은 비회원 접근 가능해야 한다.
- `GET /api/home/following`은 로그인 회원 전용이며, 실패해도 홈 전체를 실패 처리하지 않도록 FE가 분리 호출한다.
- 공통 푸터의 팀 정보, 문의 번호, 운영 시간, 공지/약관/고객센터 링크는 FE 정적 UI로 처리하므로 현재 BE 응답이나 API가 필요하지 않다.

## 현재 FE 임시 처리

| 항목 | 현재 처리 | 이유 |
| --- | --- | --- |
| 상품 `sellerName` | `판매자 정보 확인 중` | BE 홈 상품 응답에 판매자명 없음 |
| 경매 상품 `startingBid` | `시작가 미정` | BE 홈 상품 응답에 경매 시작가 없음 |
| 라이브 `startedAt` | `일정 확인` fallback | BE 홈 라이브 응답에 진행 중 라이브 시작 시간 없음 |
| `followedSellers` | FE mock 유지 | BE `/home/following` 응답에 팔로잉 판매자 카드 없음 |
| `categoryProductSections` | FE mock 유지 | BE `/home` 응답에 카테고리별 상품 묶음 없음 |
| 이미지 URL | 카드 `onerror` fallback | BE mock 이미지가 `cdn.example.com`이라 실제 접근 불가 |

## 요청 1. `GET /api/home` 응답 구조

```ts
interface HomeContentResponse {
  liveNow: HomeLiveCardResponse[]
  scheduledLives: HomeLiveCardResponse[]
  onSaleProducts: HomeProductCardResponse[]
  upcomingAuctionProducts: HomeProductCardResponse[]
  categoryProductSections?: HomeCategoryProductSectionResponse[]
}
```

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `liveNow` | `HomeLiveCardResponse[]` | 필수 | 진행 중 라이브 섹션 |
| `scheduledLives` | `HomeLiveCardResponse[]` | 필수 | 예약 라이브 섹션 |
| `onSaleProducts` | `HomeProductCardResponse[]` | 필수 | 판매 상품 섹션 |
| `upcomingAuctionProducts` | `HomeProductCardResponse[]` | 필수 | 경매 예정 상품 섹션 |
| `categoryProductSections` | `HomeCategoryProductSectionResponse[]` | 요청 | 카테고리별 상품 탭 섹션 |

## 요청 2. 라이브 카드 응답

```ts
interface HomeLiveCardResponse {
  liveId: number
  title: string
  hostNickname: string
  thumbnailUrl: string
  broadcastStatus: 'LIVE' | 'SCHEDULED'
  scheduledAt: string | null
  startedAt: string | null
  viewerCount: number | null
  productCount: number | null
}
```

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `liveId` | number | 필수 | 카드 key, `/lives/{liveId}` 경로 생성 |
| `title` | string | 필수 | 라이브 제목 |
| `hostNickname` | string | 필수 | 판매자/호스트명 |
| `thumbnailUrl` | string | 필수 | 접근 가능한 대표 이미지 URL |
| `broadcastStatus` | enum | 필수 | `LIVE`, `SCHEDULED` |
| `scheduledAt` | string/null | 예약 라이브 필수 | 예약 라이브 일시 |
| `startedAt` | string/null | 진행 중 라이브 요청 | 진행 중 라이브 시작 시간 |
| `viewerCount` | number/null | 선택 | 현재 시청자 수 |
| `productCount` | number/null | 선택 | 연결/예정 상품 수 |

- `broadcastStatus === 'LIVE'`이고 `startedAt`이 있으면 FE는 시작 시간을 표시한다.
- `startedAt`이 없다면 FE가 `viewerCount` 또는 `productCount`를 대신 표시하도록 조정할 수 있다.
- `broadcastStatus === 'SCHEDULED'`이면 FE는 `scheduledAt`과 `productCount`를 표시한다.

## 요청 3. 상품 카드 응답

```ts
interface HomeProductCardResponse {
  productId: number
  name: string
  brand: string
  thumbnailUrl: string
  sellType: 'NORMAL' | 'AUCTION_SCHEDULED'
  sellStatus: 'ON_SALE' | 'RESERVED' | 'SOLD_OUT'
  price: number | null
  auctionScheduled: boolean
  sellerName: string
  categoryName: string | null
  isWished: boolean | null
  startingBid: number | null
  auctionStartsAt: string | null
}
```

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `productId` | number | 필수 | 카드 key, `/products/{productId}` 경로 생성 |
| `name` | string | 필수 | 상품명 |
| `brand` | string | 필수 | 브랜드명 |
| `thumbnailUrl` | string | 필수 | 접근 가능한 대표 이미지 URL |
| `sellType` | enum | 필수 | `NORMAL`, `AUCTION_SCHEDULED` |
| `sellStatus` | enum | 필수 | `ON_SALE`, `RESERVED`, `SOLD_OUT` |
| `price` | number/null | 상시 판매 필수 | 판매가 |
| `auctionScheduled` | boolean | 필수 | 경매 예정 여부 |
| `sellerName` | string | 요청 | 판매자명 |
| `categoryName` | string/null | 요청 | 카테고리명 |
| `isWished` | boolean/null | 로그인 시 요청 | 회원별 찜 상태 |
| `startingBid` | number/null | 경매 상품 요청 | 경매 시작가 |
| `auctionStartsAt` | string/null | 선택 | 경매 시작 예정 시각 |

### FE 매핑 규칙

| BE 필드 | FE 필드 | 매핑 |
| --- | --- | --- |
| `productId` | `id` | 그대로 |
| `name` | `title` | 그대로 |
| `brand` | `brandName` | 그대로 |
| `thumbnailUrl` | `primaryImageUrl` | 그대로 |
| `sellType === 'NORMAL'` | `saleType` | `DIRECT_SALE` |
| `sellType === 'AUCTION_SCHEDULED'` | `saleType` | `AUCTION` |
| `sellStatus` | `saleStatus` | 그대로 |
| `price` | `price` | `null`이면 FE `undefined` |
| `auctionScheduled` | `saleStatus` 보정 | `true`면 `AUCTION_SCHEDULED` |
| `sellerName` | `sellerName` | 없으면 `판매자 정보 확인 중` |
| `startingBid` | `startingBid` | 경매 시작가 표시 |
| `auctionStartsAt` | `auctionStartsAt` | 경매 예정 시각 표시 후보 |

## 요청 4. `GET /api/home/following` 응답 구조

```ts
interface FollowingContentResponse {
  empty: boolean
  lives: HomeLiveCardResponse[]
  products: HomeProductCardResponse[]
  followedSellers: HomeFollowedSellerResponse[]
}
```

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `empty` | boolean | 필수 | 팔로잉 콘텐츠 없음 상태 판단 |
| `lives` | `HomeLiveCardResponse[]` | 필수 | 팔로우한 판매자의 라이브 |
| `products` | `HomeProductCardResponse[]` | 필수 | 팔로우한 판매자의 상품 또는 추천 상품 후보 |
| `followedSellers` | `HomeFollowedSellerResponse[]` | 요청 | 내가 팔로우한 판매자 섹션 |

## 요청 5. 팔로잉 판매자 카드 응답

```ts
interface HomeFollowedSellerResponse {
  sellerId: number
  sellerName: string
  profileImageUrl: string
  coverImageUrl: string
  followerCount: number
  productCount: number
  liveId: number | null
  liveStatus: 'LIVE' | 'SCHEDULED' | null
  liveTitle: string | null
  liveAt: string | null
}
```

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `sellerId` | number | 필수 | 판매자 카드 key |
| `sellerName` | string | 필수 | 판매자명 |
| `profileImageUrl` | string | 필수 | 접근 가능한 프로필 이미지 URL |
| `coverImageUrl` | string | 필수 | 접근 가능한 커버 이미지 URL |
| `followerCount` | number | 요청 | 팔로워 수 |
| `productCount` | number | 요청 | 판매 상품 수 |
| `liveId` | number/null | 선택 | `/lives/{liveId}` 경로 생성 |
| `liveStatus` | enum/null | 선택 | `LIVE`, `SCHEDULED` |
| `liveTitle` | string/null | 선택 | 라이브 제목 |
| `liveAt` | string/null | 선택 | 라이브 시작/예약 일시 |

## 요청 6. 카테고리별 상품 섹션 응답

```ts
interface HomeCategoryProductSectionResponse {
  id: string
  title: string
  categoryName: string
  products: HomeProductCardResponse[]
}
```

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | string | 필수 | 탭 key 및 active tab 식별 |
| `title` | string | 필수 | 탭 버튼 표시명 |
| `categoryName` | string | 필수 | 카테고리 식별/표시 |
| `products` | `HomeProductCardResponse[]` | 필수 | 선택된 카테고리 상품 목록 |

- 현재 FE 화면 기준 카테고리 탭은 `아우터`, `상의`, `하의`, `원피스`, `신발`, `액세서리` 6개를 기대한다.
- 각 카테고리의 `products`는 우선 3개 이상 내려오면 현재 카드 그리드에서 표시 가능하다.
- 상품 클릭은 기존과 동일하게 `/products/{productId}`로 이동한다.

## 요청 7. 추천 상품과 팔로잉 상품 구분

현재 FE는 `/home/following.products`를 MemberHome의 `recommendedProducts`로 임시 표시한다.
실제 서비스에서는 아래 중 한 가지로 의미를 확정해야 한다.

1. `products`를 팔로우한 판매자의 상품으로 제공하고 FE 섹션명을 조정한다.
2. `recommendedProducts`를 별도 제공하고 추천 상품으로 표시한다.

추천 상품을 별도 제공한다면 아래 필드를 추가로 사용할 수 있다.

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `recommendationReason` | string/null | 선택 | 추천 이유. 현재 카드에는 직접 표시하지 않음 |

## 요청 8. 하단 콘텐츠 카드/배너 제거 반영

GuestHome/MemberHome 하단 사진형 콘텐츠 카드 섹션은 FE 화면에서 제거했다.
따라서 `GET /api/home` 응답에 `contentCards` 또는 `HomeContentCardResponse`를 추가로 제공할
필요가 없다.

추후 운영 배너 기능을 새로 도입하는 경우에는 홈 화면 요구사항을 다시 정의한 뒤 별도 요청
문서로 진행한다.

## FE 처리

- BE 응답 보강 전까지 누락 필드는 FE 기본값 또는 mock 보조값으로 표시한다.
- BE에서 필드를 보강하면 `homeViewApi.ts` adapter에서 `HomeViewData` 매핑을 업데이트한다.
- `GET /api/home/following` 실패는 홈 전체 실패로 처리하지 않고 팔로잉 섹션만 fallback 처리한다.
- 접근 불가능한 이미지 URL은 카드 이미지 fallback으로 대체한다.
- 공통 푸터는 `DefaultLayout`의 FE 정적 컴포넌트로 유지한다.

## BE 확인 필요

1. `GET /api/home`의 상품 카드에 `sellerName`, `categoryName`, `startingBid`, `auctionStartsAt`, `isWished`를 제공할 수 있는지 확인해야 한다.
2. 진행 중 라이브 카드에 `startedAt`을 제공할 수 있는지 확인해야 한다.
3. `/api/home/following` 응답에 `followedSellers`를 추가할 수 있는지 확인해야 한다.
4. 홈 응답에 `categoryProductSections`를 추가할 수 있는지 확인해야 한다.
5. `/home/following.products`가 팔로잉 상품인지 추천 상품인지 의미를 확정해야 한다.
6. 실제 접근 가능한 이미지 URL 제공 정책을 확정해야 한다.
7. 구현 후 Swagger에 홈 응답 DTO, nullable 정책, 인증별 응답 차이를 문서화해야 한다.

## FE 관련 파일

- `FE/src/domains/home/api/homeViewApi.ts`
- `FE/src/domains/home/types/homeView.types.ts`
- `FE/src/domains/home/components/GuestHome.vue`
- `FE/src/domains/home/components/MemberHome.vue`
- `FE/src/domains/home/components/LiveCard.vue`
- `FE/src/domains/home/components/ProductCard.vue`
- `FE/src/domains/home/components/CategoryProductTabs.vue`
- `FE/src/shared/components/AppFooter.vue`
- `FE/src/shared/layouts/DefaultLayout.vue`
