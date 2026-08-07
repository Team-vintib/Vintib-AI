# 038 배송 진행 상태 필드 추가 (송장 조회 응답)

## 요청자 파트 / 대상 파트

BE → FE

## 배경/이유

지금까지는 배송 관련 응답에 "송장 등록됨"과 "배송완료" 두 시점만 있었다(`shippedAt`/`deliveredAt`).
구매자가 배송이 지금 어디까지 왔는지 볼 수 있어야 한다는 요구사항에 맞춰(`SY034` 6번), 배송사
웹훅이 보내는 중간 상태도 저장·노출하도록 바꿨다.

## 요청 내용

`OrderShipmentResponse`(송장/배송지 조회에 쓰이는 응답 — `GET /orders/{orderId}/shipment` 등)에
필드 2개가 추가됐다.

```jsonc
{
  // ...기존 필드(recipientName, courierCode, trackingNumber, shippedAt, deliveredAt 등)...
  "trackingStatus": "IN_TRANSIT",      // 신규. 12개 값 중 하나, 송장 등록 직후 첫 웹훅 전에는 null
  "trackingStatusLabel": "배송중"       // 신규. 화면에 그대로 표시할 한글 라벨
}
```

### `trackingStatus` 값 목록

| 값 | 한글 라벨 |
| --- | --- |
| `PENDING` | 접수 대기 |
| `REGISTERED` | 접수 완료 |
| `PICKUP_READY` | 집하 준비 |
| `PICKED_UP` | 집하 완료 |
| `IN_TRANSIT` | 배송중 |
| `OUT_FOR_DELIVERY` | 배송 출발 |
| `DELIVERED` | 배송 완료 |
| `FAILED` | 배송 실패 |
| `RETURNED` | 반송 |
| `CANCELLED` | 취소 |
| `HOLD` | 보류 |
| `UNKNOWN` | 알 수 없음 |

- **`trackingStatusLabel`을 그대로 써도 되고**, 자체 배지 디자인이 있으면 `trackingStatus` 값으로
  분기해도 된다.
- **구매확정 버튼 활성화 기준은 바뀌지 않는다** — 여전히 주문 상세의 `status == "DELIVERED"`로
  판단하면 된다. `trackingStatus`는 진행 상황 표시 전용이다(둘이 어긋나는 경합을 막기 위해
  일부러 분리했다).
- 웹훅이 아직 한 번도 안 왔으면(`courier`/`trackingNumber`는 있는데 상태 갱신 전) `trackingStatus`는
  `null`이다 — "송장 등록됨" 정도로 표시하면 된다.
- 실제 값이 얼마나 자주 바뀌는지는 deliveryapi.co.kr 폴링 주기(1시간, 22시~07시 KST는 폴링 안 함)에
  달려있다 — 실시간에 가깝게 계속 바뀌는 값이 아니다.

## 관련 자료

- 설계: `docs/plans/BE/SY034-delivery-tracking.md` 6번
- 구현: `OrderShipmentResponse`, `order.entity.TrackingStatus`, `DeliveryWebhookService`
