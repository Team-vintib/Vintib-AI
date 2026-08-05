# 즉시구매(포인트 결제) 및 구매/판매 내역 상세(배송·환불) 연결

## 배경/목표

상품 상세의 "구매하기" 버튼은 현재 스텁(`구매 확인 화면은 후속 스토리에서 연결됩니다` 토스트만 표시)이고,
마이페이지 구매/판매 내역 상세 페이지(`MyOrderDetailPage`/`MySaleDetailPage`)도 이미 라우팅은 되어 있지만
`getMyOrderDetail`/`getMySaleDetail`이 에러를 던지는 스텁이다. BE에는 주문 생성/배송지/송장/구매확정/환불
API가 전부 구현·문서화(`docs/APIs.md` 주문/배송/환불, 포인트 섹션 전부 ✓)되어 있으므로, 이번 작업은 그
API들을 FE에 실제로 연결하는 것이다: 포인트 잔액 기반 즉시구매 → 상품 판매완료 처리, 그리고 구매자/판매자
각각의 내역 상세에서 상품정보·구매정보·배송지·배송상태·구매확정·환불요청·(판매자) 송장등록·환불승인거절을
제공한다.

## 작업 내용

### 1. 즉시구매 플로우 (`ProductDetailView.vue` → `POST /orders` + `PATCH /orders/{id}/address`)

- "구매하기" 클릭 시 **페이지 이동 없이** 확인 다이얼로그(모달)를 띄운다 — 가격, 보유 포인트 잔액
  (`domains/point`의 `getPointBalance` 재사용, 잔액 부족 시 확인 버튼 비활성화 + 충전 페이지 링크),
  그리고 배송지 입력 폼(`recipientName`/`recipientPhone`/`zipcode`/`address1`/`address2`)을 함께 띄운다.
  배송지는 BE 계약상 주문 생성 API(`OrderCreateRequest`는 `productId`만 받는다)에 포함되지 않고 별도
  API(`PATCH /orders/{orderId}/address`, 주문 상태 `PAID`일 때만 가능)로만 등록되므로, 모달 확인 시
  `POST /orders { productId }` → 성공하면 이어서 `PATCH /orders/{orderId}/address`를 순차 호출한다.
- 두 호출 모두 성공하면 모달을 닫고 상품 상세 화면 그대로 유지하면서 `saleStatus`를 `SOLD`로 갱신(버튼
  라벨 "판매 완료"로 자동 전환), 성공 토스트에 "구매 내역 보기" 링크(`/my/orders/:orderId`)를 붙인다.
  `POST /orders`가 실패하면(포인트 부족, 이미 판매완료 등) BE 에러 메시지를 그대로 노출하고 아무 것도
  반영하지 않는다. `POST /orders`는 성공했는데 주소 등록만 실패하면(네트워크 오류 등) 주문 자체는 이미
  생성된 것이므로 "구매는 완료됐지만 배송지 등록에 실패했다, 구매 내역에서 다시 입력하라"는 안내와 함께
  구매 내역 상세로 이동할 수 있는 링크를 보여준다(상품은 이미 `SOLD` 처리).
- 구매 성공 후 `domains/point`의 잔액 갱신 이벤트(`pointBalanceEvents`)를 발행해 포인트 잔액 표시 UI(있다면)를
  동기화한다(포인트 충전 플로우와 동일 패턴).

### 2. 도메인 구조 — 기존 빈 스캐폴드(`domains/order|shipping|refund`)를 채운다

이미 `api/components/constants/pages/types` 하위 폴더까지 스캐폴딩되어 있고(`.gitkeep`만 존재), 이번 기능이
채워야 할 자리로 보인다. BE 엔드포인트 네임스페이스에 맞춰 분리한다:

- **`domains/order`**: 주문 생성/상세/배송지 API(`orderApi.ts`: `createOrder`, `getOrderDetail`,
  `getOrderAddress`, `updateOrderAddress`, `confirmOrder`), 주문 관련 타입(`OrderStatus`, `OrderDetail` 등
  BE `OrderListItemResponse` 필드 기준), 구매 확인 다이얼로그 컴포넌트.
- **`domains/shipping`**: 송장 조회/등록 API(`shipmentApi.ts`: `getShipment`, `registerShipment`), `CourierCode`
  10종 상수(코드→한글명, `docs/requests/FE/023-shipment-courier-code-contract.md` 기준 드롭다운 선택 UI),
  배송 정보 표시 컴포넌트.
- **`domains/refund`**: 환불 요청/목록/승인·거절 API(`refundApi.ts`: `createRefund`, `getRefunds`,
  `reviewRefund`), 환불 사유 5종 상수(`NOT_AS_DESCRIBED`/`UNDISCLOSED_DEFECT`/`NOT_SHIPPED`/
  `DUPLICATE_PAYMENT`/`SYSTEM_ERROR`), 구매자용 요청 폼 컴포넌트 + 판매자용 승인/거절 패널 컴포넌트.

`domains/my`의 `MyOrderDetailPage.vue`/`MySaleDetailPage.vue`는 이미 라우팅되어 있으므로 그 자리를
유지하되, 내부에서 `order`/`shipping`/`refund` 도메인 API를 조합해서 쓰도록 바꾼다. `myApi.ts`의
`getMyOrderDetail`/`getMySaleDetail` 스텁은 제거한다(목록 조회용 `getMyOrders`와 `my.types.ts`의
`MyOrderItem`/`MySaleItem`은 목록 카드용으로 그대로 두고, 상세 화면은 배송·환불 중첩 정보를 담는 별도 타입을
`domains/order`에 새로 정의한다).

