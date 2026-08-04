# SY037 - 환불 요청·승인/거절 (REFUND-001/002, 이슈 509)

## 배경/목표

구매한 상품에 하자가 있는 등의 사유로 구매자가 환불을 요청하고, **판매자**가 승인/거절하는 흐름을
추가한다. 승인되면 보관 중이던 거래 대금(`tradeEscrow`)을 판매자에게 정산하지 않고 구매자 `available`
포인트로 되돌린다. `docs/APIs.md`에 이미 미구현으로 표시돼 있던 엔드포인트 3개(`GET/POST
/orders/{id}/refunds`, `PATCH /refunds/{id}`)를 채운다.

- **승인 주체 관련 확인**: FE `기능 정의서`의 REFUND-002는 승인/거절 대상을 "운영 정책"(운영자 확인)으로
  적어뒀고 우선순위도 필수/추가가 아닌 "운영 정책" 단계다. 이 프로젝트엔 운영자/관리자 역할 자체가
  없어(회원은 GENERAL/BUSINESS만 있음) 운영자 승인을 그대로 구현하려면 관리자 인증·권한 체계부터
  새로 만들어야 한다. 이번 요청은 그 대신 **판매자가 승인/거절**하는 것으로 명시적으로 지정받았다 —
  기능정의서 문서와 달라지는 지점이라 여기 남긴다.
- **환불 요청 가능 시점**: 기능정의서 REFUND-001 사유에 "미발송"도 있어 배송 완료 전(PAID/SHIPPING
  단계)에도 환불을 요청할 수 있어야 한다. 이미 정산까지 끝난 주문(CONFIRMED/SETTLED)은 판매자가 이미
  포인트를 받은 뒤라 되돌리려면 판매자 잔액을 강제로 차감해야 하는 별도 로직이 필요해 이번 범위에서는
  제외한다 — 즉 환불 요청은 `PAID`/`SHIPPING`/`DELIVERED` 상태에서만 가능하고, 구매 확정(수동/자동)
  이후에는 요청할 수 없다.
- **증빙 자료**: 기능정의서는 "사유와 증빙 자료를 제출해야 한다"고 돼 있지만, 이번 요청 범위에 이미지
  첨부 언급이 없어 제외한다. 사유(enum)+상세 사유(자유 텍스트)까지만 받는다. 필요해지면 이미지 업로드는
  `ProductImageService`/`MemberImageService`와 같은 presigned URL 패턴으로 별도 계획을 잡는다.

## 작업 내용

### 1. 환불 요청 (REFUND-001)

새 도메인 패키지 `com.ssafy.backend.refund` 신설.

- 엔티티 `RefundRequest`: `order`(FK), `reason`(enum), `detailReason`(text), `status`(enum
  `REQUESTED`/`APPROVED`/`REJECTED`), `rejectionReason`(nullable), `reviewedAt`(nullable) +
  `BaseTimeEntity`(createdAt=요청 시각, updatedAt).
  - `reason` enum은 기능정의서 REFUND-001 사유를 그대로 옮긴다: `NOT_AS_DESCRIBED`(설명과 실제 상품
    불일치), `UNDISCLOSED_DEFECT`(미고지 하자), `NOT_SHIPPED`(미발송), `DUPLICATE_PAYMENT`(중복 결제),
    `SYSTEM_ERROR`(시스템 오류). "단순 변심"에 해당하는 값은 기능정의서가 허용하지 않는다고 명시해
    두지 않는다(=UI/서버 모두 옵션에 안 둔다).
- `POST /api/orders/{orderId}/refunds` — 구매자만 가능. 주문 상태가 `PAID`/`SHIPPING`/`DELIVERED`
  중 하나여야 하고, 이미 `REQUESTED` 상태인 환불 요청이 있으면 거부(`REFUND_ALREADY_REQUESTED`) —
  거절된 뒤 재요청은 허용한다.
- `GET /api/orders/{orderId}/refunds` — 구매자·판매자 모두 조회 가능(최신순 목록).
- `Order`에 `refundRequested`(boolean, default false) 컬럼 추가. 요청 시 `true`로 표시해 다른 주문
  진행(송장 등록, 구매 확정, 자동 확정)을 막는 용도로만 쓴다 — 요청 중에는 `Order.status`를 바꾸지
  않는다(거절되면 원래 상태 그대로 이어가면 되므로 "이전 상태 기억" 로직이 필요 없다).

### 2. 환불 승인/거절 (REFUND-002)

`PATCH /api/refunds/{refundId}` — 판매자만 가능(`order.isSeller`). body: `{ "decision": "APPROVED" |
"REJECTED", "rejectionReason": string|null }`(`REJECTED`일 때 `rejectionReason` 필수). 이미
`REQUESTED`가 아니면 거부(`REFUND_ALREADY_REVIEWED`).

- 승인(`APPROVED`): `PointService.refundOrder(buyerId, amount, orderId)` 신규 — 구매자
  `tradeEscrow -= amount`, `available += amount`로 바로 돌려주고(판매자에게는 아무 것도 정산하지
  않음) `PointTransaction(REFUND, amount=+amount)` 기록(`PointTransactionType.REFUND`는 이미 존재).
  `Order.refundRequested=false`, `Order.status=REFUNDED`로 전이.
