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
- 원문 바디를 `String`으로 받아 `X-Webhook-Signature`를 `"sha256=" + HMAC-SHA256(webhookSecret,
  "{timestamp}.{rawBody}")` 형식(문서 Node.js 참조 구현 기준 — 접두어 없이 다이제스트만 비교하면
  실제 웹훅에서 전부 검증 실패한다, 2026-08-06 실제 API 문서 확인 후 수정)으로 재계산해 검증하고,
  `X-Webhook-Timestamp`가 현재 시각과 300초 이상 차이 나면 거부한다.
- 검증 통과 후 JSON을 파싱해 `items[]`를 순회 — `status == "DELIVERED"`인 항목만 처리한다(당초
  `isDelivered` boolean으로 가정했으나, 실제 API는 `PENDING`/`REGISTERED`/`PICKUP_READY`/
  `PICKED_UP`/`IN_TRANSIT`/`OUT_FOR_DELIVERY`/`DELIVERED`/`FAILED`/`RETURNED`/`CANCELLED`/
  `HOLD`/`UNKNOWN` 상태 코드를 쓴다 — 2026-08-06 수정).
- `(courierCode, trackingNumber)`로 `OrderShipmentRepository`에서 대상 주문을 찾는다(신규 파생 쿼리).
  주문 상태가 이미 `SHIPPING`이 아니면(중복 웹훅 등) 그냥 무시한다(idempotent).
- 찾으면 `order.markDelivered(now)` 호출 — 기존 `SY033` 로직(7일 뒤 자동 확정 시각 계산)을 그대로 재사용한다.

### 5. 스키마 문서

- `docs/db/schema.sql`의 `order_shipment.courier` 컬럼 설명과 CHECK 제약을 갱신한다(실행 스키마 자체는
  `ddl-auto: update`가 로컬에서 자동 반영, 문서는 별도로 맞춰야 함).

### 6. 배송 진행 상태 노출 (2026-08-06 추가)

**배경**: 지금까지는 웹훅이 `status == "DELIVERED"`가 아닌 항목을 전부 버렸다(`continue`). 그
결과 구매자는 "배송중"인지 "배송지 도착"인지 전혀 알 수 없고 송장 등록/배송완료 두 지점만
보인다. 구매자가 배송 진행 상황을 추적할 수 있어야 한다는 요구사항에 맞춰, 중간 상태도
저장·노출한다.

- `order.entity.TrackingStatus` enum 신규 추가 — 문서 기준 12개 상태 코드를 그대로 옮긴다
  (`PENDING`/`REGISTERED`/`PICKUP_READY`/`PICKED_UP`/`IN_TRANSIT`/`OUT_FOR_DELIVERY`/
  `DELIVERED`/`FAILED`/`RETURNED`/`CANCELLED`/`HOLD`/`UNKNOWN`). `CourierCode`와 같은 모양으로
  `apiCode`(문서 값 그대로, 대문자라 apiCode == name)와 한글 `displayName`(집하 준비/배송중/
  배송완료 등)을 갖는다.
- `OrderShipment`에 `tracking_status VARCHAR(20)` 컬럼 추가(nullable — 송장 등록 직후 첫 웹훅
  받기 전에는 null). CHECK 제약은 위 12개 값으로.
- `OrderShipment.updateTrackingStatus(TrackingStatus)` 메서드 추가 — `markDelivered`와 별개로,
  웹훅이 올 때마다(상태가 무엇이든) 호출된다.
- `OrderService.markShipmentDelivered` → `updateShipmentTracking(CourierCode, String, TrackingStatus)`로
  확장한다. 항상 `shipment.updateTrackingStatus(status)`를 호출하고, `status == DELIVERED`이면서
  주문이 아직 `SHIPPING`이면 기존 `deliver(...)`(주문 확정 시각 계산 등)를 그대로 이어서 호출한다.
- `DeliveryWebhookService.handle()`: `status == "DELIVERED"`만 걸러내던 필터를 없애고, 파싱되는
  모든 item에 대해 `updateShipmentTracking`을 호출한다. `courierCode`/`trackingNumber`/`status`
  중 하나라도 파싱 실패하면 그 item만 로그 남기고 건너뛴다(기존과 동일한 방어).
