# 045 배송 즉시-확정 폴백 시 trackingStatus 미갱신

- 요청자 파트: FE
- 대상 파트: BE
- 우선순위: 참고용(현재 FE에서 보정 완료, 블로킹 아님)

## 배경

`docs/requests/FE/038-shipment-tracking-status-contract.md`로 받은 `trackingStatus`/`trackingStatusLabel`을 구매/판매 내역 상세에 노출했는데, `deliveryapi.co.kr` 웹훅 구독이 실패하는 환경(API 자격증명 미설정 등 — 로컬/개발 환경에서 항상 이 경로)에서는 `trackingStatus`가 영원히 `null`로 남는 걸 확인했습니다.

`OrderService.registerShipment()`가 `deliveryTrackingClient.subscribe()` 실패 시 즉시 `deliver()`를 호출해 `order.status`는 `DELIVERED`로 바뀌지만, `deliver()` → `OrderShipment.markDelivered()`는 `deliveredAt`만 채우고 `trackingStatus`는 건드리지 않습니다(`updateTrackingStatus()`는 실제 웹훅 경로에서만 호출됨). 그 결과 이 폴백 경로를 탄 주문은 `order.status: DELIVERED`인데 `shipment.trackingStatus: null`인 상태로 영구히 남습니다.

## 현재 처리

FE는 `order.status === 'DELIVERED'`면 `trackingStatus`가 없어도 "배송 완료"로 표시하도록 보정해뒀습니다(구매확정 버튼 게이팅은 여전히 `order.status`만 사용, 038 원칙 그대로). 그래서 지금 당장 막힌 건 없습니다.

## 참고용 제안

`deliver()`(`OrderService.java`)에서 `shipment.markDelivered(deliveredAt)` 옆에 `shipment.updateTrackingStatus(TrackingStatus.DELIVERED)`도 같이 호출하면, 폴백 경로에서도 `trackingStatus`가 실제 상태를 반영하게 되어 FE의 보정 로직이 불필요해집니다. 급하지 않으면 다음에 이 도메인 만질 때 참고해주세요.

## 관련 자료

- `docs/requests/FE/038-shipment-tracking-status-contract.md`
- `docs/plans/FE/SY042-shipment-tracking-status.md`
- `BE/src/main/java/com/ssafy/backend/order/service/OrderService.java`(`registerShipment`, `deliver`, `updateShipmentTracking`)
- `BE/src/main/java/com/ssafy/backend/order/entity/OrderShipment.java`(`markDelivered`, `updateTrackingStatus`)
