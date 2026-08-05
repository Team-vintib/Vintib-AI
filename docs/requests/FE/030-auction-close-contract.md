# 030 경매 마감·낙찰·유찰 계약 (Phase 8)

- **작성자 파트**: BE (정윤) / **대상 파트**: FE
- **작성일**: 2026-08-05
- **원 요청**: `docs/requests/BE/005-auction-chat-contract.md` 잔여분(경매 종료·낙찰자 조회·`AUCTION_CLOSED`),
  `docs/requests/BE/007-unsold-product-disposition.md` 최종 확인

경매가 이제 **자동으로 마감**됩니다. 시작·입찰(Phase 7)에 이어 끝까지 이어집니다.

---

## 1. 자동 마감 — FE가 따로 호출할 API가 없습니다

종료 예정 시각이 지나면 **서버 스케줄러가 1초 주기로 알아서 마감**합니다. "경매 종료" 버튼이나
API는 없습니다 — 호스트도 마감을 호출하지 않습니다.

마감되는 순간 `/topic/lives/{liveId}/auctions`로 이벤트가 갑니다.

```jsonc
{
  "type": "AUCTION_CLOSED",
  "auction": { /* AuctionSnapshotResponse — 시작·입찰 이벤트와 같은 구조 */ }
}
```

- **낙찰인지 유찰인지는 `auction.status`로 판단합니다** — `SUCCESS`(낙찰) / `FAILED`(유찰).
  낙찰 축하 연출은 `SUCCESS`일 때만 띄우면 됩니다.
- `auction.highestBidderId`·`currentPrice`가 낙찰자·낙찰가입니다(`endedAt`도 채워집니다).
- 유찰이면 `highestBidderId`가 `null`이고 `currentPrice`는 0입니다.

**자동 연장(AUCT-010)에 주의하세요.** 마감 직전(3초 이하) 입찰이 들어오면 종료 시각이 5초 뒤로
밀립니다. 카운트다운이 0이 됐다고 화면을 종료 상태로 바꾸지 마시고, **`AUCTION_CLOSED` 이벤트가
올 때까지 기다려 주세요.** `BID_PLACED` 이벤트의 `endsAt`이 바뀌면 카운트다운을 다시 맞추면 됩니다.

---

## 2. `GET /api/auctions/{auctionId}/winner` — 결과 조회

이벤트를 놓쳤거나 나중에 다시 확인할 때 씁니다. **비회원도 조회 가능합니다.**

```jsonc
{
  "auctionId": 301,
  "liveId": 101,
  "productId": 2001,
  "status": "SUCCESS",          // SUCCESS(낙찰) / FAILED(유찰) / READY·RUNNING(아직 진행 중)
  "winnerId": 7,
  "winnerNickname": "빈티지러버",
  "finalPrice": 45000,
  "bidCount": 5,
  "endedAt": "2026-08-05T21:41:05"
}
```

- **유찰도 200입니다.** `status`가 `FAILED`이고 낙찰자 관련 필드가 전부 `null`입니다 — 404로
  돌려주면 "경매가 없다"와 "안 팔렸다"를 구분할 수 없어서입니다.
- 아직 안 끝난 경매도 그대로 내려주므로 **종료 여부는 `status`로 판단**하세요.

---

## 3. 낙찰되면 주문이 자동으로 만들어집니다

경매에는 구매자가 결제 버튼을 누르는 시점이 없습니다 — 입찰한 순간 구매 의무가 확정되고 그
금액이 이미 보류돼 있기 때문입니다. 그래서 **마감과 동시에 서버가 주문을 만들고, 보류된 포인트가
거래 대금으로 전환됩니다.**

- 낙찰자에게 `AUCTION_WON` 알림이 갑니다(`refType: "AUCTION"`, `refId: auctionId`).
- 만들어진 주문은 **`PAID` 상태로 시작**하며, 이후 배송지 등록·송장·구매확정은 상시 판매
  즉시구매와 **완전히 같은 흐름**입니다(`GET /api/orders` 등 기존 API 그대로).
- 즉 FE는 낙찰 후 "결제하기" 화면을 만들 필요가 없습니다. 마이페이지 구매/낙찰 내역에 바로
  뜹니다.

---

## 4. 미낙찰 상품 처리 — 007 예비 답변 최종 확인 ✅

`007`에 드렸던 예비 답변이 **코드로 확정됐습니다.**

- 유찰이면 상품은 **`AUCTION_SCHEDULED`로 되돌아갑니다.** 별도 "복원" API가 필요 없습니다.
- 그대로 두면 다음 라이브에서 다시 경매에 걸 수 있고, `PATCH /products/{id}/status { price }`를
  호출하면 상시 판매로 전환됩니다.
- **`AUCTION_FAILED` 상태는 존재하지 않습니다** — 한때 계획에 있었지만 제거됐습니다. 상품
  상태만 보고 "이 상품이 유찰됐다"를 판단하지 마세요. 유찰 이력은 `auction` 테이블에 남고,
  방송별 유찰 목록은 아래 Phase 8-b 조회로 제공할 예정입니다.

이미 연결해 두신 두 엔드포인트를 **그대로 쓰시면 됩니다.**

---

## 5. 방송 종료 시

방송이 끝나면 진행 중이던 경매가 **강제로 마감**됩니다(남은 시간과 무관). 입찰이 있었으면 그
시점의 최고가로 낙찰됩니다.

이때는 `AUCTION_CLOSED`를 따로 쏘지 않습니다 — 방송 종료가 이미
`/topic/lives/{liveId}/status`로 전파되고 FE가 그 이벤트에서 시청 화면을 종료 안내로 바꾸기
때문에, 같은 순간에 두 이벤트가 겹치면 화면 전환이 두 번 일어납니다. 결과는 `GET .../winner`나
방송 종료 대시보드에서 확인해 주세요.

---

## 아직 안 된 것

- **방송별 유찰 상품 목록**(`GET /api/lives/{liveId}/unsold-products`) — Phase 8-b. FE `-440`
  미낙찰 처리 UI가 기다리는 것입니다. 다음 배치에서 나갑니다.
- **방송 종료 요약**(`docs/requests/BE/018`) — 낙찰/유찰 집계. Phase 8-b와 함께 처리합니다.
