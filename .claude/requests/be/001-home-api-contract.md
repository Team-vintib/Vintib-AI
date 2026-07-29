# HOME-001 홈 화면 API 응답 계약 확인 요청

- 요청자 파트: FE
- 대상 파트: BE

## 배경/이유

HOME 화면은 비회원/회원 상태에 따라 진행 중 라이브, 예약 라이브, 상시 판매 상품, 경매 예정 상품, 팔로잉 기반 콘텐츠를 노출해야 합니다. FE에서 화면 구현용 mock 데이터를 만들 수는 있지만, API 응답 필드는 BE 계약으로 확정되어야 하므로 아래 후보 필드의 제공 가능 여부를 확인 요청합니다.

## 관련 기능/Jira

- `S15P11A108-283` 홈 페이지 기본 레이아웃 구현
- `S15P11A108-287` 홈 화면 Mock 데이터 렌더링 및 반응형 구현
- `S15P11A108-284` 진행 중·예약 라이브 카드 및 목록 UI 구현
- `S15P11A108-285` 상시 판매·경매 예정 상품 카드 및 목록 UI 구현
- `S15P11A108-286` 홈 콘텐츠 UI 구현
- `S15P11A108-396` 로그인 홈 섹션 레이아웃 구현
- `S15P11A108-398` 비로그인 홈 진입 화면 구현

## FE 임시 판단 기준(API 확정 아님)

### 홈 라이브 카드 화면 기준 최소 후보

- `id`
- `status`: `LIVE` 또는 `SCHEDULED`
- `title`
- `thumbnailUrl`
- `hostId`
- `hostName`
- `scheduledAt`: 예약 라이브에서 필요
- `startedAt`: 진행 중 라이브에서 필요

### 홈 라이브 카드 노출 여부에 따른 선택 후보

- `viewerCount`: 진행 중 라이브 동시 시청자 수를 노출할 경우 필요
- `reservationCount`: 예약 라이브 예약/알림 신청 수를 노출할 경우 필요
- `representativeProductName`: 라이브 대표 상품명을 카드에 노출할 경우 필요
- `categoryName`: 카테고리 칩을 노출할 경우 필요

### 홈 상품 카드 화면 기준 최소 후보

- `id`
- `title`
- `saleType`: `DIRECT_SALE` 또는 `AUCTION`
- `saleStatus`: `ON_SALE` 또는 `AUCTION_SCHEDULED`
- `primaryImageUrl`
- `sellerId`
- `sellerName`
- `price`: 상시 판매 상품에서 필요

### 홈 상품 카드 노출 여부에 따른 선택 후보

- `brandName`: 브랜드명을 카드에 노출할 경우 필요
- `categoryName`: 카테고리 칩을 노출할 경우 필요
- `startingBid`: 경매 예정 상품의 시작가를 노출할 경우 필요
- `auctionStartsAt`: 경매 예정 시각을 노출할 경우 필요
- `isWished`: 로그인 회원에게 찜 상태를 노출할 경우 필요

### 로그인 홈 후보

- 팔로잉한 판매자의 진행/예약 라이브 목록
- 팔로잉한 판매자의 상시 판매/경매 예정 상품 목록
- 팔로잉 데이터가 없을 때 추천 판매자 목록

## 요청 내용

1. HOME 전용 집계 API가 필요한지, 기존 `/lives`, `/products`, `/users/{id}/followings` 조합으로 처리할지 판단 부탁드립니다.
2. 위 후보 필드 중 BE에서 제공 가능한 필드와 제공하지 않을 필드를 구분해 주세요.
3. `viewerCount`, `reservationCount`, `isWished`처럼 집계/회원별 상태가 필요한 값은 HOME 응답에서 바로 제공 가능한지 확인 부탁드립니다.
4. FE mock 데이터는 API 확정 전 임시 view model로만 사용하고, BE 응답 계약이 정리되면 그 구조에 맞춰 교체하겠습니다.
