# SY031 - 포인트 충전 토스페이먼츠 결제위젯 연동

## 배경/목표

포인트 충전에서 "서버 내부 오류가 발생했습니다"(C002 INTERNAL_SERVER_ERROR)가 뜬다. 원인은 계약 불일치다.

- FE(`pointApi.ts#chargePoints`)는 `POST /users/{userId}/points/charges`에 `{ amount }`만 보내는 **단건 충전**을 호출한다.
- BE는 `a634a4e`(포인트 충전 토스페이먼츠 결제위젯 연동)에서 이미 **2단계 흐름**으로 바뀌어 있다: `POST /charges/ready`(주문 준비, `PointChargeRequest`)로 `orderId`/`amount`/`clientKey`를 발급받고, 결제위젯 진행 후 `POST /charges/confirm`(`PointChargeConfirmRequest`: `orderId`/`paymentKey`/`amount`)으로 승인해야 잔액이 반영된다. 단건 `/charges` 엔드포인트는 더 이상 존재하지 않아 매핑되지 않고 500으로 떨어진다.
- 부가로 최소 충전 금액도 어긋난다: FE `POINT_CHARGE_MIN_AMOUNT = 1_000` vs BE `PointChargeRequest.amount`의 `@Min(10_000)`.

목표: 팀원이 공유한 [토스페이먼츠 결제위젯 연동 가이드](https://docs.tosspayments.com/guides/v2/payment-widget/integration)대로 FE를 ready → 위젯 렌더링 → 결제 요청(리다이렉트) → 성공/실패 콜백 → confirm 흐름으로 재구성해 BE와 계약을 맞춘다.

## 작업 내용

- `@tosspayments/tosspayments-sdk` 패키지를 FE에 추가한다.
- `pointApi.ts`: `chargePoints` 제거. `readyPointCharge(userId, amount)`(`POST /charges/ready`)와 `confirmPointCharge(userId, { orderId, paymentKey, amount })`(`POST /charges/confirm`)로 교체한다. 응답의 `clientKey`는 BE가 매 요청마다 내려주므로 FE에 별도 env 값을 두지 않는다.
- `pointOptions.ts`: `POINT_CHARGE_MIN_AMOUNT`를 BE `@Min(10_000)`에 맞춰 `10_000`으로 수정. 커스텀 결제수단 목록(`POINT_PAYMENT_METHODS`)은 제거한다 — 결제수단 선택 UI는 토스 위젯이 자체적으로 렌더링하므로 우리가 만든 라디오 버튼은 실제 결제와 무관해진다.
- `PointChargePanel.vue` 재구성:
  - 금액 선택(빠른 금액 버튼 + 직접 입력)은 유지.
  - "결제 수단" 커스텀 라디오 섹션을 제거하고, 위젯이 마운트될 컨테이너(결제수단 위젯 영역 + 이용약관 위젯 영역)를 추가한다.
  - 유효한 금액이 선택되면 `ready` 호출 → `loadTossPayments(clientKey)` → `widgets({ customerKey })` 초기화 → `setAmount` → `renderPaymentMethods`/`renderAgreement`로 위젯을 그린다.
  - "충전하기" 클릭 시 `widgets.requestPayment({ orderId, orderName, successUrl, failUrl })`를 호출해 토스 결제창으로 리다이렉트한다.
- 리다이렉트 콜백 라우트 신설(`ROUTE_PATHS`/`ROUTE_NAMES`에 추가):
  - `/points/charge/success`: 쿼리(`paymentKey`, `orderId`, `amount`)를 읽어 `confirmPointCharge` 호출 → 성공 시 잔액 갱신·`dispatchPointBalanceUpdated`·지갑 페이지 이동, 실패 시 에러 메시지 표시 후 충전 화면으로 복귀 유도.
  - `/points/charge/fail`: 토스가 붙여주는 쿼리(`code`, `message`)를 보여주고 충전 화면으로 돌아가는 버튼만 제공한다.
- `customerKey`는 로그인 사용자 기준 안정적인 문자열(예: `member-{userId}`)을 사용한다. 실제 PII는 노출하지 않는다.
- `PointWalletPage.vue#handleCharge`를 ready→위젯 트리거로 교체한다. 결제위젯은 전체 페이지 리다이렉트를 일으키므로, 기존처럼 같은 화면에서 성공 처리를 마무리하는 구조가 아니라 success 콜백 페이지가 마무리를 담당한다.
- 에러 코드 매핑을 추가한다: `PAYMENT_CHARGE_NOT_FOUND`(W003) / `PAYMENT_ALREADY_PROCESSED`(W004) / `PAYMENT_AMOUNT_MISMATCH`(W005) / `PAYMENT_CONFIRM_FAILED`(W006).

## 구현 목록

- [x] `@tosspayments/tosspayments-sdk` 의존성 추가
- [x] `pointApi.ts`에 `readyPointCharge`/`confirmPointCharge` 추가, `chargePoints` 제거
- [x] `point.types.ts`에 ready/confirm 요청·응답 타입 추가
- [x] `pointOptions.ts`: 최소 충전 금액 10,000으로 수정, `POINT_PAYMENT_METHODS` 제거
- [x] `PointChargePanel.vue`: 결제수단 라디오 제거, 토스 위젯 마운트 영역 추가, ready→위젯 렌더링→`requestPayment` 흐름 구현
- [x] `points/charge/success`, `points/charge/fail` 라우트 및 페이지 컴포넌트 신설
- [x] `PointWalletPage.vue`의 충전 처리를 위젯 트리거 방식(에러만 relay)으로 교체
- [x] 결제 관련 에러는 BE가 내려주는 `ApiErrorBody.message`(W003~W006 포함)를 그대로 노출 — 별도 코드별 한글 매핑 없이도 BE 메시지가 이미 사용자向이라 충분하다고 판단
- [x] `npm run type-check`, `npm run lint`로 검증

## 확인 필요 사항

- successUrl/failUrl은 절대경로가 필요하다(`window.location.origin` 기반으로 구성 예정). 로컬 개발에서는 localhost 기준으로 테스트 결제만 가능하며, 실제 배포 도메인에서의 리다이렉트 동작은 배포 후 확인이 필요하다.
- BE의 `TOSS_CLIENT_KEY`/`TOSS_SECRET_KEY`가 로컬/배포 환경에 실제로 채워져 있는지는 FE가 확인할 수 없는 영역이다. 비어 있으면 위젯 초기화(clientKey 사용)나 승인(secretKey 사용) 자체가 막힐 수 있어, 화면 구현과 별개로 BE 쪽 환경변수 세팅 확인이 필요하다.
