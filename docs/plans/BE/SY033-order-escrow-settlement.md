# SY033 - 상시 판매 주문 생성 · 거래 대금 보관 · 구매 확정/정산

## 배경/목표

포인트 잔액 조회/충전/출금(MY-007, POINT-001/002/004)은 이미 구현되어 있다(`858d017`). `PointAccount`의
`tradeEscrow`/`settling` 버킷과 `PointTransactionType.PAYMENT/SETTLEMENT`는 스키마에 이미 준비돼 있지만,
이를 채울 트리거가 없어 지금은 항상 0이다.

이번 계획은 그 트리거를 만든다 — 상시 판매(고정가) 상품을 사는 흐름 전체를 구현한다.

- 주문 생성(`POST /orders`, SALE-001/002): 구매자 결제 → `available` 차감, `tradeEscrow` 적립(거래 대금 보관)
- 배송지 등록(ORDER-001), 송장 등록(SHIP-001/002)
- 구매 확정 처리(`POST /orders/{id}/confirmation`, ORDER-002/003): `tradeEscrow` → 판매자 `available` 정산(거래 완료)
- 자동 구매 확정 배치: 배송 완료 7일 경과 주문을 스케줄러가 같은 확정 로직으로 처리

경매 낙찰(AUCT-003~014)은 입찰 자체가 아직 없어 이번 범위에서 제외한다 — `Order.auction`은 계속 NULL로 남는다.
환불(REFUND-001/002)도 사용자 요청 범위 밖이라 제외한다.

## 작업 내용

### 1. 주문 생성 (SALE-001/002)

`POST /api/orders` — 인증된 구매자가 `productId`로 상시 판매 상품을 즉시 구매한다.

- 상품이 존재/미삭제, `saleType=DIRECT_SALE`, `saleStatus=ON_SALE`인지 확인 (`Product`에 `isAvailableForDirectPurchase()` 헬퍼 추가)
- 구매자 == 판매자면 거부 (자기 자신 구매 금지, DB 제약 `ck_order_not_self`와 짝을 맞춰 애플리케이션에서도 사전 검증)
- `PointService`에 `pay(buyerId, amount, refType, refId)` 추가: `available` 부족 시 `INSUFFICIENT_POINTS`, 아니면 `available -= amount`, `tradeEscrow += amount`, `PointTransaction(PAYMENT, amount=-amount)` 기록
- `Order` 생성(`status=PAID` 기본값 그대로 사용) — 지금은 패키지 전용 빌더라 같은 `order` 패키지의 서비스에서만 생성 가능하게 유지
- `Product.markSold()` 추가 후 호출 (`saleStatus=SOLD`)
- 위 세 가지(포인트 차감, 주문 생성, 상품 SOLD 처리)는 한 트랜잭션으로 묶는다

### 2. 배송지 등록/조회 (ORDER-001)

`order_shipment` 테이블 1건을 `Order`와 1:1로 매핑하는 `OrderShipment` 엔티티를 새로 만든다
(PK=`order_id`, `PointAccount`가 `member_id`를 공유 PK로 쓰는 것과 같은 패턴).

- `PATCH /api/orders/{id}/address`: 구매자만 등록/수정 가능. 행이 없으면 생성, 있으면 갱신(upsert). `status=PAID`일 때만 허용 — 송장이 등록된 뒤에는 주소를 바꿀 수 없다.
- `GET /api/orders/{id}/address`: 구매자·판매자 모두 조회 가능(판매자가 배송을 위해 확인해야 함). 아직 등록 전이면 404류 에러.

### 3. 송장 등록/조회 (SHIP-001/002)

- `POST /api/orders/{id}/shipment`: 판매자만 등록. 전제조건 — `status=PAID`이고 배송지가 이미 등록돼 있어야 함.
  courier/trackingNumber를 받아 `shippedAt=now`로 기록한다.

  **가정(리뷰 필요)**: 실제 택배사 연동/추적 웹훅이 없어 "배송 중"과 "배송 완료"를 구분할 외부 신호가 없다.
  포인트 충전이 결제 연동 없이 즉시 반영되는 것과 같은 이유로, 이 등록 한 번으로 `shippedAt=deliveredAt=now`를
  같이 채우고 상태를 `PAID → SHIPPING → DELIVERED`까지 한 번에 전이시킨다. 이때 `autoConfirmAt = now + 7일`을
  계산해 채운다(스키마 주석과 `ix_orders_auto_confirm` 인덱스 기준). 실제 택배 연동이 붙으면 이 지점을
  "배송 시작"과 "배송 완료" 두 단계로 분리하면 된다 — 지금은 한 커밋으로 처리해도 이후 분리가 어렵지 않다.