- `OrderShipmentResponse`에 `trackingStatus`(enum name)와 `trackingStatusLabel`(한글, `CourierCode`의
  `courierName`과 같은 패턴)을 추가한다. 구매확정 버튼 활성화 기준은 그대로 `order.status ==
  DELIVERED`를 쓴다(이미 노출 중) — `trackingStatus`는 진행 상황 표시 전용이고 버튼 게이팅에는
  안 쓴다(두 값이 어긋나는 경합 상태를 만들지 않기 위함).
- FE 계약 문서(`docs/requests/FE/`)에 `trackingStatus`/`trackingStatusLabel` 필드 추가와 12개 상태
  값·한글 라벨 매핑표를 공유한다.

### 7. 웹훅 엔드포인트 등록 API화 (2026-08-06 추가)

지금까지 `POST /v1/webhooks/endpoints`(deliveryapi.co.kr에 우리 웹훅 수신 URL을 등록하는 1회성
설정)는 앱 코드가 아니라 수동 curl로 했다. 이걸 앱 코드로 옮기되, **자동 트리거는 걸지 않는다**
— 계정당 등록 가능 엔드포인트가 최대 10개라 앱 재시작마다 자동 호출하면 한도를 금방 소진한다.
대신 **수동 트리거용 내부 API**로 만든다(사용자 결정).

- `DeliveryTrackingClient.registerEndpoint(url, name)` 추가 — `POST /v1/webhooks/endpoints` 호출,
  `webhookSecret`(우리가 미리 정한 값)을 함께 보낸다. `DELIVERY_API_WEBHOOK_SECRET`이 비어 있으면
  호출 자체를 막는다(`DELIVERY_WEBHOOK_SECRET_REQUIRED`) — 비워 보내면 저쪽이 임의 생성한
  시크릿으로 검증 테스트 POST에 서명하는데 우리가 그 값을 알 방법이 없어 등록이 항상 실패하는
  문제를 이미 겪었다.
- `global.delivery.DeliveryWebhookSetupController`: `POST /api/internal/delivery/webhook-endpoint`
  신규. 일반 로그인 인증만 요구하고(별도 권한 체계 없음) `PUBLIC_ENDPOINTS`에는 넣지 않는다 —
  개발자가 필요할 때만 Swagger UI 등에서 직접 호출하는 용도라 항상 열려 있을 필요가 없다.
- `ErrorCode`에 `DELIVERY_WEBHOOK_SECRET_REQUIRED`(O009), `DELIVERY_ENDPOINT_REGISTRATION_FAILED` 추가.

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
- [x] `docs/requests/FE/023-shipment-courier-code-contract.md` 작성
- [x] `FE/docs/notion/기능 정의서.md` 히스토리에 SHIP-002 실연동 반영 기록
- [x] `.claude/skills/BE:verify`로 최종 검증(자격증명 없이도 폴백 경로가 통과하는지 포함)

### 6. 배송 진행 상태 노출 (2026-08-06 추가)

- [x] `order.entity.TrackingStatus` enum 추가(12개 상태, apiCode/displayName)
- [x] `OrderShipment`에 `trackingStatus` 컬럼 + `updateTrackingStatus()` 메서드 + CHECK 제약
- [x] `OrderService.markShipmentDelivered` → `updateShipmentTracking`으로 확장(항상 상태 갱신,
      DELIVERED일 때만 기존 확정 로직 이어감) + 테스트(중간 상태만 오면 확정 안 됨/DELIVERED
      오면 확정됨/이미 SHIPPING 아니면 무시, 3가지)
- [x] `DeliveryWebhookService.handle()` — DELIVERED 필터 제거, 모든 item에 대해
      `updateShipmentTracking` 호출 + 테스트 갱신
- [x] `OrderShipmentResponse`에 `trackingStatus`/`trackingStatusLabel` 추가
- [x] `docs/db/schema.sql`·`comments.sql` 갱신 + `regen.sh`로 `data-dictionary.md` 재생성
- [x] `docs/requests/FE/038-shipment-tracking-status-contract.md` 작성
- [x] `./gradlew build`로 최종 검증(전체 그린)

### 7. 웹훅 엔드포인트 등록 API화 (2026-08-06 추가)

- [x] `ErrorCode`에 `DELIVERY_WEBHOOK_SECRET_REQUIRED`(O009), `DELIVERY_ENDPOINT_REGISTRATION_FAILED` 추가
- [x] `WebhookEndpointResponse` 추가, `DeliveryTrackingClient.registerEndpoint(url, name)` 구현
      (webhookSecret 비어있으면 호출 전에 막음) + 테스트
