# 010 Commerce/Wallet API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 주문, 배송, 환불, 포인트/지갑 도메인의 향후 FE 구현에 필요한 API 범위를 정리한다.
- 우선순위: P2
- 시연 필수 여부: 현재 FE 화면이 없어 시연 필수 아님.

## 2. 현재 연동 상태

- 연동 완료 API: 없음
- 2026-08-02 FE 구현 완료 범위
  - `/my?section=orders`: 구매/낙찰 내역 카드형 목록과 `/my/orders/{orderId}` 상세 페이지 구현.
  - `/my?section=sales`: 판매/정산 내역 카드형 목록과 `/my/sales/{saleId}` 상세 페이지 구현.
  - 위 두 영역은 주문/배송/환불/정산 API가 없어 mock fallback으로 동작한다.
- 현재 임시 처리 또는 Mock 사용 여부
  - 주문/판매 내역, 배송지, 구매 방식, 정산 상태는 FE mock data를 사용한다.
  - `/points`, `/points/history`는 기존 point 화면의 mock fallback을 유지한다.
  - 주문/배송/환불/포인트/지갑 API가 구현되면 FE adapter를 실제 응답 mapper로 교체해야 한다.

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
# 2026-08-01 포인트 지갑 상세 계약 요청

`/points`, `/points/history` FE 화면이 구현되어 mock fallback으로 동작 중이다. 포인트는 이 문서의 Commerce/Wallet 범위에 포함되므로 별도 요청 문서로 분리하지 않고 여기에서 상세 계약을 추적한다.

## 현재 FE 상태

- `/points`: 사용 가능 포인트, 보유/출금 가능/정산 예정/출금 처리 중 카드
- `/points`: 내역/충전/출금 탭
- `/points`: 최근 내역 10개
- `/points/history`: 전체/출금/입금 필터, 시작일/종료일 기간 필터
- 충전: 금액 선택, 결제 수단 선택, 충전 금액/충전 후 잔액 표시
- 출금: 계좌 확인, 출금 금액 입력, 출금 신청
- `VITE_POINT_API_ENABLED=false` 기본값으로 mock fallback 사용
- FE adapter는 임시로 `/users/{userId}/points` 계열 호출 기준

기존 문서 충돌:

- `FE/docs/frontend/api/api-index.md`: `/api/points`, `/api/points/transactions`, `/api/points/withdrawals`
- `APIs.md`: `/users/{id}/points`, `/users/{id}/points/logs`, `/users/{id}/points/charges`, `/users/{id}/withdrawals`

## 포인트 잔액 조회

- Method / Endpoint 제안: `GET /api/users/{userId}/points`
- 인증: 필요. `{userId}`는 로그인한 본인 ID와 같아야 한다.
- FE 사용처: `/points` 상단 요약

```json
{
  "available": 128500,
  "held": 42000,
  "escrow": 78000,
  "pendingSettlement": 156000,
  "withdrawalProcessing": 30000,
  "withdrawable": 128500,
  "lastChangedAt": "2026-08-01T14:20:00"
}
```

## 포인트 거래 내역 조회

- Method / Endpoint 제안: `GET /api/users/{userId}/points/logs`
- 인증: 필요
- FE 사용처: `/points` 최근 내역, `/points/history` 전체 내역
- Query: `page`, `size`, optional `type`, optional `flow=ALL|DEPOSIT|WITHDRAWAL`, optional `startDate`, optional `endDate`
- `type` 후보: `CHARGE | USE | HOLD | HOLD_RELEASE | SETTLEMENT | REFUND | WITHDRAWAL`
- `status` 후보: `COMPLETED | PENDING | FAILED`

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": 101,
        "type": "CHARGE",
        "title": "포인트 충전",
        "amount": 50000,
        "balanceAfter": 128500,
        "status": "COMPLETED",
        "createdAt": "2026-08-01T14:20:00",
        "memo": "카드 결제"
      }
    ],
    "page": 0,
    "size": 10,
    "totalElements": 1,
    "totalPages": 1,
    "hasNext": false
  },
  "error": null
}
```

## 포인트 충전

- Method / Endpoint 제안: `POST /api/users/{userId}/points/charges`
- 인증: 필요
- FE 사용처: `/points` 충전 탭

```json
{
  "amount": 50000,
  "paymentMethod": "CARD"
}
```

결제 수단 enum 후보: `CARD`, `BANK_TRANSFER`, `SIMPLE_PAY`

확인 필요:

- MVP에서 실제 PG 없이 mock 충전을 허용할지
- 최소 충전 금액. FE 임시 기준은 `1,000P`
- 충전 실패/취소 상태를 거래 로그에 남기는지

## 출금 계좌 조회

- Method / Endpoint 제안: `GET /api/users/{userId}/points/account`
- 인증: 필요
- FE 사용처: `/points` 출금 탭

```json
{
  "bankName": "신한은행",
  "accountNumber": "110-123-456789",
  "holderName": "김서윤"
}
```

확인 필요:

- 계좌가 없을 때 `data: null`로 줄지, 별도 오류 코드로 줄지
- 계좌 등록/수정 API를 별도로 제공할지, 출금 신청 body에 포함된 계좌로 저장할지

## 출금 신청

- Method / Endpoint 제안: `POST /api/users/{userId}/withdrawals`
- 인증: 필요
- FE 사용처: `/points` 출금 탭

```json
{
  "amount": 30000,
  "account": {
    "bankName": "신한은행",
    "accountNumber": "110-123-456789",
    "holderName": "김서윤"
  }
}
```

응답 데이터 요청 필드:

```json
{
  "id": 12,
  "amount": 30000,
  "fee": 0,
  "status": "REQUESTED",
  "requestedAt": "2026-08-01T15:00:00",
  "completedAt": null,
  "account": {
    "bankName": "신한은행",
    "accountNumber": "110-123-456789",
    "holderName": "김서윤"
  }
}
```

출금 상태 enum 후보: `REQUESTED`, `PROCESSING`, `COMPLETED`, `REJECTED`

확인 필요:

- 최소 출금 금액. FE 임시 기준은 `10,000P`
- 출금 수수료 정책
- 출금 신청 시 `withdrawable` 차감 시점
- 반려 시 포인트 복구 방식

## 출금 내역 조회

- Method / Endpoint 제안: `GET /api/users/{userId}/withdrawals`
- 인증: 필요
- FE 사용처: 출금 처리 중 금액 계산, 향후 출금 내역 상세
- Query: optional `page`, `size`, `status`
- 응답 데이터: page 또는 list 중 BE 표준에 맞춰 확정 필요

## 오류 코드 요청

| 코드 | 상황 |
| --- | --- |
| `POINT_INSUFFICIENT` | 충전/출금/결제/입찰에서 포인트 부족 |
| `POINT_ACCOUNT_REQUIRED` | 출금 계좌 없음 |
| `POINT_WITHDRAWAL_MIN_AMOUNT` | 최소 출금 금액 미달 |
| `POINT_CHARGE_MIN_AMOUNT` | 최소 충전 금액 미달 |
| `POINT_FORBIDDEN_USER` | 본인이 아닌 사용자 포인트 조회/처리 |

기존 BE `ErrorCode`에 `INSUFFICIENT_POINTS`가 있다면 FE와 코드명을 맞출 필요가 있다.

## FE 반영 계획

- `FE/src/domains/point/api/pointApi.ts` endpoint 경로와 응답 mapper 수정
- `VITE_POINT_API_ENABLED=true`로 전환
- 필요 시 `/points/history` 필터를 서버 query로 위임
- API 문서와 화면 상태 문서 갱신
