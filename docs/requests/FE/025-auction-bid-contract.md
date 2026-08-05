# 025 입찰 계약 (AUCT-003~006)

- **작성자 파트**: BE (정윤) / **대상 파트**: FE
- **작성일**: 2026-08-04
- **관련 이슈**: [-462](https://ssafy.atlassian.net/browse/S15P11A108-462),
  [-463](https://ssafy.atlassian.net/browse/S15P11A108-463),
  [-464](https://ssafy.atlassian.net/browse/S15P11A108-464),
  [-465](https://ssafy.atlassian.net/browse/S15P11A108-465),
  [-469](https://ssafy.atlassian.net/browse/S15P11A108-469)
- **원 요청**: `docs/requests/BE/005-auction-chat-contract.md` §3.2 · §3.3

`017`에서 이어지는 입찰 계약입니다. 이제 실제로 입찰이 됩니다.

> **2026-08-05 후속** — 본문에서 "다음 단계(낙찰 확정)"라고 적은 것은 전부 반영됐습니다.
> 경매는 이제 서버가 자동으로 마감하고, 낙찰되면 보류가 자동으로 풀려 거래 대금으로 넘어갑니다.
> 계약은 `030-auction-close-contract.md`를 보세요.

---

## 1. `POST /api/auctions/{auctionId}/bids` — 입찰

인증 필요. 요청 본문은 요청서(009 §3.2)에 적어 주신 그대로입니다.

```json
{ "amount": 46000 }
```

**`amount`는 반드시 직전 `GET .../auctions/current`(또는 마지막으로 받은 STOMP 이벤트)의
`nextBidPrice`와 정확히 같아야 합니다.** 그 이상도 이하도 거부됩니다. FE 입찰 버튼은 서버가
계산해 준 `nextBidPrice`를 그대로 보내면 됩니다 — 클라이언트가 `현재가 + 증액 단위`를 직접
계산하면 정책이 바뀔 때 어긋납니다.

성공 응답은 `017`의 snapshot과 **완전히 같은 타입**입니다(`AuctionSnapshotResponse`). 별도의
"입찰 결과" DTO를 만들지 않았습니다 — `/current`·`/start`·`/bids` 응답과 STOMP 이벤트가 전부
같은 모양이면 FE가 화면을 하나의 상태 구조로 그릴 수 있습니다.

```jsonc
{
  "success": true,
  "data": {
    "auctionId": 301,
    "currentPrice": 46000,
    "nextBidPrice": 47000,
    "highestBidderId": 7,
    "highestBidderNickname": "빈티지러버",
    "bidCount": 6,
    "endsAt": "2026-08-04T21:41:05",   // 종료 임박이었다면 5초 밀려 있을 수 있다
    "extensionCount": 1,
    "serverNow": "2026-08-04T21:41:00",
    // ... 나머지 필드는 017과 동일
  },
  "error": null
}
```

### 실패 응답

| 코드 | 상황 |
| --- | --- |
| `A001` 400 | 경매가 진행 중(`RUNNING`)이 아니거나 이미 종료 시각이 지남 |
| `A002` 400 | 금액이 `nextBidPrice`보다 낮음 |
| `A008` 400 | 금액이 `nextBidPrice`보다 높음(화면에 보이던 값이 그 사이 바뀌었다는 뜻 — 최신 값으로 재시도) |
| `A009` 400 | **직전 최고 입찰자 본인**이 연속으로 입찰(자기 자신을 상위 입찰할 수 없음) |
| `A005` 404 | 존재하지 않는 경매 |
| `W001` 400 | **포인트 잔액 부족** |
| `A010` 409 | 같은 경매·같은 금액에 중복 입찰(정상 경로에서는 사실상 발생하지 않음 — 서버가 매번 정확한 금액을 요구하므로) |
| `A011` 409 | **다른 경매에 이미 최고 입찰자로 참여 중** — 아래 §3 참고 |

---

## 2. `GET /api/auctions/{auctionId}/bids` — 입찰 내역

**비회원 공개.** 지금 얼마까지 붙었는지 보는 것은 관전이지 참여가 아니라고 판단했습니다.

| 파라미터 | 설명 |
| --- | --- |
| `cursor` | 이 `bidId`보다 오래된 입찰을 최신순으로. 첫 페이지는 생략 |
| `size` | 기본 20, 최대 100 |

```jsonc
{
  "success": true,
  "data": {
    "content": [
      {
        "bidId": 5001,
        "bidderId": 7,
        "bidderNickname": "빈티지러버",
        "amount": 46000,
        "status": "ACTIVE",       // ACTIVE | OUTBID | WON | LOST
        "createdAt": "2026-08-04T21:40:55",
        "isMine": false           // 토큰 없으면 항상 false
      }
    ],
    "nextCursor": 5000,
    "hasNext": true
  },
  "error": null
}
```

채팅 이력 조회(`GET /api/lives/{liveId}/chat-messages`)와 같은 커서 방식입니다 — `nextCursor`를
다음 요청에 그대로 넣으면 이어집니다.

---

## 3. `/topic/lives/{liveId}/auctions`에 `BID_PLACED` 추가

```jsonc
{
  "type": "BID_PLACED",
  "auction": { /* §1과 완전히 같은 snapshot */ }
}
```

- **입찰이 성공할 때마다** 전파됩니다. 상위 입찰이 들어오면 직전 최고 입찰자의 표시(강조 등)를
  이 이벤트로 갱신하면 됩니다.
- **실패한 입찰은 전파되지 않습니다** — 4xx/409 응답만 받고 화면에 전파는 오지 않습니다.
- 종료 임박(3초 이하) 입찰이 들어오면 **`endsAt`이 5초 뒤로 밀려서** 옵니다(AUCT-010). 카운트다운
  타이머를 이 값으로 다시 맞춰야 합니다. `extensionCount`가 몇 번 밀렸는지 보여줍니다.

---

## 4. AUCT-009 — "최고 입찰자인 동안 다른 경매 참여 금지" 정책

요청서에 없던 내용이지만, **낙찰 확정(다음 단계, AUCT-012)까지 내 돈이 걸려 있는 동안에는
다른 경매에 동시에 입찰할 수 없습니다.** 최고 입찰자 자리를 유지하는 동안 그 금액은 잔액에서
`bidHeld`로 옮겨져 있고(erd.md §4), 그 상태에서 다른 경매에도 걸면 잔액 정합성이 깨지기
때문입니다.

- 상위 입찰에 밀리거나 그 경매가 유찰되면 자동으로 풀립니다(다음 단계에서 마감 처리와 함께).
- **화면 안내가 필요하시면 말씀해 주세요** — 예: "다른 경매에서 최고 입찰자 상태입니다" 같은
  안내 문구를 위한 별도 필드가 필요하면 `A011` 에러 message를 그대로 쓰시거나, 전용 조회 API를
  추가해 드릴 수 있습니다.

---

## 5. 아직 안 된 것

| 요청 | 상태 |
| --- | --- |
| `POST /api/auctions/{auctionId}/close` (종료) | 다음 단계 |
| `GET /api/auctions/{auctionId}/winner` (낙찰자) | 다음 단계 |
| `AUCTION_CLOSED` 이벤트, 낙찰 축하 연출용 필드 | 다음 단계 |
| 종료 시각 도달 시 자동 마감 스케줄러 | 다음 단계 — 지금은 시각이 지나면 입찰만 막히고(`A001`),
  경매 상태 자체는 호스트가 `close`를 눌러야 `SUCCESS`/`FAILED`로 확정됩니다 |
