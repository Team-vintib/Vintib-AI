# SY034 - 택배 배송 조회 연동 (deliveryapi.co.kr)

## 배경/목표

`SY033`(주문/배송 흐름)에서는 실제 택배 연동이 없어 판매자가 송장을 등록하는 즉시 배송완료(`DELIVERED`)까지
한 번에 처리하는 임시 방식을 썼다. 기능정의서 `SHIP-002`는 원래 "택배 배송 조회 API로 배송 상태를 확인한다"를
전제하는데, 그 갭을 `deliveryapi.co.kr`(택배조회API) 연동으로 메운다.

- `POST /v1/tracking/trace`: 송장번호로 즉시 배송 상태 조회
- `POST /v1/webhooks/register`: 웹훅 구독 등록 — 등록 후 저쪽 서버가 최대 14일간 1시간 주기로 폴링해
  상태가 바뀔 때마다 우리 웹훅 엔드포인트로 푸시한다(HMAC-SHA256 서명). 무료 티어(100회/월) 호출량을
  거의 쓰지 않아 이 방식을 쓴다(사용자 승인).
- 사용자가 API Key/Secret Key를 이미 발급받았고, 웹훅 엔드포인트(`POST /v1/webhooks/endpoints`) 등록은
  1회성 인프라 설정이라 앱 코드가 아니라 수동으로(API 테스트 콘솔/curl) 해서 나온 `endpointId`를
  환경변수로 넣는다.

## 작업 내용

### 1. 설정/클라이언트 (AiClientConfig·AiClient 패턴을 그대로 따름)

- `application.yml`에 `delivery-api:` 섹션 추가 — `base-url`, `api-key`, `secret-key`, `webhook-secret`,
  `endpoint-id`를 전부 `${DELIVERY_API_...:}` 형태로 두고, 로컬 기본값은 빈 문자열로 둔다.
- `global/config/DeliveryApiConfig.java`: `@ConfigurationProperties`로 위 값을 읽어 `Authorization: Bearer
  {apiKey}:{secretKey}` 헤더가 붙은 `RestClient` 빈을 만든다.
- `global/client/DeliveryTrackingClient.java`: `subscribe(CourierCode, trackingNumber, orderId)` 하나만
  제공한다. `POST /v1/webhooks/register`를 호출하고, `clientId=order-{orderId}`, `metadata={orderId}`를
  실어 보낸다. **API Key가 비어 있거나 호출이 실패하면 예외를 삼키고 `false`를 반환한다**(AiClient의
  `isHealthy()`와 같은 방어 — 무료 티어 소진, 네트워크 오류, 로컬 환경 등에서도 서비스가 죽지 않게).

### 2. 택배사 코드 고정

- `order.entity.CourierCode` enum 추가 — deliveryapi가 지원하는 국내 택배사 10개(`LOTTE, CJ, HANJIN, POST,
  KYUNGDONG, DAESIN, LOGEN, HAPDONG, COUPANG, WOORI`)만 정의한다. 각 상수는 `apiCode`(예: `cj`)와
  `displayName`(예: `CJ대한통운`)을 갖는다.
- `OrderShipmentRegisterRequest.courier: String` → `courierCode: CourierCode`로 교체(자유 문자열 금지).
- `OrderShipmentResponse`에 `courierCode`, `courierName`(displayName)을 함께 내려준다.
- `OrderShipment.courier` 컬럼은 그대로 두되(VARCHAR) enum name을 저장하도록 바꾸고, CHECK 제약을 추가한다
  (다른 엔티티의 `@CheckConstraint` 관례를 따름).
- FE의 송장 등록 폼이 자유 입력에서 고정 택배사 선택으로 바뀌어야 하므로 `docs/requests/FE/`에 계약 변경
  요청 문서를 남긴다.

### 3. 송장 등록 흐름 변경 (OrderService.registerShipment)

- `shipment.registerTracking(courierCode, trackingNumber, shippedAt)`만 호출하고 `deliveredAt`은 더 이상
  이 시점에 채우지 않는다. `order.markShipping()`까지만 하고 `order.markDelivered()`는 호출하지 않는다.
