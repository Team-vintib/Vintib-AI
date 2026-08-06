# 030 주문 정산 완료 시각 필드 요청

- 요청자 파트: FE
- 대상 파트: BE

## 배경/이유

마이페이지 "판매자 대시보드"에 실제 판매 데이터를 연동하면서(월별 수익 바 그래프, 마지막 정산일 등)
정산이 언제 이뤄졌는지를 알아야 하는데, `GET /users/{userId}/orders` 응답
(`OrderListItemResponse`)에는 `createdAt`(주문 생성일)만 있고 상태가 언제 `SETTLED`로
바뀌었는지 알 수 있는 시각 필드가 없다. `Order` 엔티티는 `BaseTimeEntity`를 상속해
`updatedAt`을 갖고 있지만 DTO에 매핑돼 있지 않다.

당장은 `createdAt`(주문 생성일)을 정산일 근사치로 써서 월별 수익 그래프/마지막 정산일을
표시하기로 사용자와 합의했다. 다만 주문 생성 시점과 실제 정산 완료 시점(구매확정 시) 사이에
차이가 있을 수 있어(예: 이번 달에 산 상품을 다음 달에 구매확정하면 그래프상 이번 달 매출로
잡힘), 정확한 필드가 생기면 교체할 계획이다.

## 요청 내용

- `OrderListItemResponse`(`GET /users/{userId}/orders`)에 정산 완료 시각을 내려 주세요.
  - `Order.updatedAt`을 그대로 노출해도 되고, 별도 `settledAt` 필드를 신설해도 됩니다
    (상태가 `SETTLED`가 아닌 주문은 `null`).
- 필드가 추가되면 FE는 `docs/plans/FE/`에 남긴 대시보드 집계 로직에서 `createdAt` 대신 이
  필드로 교체하겠습니다.

## 관련 자료

- `BE/src/main/java/com/ssafy/backend/order/entity/Order.java` (`confirmAndSettle()` —
  "정산 대기 절차가 없어 CONFIRMED를 거쳐 곧바로 SETTLED로 끝난다" 주석)
- `BE/src/main/java/com/ssafy/backend/order/controller/MyOrderController.java`,
  `OrderListItemResponse`
- `FE/src/domains/my/api/myApi.ts` `buildSellerDashboardMetrics`/`buildMonthlyRevenue`
