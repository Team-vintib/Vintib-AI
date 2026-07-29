# HOME 홈 카드 응답 필드 보강 요청

## 요청자 파트 / 대상 파트

- 요청자 파트: FE
- 대상 파트: BE

## 배경/이유

FE 홈 화면은 `GET /api/home`과 `GET /api/home/following`을 연결해 GuestHome/MemberHome에 표시하고 있습니다. 현재 BE 홈 응답은 mock 중심이고 카드 표시용 일부 필드가 없어, FE에서 임시 기본값 또는 mock 보조값을 사용 중입니다.

홈 화면을 실제 DB 기준으로 완전히 표시하려면 BE 홈 응답에서 아래 필드를 제공해야 합니다. 이 문서는 FE 화면이 실제로 읽는 필드명, 타입, 목적을 항목별로 정리한 요청서입니다.

## 현재 FE 연동 상태

### 사용 중인 API

| API | 인증 | FE 사용 방식 |
| --- | --- | --- |
| `GET /api/home` | 비회원 접근 가능 | `skipAuth`로 공개 호출. GuestHome/MemberHome 공통 콘텐츠 |
| `GET /api/home/following` | 로그인 필요 | 로그인 회원 팔로잉 콘텐츠. 실패해도 홈 전체는 실패 처리하지 않음 |

### 현재 FE 임시 처리

| 항목 | 현재 처리 | 이유 |
| --- | --- | --- |
| 상품 `sellerName` | `판매자 정보 확인 중` | BE 홈 상품 응답에 판매자명 없음 |
| 경매 상품 `startingBid` | `시작가 미정` | BE 홈 상품 응답에 경매 시작가 없음 |
| 라이브 `startedAt` | `일정 확인` fallback | BE 홈 라이브 응답에 진행 중 라이브 시작 시간 없음 |
| `followedSellers` | FE mock 유지 | BE `/home/following` 응답에 팔로잉 판매자 카드 없음 |
| `categoryProductSections` | FE mock 유지 | BE `/home` 응답에 카테고리별 상품 묶음 없음 |
| 이미지 URL | 카드 `onerror` fallback | BE mock 이미지가 `cdn.example.com`이라 실제 접근 불가 |

## 요청 1. `GET /api/home` 응답 구조

현재 FE가 사용하는 최상위 구조는 아래와 같습니다. 가능하면 동일한 구조를 유지해 주세요.

```ts
interface HomeContentResponse {
  liveNow: HomeLiveCardResponse[]
  scheduledLives: HomeLiveCardResponse[]
  onSaleProducts: HomeProductCardResponse[]
  upcomingAuctionProducts: HomeProductCardResponse[]
  categoryProductSections?: HomeCategoryProductSectionResponse[]
}
```

### 최상위 필드 상세

| 필드명 | 타입 | 필수 | 목적 | 현재 FE 상태 |
| --- | --- | --- | --- | --- |
| `liveNow` | `HomeLiveCardResponse[]` | 예 | GuestHome/MemberHome의 `지금 진행 중인 라이브` 섹션 | BE 응답 사용 중 |
| `scheduledLives` | `HomeLiveCardResponse[]` | 예 | GuestHome/MemberHome의 `예약 라이브` 섹션 | BE 응답 사용 중 |
| `onSaleProducts` | `HomeProductCardResponse[]` | 예 | GuestHome의 `판매 상품` 섹션 | BE 응답 사용 중 |
| `upcomingAuctionProducts` | `HomeProductCardResponse[]` | 예 | GuestHome/MemberHome의 `경매 예정 상품` 섹션 | BE 응답 사용 중 |
| `categoryProductSections` | `HomeCategoryProductSectionResponse[]` | 요청 | GuestHome/MemberHome의 `카테고리별 상품` 탭 섹션 | FE mock 유지 |

## 요청 2. 라이브 카드 응답

### DTO 후보

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

### 필드 상세