- 이어서 `deliveryTrackingClient.subscribe(...)`를 호출한다.
  - 구독 성공: 이후 배송완료는 웹훅으로만 반영된다(4번).
  - 구독 실패/미설정(`false` 반환): `SY033`과 동일하게 그 자리에서 즉시 `order.markDelivered(now)`를
    호출하는 폴백을 유지한다 — 로컬 개발·자격증명 미설정 환경에서도 데모가 끊기지 않게 하기 위함이다.

### 4. 웹훅 수신

- `order.controller.DeliveryWebhookController`: `POST /api/webhooks/delivery`. `SecurityConfig`
  `PUBLIC_ENDPOINTS`에 추가한다(JWT 인증 대상이 아님 — 대신 서명으로 검증).
- 원문 바디를 `String`으로 받아 `X-Webhook-Signature`를 `HMAC-SHA256(webhookSecret, "{timestamp}.{rawBody}")`
  로 재계산해 검증하고, `X-Webhook-Timestamp`가 현재 시각과 300초 이상 차이 나면 거부한다.
- 검증 통과 후 JSON을 파싱해 `items[]`를 순회 — `isDelivered == true`인 항목만 처리한다.
- `(courierCode, trackingNumber)`로 `OrderShipmentRepository`에서 대상 주문을 찾는다(신규 파생 쿼리).
  주문 상태가 이미 `SHIPPING`이 아니면(중복 웹훅 등) 그냥 무시한다(idempotent).
- 찾으면 `order.markDelivered(now)` 호출 — 기존 `SY033` 로직(7일 뒤 자동 확정 시각 계산)을 그대로 재사용한다.

### 5. 스키마 문서

- `docs/db/schema.sql`의 `order_shipment.courier` 컬럼 설명과 CHECK 제약을 갱신한다(실행 스키마 자체는
  `ddl-auto: update`가 로컬에서 자동 반영, 문서는 별도로 맞춰야 함).

## 구현 목록

- [x] `application.yml`에 `delivery-api` 설정 추가
- [x] `DeliveryApiConfig`(RestClient 빈), `DeliveryTrackingClient`(subscribe, 실패 시 false) 추가 + 테스트
- [x] `CourierCode` enum 추가(국내 10개)
- [x] `OrderShipment`에 CHECK 제약 추가, `registerTracking`을 courierCode/trackingNumber/shippedAt만 받도록 축소, `markDelivered` 추가
- [x] `OrderShipmentRegisterRequest`/`OrderShipmentResponse`를 courierCode 기반으로 변경
- [x] `OrderService.registerShipment` 수정 — 구독 성공/실패 분기, 실패 시 기존 즉시-확정 폴백 유지 + `markShipmentDelivered` 추가 + 테스트
- [x] `DeliveryWebhookController` + `DeliveryWebhookService`(서명 검증) + `OrderShipmentRepository` 파생 쿼리 추가 + 테스트
- [x] `SecurityConfig` PUBLIC_ENDPOINTS에 웹훅 경로 추가
- [x] `docs/db/schema.sql` 갱신
- [x] `docs/APIs.md`에 웹훅 엔드포인트(내부용, 인증 불필요) 추가, 실제 웹훅 연동 흐름으로 설명 갱신
- [x] `docs/requests/FE/016-shipment-courier-code-contract.md` 작성
- [x] `FE/docs/notion/기능 정의서.md` 히스토리에 SHIP-002 실연동 반영 기록
- [x] `.claude/skills/BE:verify`로 최종 검증(자격증명 없이도 폴백 경로가 통과하는지 포함)

## 확인 필요 사항 (해결됨/남은 것)

- `endpoint-id`(웹훅 수신 URL 등록)는 1회성 수동 설정으로 가정 — API Key/Secret/Webhook Secret/Endpoint ID는
  환경변수(`DELIVERY_API_KEY` 등)로 사용자가 직접 넣어야 한다(코드에는 없음).
- prod 공개 도메인(Caddyfile 리버스프록시)이 `/api/webhooks/delivery`를 실제로 외부에 노출하는지는 아직
  미확인 — 인프라 쪽에서 별도로 확인 필요.