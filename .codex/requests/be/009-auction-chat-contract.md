# 009 Auction/Chat API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 라이브 채팅/반응/시청자 수 연동 상태와 경매 진행 API 및 STOMP 계약 요청을 정리한다.
- 우선순위: P0
- 시연 필수 여부: 채팅/반응/시청자 수는 현재 시연 가능. 경매 패널 시연 시 경매 API가 필수.

## 2. 현재 연동 상태

- 연동 완료 API/topic
  - `GET /api/lives/{liveId}/chat-messages`
  - WebSocket `/ws`
  - publish `/app/lives/{liveId}/chat`
  - subscribe `/topic/lives/{liveId}/chat`
  - publish `/app/lives/{liveId}/reactions`
  - subscribe `/topic/lives/{liveId}/reactions`
  - subscribe `/topic/lives/{liveId}/viewers`
- FE 구현 완료 범위
  - 채팅 내역 표시
  - 채팅 발송
  - 반응 발송/표시
  - 시청자 수 표시
  - 경매 패널 UI
- 현재 임시 처리 또는 Mock 사용 여부
  - 경매 snapshot과 입찰 진행은 mock snapshot 기반으로 표시 중이다.
  - 경매 시작/입찰/종료 STOMP 이벤트는 실제 계약이 필요하다.

## 3. 추가 구현 요청

### 3.1 경매 snapshot

- Method / Endpoint: `GET /api/lives/{liveId}/auctions/current`
- 요청 목적: 라이브 진입 시 현재 진행 중이거나 준비 중인 경매 상태를 초기화한다.
- FE 사용처: 라이브 경매 패널
- 요청 데이터
  - Path: `liveId`
- 응답 데이터
  - `auctionId`: number
  - `liveId`: number
  - `productId`: number
  - `productTitle`: string
  - `status`: `READY` | `IN_PROGRESS` | `ENDED`
  - `startPrice`: number
  - `bidUnit`: number
  - `currentPrice`: number
  - `highestBidderId`: number | null
  - `highestBidderNickname`: string | null
  - `bidCount`: number
  - `startedAt`: string(datetime) | null
  - `endsAt`: string(datetime) | null
  - `serverNow`: string(datetime)
- 응답 예시

```json
{
  "success": true,
  "data": {
    "auctionId": 1,
    "liveId": 1,
    "productId": 10,
    "productTitle": "빈티지 자켓",
    "status": "IN_PROGRESS",
    "startPrice": 30000,
    "bidUnit": 3000,
    "currentPrice": 45000,
    "highestBidderId": 7,
    "highestBidderNickname": "buyer",
    "bidCount": 5,
    "startedAt": "2026-07-31T12:00:00",
    "endsAt": "2026-07-31T12:05:00",
    "serverNow": "2026-07-31T12:03:00"
  },
  "error": null
}
```

### 3.2 경매 진행 API

- Method / Endpoint
  - `POST /api/auctions/{auctionId}/start`
  - `POST /api/auctions/{auctionId}/bids`
  - `POST /api/auctions/{auctionId}/close`
  - `GET /api/auctions/{auctionId}/bids`
  - `GET /api/auctions/{auctionId}/winner`
- 요청 목적: 호스트 경매 진행, 사용자 입찰, 입찰 내역/낙찰 결과 조회를 처리한다.
- FE 사용처: 라이브 경매 패널
- 요청 데이터
  - 입찰: `{ "amount": number }`
- 응답 데이터: 경매 snapshot 또는 bid result
- 응답 예시

```json
{
  "success": true,
  "data": {
    "auctionId": 1,
    "bidId": 10,
    "amount": 48000,
    "bidderId": 7,
    "bidderNickname": "buyer",
    "createdAt": "2026-07-31T12:03:30"
  },
  "error": null
}
```

### 3.3 경매 STOMP topic

- Method / Endpoint
  - subscribe `/topic/lives/{liveId}/auctions`
  - subscribe `/topic/auctions/{auctionId}`
- 요청 목적: 경매 시작/입찰/종료 이벤트를 실시간 반영한다.
- FE 사용처: 라이브 경매 패널
- 요청 데이터: 없음
- 응답 데이터
  - `type`: `AUCTION_STARTED` | `BID_PLACED` | `AUCTION_CLOSED`
  - `auction`: snapshot
- 응답 예시

```json
{
  "type": "BID_PLACED",
  "auction": {
    "auctionId": 1,
    "currentPrice": 48000,
    "highestBidderId": 7,
    "bidCount": 6,
    "serverNow": "2026-07-31T12:03:30"
  }
}
```

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - 채팅/반응/시청자 수는 현재 연결되어 있어 변경 요청 없음
- 추가할 필드
  - 없음
- 변경 영향 범위
  - 없음

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - 경매 시연이 없으면 경매 API/topic은 보류 가능
  - 낙찰 후 주문 생성 연동은 Commerce 범위로 보류 가능
- 추후 구현 예정 기능
  - 경매 예약/상품 큐 관리
  - 경매 입찰 내역 상세 모달
  - 낙찰자 결제 유도

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - 경매 topic을 live 기준으로 통일할지 auction 기준 topic도 제공할지
  - `serverNow` 포함 여부
  - 자동 종료 시점과 연장 입찰 정책
  - 최고 입찰자가 본인일 때 재입찰 허용 여부
- 아직 확정되지 않은 응답 구조나 정책
  - bid error code
  - 경매 상태 enum
  - 종료/낙찰 이벤트 payload

## 7. 추가 요청 없음

- 이미 정상 연동된 API
  - 채팅 내역
  - 채팅 STOMP
  - 반응 STOMP
  - 시청자 수 STOMP
- 기존 규격을 유지하면 되는 기능
  - 채팅/반응/시청자 수 연결
