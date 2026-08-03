# 010 Commerce/Wallet API 요청

## 2026-08-03 확인 결과 — 주문/배송/포인트 잔액·충전·출금은 이미 구현됨(계약은 다름)

원래 요청한 3.1(주문 생성)·3.2(주문 목록/상세)·3.3(배송/송장)과 포인트 잔액/내역/충전/출금 신청·내역은
`SY033`(주문/배송/구매확정)·`SY034`(택배 배송 조회 웹훅)·`858d017`(포인트 잔액/충전/출금)으로 전부
구현됐다. 다만 요청한 필드명·경로와 실제 계약이 다르니 FE는 아래를 기준으로 연동한다.

| 기능 | 요청했던 것 | 실제 계약 |
| --- | --- | --- |
| 주문 생성 | `POST /api/orders` body `{productId, quantity, addressId, recipientName, ...}` | `POST /api/orders` body `{productId}`만 받는다. 배송지는 별도(`PATCH /api/orders/{orderId}/address`, 아래) |
| 주문 생성 응답 | `orderId, status, paidAmount, createdAt` | `orderId, product, buyerId, buyerNickname, sellerId, sellerNickname, orderPrice, status, createdAt` — `paidAmount`가 아니라 `orderPrice` |
| 주문 목록/상세 | `GET /api/orders`, `GET /api/orders/{orderId}` | 목록은 `GET /api/users/{userId}/orders?role=BUYER\|SELLER`(query `type/status`가 아니라 `role`). 상세는 동일하게 `GET /api/orders/{orderId}` |
| 배송지 | BE 확정 필요 | `PATCH/GET /api/orders/{orderId}/address` — `recipientName/recipientPhone/zipcode/address1/address2` |
| 송장 | BE 확정 필요 | `POST/GET /api/orders/{orderId}/shipment` — 택배사는 자유 문자열이 아니라 고정 코드(`courierCode`, `docs/requests/FE/016` 참고). 실제 택배사 배송완료 신호(`deliveryapi.co.kr` 웹훅)를 받아야 `DELIVERED`로 바뀐다 |
| 구매 확정 | (요청에 없었음) | `POST /api/orders/{orderId}/confirmation` — 수동 확정 또는 배송완료 7일 후 자동 확정 |
| 포인트 잔액 | `GET /api/users/{userId}/points` → `available/held/escrow/pendingSettlement/withdrawalProcessing/withdrawable/lastChangedAt` | 같은 경로, 필드는 `available/bidHeld/tradeEscrow/settling/withdrawing/updatedAt` |
| 포인트 내역 | `GET /api/users/{userId}/points/logs` | 같은 경로. 필드는 `id/type/amount/balanceAfter/refType/refId/createdAt`(요청한 `title/status/memo` 없음). `type`은 `CHARGE/BID_HOLD/BID_RELEASE/PAYMENT/SETTLEMENT/REFUND/WITHDRAW`(요청한 `USE/HOLD_RELEASE/WITHDRAWAL`과 이름이 다름). `flow`/기간 필터 쿼리는 없음 — `type`만 별도 엔드포인트(`/withdrawals`)로 나뉜다 |
| 포인트 충전 | `POST /api/users/{userId}/points/charges` body `{amount, paymentMethod}` | 같은 경로, body는 `{amount}`만 — 결제 수단 없음(PG 연동 없는 테스트/데모 전용 API라 결제 수단 선택 자체가 무의미) |
| 출금 신청 | `POST /api/users/{userId}/withdrawals` body `{amount, account:{...}}` | 같은 경로, body는 `{amount}`만 — **출금 계좌 관리 기능 자체가 없다**(아래 미반영 참고) |
| 출금 내역 | `GET /api/users/{userId}/withdrawals` | 같은 경로, `PageResponse` 형태(`content/page/size/totalElements/totalPages/hasNext`) |

## 여전히 미반영 — 남은 요청

### 1. 환불 (REFUND-001/002)

- 요청 목적: 환불 요청과 검토 상태를 관리한다.
- 요청 데이터: 주문 id, 환불 사유, 상세 사유
- 응답 데이터: `refundId`, `orderId`, `reason`, `detailReason`, `status`, `requestedAt`, `reviewedAt`, `rejectionReason`
- 현재 BE에 관련 엔드포인트·엔티티 없음(`docs/APIs.md` 환불 섹션 미구현으로 표시돼 있음).

### 2. 출금 계좌 관리 (POINT-003)

- 요청: `GET /api/users/{userId}/points/account` — 은행명/계좌번호/예금주 조회.
- 현재 BE에 계좌 저장 기능 자체가 없다. 출금 신청(`POST /withdrawals`)도 금액만 받고 계좌 정보를 받지
  않는다 — 실제 송금 처리(관리자 승인·계좌 이체)는 애초에 범위 밖이라, 신청까지만 하고 완료 처리는
  DB 직접 조작으로 가정한 상태다(`PointService` 클래스 주석 참고).
- 계좌 등록/수정 API를 별도로 만들지, 출금 신청 body에 매번 포함시킬지는 여전히 협의 필요.

### 3. 오류 코드

기존 요청은 `POINT_INSUFFICIENT`/`POINT_ACCOUNT_REQUIRED`/`POINT_WITHDRAWAL_MIN_AMOUNT`/
`POINT_CHARGE_MIN_AMOUNT`/`POINT_FORBIDDEN_USER`를 제안했는데, 실제 BE `ErrorCode`는 다음만 있다.

| 상황 | 실제 코드 |
| --- | --- |
| 포인트 잔액 부족(충전/출금/결제 공통) | `INSUFFICIENT_POINTS`(`W001`) |
| 본인 아닌 사용자 처리 시도 | `MEMBER_FORBIDDEN`(`U013`, 지갑 전용 코드 아니고 공용) |
| 계좌 없음 | 없음 — 계좌 기능 자체가 없어서(위 2번) |
| 최소 충전/출금 금액 미달 | 없음 — 현재 최소 금액 제한이 없다(`@Positive`만 검증, 1원도 가능) |

최소 금액 제한, 계좌 필수 여부는 BE가 아직 정책을 안 정한 상태다. FE가 최소 금액을 화면에서 강제하고
싶다면 당분간 FE 자체 기준(요청서의 충전 1,000P/출금 10,000P)으로 두고, BE 정책이 정해지면 다시 맞춘다.
