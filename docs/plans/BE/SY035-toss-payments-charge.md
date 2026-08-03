# SY035 - 포인트 충전 토스페이먼츠 연동 (결제위젯)

## 배경/목표

현재 `POST /api/users/{userId}/points/charges`는 결제 연동 없이 금액만 받아 즉시 잔액에 더하는
테스트/데모 전용 API다(POINT-001 "결제 API 추가 선정 필요" 상태 그대로 남아있음). 이번 계획은
토스페이먼츠 결제위젯(Payment Widget)을 붙여, 실제 결제 승인(테스트 키 기준)을 거쳐야만 포인트가
충전되도록 바꾼다.

- 연동 방식: 결제위젯(Payment Widget) — 카드/간편결제 등 결제수단 UI는 토스 SDK가 제공하고 FE가
  그대로 붙인다. BE는 결제 준비(주문 생성)·승인(confirm) API, 그리고 토스 서버 API 호출만 담당한다.
- 키: 테스트 키(샌드박스)로 연동한다 — 사업자 심사 없이 바로 쓸 수 있고, 실제 카드 승인은 나지 않는다.
- 기존 즉시-충전 엔드포인트는 폐기한다. 테스트 키로도 결제위젯 플로우 자체는 실 연동과 동일하게
  동작하므로, `DeliveryTrackingClient.subscribe`처럼 "연동 실패 시 즉시 처리" 폴백을 둘 이유가 없다
  (결제는 실패를 삼키면 안 되는 영역이라 그런 폴백 자체가 부적절하기도 하다).
- 환불/취소(토스 cancel API), 가상계좌 등 비동기 결제수단(웹훅 필요)은 이번 범위 밖 — 카드 등
  동기 confirm으로 끝나는 결제수단만 다룬다. 포인트 환불(REFUND-001/002) 자체가 아직 없는 것과 같은 이유.

## 작업 내용

### 1. 설정/클라이언트 (`AiClientConfig`/`DeliveryApiConfig` 패턴을 그대로 따름)

- `application.yml`에 `toss-payments:` 섹션 추가 — `base-url`(기본 `https://api.tosspayments.com`),
  `secret-key`, `client-key`를 `${TOSS_...:}` 형태로 두고 로컬 기본값은 빈 문자열.
- `global/config/TossPaymentsConfig.java`: `@ConfigurationProperties`로 위 값을 읽어
  `Authorization: Basic base64(secretKey:)` 헤더가 붙은 `RestClient` 빈을 만든다(토스는 시크릿 키를
  Basic Auth 사용자명으로, 비밀번호는 빈 문자열로 쓴다).
- `global/client/TossPaymentsClient.java`: `confirm(paymentKey, orderId, amount)` 하나만 제공한다.
  `POST /v1/payments/confirm` 호출, 실패(4xx/5xx) 시 예외를 삼키지 않고
  `CustomException(PAYMENT_CONFIRM_FAILED)`로 전파한다 — 결제 승인 실패를 조용히 넘기면 안 되므로
  `AiClient`/`DeliveryTrackingClient`와 달리 여기서는 방어적으로 `false`/폴백을 쓰지 않는다.

### 2. 결제 준비/승인 상태를 담을 엔티티

- `point.entity.PointCharge` 신규: `id, member, orderId(String, unique, BE 생성 UUID), amount,
  status(READY/DONE/FAILED), paymentKey(nullable, 승인 후 채움), approvedAt(nullable), createdAt`.
- `point.repository.PointChargeRepository`: `findByOrderId` 파생 쿼리.
- `docs/db/schema.sql`에 `point_charge` 테이블 추가(`ck_point_charge_status`,
  `ck_point_charge_amount_positive` CHECK 포함). `PointTransaction`은 기존 `ref_type/ref_id` 컬럼을
  그대로 써서 `ref_type='POINT_CHARGE', ref_id=charge.id`로 연결한다(스키마 변경 없음).

### 3. 충전 API를 준비/승인 2단계로 교체 (POINT-001)

기존 `POST /api/users/{userId}/points/charges`(즉시 충전)는 제거하고 아래 두 엔드포인트로 대체한다.

- `POST /api/users/{userId}/points/charges/ready`: body `{amount}` → `PointCharge(READY)` 생성,
  응답 `{orderId, amount, clientKey}`. `clientKey`는 설정값을 그대로 내려줘 FE가 위젯 초기화에 바로
  쓸 수 있게 한다(토스 클라이언트 키는 공개 키라 응답에 실어도 문제없다).
