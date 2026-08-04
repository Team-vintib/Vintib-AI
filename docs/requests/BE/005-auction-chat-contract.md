# 005 Auction/Chat API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 라이브 채팅/반응/시청자 수 연동 상태와 경매 진행 API 및 STOMP 계약 요청을 정리한다.
- 우선순위: P0
- 시연 필수 여부: 채팅/반응/시청자 수는 현재 시연 가능. 경매 패널 시연 시 경매 API가 필수.

## 2. 현재 연동 상태

- FE 구현 완료 범위
  - 채팅 내역 표시
  - 채팅 발송
  - 반응 발송/표시
  - 시청자 수 표시
  - 경매 패널 UI
- 현재 임시 처리 또는 Mock 사용 여부
  - snapshot 조회·시작·입찰·입찰내역은 실제 API로 전환 가능(§3.1/3.2 참고).
  - 종료(`close`)·낙찰자 조회·`AUCTION_CLOSED` 이벤트만 아직 mock으로 남아 있다.

> **2026-08-04 정윤 — 추가 반영.** 입찰(`POST .../bids`)·입찰 내역 조회(`GET .../bids`)·
> `BID_PLACED` 이벤트까지 구현했다. 포인트 보류/해제(AUCT-007~008, 이 문서에는 없던 내용이지만
> 입찰과 원자적으로 묶여 있어 함께 반영)도 들어갔다. 계약은
> `docs/requests/FE/025-auction-bid-contract.md` 참고.
> **남은 것은 종료(`close`)·낙찰자 조회·자동 연장 스케줄러·`AUCTION_CLOSED` 이벤트다.**
>
> **2026-08-03 정윤 — 부분 반영.** snapshot 조회(§3.1)와 경매 시작(§3.2 중 `start`), 시작 이벤트
> 전파(§3.3)는 구현했다. 계약은 `docs/requests/FE/024-auction-snapshot-start-contract.md` 참고.
>
> §6에서 물어보신 것 중 정한 것:
>
> | 질문 | 정한 것 |
> | --- | --- |
> | 경매 topic 을 live 기준으로 통일할지 | **live 기준 하나만** (`/topic/lives/{liveId}/auctions`). 시청자는 이미 라이브 단위로 구독 중이라 축이 둘이면 구독 정리가 두 벌이 된다 |
> | `serverNow` 포함 여부 | **포함한다.** 없으면 카운트다운이 서버와 어긋난다 |
> | 경매 상태 enum | `READY`·`RUNNING`·`SUCCESS`·`FAILED`·`CANCELED`. 종료를 낙찰/유찰로 나눈다(낙찰 연출 판단을 FE에 넘기지 않기 위해) |
> | 최고 입찰자가 본인일 때 재입찰 | **미정** — 다음 단계에서 확정한다 |

## 3. 추가 구현 요청

### 3.1 경매 snapshot — 반영 완료

`GET /api/lives/{liveId}/auctions/current` 구현됨. 요청한 필드는 전부 있고 이름/값이 일부 다르며
필드가 더 있다(`AuctionSnapshotResponse` 참고):

- `status`: 요청한 `READY|IN_PROGRESS|ENDED`가 아니라 **`READY|RUNNING|SUCCESS|FAILED|CANCELED`**
  (종료가 낙찰/유찰로 나뉜다)
- `endsAt` → **`endsAt` 그대로**지만 필드 하나 더 있음: `endedAt`(실제 종료 시각, 진행 중이면 null)
- 추가 필드: `nextBidPrice`(다음 최소 입찰가, 첫 입찰은 시작가), `durationSeconds`, `extensionCount`(연장 횟수)

### 3.2 경매 진행 API — 시작/입찰/입찰내역 반영 완료, 종료·낙찰만 남음

- **반영 완료** (`docs/requests/FE/024-auction-snapshot-start-contract.md`, `025-auction-bid-contract.md` 참고)
  - `POST /api/auctions/{auctionId}/start` — 호스트만, 시작 시각/종료 예정 시각 확정, `AUCTION_IN_PROGRESS` 전환
  - `POST /api/auctions/{auctionId}/bids` — 선착순(AUCT-005)·연속 입찰 제한(AUCT-006)·종료 직전 연장(AUCT-010, 3초 이하 → +5초) 전부 서버가 판정. 포인트 보류/해제(AUCT-007/008)도 원자적으로 처리
  - `GET /api/auctions/{auctionId}/bids` — 커서 기반(page 아님, `cursor`=bidId) 입찰 내역 조회
- **아직 없음**
  - `POST /api/auctions/{auctionId}/close` — 경매 종료
  - `GET /api/auctions/{auctionId}/winner` — 낙찰자 조회
  - 종료 시각 도래 시 자동으로 닫아주는 스케줄러도 없음(수동 `close` 호출 전제로 보임 — 확인 필요)

### 3.3 경매 STOMP topic — 시작/입찰 이벤트 반영 완료, 종료 이벤트만 남음

- Method / Endpoint: subscribe `/topic/lives/{liveId}/auctions` (topic은 live 기준으로 확정 — auction 기준 topic은 없음)
- **반영 완료**: `type: AUCTION_STARTED`, `type: BID_PLACED` (`auction`에 snapshot 전체, `serverNow` 포함)
- **아직 없음**: `type: AUCTION_CLOSED` — 3.2의 `close` API가 없어서 같이 미구현. 낙찰 축하 연출(AUCT-013)은 이 이벤트가 나와야 가능하다.

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

- 위 blockquote(§1)에서 대부분 확정됨: topic은 live 기준 하나, `serverNow` 포함, 경매 상태 enum은
  `READY`/`RUNNING`/`SUCCESS`/`FAILED`/`CANCELED`, bid error code는 `ErrorCode`의 A005~A011 참고.
- 아직 남은 것
  - 최고 입찰자가 본인일 때 재입찰 허용 여부(**미정**)
  - 종료/낙찰 이벤트(`AUCTION_CLOSED`) payload — `close`/`winner` API가 아직 없어 함께 미정
  - 자동 종료 스케줄러 존재 여부(수동 `close`만 있는지 확인 필요)

## 7. 추가 요청 없음

- 이미 정상 연동된 API: 없음
- 기존 규격을 유지하면 되는 기능: 없음
