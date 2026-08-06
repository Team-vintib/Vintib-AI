# SY038 포인트 충전 — 토스 위젯을 새 탭으로 분리

## 배경/목표

토스 결제위젯(결제수단/약관 UI)이 지금은 포인트 충전 화면 안에 인라인으로 렌더링돼, 앱 다크 테마와 안 어울리는 흰 위젯이 그대로 노출된다(카드 프레임은 앞서 추가했지만 위젯 내부 색은 못 바꾼다). 위젯을 새 탭에서 띄우고, 기존 화면에는 금액 선택과 "충전하기" 버튼만 남긴다.

## 작업 내용

1. **라우트 추가**: `POINT_CHARGE_CHECKOUT` (`/points/charge/checkout`, `requiresAuth`). 쿼리로 `amount`를 받는다.
2. **`PointChargePanel.vue` 축소**: 금액 선택 UI(빠른 금액 버튼 + 직접 입력)와 "충전하기" 버튼만 남긴다. 토스 SDK 관련 코드(`initWidgets`, `widgets` 상태, 결제수단/약관 위젯 div)를 전부 제거한다. "충전하기" 클릭 시 **클릭 핸들러 안에서 동기적으로** `window.open('/points/charge/checkout?amount=...', '_blank')`를 호출한다 — `await` 뒤에 호출하면 팝업 차단에 걸리므로, 비동기 작업(위젯 준비 등) 없이 URL만 조립해서 바로 연다.
3. **신규 페이지 `PointChargeCheckoutPage.vue`**: 지금 `PointChargePanel.vue`가 하던 토스 SDK 초기화(`readyPointCharge` → `loadTossPayments` → `widgets` → `renderPaymentMethods`/`renderAgreement`)와 `submitCharge`(→ `requestPayment`)를 그대로 옮긴다. 쿼리의 `amount`를 최종 금액으로 확정해 화면 상단에 읽기 전용으로 보여준다. 기존엔 위젯 준비용으로 최소금액으로 한 번, 제출 시 실제 금액으로 한 번, `readyPointCharge`를 두 번 불렀는데(위젯을 먼저 그려야 해서 실제 금액을 몰랐던 시절의 우회) — 이제는 진입 시점에 이미 최종 금액을 알고 있으니 `readyPointCharge`를 한 번만 부르도록 정리한다.
4. **탭 간 잔액 동기화**: `pointBalanceEvents.ts`의 `dispatchPointBalanceUpdated`는 `window.dispatchEvent`라 같은 탭 안에서만 전달된다. 결제가 새 탭에서 끝나면 원래 탭(헤더 잔액을 구독 중인 `GlobalNavigation.vue`)이 갱신되지 않는다. `BroadcastChannel`(같은 오리진 탭 간 통신, `window.opener` 유무와 무관하게 동작)을 추가해 두 경로(같은 탭 CustomEvent + 전체 탭 BroadcastChannel)로 함께 알리도록 `pointBalanceEvents.ts`를 확장한다. `GlobalNavigation.vue`가 이 채널도 구독한다.
5. **성공/실패 페이지**: 기존 `PointChargeSuccessPage.vue`/`PointChargeFailPage.vue`는 로직 그대로 두되(리다이렉트 콜백이라 어차피 새 탭에서 열리게 된다), "포인트 지갑으로 이동" 버튼을 `window.opener`가 있으면(= 새 탭으로 열렸으면) `window.close()`로, 없으면(직접 진입/새로고침) 기존처럼 `/points`로 이동하도록 분기한다.

## 구현 목록

- [x] `routes.ts`: `POINT_CHARGE_CHECKOUT` 이름/경로 추가
- [x] `PointChargeCheckoutPage.vue` 신설 — 토스 SDK 초기화/제출 로직 이관, 금액 읽기 전용 표시, `readyPointCharge` 1회 호출로 단순화
- [x] `PointChargePanel.vue` — 토스 SDK 관련 코드 제거, "충전하기" 클릭 시 `router.resolve` + `window.open`으로 새 탭 오픈. 더 이상 안 쓰는 `userId`/`currentBalance` prop과 `PointWalletPage.vue`의 관련 바인딩(및 이제 쓰이지 않는 `userId` computed)도 함께 정리
- [x] `pointBalanceEvents.ts` — `BroadcastChannel` 브로드캐스트 추가(같은 탭 CustomEvent는 유지), `subscribePointBalanceUpdatedAcrossTabs` 헬퍼 추가
- [x] `GlobalNavigation.vue` — `BroadcastChannel` 구독 추가(`applyPointBalanceUpdate` 공통 핸들러로 통합)
- [x] `PointChargeSuccessPage.vue`/`PointChargeFailPage.vue` — 버튼을 `window.opener` 유무에 따라 탭 닫기/이동으로 분기
- [x] `npm run type-check`, `eslint` 검증

## 확인이 필요한 미결정 사항

- 성공 후 새 탭을 **자동으로** 닫을지 — 사용자 확인: 버튼 클릭으로만 닫히도록 결정. 구현 완료.
- `window.opener`는 결제 흐름 중 토스의 결제 도메인(교차 출처)을 거쳤다가 돌아오는데, 그 도메인이 `Cross-Origin-Opener-Policy`를 엄격하게 설정해두면 브라우저가 opener 참조를 끊을 수 있다. 그러면 `openedAsNewTab`이 `false`로 떨어져 "창 닫기" 대신 일반 이동 버튼으로 자연스럽게 대체된다(에러 없이 저하된 동작으로 처리됨) — 실제 배포 환경에서 opener가 살아있는지는 실사용 확인이 필요하다.
- 모바일에서는 "새 탭"이 데스크톱만큼 자연스럽지 않을 수 있다(브라우저마다 새 탭 전환 UX가 다름). 토스 결제 자체도 어차피 앱 밖(카드사 앱/웹뷰)으로 나가는 경우가 많아 감수 가능하다고 보고 별도 분기 없이 동일하게 처리한다 — 문제 되면 추후 조정.