| 필드명 | 타입 | 필수 | 목적 | 표시 위치 | 현재 FE 상태 |
| --- | --- | --- | --- | --- | --- |
| `liveId` | `number` | 예 | 카드 key, 라이브 상세/시청 경로 생성 | `LiveCard` 클릭 시 `/lives/{liveId}` | BE 응답 사용 중 |
| `title` | `string` | 예 | 라이브 제목 표시 | 라이브 카드 제목 | BE 응답 사용 중 |
| `hostNickname` | `string` | 예 | 판매자/호스트명 표시 | `판매자 {hostNickname}` | BE 응답 사용 중 |
| `thumbnailUrl` | `string` | 예 | 라이브 카드 이미지 | 카드 상단 이미지 | BE 응답 사용 중. 실제 접근 가능한 URL 필요 |
| `broadcastStatus` | `'LIVE' \| 'SCHEDULED'` | 예 | 진행 중/예약 라이브 구분 | LIVE badge, 예약 카드 variant | BE 응답 사용 중 |
| `scheduledAt` | `string \| null` | 예약 라이브 필수 | 예약 라이브 일시 표시 | 예약 라이브 카드 상단 시간, 본문 예정 일자 | BE 응답 사용 중 |
| `startedAt` | `string \| null` | 진행 중 라이브 요청 | 진행 중 라이브 시작 시간 표시 | 진행 중 라이브 본문 `시작 시간` | 현재 없음. 없으면 `일정 확인`으로 보임 |
| `viewerCount` | `number \| null` | 선택 | 현재 시청자 수 표시 후보 | 현재 화면에는 직접 노출하지 않음 | BE 응답 타입에는 있으나 현재 카드 렌더링 필수는 아님 |
| `productCount` | `number \| null` | 선택 | 연결/예정 상품 수 표시 | 예약 카드 `예정 상품 n개` | BE 응답 사용 중 |

### FE에서 원하는 표시 정책

- `broadcastStatus === 'LIVE'`
  - LIVE badge 표시
  - `startedAt`이 있으면 `시작 시간 {format(startedAt)}` 표시
  - `startedAt`이 없다면 FE가 `viewerCount` 또는 `productCount`를 대신 표시하도록 조정 가능
- `broadcastStatus === 'SCHEDULED'`
  - 예약 일시 `scheduledAt` 표시
  - `productCount`로 `예정 상품 n개` 표시

## 요청 3. 상품 카드 응답

### DTO 후보

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

### 필드 상세

| 필드명 | 타입 | 필수 | 목적 | 표시 위치 | 현재 FE 상태 |
| --- | --- | --- | --- | --- | --- |
| `productId` | `number` | 예 | 카드 key, 상품 상세 경로 생성 | `ProductCard` 클릭 시 `/products/{productId}` | BE 응답 사용 중 |
| `name` | `string` | 예 | 상품명 표시 | 상품 카드 제목 | BE 응답 사용 중 |
| `brand` | `string` | 예 | 브랜드명 표시 | 상품 카드 상단 브랜드 | BE 응답 사용 중 |
| `thumbnailUrl` | `string` | 예 | 상품 카드 이미지 | 카드 상단 이미지 | BE 응답 사용 중. 실제 접근 가능한 URL 필요 |
| `sellType` | `'NORMAL' \| 'AUCTION_SCHEDULED'` | 예 | 상시 판매/경매 예정 구분 | badge, FE `saleType` 변환 | BE 응답 사용 중 |
| `sellStatus` | `'ON_SALE' \| 'RESERVED' \| 'SOLD_OUT'` | 예 | 판매 상태 구분 | 향후 상태 badge/비활성 처리 | BE 응답 사용 중 |
| `price` | `number \| null` | 상시 판매 필수 | 판매가 표시 | 상품 가격 | BE 응답 사용 중 |
| `auctionScheduled` | `boolean` | 예 | 경매 예정 여부 명시 | 경매 예정 badge, FE `saleStatus` 변환 | BE 응답 사용 중 |
| `sellerName` | `string` | 요청 | 판매자명 표시 | `판매자 {sellerName}` | 현재 없음. FE 기본값 사용 |
| `isWished` | `boolean \| null` | 로그인 시 요청 | 회원별 찜 상태 표시 | 찜 버튼/상태 표시 예정 | 현재 없음. FE `false` 기본값 |
| `startingBid` | `number \| null` | 경매 상품 요청 | 경매 시작가 표시 | 경매 상품 가격/보조 가격 | 현재 없음. `시작가 미정` 표시 |
| `auctionStartsAt` | `string \| null` | 선택 | 경매 시작 예정 시각 표시 후보 | 현재 상품 카드에는 직접 노출하지 않음 | 추후 경매 시작 시각 노출 시 사용 |

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
| `auctionStartsAt` | `auctionStartsAt` | 경매 예정 시각 표시 후보. 현재 화면 필수는 아님 |

