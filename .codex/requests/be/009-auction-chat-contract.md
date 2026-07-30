# 경매/채팅 실시간 API 계약 보완 요청

## 요청 파트 / 대상 파트

- 요청: FE
- 대상: BE

## 배경/이유

라이브 시청 화면에는 채팅, 반응, 경매 패널이 함께 표시된다. 현재 BE는 채팅 이력, 채팅 STOMP, 반응 STOMP, 경매 조건 설정까지만 구현되어 있어 실제 입찰/낙찰/경매 상태 동기화는 FE mock을 유지해야 한다.

## 현재 BE에서 사용할 수 있는 계약

| 기능 | Method/Protocol | Endpoint/Destination | 현재 BE 상태 |
| --- | --- | --- | --- |
| 채팅 이력 조회 | `GET` | `/api/lives/{liveId}/chat-messages` | 구현됨 |
| 채팅 발행 | STOMP publish | `/app/lives/{liveId}/chat` | 구현됨 |
| 채팅 구독 | STOMP subscribe | `/topic/lives/{liveId}/chat` | 구현됨 |
| 반응 발행 | STOMP publish | `/app/lives/{liveId}/reactions` | 구현됨 |
| 반응 구독 | STOMP subscribe | `/topic/lives/{liveId}/reactions` | 구현됨 |
| 시청자 수 구독 | STOMP subscribe | `/topic/lives/{liveId}/viewers` | DTO 존재 |
| 경매 조건 설정 | `POST` | `/api/lives/{liveId}/auctions` | 구현됨 |

## 추가 구현 요청

### 1. 경매 snapshot 조회

라이브 진입 시 현재 경매 상태를 초기화할 수 있어야 한다.

```http
GET /api/lives/{liveId}/auctions/current
GET /api/auctions/{auctionId}
```

응답 후보:

```json
{
  "auctionId": 301,
  "liveId": 101,
  "productId": 2001,
  "productTitle": "리바이스 501 빈티지",
  "status": "READY",
  "startPrice": 10000,
  "bidUnit": 1000,
  "currentPrice": 0,
  "highestBidderId": null,
  "highestBidderNickname": null,
  "startedAt": null,
  "endsAt": null,
  "serverNow": "2026-07-31T01:30:00"
}
```

### 2. 경매 시작/종료/입찰 API

요청 endpoint 후보:

```http
POST /api/auctions/{auctionId}/start
POST /api/auctions/{auctionId}/bids
POST /api/auctions/{auctionId}/close
GET /api/auctions/{auctionId}/bids
GET /api/auctions/{auctionId}/winner
```

요청 사항:

- 입찰 요청 body와 응답을 확정한다.
- 최고 입찰자 본인 재입찰 허용 여부를 확정한다.
- 입찰 단위 미달, 경매 종료, 포인트 부족, 본인 상품 입찰 등 오류 코드를 문서화한다.
- 서버 시간을 기준으로 남은 시간을 계산할 수 있도록 `serverNow`, `endsAt`을 제공한다.

### 3. 경매 STOMP topic

입찰과 상태 변경을 모든 시청자에게 동기화해야 한다.

후보:

```text
/topic/lives/{liveId}/auctions
/topic/auctions/{auctionId}
/user/queue/errors
```

payload 후보:

```json
{
  "type": "BID_PLACED",
  "auctionId": 301,
  "productId": 2001,
  "status": "IN_PROGRESS",
  "currentPrice": 53000,
  "highestBidderId": 7,
  "highestBidderNickname": "vintagebuyer",
  "bidCount": 12,
  "endsAt": "2026-07-31T01:35:00",
  "serverNow": "2026-07-31T01:34:11"
}
```

### 4. 채팅/반응 오류 payload 문서화

STOMP 실패가 `/user/queue/errors`로 내려가는 구조는 확인되었다. FE가 메시지를 표시할 수 있도록 오류 payload 필드를 문서화해 달라.

요청 필드:

- `code`
- `message`
- `destination`
- `clientMessageId`
- `timestamp`

## FE 관련 파일

- `FE/src/domains/live/pages/LiveWatchPage.vue`
- `FE/src/domains/chat/components/LiveChatOverlay.vue`
- `FE/src/domains/auction/components/LiveAuctionPanel.vue`
- `FE/src/domains/auction/types/liveAuction.types.ts`
- `FE/src/domains/live/api/liveWatchApi.ts`