### 3. 구매 내역 상세 (`MyOrderDetailPage`, 구매자 시점)

- 상품정보, 구매정보(가격/일시/주문상태 — 기존 `MY_ORDER_STATUS_LABELS` 재사용)는 기존 레이아웃 유지.
- 배송지: 구매 시 모달에서 이미 등록되지만, `PAID` 상태(송장 등록 전)까지는 수정 폼을 계속 제공한다(오타
  정정, 구매 시 주소 등록이 실패했던 경우의 재입력 등). 그 이후 상태(`SHIPPING` 이후)는 읽기 전용 표시.
- 배송 정보: 택배사명(`courierName`)·송장번호·배송 상태 라벨(주문 `status` 기반: 배송중/배송완료)·발송일시/
  도착일시. **"현재 위치"는 BE 응답에 없다** — 아래 미결정 사항 참고.
- 액션 버튼: 구매확정(`POST .../confirmation`, `DELIVERED` 상태에서만 노출), 환불요청(`PAID`/`SHIPPING`/
  `DELIVERED` 상태 & 처리 대기 중인 환불요청이 없을 때만 노출 — 사유 선택 + 상세사유 입력 폼).
- 환불요청을 이미 넣었다면 그 상태(`REQUESTED`/`APPROVED`/`REJECTED`, 거절 사유)를 표시한다.

### 4. 판매 내역 상세 (`MySaleDetailPage`, 판매자 시점)

- 상품정보, 판매정보(금액/일시/주문상태/정산상태 — 기존 `MY_SETTLEMENT_STATUS_LABELS` 재사용).
- 구매자가 등록한 배송지 표시(읽기 전용, `GET .../address`).
- 송장 등록 폼: `PAID` 상태이고 구매자가 배송지를 등록했을 때 노출(택배사 드롭다운 + 송장번호 입력 →
  `POST .../shipment`). 배송지 미등록 시 "구매자 배송지 입력 대기" 안내로 대체.
- 배송 정보(등록 후): 택배사명/송장번호/배송 상태 라벨.
- 환불요청이 들어와 있으면(`REQUESTED`) 승인/거절 패널 노출(`PATCH /refunds/{id}`, 거절 시 거절 사유 입력
  필수).

## 구현 목록

- [x] `domains/order/types/order.types.ts`, `domains/order/api/orderApi.ts`
      (`createOrder`/`getOrderDetail`/`getOrderAddress`/`updateOrderAddress`/`confirmOrder`)
- [x] `domains/shipping/types/shipping.types.ts`(`CourierCode` 등), `domains/shipping/api/shipmentApi.ts`
      (`getShipment`/`registerShipment`), `domains/shipping/constants`(택배사 코드↔한글명)
- [x] `domains/refund/types/refund.types.ts`, `domains/refund/api/refundApi.ts`
      (`createRefund`/`getRefunds`/`reviewRefund`), `domains/refund/constants`(사유 라벨)
- [x] `domains/order/components/PurchaseConfirmDialog.vue`(잔액 표시 + 배송지 입력 폼 포함) +
      `ProductDetailView.vue`의 `handlePurchase`를 실제 흐름(다이얼로그 → `POST /orders` →
      `PATCH .../address` → 성공 시 상품 상태 갱신·토스트)으로 교체
- [x] `MyOrderDetailPage.vue` 개편: 배송지 등록/수정 폼, 배송정보(택배사/송장/상태), 구매확정 버튼, 환불요청
      폼 및 상태 표시
- [x] `MySaleDetailPage.vue` 개편: 구매자 배송지 표시, 송장 등록 폼, 배송정보, 환불 승인/거절 패널
- [x] `myApi.ts`의 `getMyOrderDetail`/`getMySaleDetail` 스텁 제거, 상세 페이지가 새 도메인 API를 직접 호출
- [ ] 수동 확인: 구매 → 판매완료 처리 → 배송지 입력 → 송장 등록 → 구매확정/환불요청·승인 전체 플로우
      (BE 서버·로그인 세션이 필요한 브라우저 수동 QA는 아직 수행하지 않음 — `npm run type-check`/`eslint`만
      통과 확인)

## 결정 사항 (사용자 확인 완료)

1. **구매 확인 UX**: 확인 모달을 띄우고, 모달에서 확인하면 즉시 처리(페이지 이동 없음).
2. **배송지 입력 시점**: 구매 확인 모달에서 가격/잔액과 함께 배송지도 입력받아 `POST /orders` 직후
   `PATCH .../address`까지 이어서 호출한다(§1 참고). 이후 `PAID` 상태 동안은 구매 내역 상세에서 재수정 가능.
3. **"현재 위치" 배송 추적**: 이번 범위에서 제외한다. 배송 상태는 라벨(배송중/배송완료)로만 표시하고,
   실시간 위치가 필요해지면 그때 `docs/requests/BE/`에 별도 요청 문서를 남긴다.
4. **구매 성공 후 이동**: 상품 상세 페이지에 그대로 머문다(토스트 + "구매 내역 보기" 링크만 제공).