## 요청 4. `GET /api/home/following` 응답 구조

### DTO 후보

```ts
interface FollowingContentResponse {
  empty: boolean
  lives: HomeLiveCardResponse[]
  products: HomeProductCardResponse[]
  followedSellers: HomeFollowedSellerResponse[]
}
```

### 최상위 필드 상세

| 필드명 | 타입 | 필수 | 목적 | 현재 FE 상태 |
| --- | --- | --- | --- | --- |
| `empty` | `boolean` | 예 | 팔로잉 콘텐츠 없음 상태 판단 | BE 응답 사용 중 |
| `lives` | `HomeLiveCardResponse[]` | 예 | 팔로우한 판매자의 라이브를 홈 라이브 섹션에 보강 | BE 응답 사용 중 |
| `products` | `HomeProductCardResponse[]` | 예 | 팔로우한 판매자의 상품 또는 추천 상품 후보 | BE 응답 사용 중. 현재 추천 상품으로 임시 매핑 |
| `followedSellers` | `HomeFollowedSellerResponse[]` | 요청 | MemberHome `내가 팔로우한 판매자` 섹션 | 현재 FE mock 유지 |

## 요청 5. 팔로잉 판매자 카드 응답

### DTO 후보

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

### 필드 상세

| 필드명 | 타입 | 필수 | 목적 | 표시 위치 | 현재 FE 상태 |
| --- | --- | --- | --- | --- | --- |
| `sellerId` | `number` | 예 | 판매자 카드 key, 추후 판매자 상세 이동 | 팔로잉 판매자 카드 | FE mock `id` 사용 |
| `sellerName` | `string` | 예 | 판매자명 표시 | 팔로잉 판매자 카드 이름 | FE mock `name` 사용 |
| `profileImageUrl` | `string` | 예 | 판매자 프로필 이미지 표시 | 카드 본문 원형 아바타 | FE mock 사용 |
| `coverImageUrl` | `string` | 예 | 판매자 대표/커버 이미지 표시 | 카드 상단 16:9 이미지 | FE mock 사용 |
| `followerCount` | `number` | 요청 | 팔로워 수 표시 | `팔로워 n` | FE mock 사용 |
| `productCount` | `number` | 요청 | 판매 상품 수 표시 | `판매 상품 n개` | FE mock `newProductCount` 사용 |
| `liveId` | `number \| null` | 선택 | 라이브 CTA 이동 | 버튼 경로 `/lives/{liveId}` | FE mock 사용 |
| `liveStatus` | `'LIVE' \| 'SCHEDULED' \| null` | 선택 | LIVE/예약 상태 표시 및 CTA 문구 결정 | 카드 상태 badge, 버튼 문구 | FE mock 사용 |
| `liveTitle` | `string \| null` | 선택 | 판매자의 진행/예약 라이브 제목 표시 | 카드 본문 라이브 제목 | FE mock 사용 |
| `liveAt` | `string \| null` | 선택 | 라이브 시작/예약 일시 표시 | 카드 본문 시간 | FE mock 사용 |

## 요청 6. 추천 상품과 팔로잉 상품 구분

현재 FE는 `/home/following.products`를 MemberHome의 `recommendedProducts`로 임시 표시합니다. 실제 서비스에서는 아래 개념을 구분할지 결정이 필요합니다.
AI 작업과 연계하여 recommend 기능을 보강할 경우, 양 섹션을 모두 구현할 예정입니다.

### 선택지 A. 팔로잉 상품만 제공

```ts
interface FollowingContentResponse {
  products: HomeProductCardResponse[]
}
```

- 의미: 팔로우한 판매자의 상품
- FE 섹션명은 `팔로우한 판매자의 상품` 계열로 바꾸는 것이 정확합니다.

### 선택지 B. 추천 상품을 별도 제공

```ts
interface FollowingContentResponse {
  products: HomeProductCardResponse[]
  recommendedProducts: HomeRecommendedProductResponse[]
}
```

추천 상품 DTO 후보:

