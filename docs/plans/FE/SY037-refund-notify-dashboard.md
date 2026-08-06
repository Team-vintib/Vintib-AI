# SY037 환불 요청 알림 연결 + 판매 대시보드 노출

## 배경/목표

구매자가 환불을 요청하면 판매자는 해당 주문 상세에서 승인/거절할 수 있지만, 알림센터와 판매 대시보드 어디에도 뜨지 않아 주문을 직접 열어보기 전에는 존재를 알 방법이 없다. 알림센터에서 해당 주문으로 바로 이동하게 하고, 판매 대시보드 "처리할 일" 카드에 환불 요청 개수를 추가한다.

**선행 조건**: `docs/requests/BE/041-refund-notification-dashboard.md` — BE가 (1) 환불 요청 시 판매자에게, 승인/거절 시 구매자에게 알림(`refType: REFUND`, `refId: orderId`, `type: REFUND_REQUESTED`/`REFUND_APPROVED`/`REFUND_REJECTED`)을 만들고 (2) `GET /users/{userId}/orders?role=SELLER` 응답에 `refundRequested: boolean`을 추가해 줘야 실제 데이터가 흐른다. FE 코드는 이 문서 승인 즉시 먼저 구현해 두고(BE 필드가 아직 없어도 타입/분기만 추가하는 안전한 변경), BE가 반영되면 바로 동작한다.

## 작업 내용

1. **알림 라우팅**: `getNotificationRoute`(`FE/src/domains/notification/constants/notificationOptions.ts`)의 파라미터를 `type`까지 받도록 넓히고, `refType === 'REFUND'`일 때 `type`으로 대상을 나눈다 — `REFUND_REQUESTED`(판매자 알림)는 `ROUTE_NAMES.MY_SALE_DETAIL`(`params: { saleId: refId }`)로, `REFUND_APPROVED`/`REFUND_REJECTED`(구매자 알림)는 `ROUTE_NAMES.MY_ORDER_DETAIL`(`params: { orderId: refId }`)로 보낸다. 카테고리 분류(`getNotificationCategory`)는 기존 로직대로 `TRADE`(거래)로 떨어지므로 별도 케이스 불필요.
2. **판매 대시보드 to-do 카드**: `MyTodoCounts`(`FE/src/domains/my/types/my.types.ts`)에 `refundRequests: number` 필드를 추가하고, `buildSellerDashboardMetrics`(`FE/src/domains/my/api/myApi.ts`)에서 `shippingPending`과 같은 방식으로 `sellerOrders.filter((order) => order.refundRequested).length`로 채운다. `OrderListItemDto`에도 `refundRequested: boolean` 필드를 추가한다.
3. **대시보드 UI**: `MyPage.vue`의 `todoCards` computed에 `{ label: '환불 요청', value: todo?.refundRequests ?? 0, section: 'sales' }` 카드를 추가한다(기존 "배송 대기" 카드와 동일한 패턴 — 클릭 시 판매 섹션으로 이동, 특정 주문으로 딥링크하지는 않음. 특정 주문 확인은 알림 클릭 경로로 충분하다고 판단).

## 구현 목록

- [x] `notificationOptions.ts`: `getNotificationRoute`가 `type`도 받도록 시그니처 확장, `REFUND` → `MY_SALE_DETAIL`(요청) / `MY_ORDER_DETAIL`(승인·거절) 분기 추가
- [x] 호출부(`notificationApi.ts`의 `toNotificationItem`)는 이미 `NotificationItemDto` 전체를 넘기고 있어 별도 수정 불필요 — `type` 필드가 그대로 전달됨을 확인
- [x] `my.types.ts`: `MyTodoCounts.refundRequests` 필드 추가
- [x] `myApi.ts`: `OrderListItemDto.refundRequested?` 필드 추가(BE 반영 전이라 optional), `buildSellerDashboardMetrics`에서 집계해 `SellerDashboardMetrics`/`MyTodoCounts`에 반영
- [x] `MyPage.vue`: `todoCards`에 "환불 요청" 카드 추가
- [x] `myMockData.ts`: `MyTodoCounts` mock에도 `refundRequests` 반영(타입 에러 수정 겸)
- [x] `MySaleDetailPage.vue` 확인 — `refunds`를 `onMounted`에서 무조건 조회하고 `activeRefund || latestRefund`면 패널이 자동으로 뜬다(`:52-53`, `:95`, `:350`). 추가 스크롤/포커스 로직 불필요.

FE 코드는 완료. `docs/requests/BE/041-refund-notification-dashboard.md`이 반영되기 전까지는 `refundRequested`가 항상 `undefined`/`false`로 내려와 "환불 요청" 카드가 0으로 보이고, REFUND 알림 자체가 생성되지 않아 라우팅 분기도 아직 실사용되지 않는다. BE 반영 후 별도 FE 변경 없이 바로 동작한다.
