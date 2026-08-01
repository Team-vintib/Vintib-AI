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
- 요청 목적: 호스트 경매 진행, 사용자 입찰, 입찰 내역/낙찰 결과 조회를 처리한다. FE 입찰 버튼(AUCT-003~006)이 이 API로 동작하며, **선착순(AUCT-005)·연속 입찰 제한(AUCT-006)·종료 직전 연장(AUCT-010, 종료 3초 이하 → +5초) 판정은 서버가 확정**한다. (현재 FE는 mock 사이클로 연출 중)
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
  - **낙찰 축하 연출(AUCT-013)**: `AUCTION_CLOSED` 이벤트(및 `GET /api/auctions/{auctionId}/winner`)로 FE가 라이브 화면 위에 낙찰자 닉네임(전체)·낙찰가를 강조 연출한다. → snapshot에 `highestBidderNickname`(낙찰자)·`currentPrice`(낙찰가)가 반드시 포함돼야 한다. (현재 FE는 이 이벤트가 없어 mock 트리거로 연출)
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

### 3.4 경매 생성·조건 설정 (AUCT-001, 판매자) — 추가 확인 요청

- 3.2의 `POST /api/auctions/{auctionId}/start`는 **이미 만들어진 경매(auctionId)를 시작**한다.
  그런데 판매자가 연결 상품에 대해 **경매를 만들고 시작가·증액 단위·진행 시간을 설정(AUCT-001)**하는
  단계의 엔드포인트가 계약에 없다. FE 판매자 경매 설정 패널(`S15P11A108-436`)이 이 값을 입력받는다.
- 필요한 것(형태는 BE가 정함):
  - 예: `POST /api/lives/{liveId}/auctions` body `{ productId, startPrice, bidUnit, durationSeconds }`
    → 생성된 `auctionId`(status `READY`) 반환 후 3.2 `/start`로 시작. 또는 생성+시작 통합.
- 확인 부탁
  - 경매 **생성/설정과 시작이 분리인지 통합**인지
  - 진행 시간(`durationSeconds`) **단위·허용 범위**, 증액 단위(`bidUnit`) 프리셋 정책
  - (FE는 확정 전까지 mock 기본값: 진행 1/3/5분, 증액 1,000/5,000/10,000P 사용 중)

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
