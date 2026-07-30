# 구매/주문/배송/환불/포인트 API 계약 요청

## 요청 파트 / 대상 파트

- 요청: FE
- 대상: BE

## 배경/이유

기능 정의서와 `APIs.md`에는 상시 판매 구매, 주문 확정, 배송지, 송장, 환불, 포인트 충전/출금/정산 흐름이 있으나 현재 BE 구현에는 해당 컨트롤러가 없다. FE 마이페이지와 구매 플로우를 실제 API에 붙이려면 최소 계약 확정이 필요하다.

## 현재 BE 구현 확인

- 주문/구매/배송/환불 컨트롤러 없음
- 포인트/지갑/출금 컨트롤러 없음
- 사업자 세금계산서/정산 API 없음

## 요청 API

### 1. 상시 판매 주문 생성

```http
POST /api/orders
Authorization: Bearer {accessToken}
Content-Type: application/json
```

요청 후보:

```json
{
  "productId": 2001,
  "quantity": 1,
  "addressId": 10
}
```

요청 사항:

- 상시 판매 상품만 주문 가능하도록 검증한다.
- SOLD/PRIVATE/DRAFT 상품 구매 시 오류 코드를 확정한다.
- 본인 상품 구매 가능 여부를 확정한다.
- 포인트 차감 시점과 주문 생성 트랜잭션 경계를 확정한다.

### 2. 주문 목록/상세

```http
GET /api/users/{userId}/orders?page=0&size=20&type=BUYING
GET /api/orders/{orderId}
```

요청 사항:

- 구매 내역과 판매 내역을 같은 endpoint에서 구분할지 별도 endpoint로 나눌지 확정한다.
- 주문 상태 enum을 문서화한다. 예: `CREATED`, `PAID`, `SHIPPING_REQUIRED`, `SHIPPED`, `DELIVERED`, `CONFIRMED`, `REFUND_REQUESTED`, `REFUNDED`, `CANCELED`.
- 목록 카드에 필요한 상품 이미지, 상품명, 가격, 상대방 닉네임, 배송 상태를 포함한다.

### 3. 배송지/송장

```http
GET /api/orders/{orderId}/address
PATCH /api/orders/{orderId}/address
GET /api/orders/{orderId}/shipment
POST /api/orders/{orderId}/shipment
```

요청 사항:

- 배송지 저장 필드(`recipientName`, `phoneNumber`, `postalCode`, `address`, `detailAddress`)를 확정한다.
- 송장 등록 필드(`carrierCode`, `trackingNumber`)와 택배사 enum을 확정한다.
- 송장 번호 중복/형식 검증 정책을 확정한다.
- 배송 조회 외부 API 연동 여부와 실패 fallback 정책을 확정한다.

### 4. 구매 확정/환불

```http
POST /api/orders/{orderId}/confirmation
GET /api/orders/{orderId}/refunds
POST /api/orders/{orderId}/refunds
PATCH /api/refunds/{refundId}
```

요청 사항:

- 구매 확정 가능 상태와 중복 요청 처리 정책을 확정한다.
- 환불 요청 사유 enum, 첨부 이미지 여부, 판매자 승인/거절 payload를 확정한다.
- 환불 승인 시 포인트 환급과 상품 상태 복구 여부를 확정한다.

### 5. 포인트/출금/정산

```http
GET /api/users/{userId}/points
GET /api/users/{userId}/points/logs
POST /api/users/{userId}/points/charges
POST /api/users/{userId}/withdrawals
GET /api/users/{userId}/withdrawals
```

요청 사항:

- 포인트 잔액, 사용 가능 금액, 정산 예정 금액을 구분할지 확정한다.
- 충전 provider, 결제 승인 callback, 실패 복구 정책을 확정한다.
- 출금 계좌 등록/검증 API가 별도로 필요한지 확정한다.
- 포인트 로그 type enum과 `refType/refId` 이동 정책을 문서화한다.

## FE 관련 파일

- `FE/docs/frontend/screens/screen-inventory.md`
- `FE/docs/frontend/decisions/open-questions.md`
- 추후 `FE/src/domains/order`
- 추후 `FE/src/domains/shipping`
- 추후 `FE/src/domains/refund`
- 추후 `FE/src/domains/point`