```ts
interface HomeRecommendedProductResponse extends HomeProductCardResponse {
  recommendationReason: string | null
}
```

| 필드명 | 타입 | 필수 | 목적 |
| --- | --- | --- | --- |
| `recommendationReason` | `string \| null` | 선택 | 추천 이유 표시. 예: `최근 데님 상품을 자주 봤어요` |

현재 FE에는 `recommendationReason` 타입이 있지만 카드에는 직접 표시하지 않습니다. 현재 홈 화면 필수 응답은 아니며, 추후 추천 이유를 노출할 경우 사용할 수 있습니다.

## 요청 7. 카테고리별 상품 섹션 응답

FE 홈 화면에 GuestHome/MemberHome 공통 `카테고리별 상품` 탭 섹션이 추가되었습니다. 현재는 FE mock 보조 데이터로 표시하지만, 실제 서비스 데이터로 전환하려면 홈 응답에 카테고리별 상품 묶음이 필요합니다.

### DTO 후보

```ts
interface HomeCategoryProductSectionResponse {
  id: string
  title: string
  categoryName: string
  products: HomeProductCardResponse[]
}
```

### 필드 상세

| 필드명 | 타입 | 필수 | 목적 | 표시 위치 | 현재 FE 상태 |
| --- | --- | --- | --- | --- | --- |
| `id` | `string` | 예 | 탭 key 및 active tab 식별 | 카테고리 탭 내부 상태 | FE mock 사용 |
| `title` | `string` | 예 | 탭 버튼 표시명 | 탭 버튼 텍스트. 현재 FE 기준 필수 노출 카테고리: `아우터`, `상의`, `하의`, `원피스`, `신발`, `액세서리` | FE mock 사용 |
| `categoryName` | `string` | 예 | 카테고리 식별/표시 | 상품 카테고리, 향후 query 연결 | FE mock 사용 |
| `products` | `HomeProductCardResponse[]` | 예 | 선택된 카테고리 상품 목록 | 탭 패널 상품 카드 | FE mock 사용 |

### `products[]` 내부 상품 필드 상세

카테고리별 상품 섹션의 `products`도 단순 ID 목록이 아니라 홈 상품 카드 렌더링에 필요한 상품 정보를 함께 내려받아야 합니다.

```ts
interface HomeCategoryProductItemResponse {
  productId: number
  name: string
  brand: string
  thumbnailUrl: string
  sellType: 'NORMAL' | 'AUCTION_SCHEDULED'
  sellStatus: 'ON_SALE' | 'RESERVED' | 'SOLD_OUT'
  price: number | null
  auctionScheduled: boolean
  sellerName: string
  categoryName: string
  isWished: boolean | null
  startingBid: number | null
  auctionStartsAt: string | null
}
```

| 필드명 | 타입 | 필수 | 목적 | 표시 위치/사용 방식 |
| --- | --- | --- | --- | --- |
| `productId` | `number` | 예 | 상품 카드 key 및 상세 이동 경로 생성 | 카드 클릭 시 `/products/{productId}` |
| `name` | `string` | 예 | 상품명 표시 | 상품 카드 제목 |
| `brand` | `string` | 예 | 브랜드명 표시 | 상품 카드 상단 브랜드 텍스트 |
| `thumbnailUrl` | `string` | 예 | 상품 대표 이미지 표시 | 상품 카드 이미지 영역 |
| `sellType` | `'NORMAL' \| 'AUCTION_SCHEDULED'` | 예 | 일반 판매/경매 예정 상품 구분 | 카드 배지 및 가격 문구 결정 |
| `sellStatus` | `'ON_SALE' \| 'RESERVED' \| 'SOLD_OUT'` | 예 | 판매 상태 표시 및 비활성 상태 판단 | 판매중/예약중/판매완료 상태 처리 |
| `price` | `number \| null` | 일반 판매 상품은 예 | 일반 판매 가격 표시 | `₩가격` 형태로 표시. 경매 예정이면 `startingBid` 우선 사용 |
| `auctionScheduled` | `boolean` | 예 | 경매 예정 여부 명시 | `true`면 경매 예정 UI로 표시 |
| `sellerName` | `string` | 예 | 판매자명 표시 | `판매자 {sellerName}` |
| `categoryName` | `string` | 예 | 상품이 속한 카테고리 표시 및 검증 | 현재 탭 카테고리와 같은 값 기대 |
| `isWished` | `boolean \| null` | 회원 응답에서 요청 | 찜 여부 표시 | 찜 버튼 상태. 비회원이면 `null` 또는 `false` 가능 |
| `startingBid` | `number \| null` | 경매 예정 상품은 예 | 경매 시작가 표시 | `시작가 ₩가격` 형태로 표시 |
| `auctionStartsAt` | `string \| null` | 선택 | 경매 시작 예정 시간 표시 후보 | 현재 상품 카드에는 직접 노출하지 않음 |

