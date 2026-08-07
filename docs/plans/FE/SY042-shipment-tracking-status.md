# SY042 구매/판매 내역 배송 진행 상태 연동

## 배경/목표

BE가 `docs/requests/FE/038-shipment-tracking-status-contract.md`(SY034 6번)로 `OrderShipmentResponse`에 `trackingStatus`(12개 값)/`trackingStatusLabel`(한글) 필드를 추가했고, 코드로도 확인됨(`OrderShipmentResponse.java`). 그런데 FE는 아직 이 필드를 전혀 소비하지 않는다 — 구매 내역(`MyOrderDetailPage.vue`)/판매 내역(`MySaleDetailPage.vue`)의 "배송 상태" 행이 지금은 `order.status`(PAID/SHIPPING/DELIVERED 3단계)만 보여줘서, 택배가 집하 중인지 배송 출발했는지 등 세부 진행 상황을 알 수 없다. 두 화면에 `trackingStatusLabel`을 노출해 실제 배송 조회가 되게 한다.

## 작업 내용

1. `shipping.types.ts`: `TrackingStatus` 유니온 타입 신설(038 문서 12개 값: `PENDING`/`REGISTERED`/`PICKUP_READY`/`PICKED_UP`/`IN_TRANSIT`/`OUT_FOR_DELIVERY`/`DELIVERED`/`FAILED`/`RETURNED`/`CANCELLED`/`HOLD`/`UNKNOWN`). `OrderShipmentInfo`에 `trackingStatus: TrackingStatus | null`, `trackingStatusLabel: string | null` 추가.
2. `shipmentApi.ts`, `orderApi.ts`: 각자 갖고 있는 `BackendOrderShipmentDto`/`toShipmentInfo`(두 파일에 중복 정의돼 있음, 이번 범위에서는 구조를 유지하고 필드만 추가)에 신규 필드 매핑 추가.
3. `MyOrderDetailPage.vue`/`MySaleDetailPage.vue`: "배송 상태" `dd`를 `order.status` 라벨 대신 `shipment.trackingStatusLabel`로 교체. `trackingStatus`가 `null`(웹훅 아직 안 옴)이면 038 안내대로 "송장 등록됨"으로 폴백 표시. 구매확정 버튼 활성화 조건(`canConfirm`)은 그대로 `order.status === 'DELIVERED'` 유지(038이 "버튼 게이팅에는 안 쓴다"고 명시).

## 구현 목록

- [x] `shipping.types.ts`: `TrackingStatus` 타입 + `OrderShipmentInfo` 필드 추가
- [x] `shipmentApi.ts`, `orderApi.ts`: DTO/매핑에 `trackingStatus`/`trackingStatusLabel` 추가
- [x] `MyOrderDetailPage.vue`: 배송 상태 표시를 `trackingStatusLabel`(null 폴백 포함)로 교체
- [x] `MySaleDetailPage.vue`: 동일 적용
- [x] `npm run type-check`, `npm run lint` 통과

## 추가 수정 (구현 후 발견)

BE의 배송 웹훅 구독 실패 폴백(`deliveryapi.co.kr` 자격증명 없는 환경 등)이 `order.status`만 `DELIVERED`로 즉시 확정하고 `shipment.trackingStatus`는 영영 `null`로 남기는 구조적 갭을 발견(`docs/requests/BE/045-shipment-fallback-tracking-status-gap.md`). `trackingStatusLabel`만 믿으면 이 경로에서 "배송 완료"가 영원히 안 뜨는 버그가 생겨, `shipmentStatusLabel` computed를 추가해 `trackingStatusLabel`이 없을 때 `order.status === 'DELIVERED'`면 "배송 완료"로 보정하도록 두 페이지 모두 수정. 판매 내역 페이지의 `refreshOrderStatus`도 `order`만 갱신하고 `shipment`는 갱신 안 하던 버그를 같이 고쳐(`refreshOrderAndShipment`로 통합) 송장 등록/환불 처리 후 배송 정보도 함께 새로고침되게 함.

- [x] `shipmentStatusLabel` computed 추가(양쪽 페이지) — `trackingStatusLabel` 없으면 `order.status` 기준 보정
- [x] `MySaleDetailPage.vue`: `refreshOrderStatus` → `refreshOrderAndShipment`(shipment도 재조회)
- [x] `docs/requests/BE/045` 작성(BE 폴백 경로의 근본 원인 공유, 비블로킹)
