# 039 주문·배송·포인트 알림 6종 반영

- **작성자 파트**: BE (서윤) / **대상 파트**: FE
- **작성일**: 2026-08-07
- **원 요청**: `docs/requests/BE/004-social-notification-contract.md` §3.2(알림 생성 이벤트, 나머지 5개)

004에서 남아 있던 주문·배송·포인트 알림을 전부 반영했습니다. `OrderService`(3종)·`PointService`
(3종)에서 각각 `NotificationCommandPort`로 직접 알림을 만듭니다.

| type | 트리거 시점 | refType/refId | title/body | 받는 사람 |
| --- | --- | --- | --- | --- |
| `ORDER_PAID` | 상시 판매 상품 구매 또는 경매 낙찰로 주문이 결제될 때 | `ORDER` / orderId | "상품이 판매되었습니다" / "주문이 결제됐어요. 배송지를 확인하고 송장을 등록해주세요." | 판매자 |
| `SHIPMENT_STARTED` | 판매자가 송장을 등록할 때 | `ORDER` / orderId | "배송이 시작되었습니다" / "판매자가 송장을 등록했어요." | 구매자 |
| `SHIPMENT_COMPLETED` | 배송완료 웹훅을 받아 주문이 배송완료로 바뀔 때 | `ORDER` / orderId | "배송이 완료되었습니다" / "구매를 확정하면 거래가 끝나요. 확정하지 않으면 3일 후 자동으로 처리됩니다." | 구매자 |
| `POINT_CHARGED` | 포인트 충전이 완료될 때 | `POINT` / point transaction id | "포인트가 충전되었습니다" / "{금액}원이 충전됐어요." | 충전한 회원 |
| `POINT_REFUNDED` | 주문 환불이 완료될 때 | `POINT` / point transaction id | "환불이 완료되었습니다" / "{금액}원이 환불됐어요." | 환불받는 회원 |
| `WITHDRAW_COMPLETED` | 출금 신청이 접수될 때 | `POINT` / point transaction id | "출금이 신청되었습니다" / "{금액}원 출금이 접수됐어요." | 출금 신청한 회원 |

- 위 6종 모두 `refType`/`refId`가 반드시 채워집니다.
- **`SHIPMENT_STARTED`/`SHIPMENT_COMPLETED`의 `refType`은 `SHIPMENT`가 아니라 `ORDER`입니다.**
  `OrderShipment`가 `Order`와 PK를 공유해서(같은 값) 굳이 별도 refType을 두지 않았습니다. FE의
  현재 임시 이동 규칙(004 §3.1)이 이미 `ORDER`/`SHIPMENT`/`SHIPPING` 전부를
  `/my?section=orders`로 보내고 있어서 그대로 두셔도 됩니다.
- `type` 문자열에 `SHIP`/`POINT`/`WITHDRAW`가 포함되는 현재 FE 임시 분류 규칙(004 §3.1)도 위
  6종을 그대로 통과합니다 — 분류 규칙을 바꾸지 않아도 됩니다.
- 경매 낙찰로 주문이 생성될 때 판매자에게 보내는 `ORDER_PAID`는 이번 범위에서 뺐습니다 —
  `AuctionCloseService`는 판매자 `Member`가 아니라 port로 노출된 id만 들고 있어서, 필요해지면
  포트를 먼저 확장해야 합니다. 필요하시면 별도로 알려주세요.

이제 004에 남아 있던 "실제 알림 생성 이벤트가 없어 시연 데이터가 없다"는 문제가 8종 전부 해소됐습니다.