### 카테고리별 기대 응답 예시

```json
{
  "id": "outer",
  "title": "아우터",
  "categoryName": "아우터",
  "products": [
    {
      "productId": 801,
      "name": "Vintage leather bomber",
      "brand": "Schott",
      "thumbnailUrl": "https://cdn.example.com/product/801.jpg",
      "sellType": "NORMAL",
      "sellStatus": "ON_SALE",
      "price": 210000,
      "auctionScheduled": false,
      "sellerName": "Heritage Depot",
      "categoryName": "아우터",
      "isWished": false,
      "startingBid": null,
      "auctionStartsAt": null
    }
  ]
}
```

### FE 배치

| 화면 | 위치 |
| --- | --- |
| GuestHome | `판매 상품` 아래, `경매 예정 상품` 위 |
| MemberHome | `내 취향의 빈티지 상품` 아래, `경매 예정 상품` 위 |

### FE 동작

- 탭 상태는 FE에서 관리합니다.
- 탭 클릭 시 해당 section의 `products`만 표시합니다.
- 상품 클릭은 기존과 동일하게 `/products/{productId}`로 이동합니다.
- 상품 카드 필드는 `HomeProductCardResponse`와 동일한 계약을 사용합니다.
- 현재 FE 화면 기준 카테고리 탭은 `아우터 / 상의 / 하의 / 원피스 / 신발 / 액세서리` 6개를 기대합니다.
- 각 카테고리의 `products`는 우선 3개 이상 내려오면 현재 카드 그리드에서 자연스럽게 표시됩니다.

## 요청 8. 하단 콘텐츠 카드/배너 제거 반영

GuestHome/MemberHome 하단 사진형 콘텐츠 카드 섹션은 FE 화면에서 제거했습니다. 따라서 `GET /api/home` 응답에 `contentCards` 또는 `HomeContentCardResponse`를 추가로 제공할 필요가 없습니다.

추후 운영 배너 기능을 새로 도입하는 경우에는 홈 화면 요구사항을 다시 정의한 뒤 별도 요청 문서로 진행하겠습니다.

## 관련 FE 파일

| 파일 | 역할 |
| --- | --- |
| `FE/src/domains/home/api/homeViewApi.ts` | BE 응답을 `HomeViewData`로 변환하는 adapter |
| `FE/src/domains/home/types/homeView.types.ts` | 홈 화면 view model 타입 |
| `FE/src/domains/home/components/GuestHome.vue` | 비회원 홈 화면 |
| `FE/src/domains/home/components/MemberHome.vue` | 회원 홈 화면 |
| `FE/src/domains/home/components/LiveCard.vue` | 홈 라이브 카드 |
| `FE/src/domains/home/components/ProductCard.vue` | 홈 상품 카드 |
| `FE/src/domains/home/components/CategoryProductTabs.vue` | 카테고리별 상품 탭 |

## 우선순위 제안

| 우선순위 | 항목 | 이유 |
| --- | --- | --- |
| 1 | `HomeService` mock 제거 및 상품/라이브 DB 조회 연결 | 홈이 실제 데이터로 보여야 함 |
| 2 | 상품 `sellerName`, `startingBid`, `categoryName` 보강 | 현재 화면에 기본값/미정 표시가 노출됨 |
| 3 | 라이브 `startedAt` 보강 | 진행 중 라이브 시간이 `일정 확인`으로 보임 |
| 4 | `followedSellers` 응답 추가. `profileImageUrl`, `coverImageUrl` 포함 필요 | MemberHome의 팔로잉 판매자 섹션이 mock에 의존 중 |
| 5 | `categoryProductSections` 응답 추가 | 카테고리별 상품 탭이 mock에 의존 중 |
