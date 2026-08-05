# 026 - 토스페이먼츠 클라이언트 키 종류 확인 요청

## 요청자 파트 / 대상 파트

FE → BE

## 배경/이유

포인트 충전 화면(`/points` 충전 탭)에 진입하면 결제수단 위젯이 뜨지 않고 "결제 수단을 불러오지 못했습니다"로 실패한다. 실제 배포 서버(`https://i15a108.p.ssafy.io`)에서 재현해 원인을 특정했다.

- `POST /users/{id}/points/charges/ready`는 정상 200을 반환하고 `clientKey`도 채워져 있다(`test_ck_...`로 시작).
- 그 `clientKey`로 FE가 `@tosspayments/tosspayments-sdk`의 `loadTossPayments(clientKey)` → `tossPayments.widgets({ customerKey })`를 호출하면, 토스 SDK가 다음 오류를 던진다:

  ```
  결제위젯 연동 키의 클라이언트 키로 SDK를 연동해주세요. API 개별 연동 키는 지원하지 않습니다.
  ```

- 즉 현재 `TOSS_CLIENT_KEY`(배포는 `PROD_TOSS_CLIENT_KEY` CI 변수)로 등록된 값이 **API 개별 연동 키**(`tossPayments.payment()`용, 보통 `test_ck_...`)이고, 결제위젯(`tossPayments.widgets()`)에는 **결제위젯 연동 키**(보통 `test_gck_...`로 시작)가 필요하다. 두 키는 토스 개발자센터에서 서로 다른 발급 항목이다.

## 요청 내용

- 토스 개발자센터에서 **결제위젯 연동 키**(결제위젯 연동 키 client/secret 한 쌍, 테스트 키는 사업자 등록 없이 바로 발급 가능)를 발급받아 `TOSS_CLIENT_KEY`/`TOSS_SECRET_KEY`를 교체해 달라.
- 로컬 개발용 `.env`(또는 `application-local.yml`)와 배포용 GitLab CI/CD 변수(`PROD_TOSS_CLIENT_KEY`, `PROD_TOSS_SECRET_KEY`) 둘 다 확인해 달라 — 로컬은 이번에 직접 확인하지 못했다.
- 서버 승인(`POST /v1/payments/confirm`)에 쓰는 `TOSS_SECRET_KEY`는 API 자체는 키 종류를 가리지 않지만, 클라이언트 키와 짝을 맞춰 함께 발급된 결제위젯용 시크릿 키로 교체하는 걸 권장한다(발급 페이지에서 위젯 연동 키는 client/secret이 쌍으로 나온다).

## 관련 자료

- 재현: FE `npm run dev` → `/points` → 충전 탭 진입 시 `PointChargePanel`의 `initWidgets()`에서 실패
- 참고: [토스페이먼츠 결제위젯 연동 가이드](https://docs.tosspayments.com/guides/v2/payment-widget/integration)
- FE 쪽 위젯 연동 코드는 `FE/src/domains/point/components/PointChargePanel.vue` (`docs/plans/FE/SY031-point-charge-toss-widget.md` 계획대로 구현 완료, 이 키 교체만 남음)
