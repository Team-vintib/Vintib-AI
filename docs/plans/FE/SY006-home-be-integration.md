# HOME-001/002 홈 BE 연동 계획

## 배경/목표

홈 화면은 현재 `homeMockData`를 반환하는 mock adapter로 동작한다. BE 코드는 수정하지 않고, 이미 제공된 `GET /api/home`과 `GET /api/home/following` 응답 중 FE 화면에 바로 매칭 가능한 필드만 `HomeViewData`로 변환해 실제 호출로 전환한다.

## 작업 내용

- `FE/src/domains/home/api/homeViewApi.ts` 안에 HOME BE 응답 타입과 adapter를 추가한다.
- 공통 홈 콘텐츠는 항상 `GET /home`에서 조회한다.
- 로그인 상태에서는 `GET /home/following`을 추가 조회해 팔로잉 기반 라이브/상품을 회원 홈 섹션에 반영한다.
- BE가 내려주지 않는 화면 전용 필드는 FE 기본값 또는 기존 mock 보조 데이터로 처리하되, BE 계약처럼 보이게 확정하지 않는다.
- BE 응답 이미지가 깨질 수 있으므로 카드 컴포넌트에서 기존 화면 품질이 무너지지 않도록 fallback을 둔다.

## 구현 목록

- [x] `homeViewApi.ts`에 `HomeContentResponse`, `FollowingContentResponse`, `HomeLiveCardResponse`, `HomeProductCardResponse` 타입을 추가한다.
- [x] `http.get<ApiResponse<HomeContentResponse>>('/home')` 호출을 추가하고 `success/data`를 검증한다.
- [x] `HomePage.vue`에서 로그인 여부를 `getHomeViewData`에 전달하거나, `getHomeViewData` 호출부를 인증 상태 기준으로 분기할 수 있게 바꾼다.
- [x] 로그인 상태에서만 `http.get<ApiResponse<FollowingContentResponse>>('/home/following')`을 호출한다.
- [x] BE 라이브 카드 응답을 `HomeLiveCardItem`으로 변환한다.
- [x] BE 상품 카드 응답을 `HomeProductCardItem`으로 변환한다.
- [x] `following.products`는 회원 홈의 `recommendedProducts`로 매핑하고, `following.lives`는 판매자 카드 구조가 확정될 때까지 라이브 섹션에 섞지 않는다.
- [x] `contentCards`는 BE 응답에 없으므로 기존 mock 값을 유지한다.
- [x] `followedSellers`는 BE 응답에 판매자 카드 필드가 없으므로 기존 mock 유지 또는 빈 배열 처리 중 화면 영향이 적은 방식을 택한다.
- [x] 이미지 로드 실패 시 기본 이미지 또는 기존 mock 이미지 fallback을 적용한다.
- [x] `FE/docs/frontend/api/api-index.md`, `FE/docs/frontend/implementation/status.md`에 홈 API 연동 상태와 BE 미제공 필드 처리 방식을 갱신한다.
- [x] `npm run type-check`로 타입 검증한다.
- [x] auth 세션 검증 이후 로그인 상태에서만 `/home/following`을 호출하는 흐름을 재확인한다.
- [x] `npm run build`로 번들 검증한다.

## 매핑 기준

### 라이브

- `liveId` → `id`
- `title` → `title`
- `hostNickname` → `hostName`
- `thumbnailUrl` → `thumbnailUrl`
- `broadcastStatus` → `status`
- `scheduledAt` → `scheduledAt`
- `viewerCount` → `viewerCount`
- `productCount` → `scheduledProductCount`

`startedAt`, `reservationCount`, `categoryName`은 BE 응답에 없으므로 선택 필드로 비워 둔다.

### 상품

- `productId` → `id`
- `name` → `title`
- `brand` → `brandName`
- `thumbnailUrl` → `primaryImageUrl`
- `sellType === 'NORMAL'` → `saleType: 'DIRECT_SALE'`
- `sellType === 'AUCTION_SCHEDULED'` 또는 `auctionScheduled === true` → `saleType: 'AUCTION'`
- `sellStatus` → `saleStatus`
- `price` → `price`

`sellerName`, `categoryName`, `startingBid`, `auctionStartsAt`, `isWished`는 BE 응답에 없으므로 기본값 또는 mock 보조값으로 처리한다.

## 확인이 필요한 미결정 사항

- 팔로잉 API의 `products`는 회원 홈의 `recommendedProducts`로 표시한다.
- 팔로잉 API의 `lives`는 추후 BE가 판매자 카드에 필요한 `followedSellers` 구조를 제공하면 `내가 팔로우한 판매자` 섹션에 연결한다.
- BE mock 이미지 URL이 실제 접근 가능한 CDN이 아니므로 FE fallback 이미지가 필요하다.
- 검색 화면 `SearchResultsPage.vue`는 현재 mock 기반이라 이번 홈 연동의 직접 수정 대상은 아니다. 다만 추후 검색 API도 같은 `http + ApiResponse + adapter` 패턴으로 분리하는 것이 맞다.
