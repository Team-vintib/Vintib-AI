# 010 Commerce/Wallet API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 주문, 배송, 환불, 포인트/지갑 도메인의 향후 FE 구현에 필요한 API 범위를 정리한다.
- 우선순위: P2
- 시연 필수 여부: 현재 FE 화면이 없어 시연 필수 아님.

## 2. 현재 연동 상태

- 연동 완료 API: 없음
- FE 구현 완료 범위: 없음
- 현재 임시 처리 또는 Mock 사용 여부
  - 주문/배송/환불/포인트/지갑 화면과 route가 아직 없다.
  - API가 구현되어도 별도 FE 설계 후 연결해야 한다.

## 3. 추가 구현 요청

### 3.1 주문 생성

- Method / Endpoint: `POST /api/orders`
- 요청 목적: 상품 상세 구매 버튼에서 주문을 생성한다.
- FE 사용처: 향후 주문서/상품 상세 구매 플로우
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
  - Body
    - `productId`: number
    - `quantity`: number, MVP는 1 고정 가능
    - `addressId`: number | null
    - `recipientName`: string | null
    - `phoneNumber`: string | null
    - `postalCode`: string | null
    - `address`: string | null
    - `detailAddress`: string | null
- 응답 데이터
  - `orderId`: number
  - `status`: enum
  - `paidAmount`: number
  - `createdAt`: string(datetime)
- 응답 예시

```json
{
  "success": true,
  "data": {
    "orderId": 1,
    "status": "CREATED",
    "paidAmount": 59000,
    "createdAt": "2026-07-31T12:00:00"
  },
  "error": null
}
```

### 3.2 주문 목록/상세

- Method / Endpoint: `GET /api/orders`, `GET /api/orders/{orderId}`
- 요청 목적: 구매/판매 내역과 주문 상세를 조회한다.
- FE 사용처: 향후 마이페이지 주문/판매 내역
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
  - Query: `type`, `status`, `page`, `size`
- 응답 데이터
  - `orderId`, `type`, `status`, `productId`, `productTitle`, `productThumbnailUrl`, `price`, `buyerNickname`, `sellerNickname`, `createdAt`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "orderId": 1,
    "type": "BUYING",
    "status": "CREATED",
    "productId": 10,
    "productTitle": "빈티지 자켓",
    "productThumbnailUrl": null,
    "price": 59000,
    "sellerNickname": "seller",
    "createdAt": "2026-07-31T12:00:00"
  },
  "error": null
}
```

### 3.3 배송/송장

- Method / Endpoint: BE 확정 필요
- 요청 목적: 주문 배송지와 송장 정보를 조회/등록한다.
- FE 사용처: 향후 주문 상세, 판매자 배송 처리 화면
- 요청 데이터: 주문 id, 배송지, 택배사 코드, 송장번호
- 응답 데이터: `recipientName`, `phoneNumber`, `postalCode`, `address`, `detailAddress`, `carrierCode`, `trackingNumber`, `shippedAt`, `deliveredAt`
- 응답 예시: BE 계약 확정 전이라 없음

### 3.4 환불

- Method / Endpoint: BE 확정 필요
- 요청 목적: 환불 요청과 검토 상태를 관리한다.
- FE 사용처: 향후 주문 상세 환불 플로우
- 요청 데이터: 주문 id, 환불 사유, 상세 사유
- 응답 데이터: `refundId`, `orderId`, `reason`, `detailReason`, `status`, `requestedAt`, `reviewedAt`, `rejectionReason`
- 응답 예시: BE 계약 확정 전이라 없음

### 3.5 포인트/지갑

- Method / Endpoint: BE 확정 필요
- 요청 목적: 포인트 잔액, 정산 예정 금액, 출금 가능 금액, 거래 로그를 조회한다.
- FE 사용처: 향후 포인트/지갑 화면
- 요청 데이터: Header `Authorization: Bearer {accessToken}`
- 응답 데이터: `balance`, `pendingSettlementAmount`, `availableWithdrawalAmount`, `logs[]`
- 응답 예시: BE 계약 확정 전이라 없음

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용: 없음
- 추가할 필드: 없음
- 변경 영향 범위: 없음

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - 주문/배송/환불/포인트/지갑 전체
  - 결제 연동
  - 정산/출금 처리
- 추후 구현 예정 기능
  - 주문서 화면
  - 구매/판매 내역
  - 배송/송장 입력
  - 환불 요청
  - 포인트 충전/사용/환불/정산/출금 로그

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - 주문 상태 enum
  - 주문 생성 시 포인트 결제/차감 정책
  - 배송지 저장 API 분리 여부
  - 환불 가능 조건
  - 정산/출금 정책
- 아직 확정되지 않은 응답 구조나 정책
  - 결제 API 범위
  - 택배사 코드 enum
  - 포인트 로그 `refType` enum

## 7. 추가 요청 없음

- 이미 정상 연동된 API: 없음
- 기존 규격을 유지하면 되는 기능: 없음