- `GET /api/orders/{id}/shipment`: 구매자·판매자 모두 조회 가능. 배송지+송장 정보를 함께 반환한다.

### 4. 구매 확정 처리 (ORDER-002/003) — 거래 완료

`POST /api/orders/{id}/confirmation` — 구매자만 호출. 전제조건 `status=DELIVERED`.

- `PointService`에 `settleOrder(buyerId, sellerId, amount, orderId)` 추가:
  구매자 `tradeEscrow -= amount`(원장 기록 없음 — 결제 시점 PAYMENT 기록으로 이미 설명됨),
  판매자 `available += amount`, `PointTransaction(SETTLEMENT, amount=+amount)` 기록
- `Order.status`를 `DELIVERED → CONFIRMED → SETTLED`까지 같은 호출 안에서 전이시킨다.
  이유: `MyOrderController`/`OrderService`가 이미 "정산 완료 여부 = status가 SETTLED"로 판단하도록
  구현돼 있고, 별도의 관리자 정산 승인 절차가 정의돼 있지 않다.
  **가정(리뷰 필요)**: `settling`(정산 대기) 버킷은 이번 범위에서 쓰지 않는다 — `bidHeld`가 AUCT-007
  이전까지 항상 0인 것과 같은 이유로, 정산 대기 기간/승인 절차가 확정되기 전까지는 바로 `available`로
  정산한다. 이 정책이 나중에 정의되면 `settling`을 경유하도록 바꾼다.

### 5. 자동 구매 확정 배치

- `global/config`에 `@EnableScheduling` 설정 클래스 추가(코드베이스에 `@Scheduled` 사용 사례가 아직 없음)
- `OrderService`(또는 별도 `OrderAutoConfirmScheduler`)에 주기적 작업 추가: `status=DELIVERED AND auto_confirm_at <= now`인 주문을 `ix_orders_auto_confirm` 인덱스를 타는 쿼리로 찾아 4번과 동일한 확정 로직을 재사용해 처리
- 주기는 우선 10분으로 잡는다(운영 정책 미확정 — 실제 배포 시 조정 가능하게 값만 상수로 분리)

### 6. 에러 코드

`ErrorCode`에 O-시리즈 추가: 구매자 전용/판매자 전용 처리 거부, 배송지 미등록, 자기 자신 구매 금지.
기존 "거래 당사자 아님" 케이스는 `INVOICE_FORBIDDEN` 재사용 관례를 그대로 따른다(기존 `OrderService`/`OrderController` 주석 참고).

## 구현 목록

- [x] `Product`에 `isAvailableForDirectPurchase()`, `markSold()` 추가
- [x] `order.entity.OrderShipment` 엔티티 추가(1:1 PK=order_id), `order.repository.OrderShipmentRepository` 추가
- [x] `PointAccount`에 `pay(amount)`, `releaseEscrow(amount)`, `settle(amount)` 추가
- [x] `PointService`에 `pay(buyerId, amount, orderId)`, `settleOrder(buyerId, sellerId, amount, orderId)` 추가 + 테스트
- [x] `Order` 생성용 정적 팩토리(`createDirectSale`) — 패키지 전용 빌더 대신 public static factory로 결정
- [x] `OrderService`에 `createOrder`, `registerAddress`, `getShipment`(address/shipment 공용), `registerShipment`, `confirmOrder`, `autoConfirmDueOrders` 추가 + 테스트
- [x] `OrderController`에 `POST /api/orders`, `PATCH/GET /api/orders/{id}/address`, `POST/GET /api/orders/{id}/shipment`, `POST /api/orders/{id}/confirmation` 추가 + Swagger 문서화
- [x] 요청/응답 DTO 추가: `OrderCreateRequest`, `OrderShipmentAddressRequest`, `OrderShipmentRegisterRequest`, `OrderShipmentResponse`
- [x] `ErrorCode`에 O003~O008 추가(자기거래 금지/구매불가 상품/구매자·판매자 전용/배송지 미등록/미등록 배송지·송장)
- [x] `global/config`에 `SchedulingConfig`(`@EnableScheduling`) + `order.scheduler.OrderAutoConfirmScheduler` 추가
- [x] `docs/APIs.md` 주문 섹션 구현 완료 여부(✓) 갱신
- [x] `BE/README.md`에 order/point 패키지 설명 갱신
- [x] `.claude/skills/BE:verify`로 최종 검증 — `BUILD SUCCESSFUL`

## 확인 필요 사항 (해결됨)

- 3번(송장 등록 시 배송 시작=완료 동시 처리), 4번(`settling` 버킷 미사용) 모두 사용자 승인하에 계획대로 진행
- 자동 확정 배치 주기는 10분(고정 지연)으로 구현