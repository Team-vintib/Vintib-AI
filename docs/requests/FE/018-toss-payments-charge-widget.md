# 018 - 포인트 충전 토스페이먼츠 결제위젯 연동 계약

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

`SY035`로 포인트 충전(POINT-001)이 결제 연동 없는 즉시-충전에서 토스페이먼츠 결제위젯(Payment Widget,
테스트 키) 연동으로 바뀌었다. 기존 `POST /users/{id}/points/charges`(요청 즉시 충전)는 제거됐고,
아래 준비(ready)/승인(confirm) 2단계로 대체됐다.

## 요청 내용

### 1. 충전 준비 — `POST /users/{id}/points/charges/ready`

- 요청 바디: `{ amount }` (기존과 동일)
  - `amount`는 최소 10,000원(`@Min(10_000)`)이다. 미달이면 Bean Validation 오류(400,
    `INVALID_INPUT_VALUE`)로 거부된다 — FE도 위젯 호출 전 같은 기준으로 막아주면 좋다. 출금 신청
    (`POST /users/{id}/withdrawals`)도 동일하게 최소 10,000원이다.
- 응답: `{ orderId, amount, clientKey }`
  - `orderId`: BE가 발급한 주문번호. 결제위젯 `requestPayment` 호출 시 그대로 넘긴다.
  - `clientKey`: 토스 결제위젯 초기화용 공개 키. FE가 직접 갖고 있지 않아도 이 응답으로 받으면 된다.

### 2. 결제위젯 호출

FE가 토스 결제위젯 SDK로 `orderId`/`amount`/`clientKey`를 넘겨 `requestPayment`를 호출한다
(수단은 FE 판단 — 카드/간편결제 등 위젯이 제공하는 UI 그대로 사용). `successUrl`/`failUrl`은 FE
라우트로 지정해야 한다(아래 4번 참고).

### 3. 충전 승인 — `POST /users/{id}/points/charges/confirm`

- `successUrl` 리다이렉트 쿼리 파라미터(`paymentKey`, `orderId`, `amount`)를 그대로 요청 바디로 보낸다:
  `{ orderId, paymentKey, amount }`
- 응답: 기존과 동일한 포인트 잔액 응답(`available/bidHeld/tradeEscrow/settling/withdrawing/updatedAt`)
- 실패 응답:
  - `404 PAYMENT_CHARGE_NOT_FOUND`: orderId에 해당하는 준비 정보 없음(잘못된 orderId)
  - `400 PAYMENT_ALREADY_PROCESSED`: 이미 실패 처리된 결제를 다시 승인 시도
  - `400 PAYMENT_AMOUNT_MISMATCH`: 준비 시점 금액과 다른 금액으로 승인 시도
  - `400 PAYMENT_CONFIRM_FAILED`: 토스 승인 자체가 실패(카드 거절 등)
- 이미 승인 완료된 orderId로 다시 호출해도 에러 없이 현재 잔액을 그대로 반환한다(중복 호출 안전).

### 4. `successUrl`/`failUrl` 라우트

- `failUrl` 쿼리 파라미터는 `code`, `message`, `orderId`다 — 에러 메시지 표시만 하면 되고, BE 호출은
  필요 없다.
- BE 문서·설정에는 우선 `/mypage/points/charge/success`, `/mypage/points/charge/fail`로 가정해
  적어뒀다. 실제 FE 라우트 이름이 다르면 알려달라 — BE 쪽에서 특별히 고정해야 할 값은 없다(리다이렉트
  URL 자체는 결제위젯 호출 시 FE가 넘기는 값이라 BE 설정과 무관하다).

## 관련 자료

- `docs/APIs.md` "포인트 / 출금(Wallet)" 섹션
- `docs/plans/BE/SY035-toss-payments-charge.md`
