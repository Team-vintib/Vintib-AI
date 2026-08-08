# SY045 환불 요청 알림 + 판매 대시보드 노출 (REFUND-001/002)

## 배경/목표

`docs/requests/BE/041-refund-notification-dashboard.md`. 환불 요청이 판매자 알림·대시보드
어디에도 안 떠서, 판매자가 주문 상세를 직접 열어보기 전까지 알 방법이 없다.

## 작업 내용

- **`REFUND_REQUESTED`**: `RefundService.requestRefund()` 성공 시 판매자에게 알림.
- **`REFUND_REJECTED`**: `RefundService.reviewRefund()` 거절 시 구매자에게 알림(사유 그대로 body에).
- **승인(`REFUND_APPROVED`)은 새로 만들지 않는다.** `PointService.refundOrder()`가 승인 시점에
  이미 구매자에게 `POINT_REFUNDED`("환불이 완료되었습니다")를 보내고 있어(041 문서 작성 시점엔
  몰랐던 기존 코드) — 같은 이벤트에 알림이 두 번 생기는 걸 피하려고 그대로 둔다.
- **`refType`/`refId`는 요청이 제안한 `REFUND`/환불ID 대신 기존 `ORDER`/`orderId`를 그대로 쓴다**
  (041 §4가 허용한 대안). 이미 `ORDER_PAID`/`SHIPMENT_STARTED`/`SHIPMENT_COMPLETED`가 같은
  방식이라, FE 라우팅 코드를 추가로 분기할 필요가 없다.
- `NotificationCategory`에 새 type을 추가하지 않는다 — `ORDER_PAID`와 같은 이유로 `TRADE`
  catch-all에 자동으로 떨어진다(의도된 동작, `NotificationCategoryTest` 참고).
- `OrderListItemResponse`에 `refundRequested: boolean` 추가(`order.isRefundRequested()` 그대로).

## 구현 목록

- [x] `RefundService`에 `NotificationCommandPort` 주입, `requestRefund`/`reviewRefund`(거절)에
      알림 추가
- [x] `OrderListItemResponse.refundRequested` 추가
- [x] `NotificationCommandPort` Javadoc에 새 dedup 근거 추가
- [x] 테스트: 요청 시 알림, 거절 시 알림, 승인 시 알림 없음(중복 방지) 검증
- [x] `docs/APIs.md` 반영, `041` 요청 문서 삭제
