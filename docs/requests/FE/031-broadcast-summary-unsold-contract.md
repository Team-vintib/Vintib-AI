# 031 라이브 즉시구매 — 남은 FE 항목

- **작성자 파트**: BE (정윤) / **대상 파트**: FE
- **작성일**: 2026-08-05
- **원 요청**: `docs/requests/BE/018`(방송 종료 요약), `docs/requests/BE/007`(미낙찰 상품 처리)

> §1 방송 종료 요약(`GET /api/lives/{id}/summary` — `LiveBroadcastPage.vue` 하드코딩 대체)·
> §2 유찰 목록(`GET /api/lives/{id}/unsold-products`)·§3 유찰 상품 `PATCH /products/{id}` 허용·
> §4 시청자 STOMP 이중 연결 단일화는 반영 완료되어 덜어냈다. 아래 라이브 즉시구매만 남는다.

## 남은 항목 — 라이브 시청 화면 즉시구매 (미구현)

현재 `createOrder`(`order/api/orderApi.ts`)가 `{ productId }`만 보내고 상품 상세에서만 호출된다.
라이브 시청 상품 카드 액션이 찜/상세보기뿐이라 구매 버튼이 없다. 붙일 때 체크리스트:

- [ ] `POST /api/orders`에 **`liveId`를 함께 보낸다.** 빠지면 그 판매가 방송 종료 요약(§1 집계)에 안 잡힌다.
  ```jsonc
  { "productId": 2003, "liveId": 101 }   // liveId 신규(선택). 라이브 밖 구매는 생략. 없는 방송 ID면 404
  ```
- [ ] 구매 대상은 **`saleType === 'DIRECT_SALE' && saleStatus === 'ON_SALE'`** 인 상품만. 경매 상품
      (`AUCTION_SCHEDULED`/`AUCTION_IN_PROGRESS`)은 400 — 버튼 노출을 `saleType`으로 가른다.
- [ ] 본인 상품은 구매 불가(400) — 호스트 화면에서는 버튼 숨김.
- [ ] 결제는 포인트 차감. 잔액 부족 시 400(`W001`)이며 충전 안내 필요.