- 거절(`REJECTED`): `Order.refundRequested=false`만 하고 `status`는 그대로 둔다 — 원래 진행하던
  배송/구매확정 흐름을 이어갈 수 있다(예: `DELIVERED`였다면 여전히 3일 자동 확정 대상).

### 3. 기존 주문 흐름 가드

`refundRequested=true`인 동안 아래를 막는다.

- `OrderService.registerShipment`: 상태 체크에 더해 `refundRequested`면 거부.
- `OrderService.settle`(수동 확정 `confirmOrder` + 자동 확정 공용): `refundRequested`면 거부.
- `OrderService.autoConfirmDueOrders` 조회 쿼리 자체에 `refundRequested=false` 조건을 추가한다 —
  스케줄러 배치가 한 건이라도 예외를 던지면 `@Transactional` 전체가 롤백돼 그 배치의 다른 정상 주문까지
  같이 실패하기 때문에, 쿼리 단계에서 걸러내는 쪽이 안전하다.

### 4. 에러 코드

| 상황 | 코드 |
| --- | --- |
| 환불 대상 주문이 아님(이미 CONFIRMED/SETTLED 등) | `INVALID_ORDER_STATE`(기존 O001 재사용) |
| 이미 진행 중인 환불 요청이 있음 | `REFUND_ALREADY_REQUESTED`(신규) |
| 존재하지 않는 환불 요청 | `REFUND_NOT_FOUND`(신규) |
| 이미 승인/거절 처리된 요청을 다시 처리하려 함 | `REFUND_ALREADY_REVIEWED`(신규) |
| 구매자/판매자 아님 | 기존 `ORDER_BUYER_ONLY`/`ORDER_SELLER_ONLY` 재사용 |

### 5. 최소 충전/출금 금액 10,000원 (별도 요청, 계획 불필요한 정책 변경이라 이미 반영)

`PointChargeRequest`/`PointWithdrawalRequest`의 `@Positive`를 `@Min(10_000)`으로 교체 — 이건 기존
API의 검증 규칙만 바꾸는 것이라 새 도메인 로직이 아니어서 계획 승인 없이 바로 반영했다(BE/CLAUDE.md
"버그 수정 등 설계 판단이 필요 없는 변경" 기준).

## 구현 목록

- [x] `PointChargeRequest`/`PointWithdrawalRequest` 최소 금액 10,000원(`@Min`)으로 변경
- [x] `refund.entity.RefundRequest`, `refund.entity.RefundReason`, `refund.entity.RefundStatus` 추가
- [x] `refund.repository.RefundRequestRepository` 추가(주문별 최신순 조회, `order_id`+`status`로 활성 요청 조회)
- [x] `Order`에 `refundRequested` 컬럼 + `markRefundRequested()`/`clearRefundRequested()`/`markRefunded()` 추가
- [x] `docs/db/schema.sql`에 `refund_request` 테이블 + `orders.refund_requested` 컬럼 추가, `comments.sql` 갱신 후 regen
- [x] `PointAccount`에 `refund(amount)` 추가(`tradeEscrow -= amount`, `available += amount`)
- [x] `PointService`에 `refundOrder(buyerId, amount, orderId)` 추가 + 테스트
- [x] `refund.service.RefundService`: `requestRefund`, `getRefunds`, `reviewRefund`(승인/거절) + 테스트
- [x] `OrderService.registerShipment`/`settle`에 `refundRequested` 가드 추가, `autoConfirmDueOrders` 조회 쿼리에 `refundRequested=false` 조건 추가 + 테스트
- [x] `refund.controller.RefundController`: `POST/GET /api/orders/{orderId}/refunds`, `PATCH /api/refunds/{refundId}` + Swagger 문서화
- [x] `RefundCreateRequest`, `RefundReviewRequest`, `RefundResponse` DTO 추가
- [x] `ErrorCode`에 `REFUND_ALREADY_REQUESTED`/`REFUND_NOT_FOUND`/`REFUND_ALREADY_REVIEWED` 추가(R001~R003)
- [x] `docs/APIs.md` 환불 3개 행 구현 완료(✓)로 갱신 + 7일→3일 잔여 문구 정리
- [x] `BE/README.md`에 `refund` 패키지 설명 추가
- [x] `docs/requests/BE/010-commerce-wallet-contract.md` 전체 반영 완료로 삭제(환불 포함 남은 요청 모두 해소), `012-be-request-index.md` 갱신
- [x] `.claude/skills/verify`로 최종 검증 — `BUILD SUCCESSFUL`

## 확인 필요 사항

- **승인 주체를 판매자로 확정** — 기능정의서 원문(운영 정책/운영자)과 다르다는 점을 위 배경에 남겨뒀다.
  나중에 운영자 콘솔이 생기면 이 부분을 다시 논의해야 한다.
- **환불 가능 시점을 `PAID`/`SHIPPING`/`DELIVERED`로 확정** — `CONFIRMED`/`SETTLED` 이후(이미 판매자
  정산 완료) 환불은 이번 범위에서 지원하지 않는다. 정산 후 환불이 필요해지면 판매자 잔액 차감 로직을
  별도로 설계해야 한다.
- **증빙 자료(이미지) 업로드는 이번 범위에서 제외** — 필요하면 별도 계획으로 분리한다.
- **재요청 허용**: 거절된 이후 같은 주문으로 다시 요청할 수 있게 열어둔다(사유가 다를 수 있어서). 막고
  싶다면 알려달라.