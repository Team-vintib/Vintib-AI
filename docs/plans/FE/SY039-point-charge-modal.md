# SY039 포인트 충전 — 토스 위젯을 모달로 전환

## 배경/목표

SY038에서 토스 결제위젯을 새 탭(`/points/charge/checkout`)으로 분리했으나, "충전하기"를 누르면 새 탭이 뜨는 흐름이 부자연스럽다. 새 페이지/탭 이동 없이 현재 포인트 화면 위에 모달로 결제창(결제수단 선택 + 약관 동의 + 결제 버튼)을 띄우도록 되돌린다.

단, 결제위젯 SDK(`@tosspayments/tosspayments-sdk` v2)의 `widgets.requestPayment()`는 호출 시 브라우저를 실제로 토스 결제 도메인으로 이동시키고 승인 후 `successUrl`/`failUrl`로 돌아오는 리다이렉트 구조라, 이 마지막 결제 승인 스텝의 리다이렉트 자체는 막을 수 없다. 모달로 감싸는 범위는 "금액 확인 → 결제수단 선택 → 약관 동의 → 결제 요청 버튼"까지다.

## 작업 내용

1. **`PointChargeModal.vue` 신설**: `PointChargeCheckoutPage.vue`가 하던 토스 SDK 초기화(`readyPointCharge` → `loadTossPayments` → `widgets` → `renderPaymentMethods`/`renderAgreement`)와 `submitCharge`(→ `requestPayment`)를 옮긴다. props로 `amount`를 받는다(쿼리 대신). `PurchaseConfirmDialog.vue`와 동일한 모달 마크업 컨벤션(오버레이+dialog, z-index 500, 헤더 X 버튼)을 따른다. 결제 요청 중(`isRequesting`)에는 닫기를 막는다.
2. **`PointChargePanel.vue` 축소**: `window.open` 기반 `openCheckout`을 제거하고, 유효성 검증 통과 시 로컬 상태(`isCheckoutOpen`, `checkoutAmount`)로 모달을 연다. 안내 문구를 "결제창이 열립니다"로 수정.
3. **`PointChargeCheckoutPage.vue` 삭제** 및 `POINT_CHARGE_CHECKOUT` 라우트/이름 상수(`routes.ts`, `shared/constants/routes.ts`) 제거. `POINT_CHARGE_SUCCESS`/`FAIL` 라우트는 토스 리다이렉트 콜백에 계속 필요하므로 유지.
4. **성공/실패 페이지 단순화**: 더 이상 새 탭에서 열리는 경우가 없으므로 `PointChargeSuccessPage.vue`/`PointChargeFailPage.vue`의 `window.opener` 기반 "새 탭이면 창 닫기" 분기를 제거하고, 항상 `/points`(실패 시 `?section=charge`)로 이동하는 단일 동작으로 정리한다.
5. **위젯 재마운트**: 모달을 `v-if`로 조건부 렌더링하므로 닫으면 컴포넌트와 위젯 DOM이 완전히 파괴되고, 재오픈 시 새 인스턴스로 새로 mount된다. SDK에 별도 dispose API가 없어 이 unmount/remount 자체가 cleanup이다.
6. **`pointBalanceEvents.ts`**: 변경 없음. `requestPayment()` 리다이렉트로 같은 탭이 토스 도메인 → successUrl로 완전히 새로고침되므로, 사용자가 별도로 열어둔 다른 탭과의 잔액 동기화 목적(BroadcastChannel)은 여전히 유효하다. 다만 주석 문구가 "새 탭에서 끝날 수 있어"로 돼 있어 리다이렉트/새로고침 기준으로 갱신했다.

## 구현 목록

- [x] `PointChargeModal.vue` 신설 — 위젯 초기화/제출 로직 이관, `amount` prop, `close` emit
- [x] `PointChargePanel.vue` — `window.open` 제거, 모달 트리거로 교체, 안내 문구 수정
- [x] `PointChargeCheckoutPage.vue` 삭제, `POINT_CHARGE_CHECKOUT` 라우트/이름 상수 제거 (`router/routes.ts`, `shared/constants/routes.ts`)
- [x] `PointChargeSuccessPage.vue`/`PointChargeFailPage.vue` — `window.opener` 분기 제거, 버튼 문구 고정
- [x] `pointBalanceEvents.ts` 주석 갱신(리다이렉트/새로고침 기준)
- [ ] `npm run type-check`, `npm run lint` 검증
- [ ] 개발 서버에서 실제 결제 흐름(모달 오픈 → 위젯 렌더 → 결제 요청 → 성공/실패 콜백) 확인

## 확인이 필요한 미결정 사항

- 결제 요청 시 브라우저가 실제로 토스 도메인으로 이동했다가 돌아오는 것은 SDK 기본 동작이라 막을 수 없다 — "현재 화면 위에 뜨는" 범위는 금액 입력~결제수단 선택까지이고, 결제 승인 스텝 자체는 여전히 리다이렉트가 발생한다는 점은 사용자에게 계획 승인 시 확인받음.
- 모달 안에서도 토스 위젯 자체는 흰 배경 UI를 그대로 유지한다(SDK가 내부 스타일을 제공하지 않음). 카드 프레임으로 감싸는 정도로만 대응했고, 완전한 다크 테마 일치는 SDK 한계로 불가능하다.
