# SY028 마이페이지 데이터 연동 버그 4건

## 배경/목표

마이페이지에서 (1) 온보딩에서 입력한 정보(닉네임/이름/이메일 제외)가 저장 안 됨, (2) 팔로잉 42 고정값, (3) 등록 상품이 판매 내역에 연결 안 됨, (4) 포인트 0P인데 입찰 보류 39000P 고정값 — 4가지를 고친다.

## 작업 내용

- `VITE_MY_API_ENABLED`가 `.env`/`.env.production`/`.env.example` 어디서도 `true`인 적이 없어서 `getMyProfile` 등이 계속 localStorage mock을 썼던 게 (1)(3 일부)의 원인. `true`로 변경.
- `myApi.ts`에 `getMyOrders(userId, role)` 추가(`GET /users/{id}/orders?role=BUYER|SELLER`, BE 구현 완료 확인됨 — `docs/requests/FE/018-mypage-contract.md`, BE 소스 `OrderListItemResponse.java`/`OrderStatus.java` 직접 확인). `getMyPageViewData`에 orders/sales 연동.
- `MyOrderStatus`를 실제 BE enum(`PAID/SHIPPING/DELIVERED/CONFIRMED/SETTLED/REFUNDED/CANCELED`)에 맞게 수정, 라벨/필터 버킷 갱신.
- `MyPage.vue`: 팔로잉/팔로워는 이미 호출 중인 `getPublicProfile`의 `followingCount`/`followerCount`로, 포인트 카드들은 새로 호출하는 `getPointBalance`의 `available`/`held`/`escrow`/`pendingSettlement`로 교체.

## 구현 목록

- [ ] `.env`/`.env.production`/`.env.example`: `VITE_MY_API_ENABLED=true`
- [ ] `myApi.ts`: `getMyOrders` + DTO/매퍼, `getMyPageViewData` 연동
- [ ] `my.types.ts`/`myMockData.ts`: `MyOrderStatus` 수정
- [ ] `MyPage.vue`: 필터 버킷, 팔로잉/팔로워, 포인트 카드 교체
- [ ] `vue-tsc --noEmit` 통과 확인
