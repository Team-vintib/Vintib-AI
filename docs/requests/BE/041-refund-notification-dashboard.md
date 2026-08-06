# 041 환불 요청 알림 + 판매 대시보드 노출 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 구매자가 환불을 요청해도 판매자에게 알림이 가지 않고 판매 대시보드에도 안 떠서, 판매자가 주문 상세를 직접 열어보기 전에는 환불 요청이 있었는지 알 방법이 없다. 알림·대시보드에서 발견 가능하게 만든다.
- 우선순위: P1

## 2. 배경

- `RefundService.requestRefund`/`reviewRefund`(`BE/src/main/java/com/ssafy/backend/refund/service/RefundService.java`)는 알림을 전혀 만들지 않는다. `Notification.builder()` 호출은 코드베이스 전체에서 `live/port/NotificationCommandAdapter.java` 한 곳뿐이다(`docs/requests/BE/004-social-notification-contract.md` §3.2에도 환불 알림은 아예 없음).
- `Order.refundRequested`(boolean, `BE/src/main/java/com/ssafy/backend/order/entity/Order.java:84`)는 이미 정확한 신호다 — 요청 시 `true`(`markRefundRequested`), 승인/거절 시 `false`(`markRefunded`/`clearRefundRequested`)로 정리된다. 그런데 이 필드가 어떤 주문 응답 DTO에도 노출되지 않는다(`OrderListItemResponse` 등).
- FE 판매 대시보드(`MyPage.vue` 상단 "처리할 일" 카드)는 `GET /api/users/{userId}/orders?role=SELLER` 응답을 그대로 받아 클라이언트에서 집계한다(`FE/src/domains/my/api/myApi.ts` `buildSellerDashboardMetrics`, `shippingPending`처럼). 판매자 단위 환불 집계 API가 없다는 이유로 이 카드는 `docs/plans/FE/SY036-seller-dashboard-api.md`에서 한 번 범위 제외됐었다.

## 3. 추가 구현 요청

### 3.1 환불 요청 시 판매자에게 알림 생성

- Method / Endpoint: 없음(트리거 — `RefundService.requestRefund` 내부에서 알림 도메인 호출)
- 요청 목적: 구매자가 환불을 요청하면 판매자가 알림센터에서 바로 알 수 있게 한다.
- 패턴 제안: `live/port/NotificationCommandPort`와 같은 구조로 `refund` 도메인 전용 포트(예: `refund/port/RefundNotificationPort` + 어댑터)를 두고, `requestRefund` 성공 시 판매자(`order.getSeller()`)에게 알림 1건을 만든다.
- 알림 필드 제안:
  - `type`: `REFUND_REQUESTED` (신규)
  - `refType`: `REFUND` (신규 — 기존 `ORDER`는 FE에서 이미 "주문 목록"으로 라우팅되는 의미로 쓰고 있어서, 특정 주문 상세로 바로 보내야 하는 이 케이스는 구분하는 편이 낫다고 판단)
  - `refId`: **`orderId`** (환불 요청 ID가 아니라 주문 ID로 부탁한다 — FE는 판매자 주문 상세 화면을 `saleId`=주문 ID로 라우팅한다)
  - `title`/`body`: 예) "환불 요청이 접수되었습니다" / 상품명 등 (문구는 BE 재량)

### 3.1-1 환불 승인/거절 시 구매자에게도 결과 알림 생성

- Method / Endpoint: 없음(트리거 — `RefundService.reviewRefund` 내부에서 알림 도메인 호출)
- 요청 목적: 구매자도 환불 처리 결과(승인/거절)를 알림으로 받게 한다.
- `reviewRefund` 성공 시 구매자(`order.getBuyer()`)에게 알림 1건 생성:
  - `type`: 승인이면 `REFUND_APPROVED`, 거절이면 `REFUND_REJECTED` (신규)
  - `refType`: `REFUND`
  - `refId`: **`orderId`** — FE는 구매자 주문 상세 화면을 `orderId`로 라우팅한다(`/my/orders/{orderId}`)
  - `title`/`body`: 예) "환불 요청이 승인/거절되었습니다" (문구는 BE 재량)

### 3.2 판매 대시보드용 환불 대기 여부 노출

- Method / Endpoint: 기존 `GET /api/users/{userId}/orders?role=SELLER` 응답(`OrderListItemResponse`)
- 요청 목적: FE가 `shippingPending`과 같은 방식으로 클라이언트에서 "환불 요청 대기" 개수를 집계할 수 있게 한다. 별도 집계 API를 새로 만들 필요는 없다 — 이미 받는 목록에 필드 하나만 추가되면 된다.
- 요청 데이터: 없음(응답 필드 추가만)
- 응답 데이터: `OrderListItemResponse`에 `refundRequested: boolean` 필드 추가 (`order.isRefundRequested()` 그대로 노출)
- 응답 예시:
  ```json
  { "orderId": 10, "...": "...", "status": "SHIPPING", "refundRequested": true, "createdAt": "2026-08-06T12:00:00" }
  ```

## 4. 확인 필요 사항

- `refType: REFUND`가 부담스러우면 대안으로 `refType: ORDER` + `refId: orderId`를 쓰고 FE가 `type`(=`REFUND_REQUESTED`/`REFUND_APPROVED`/`REFUND_REJECTED`)으로 분기하는 방법도 가능하다 — BE 쪽에서 더 자연스러운 쪽으로 결정해도 무방하다(FE 라우팅 코드에서 어느 쪽이든 대응 가능).

## 5. 관련 자료

- `docs/plans/BE/SY037-refund.md` — 환불 기능 원 설계(알림 언급 없음)
- `docs/plans/FE/SY036-seller-dashboard-api.md` — 환불 카드가 한 번 범위 제외된 근거
- `docs/requests/BE/004-social-notification-contract.md` §3.2 — 현재 반영된 알림 타입 목록(라이브/경매뿐, 환불 없음)