- `POST /api/users/{userId}/points/charges/confirm`: body `{orderId, paymentKey, amount}` →
  1) `orderId`로 `PointCharge` 조회, 없으면 `PAYMENT_CHARGE_NOT_FOUND`
  2) 이미 `DONE`이면 그대로 현재 잔액을 반환하고 재적립하지 않는다(중복 confirm에 대한 idempotent 처리)
  3) `status != READY`(예: FAILED로 이미 종료)면 `PAYMENT_ALREADY_PROCESSED`
  4) 요청 `amount`가 준비 시점 저장된 `amount`와 다르면 위변조로 간주해 `PAYMENT_AMOUNT_MISMATCH`
     (토스 confirm 호출 전에 막는다)
  5) `TossPaymentsClient.confirm(paymentKey, orderId, amount)` 호출 — 성공하면
     `PointCharge.markDone(paymentKey)` + 기존 `PointService.charge`로 포인트 적립
     (`PointTransaction.refType="POINT_CHARGE", refId=charge.id`), 실패하면 `PointCharge.markFailed()`
     후 예외 전파(포인트는 적립되지 않는다)
  6) 응답은 기존과 동일하게 `PointBalanceResponse`

### 4. 에러 코드

`ErrorCode`에 W-시리즈 추가:

| 상황 | 코드(가칭) |
| --- | --- |
| orderId에 해당하는 결제 준비 정보 없음 | `PAYMENT_CHARGE_NOT_FOUND`(W003) |
| 이미 완료/실패 처리된 결제를 다시 confirm 시도(FAILED 상태) | `PAYMENT_ALREADY_PROCESSED`(W004) |
| confirm 요청 금액과 준비 시점 금액 불일치 | `PAYMENT_AMOUNT_MISMATCH`(W005) |
| 토스 승인 API 실패 | `PAYMENT_CONFIRM_FAILED`(W006) |

### 5. FE 계약 전달

- `docs/requests/FE/018-toss-payments-charge-widget.md` 작성 — 아래를 계약으로 정리한다.
  - 위젯 초기화: `ready` 응답의 `clientKey`/`orderId`/`amount`로 `requestPayment` 호출
  - 성공 리다이렉트(`successUrl`) 쿼리 파라미터: `paymentKey`, `orderId`, `amount` → 그대로
    `confirm` 바디로 전달
  - 실패 리다이렉트(`failUrl`) 쿼리 파라미터: `code`, `message`, `orderId` → 에러 메시지 표시만 하면 됨
    (BE 호출 불필요, `PointCharge`는 `READY`로 남고 이후 confirm 시도해도 어차피 토스에서 재실패함)
  - `successUrl`/`failUrl` 라우트 이름은 FE가 확정해서 알려달라고 요청(우선 BE 문서에는
    `/mypage/points/charge/success`, `/mypage/points/charge/fail`로 가정해 적어둔다)

## 구현 목록

- [x] `application.yml`에 `toss-payments` 설정 추가
- [x] `TossPaymentsConfig`(RestClient 빈), `TossPaymentsClient`(confirm) 추가 + 테스트
- [x] `point.entity.PointCharge` 엔티티 + `PointChargeRepository` 추가
- [x] `docs/db/schema.sql`에 `point_charge` 테이블 추가
- [x] `PointService`에 `readyCharge(memberId, amount)`, `confirmCharge(memberId, orderId, paymentKey, amount)` 추가 + 기존 즉시-충전용 `charge` 메서드는 내부 적립 로직으로만 남기고 컨트롤러 직접 호출은 제거 + 테스트
- [x] `PointChargeReadyResponse`, `PointChargeConfirmRequest` DTO 추가
- [x] `PointController`의 기존 `POST /charges` 제거, `POST /charges/ready`·`POST /charges/confirm` 추가 + Swagger 문서화
- [x] `ErrorCode`에 W003~W006 추가
- [x] `docs/APIs.md` 포인트 충전 섹션 갱신(요청/응답 계약 변경 반영)
- [x] `docs/requests/FE/018-toss-payments-charge-widget.md` 작성
- [x] `.claude/skills/BE:verify`로 최종 검증 — `PointServiceTest`/`TossPaymentsClientTest`/`DeliveryTrackingClientTest`/`OrderServiceTest` 전부 통과. 전체 `./gradlew build`는 이 작업과 무관한 사전 존재 이슈(로컬 Postgres의 `category.name_en` 컬럼 누락, auction/live/home 5개 테스트 클래스)로 실패했으나 이번 변경과는 무관함을 확인
- [x] `.env.example`/`docker-compose.yml`/`infra/ci/deploy.sh`/`.gitlab-ci.yml`에 `TOSS_SECRET_KEY`/`TOSS_CLIENT_KEY` 설정 전달 추가(루트 세션에서 진행 — BE 세션은 앱 코드만 담당)

## 확인 필요 사항

- `successUrl`/`failUrl` 실제 라우트는 FE 확정 필요 — 우선 가정값으로 진행하고 FE 요청 문서에서
  조정 요청.
- 결제 취소/환불(토스 cancel API 연동)은 이번 범위 밖 — 포인트 환불 기능 자체가 없어서 함께 제외.
- 가상계좌 등 비동기 결제수단(웹훅 필요)은 이번 범위 밖 — 카드 등 동기 confirm 결제수단만 지원.
- 최소 충전 금액 정책은 기존과 동일하게 미확정 상태 유지(`@Positive`만 검증).