- [x] `global.delivery.DeliveryWebhookSetupController` — `POST /api/internal/delivery/webhook-endpoint`
      (인증 필요, PUBLIC_ENDPOINTS 미포함)
- [x] `README.md` 디렉터리 구조에 `global/delivery/` 반영
- [x] `./gradlew build`로 최종 검증

### 8. 즉시-확정 폴백 → 지연 폴백 배치로 변경 (2026-08-11 추가)

**배경**: 즉시-확정 폴백(웹훅 구독 실패 시 그 자리에서 바로 `deliver(order, shipment, now)`)이
버그로 드러났다 — 구매 상세 화면에서 송장 등록과 동시에 배송 상태 바가 "배송완료"로 뛰고,
`deliveredAt`도 실제 완료 시각이 아니라 송장 등록 시각 그대로였다. `deliveryapi.co.kr` 자격증명이
없는 로컬/CI 환경에서는 항상 이 폴백을 타기 때문에 매번 재현됐다.

사용자 결정: 즉시 확정 대신, 기존 `OrderAutoConfirmScheduler`(배송완료 3일 후 자동 구매확정,
`ORDER-003`)와 같은 모양의 배치로 지연 시뮬레이션한다.

- `OrderShipment`에 `webhook_subscribed BOOLEAN NOT NULL DEFAULT FALSE` 추가 — 웹훅 구독 성공
  건(진짜 웹훅을 기다리는 중)과 실패 건(폴백 대상)을 구분한다. `trackingStatus`만으로는 둘 다
  `null`이라 구분이 안 된다.
- `OrderService.registerShipment()`에서 `deliver()` 즉시 호출 제거, `shipment.markWebhookSubscribed
  (subscribed)`로 결과만 저장. 구독 성공/실패 모두 `order.markShipping()`까지만 하고 끝.
- `OrderService.deliverDueFallbackShipments()` 신규 — `webhookSubscribed=false`이고 `shippedAt`이
  `FALLBACK_DELAY`(5분, 운영 정책 미확정이라 데모/로컬용으로 짧게 잡음) 이상 지난 건을 찾아 기존
  `deliver(...)`를 배치 처리 시각으로 호출한다. `deliveredAt`이 이제 등록 시각과 달라진다.
- `order/scheduler/ShipmentFallbackDeliveryScheduler` 신규 — `OrderAutoConfirmScheduler`와 동일한
  `@Scheduled(fixedDelay=...)` 패턴, 1분 주기로 위 메서드를 호출한다.
- `DemoOrderSeeder`의 `SHIPPING` 스테이지 데모 주문은 `shippedAt`이 이미 과거로 시딩돼 있어 이
  배치가 그대로 두면 바로 완료 처리해버린다 — `markWebhookSubscribed(true)`를 강제로 호출해
  스케줄러 대상에서 제외했다(데모 데이터는 "배송중" 스테이지로 고정돼야 하므로).
- `docs/db/schema.sql`/`comments.sql`에 컬럼 반영 + `regen.sh`로 `data-dictionary.md` 재생성.

- [x] `OrderShipment`: `webhookSubscribed` 컬럼 + `markWebhookSubscribed()` 추가
- [x] `OrderService.registerShipment()`: 즉시 `deliver()` 호출 제거, `markWebhookSubscribed(subscribed)`로 대체
- [x] `OrderShipmentRepository`: 지연 대상 조회 파생 쿼리 추가
- [x] `OrderService.deliverDueFallbackShipments()` 추가(`FALLBACK_DELAY` 상수 포함)
- [x] `order/scheduler/ShipmentFallbackDeliveryScheduler` 추가
- [x] `DemoOrderSeeder`: `SHIPPING` 스테이지에서 `markWebhookSubscribed(true)` 호출 추가
- [x] 관련 테스트 추가/갱신
- [x] `docs/db/schema.sql`/`comments.sql` 갱신 + `regen.sh`
- [x] `.claude/skills/BE:verify`로 최종 검증

## 확인 필요 사항 (해결됨/남은 것)

- `endpoint-id`(웹훅 수신 URL 등록)는 1회성 수동 설정으로 가정 — API Key/Secret/Webhook Secret/Endpoint ID는
  환경변수(`DELIVERY_API_KEY` 등)로 사용자가 직접 넣어야 한다(코드에는 없음).
- prod 공개 도메인(Caddyfile 리버스프록시)이 `/api/webhooks/delivery`를 실제로 외부에 노출하는지는 아직
  미확인 — 인프라 쪽에서 별도로 확인 필요.