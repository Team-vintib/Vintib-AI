# 024 경매 현황 조회·시작 계약 (AUCT-002)

- **작성자 파트**: BE (정윤) / **대상 파트**: FE
- **작성일**: 2026-08-03
- **관련 이슈**: [-460](https://ssafy.atlassian.net/browse/S15P11A108-460), [-461](https://ssafy.atlassian.net/browse/S15P11A108-461)
- **원 요청**: `docs/requests/BE/005-auction-chat-contract.md` §3.1 · §3.2 · §3.3

`009`에서 요청하신 경매 API 중 **snapshot 조회와 시작**이 나왔습니다. 입찰·종료·입찰 내역·낙찰자는
다음 단계입니다(§4).

---

## 1. `GET /api/lives/{liveId}/auctions/current` — 경매 패널 초기화

**비회원 공개.** 라이브 진입 시 한 번 호출하고, 이후 변화는 §3 토픽으로 받습니다.

```jsonc
{
  "success": true,
  "data": {
    "auctionId": 301,
    "liveId": 101,
    "productId": 2001,
    "productTitle": "리바이스 501 빈티지",
    "status": "RUNNING",
    "startPrice": 10000,
    "bidUnit": 1000,
    "durationSeconds": 60,
    "currentPrice": 45000,
    "nextBidPrice": 46000,
    "highestBidderId": 7,
    "highestBidderNickname": "빈티지러버",
    "bidCount": 5,
    "startedAt": "2026-08-03T21:40:00",
    "endsAt": "2026-08-03T21:41:00",
    "endedAt": null,
    "extensionCount": 0,
    "serverNow": "2026-08-03T21:40:30"
  },
  "error": null
}
```

### 꼭 확인해 주셔야 하는 것

| 항목 | 내용 |
| --- | --- |
| **경매가 없으면 `data: null`** | 404가 아닙니다. 아직 경매를 걸지 않은 방송이 정상이라 에러로 만들지 않았습니다. 패널을 숨기면 됩니다 |
| **진행 중 > 준비 중 우선** | 두 경매가 있으면 `RUNNING`이 먼저 나옵니다. 지금 입찰할 수 있는 쪽을 보여 줘야 하기 때문입니다 |
| **종료된 경매는 안 나옵니다** | `SUCCESS`/`FAILED`/`CANCELED`는 대상이 아닙니다 — 남은 시간이 음수인 화면이 됩니다. 낙찰 결과는 §3 종료 이벤트로 받습니다 |
| **`currentPrice`는 입찰이 없으면 0** | 시작가가 아닙니다. 표시할 금액은 `nextBidPrice`를 쓰세요 |
| **`nextBidPrice`를 그대로 입찰에 쓰세요** | **첫 입찰은 시작가 그대로**이고 두 번째부터 `현재가 + 증액 단위`입니다. FE가 이 계산을 다시 하면 정책이 바뀔 때 어긋납니다 |
| **남은 시간 = `endsAt - serverNow`** | 클라이언트 시계로 계산하면 카운트다운이 0인데 서버는 아직 진행 중인 구간이 생깁니다. `serverNow`로 기준을 잡고 그 뒤로는 자기 시계로 세면 됩니다 |

### `status` enum — 요청서와 다릅니다

요청서에는 `READY | IN_PROGRESS | ENDED`로 적어 주셨는데, 실제로는 다음 5개입니다.

| 값 | 뜻 |
| --- | --- |
| `READY` | 조건 설정됨, 시작 전 |
| `RUNNING` | 진행 중 (요청서의 `IN_PROGRESS`) |
| `SUCCESS` | 낙찰 |
| `FAILED` | 유찰(입찰자 없이 종료) |
| `CANCELED` | 취소 |

**종료를 `ENDED` 하나로 합치지 않은 이유**는 낙찰 축하 연출(AUCT-013) 때문입니다. `ENDED`만
내려주면 FE가 "낙찰자가 있나?"를 따로 판단해야 하는데, 그 판단 기준을 서버가 이미 알고 있습니다.
**낙찰 연출은 `SUCCESS`일 때만** 띄우면 됩니다.

---

## 2. `POST /api/auctions/{auctionId}/start` — 경매 시작 (호스트)

인증 필요. 요청 본문 없음. 응답은 §1과 같은 snapshot입니다.

- `READY` 상태에서만 가능하고, 시작 시각·`endsAt`이 이때 확정됩니다.
- 상품도 함께 `AUCTION_IN_PROGRESS`로 바뀝니다.
- **한 방송에서 동시에 진행할 수 있는 경매는 하나뿐입니다**(LIVE-004). 이미 진행 중인 게 있으면
  409이고, 먼저 그 경매를 끝내야 합니다.

| 코드 | 상황 |
| --- | --- |
| `A005` 404 | 존재하지 않는 경매 |
| `A006` 400 | 이미 시작했거나 끝난 경매 |
| `A007` 409 | 이 방송에 이미 진행 중인 경매가 있음 |
| `L004` 403 | 본인 라이브가 아님 |
| `L007` 400 | 종료·취소된 방송 |

> **경로에 `liveId`가 없습니다.** 요청서(009 §3.2)에 적어 주신 `POST /api/auctions/{auctionId}/start`
> 그대로입니다. 조건 설정만 `POST /api/lives/{liveId}/auctions`로 라이브 아래에 있습니다 —
> "이 방송에 경매를 건다"는 뜻이라 라이브가 경로에 있는 게 맞기 때문입니다.

---

## 3. `SUBSCRIBE /topic/lives/{liveId}/auctions` — 실시간 이벤트

```jsonc
{
  "type": "AUCTION_STARTED",
  "auction": { /* §1과 완전히 같은 snapshot */ }
}
```

- `type`: `AUCTION_STARTED` | `BID_PLACED` | `AUCTION_CLOSED` (뒤 둘은 다음 단계)
- **어떤 이벤트든 현황 전체를 함께 보냅니다.** 변화분만 보내면 프레임 하나를 놓친 클라이언트가
  영영 어긋난 채로 남습니다. 받은 `auction`으로 패널을 통째로 덮어쓰면 됩니다.
- **커밋 이후에 나갑니다** — 시작이 거부되면(4xx) 아무것도 전파되지 않습니다.
- `serverNow`가 매 이벤트마다 갱신되므로, 이벤트를 받을 때마다 카운트다운 기준을 다시 맞추면
  시계 오차가 누적되지 않습니다.

요청서에서 물어보신 것 중 **`/topic/auctions/{auctionId}`는 만들지 않았습니다.** 시청자는 이미
라이브 단위로 구독하고 있고(`chat`·`viewers`·`product`·`status`), 경매만 다른 축으로 구독하면
방을 옮길 때 구독 정리가 두 벌이 됩니다. 경매 단위 구독이 꼭 필요한 화면이 있으면 알려 주세요.

---

## 4. 아직 안 된 것 (다음 단계)

| 요청 | 상태 |
| --- | --- |
| `POST /api/auctions/{auctionId}/bids` (입찰) | 다음 단계 — 동시성(비관적 락)이 핵심이라 따로 뺐습니다 |
| `POST /api/auctions/{auctionId}/close` (종료) | 다음 단계 |
| `GET /api/auctions/{auctionId}/bids` (입찰 내역) | 다음 단계 |
| `GET /api/auctions/{auctionId}/winner` (낙찰자) | 다음 단계 |
| `BID_PLACED` · `AUCTION_CLOSED` 이벤트 | 다음 단계 |
| 종료 3초 이하 → +5초 연장(AUCT-010) | 다음 단계. `endsAt`·`extensionCount`가 이미 응답에 있으니 필드는 안 바뀝니다 |

**지금 FE가 연결할 수 있는 것**: 경매 패널 초기 렌더(§1), 호스트 시작 버튼(§2), 시작 이벤트 수신(§3).
입찰 버튼은 `nextBidPrice`를 표시해 두고 클릭 핸들러만 mock으로 남겨 두시면, 다음 단계에서
엔드포인트만 갈아 끼우면 됩니다.

---

## 5. 그 밖에 알려드릴 것 — 상품 판매 상태가 경매와 연동됩니다

지금까지는 경매 조건을 걸어도 **상품이 `DRAFT`·`ON_SALE`에 머물러** 홈·상품 목록에 상시 판매처럼
보였습니다. 이제 짝이 맞습니다.

| 경매 | 상품 `saleStatus` |
| --- | --- |
| 조건 설정(`READY`) | `AUCTION_SCHEDULED` |
| 시작(`RUNNING`) | `AUCTION_IN_PROGRESS` |

홈의 "경매 예정" 섹션과 상품 카드의 `sellType`이 이 값을 따라가므로, **경매를 건 상품이 홈
경매 예정 섹션에 뜨는지** 한 번 확인해 주시면 좋겠습니다.
