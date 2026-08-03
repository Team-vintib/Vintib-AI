# 사업자 정보 제출(BIZ-001) + 세금계산서 발행(BIZ-002) API 요청

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

사업자 인증 정보 제출/조회(BIZ-001)와 세금계산서 발행/조회(BIZ-002)를 구현했다.

BIZ-001은 FE 요청 문서(`docs/requests/BE/003-business-contract.md`)의 §3.1/§3.2가 요청한 계약과 실제 구현이 다르다 — 이 프로젝트의 다른 온보딩류 API와 동일하게 경로가 `/api/users/{userId}/business`로 확정됐고, `multipart/form-data` 한 번에 제출하는 대신 상품 이미지·시착 프로필과 동일한 **presigned 2단계 업로드**를 쓴다. 관리자 승인/거절 API는 이 프로젝트에 관리자 권한 체계 자체가 없어(회원 유형은 `GENERAL`/`BUSINESS`뿐) 이번 범위 밖이다 — 승인 상태 전환은 현재 DB를 직접 조작해야만 일어난다.

BIZ-002(세금계산서)는 FE가 요청한 적이 없는 BE 주도 신규 API다. **주문(order) 생성 API가 아직 없어**, 이 API를 실제로 호출할 수 있는 진짜 주문이 지금은 존재하지 않는다 — 계약만 먼저 공유한다. 주문 생성 API가 생기면(Commerce/Wallet, `docs/requests/BE/010-commerce-wallet-contract.md` 참고) 실제 연동이 가능해진다.

## 요청 내용

### 1. 사업자등록증 업로드 (신규/교체 시에만, 2단계)

1. **업로드 URL 발급** — `POST /api/users/{userId}/business/upload-url`
   - 요청: `{ "contentType": string }` (`image/jpeg`, `image/png`, `image/webp` 중 하나만 허용)
   - 응답: `{ "key": string, "uploadUrl": string, "expiresInSeconds": number }`(`expiresInSeconds`는 300, 즉 5분)
2. **S3 직접 업로드** — 1번 응답의 `uploadUrl`로 파일 바이트를 **PUT**(헤더 `Content-Type`을 1번에서 보낸 `contentType`과 동일하게 지정). 상품 이미지·시착 프로필과 완전히 동일한 흐름.

### 2. 사업자 정보 제출/재제출 — `POST /api/users/{userId}/business`

- 요청 바디(전부 필수):
  ```json
  {
    "businessNumber": "1234567890",
    "businessName": "빈티브 상회",
    "representativeName": "홍길동",
    "certificateKey": "business-certificates/1/abc123.jpg"
  }
  ```
  - `businessNumber`: 숫자 10자리.
  - `certificateKey`: 1단계에서 받은 `key`를 그대로 사용.
- 동작: 최초 제출이면 새로 생성되고 상태는 항상 `PENDING`이다(제출만으로 즉시 승인되지 않는다). **`PENDING`/`APPROVED` 상태에서 다시 호출하면 409(`B003`)로 거부된다** — 이미 제출했거나 승인된 정보는 이 엔드포인트로 덮어쓸 수 없다. `REJECTED` 상태에서만 이 엔드포인트가 재제출로 동작해 정보를 갱신하고 상태를 다시 `PENDING`으로 되돌린다.
- 성공(200) 응답:
  ```json
  {
    "status": "PENDING",
    "businessNumber": "1234567890",
    "businessName": "빈티브 상회",
    "representativeName": "홍길동",
    "certificateUrl": "https://s3.example.com/business-certificates/1/abc123.jpg?X-Amz-...",
    "submittedAt": "2026-08-02T12:00:00",
    "verifiedAt": null
  }
  ```
  `certificateUrl`은 짧은 만료시간(10분)의 presigned GET URL이다 — 화면에 오래 캐싱하지 말 것.

### 3. 사업자 정보 조회 — `GET /api/users/{userId}/business`

- 성공(200): 위와 동일한 응답 구조.
- **제출 이력이 없어도 200이다** — 이때 `status: "NONE"`이고 나머지 필드는 전부 `null`이다(에러 아님, 빈 입력 폼으로 처리).
- `APPROVED`/`REJECTED` 상태는 현재 관리자 API가 없어 DB를 직접 바꿔야만 만들어진다 — 화면 시연 시 참고.

### 4. 세금계산서 발행 — `POST /api/orders/{orderId}/invoices`

- 요청 목적: 주문의 판매자가 사업자 인증(`APPROVED`)을 완료했을 때 세금계산서를 발행한다.
- 요청 바디: 없음(서버가 주문·판매자 사업자 정보로 전부 계산한다).
- 권한: 해당 주문의 구매자 또는 판매자만 호출할 수 있다(경로에 `userId`가 없다 — 토큰의 로그인 사용자가 주문 당사자인지로 판별).
- 성공(201) 응답:
  ```json
  {
    "id": 1,
    "orderId": 10,
    "businessNumber": "1234567890",
    "businessName": "빈티브 상회",
    "representativeName": "홍길동",
    "supplyAmount": 100000,
    "taxAmount": 10000,
    "totalAmount": 110000,
    "issuedAt": "2026-08-02T12:00:00"
  }
  ```
  `supplyAmount`(공급가액)·`taxAmount`(부가세)는 주문 금액(`totalAmount`)에서 부가세 10%를 역산한다(`supplyAmount = round(totalAmount / 1.1)`). 주문당 1건만 발행할 수 있다(중복 발행 시 409).

### 5. 세금계산서 조회 — `GET /api/orders/{orderId}/invoices`

- 성공(200): 4번과 동일한 응답 구조.
- 발행된 세금계산서가 없으면 404(`I002`).

### 에러코드

| 코드 | 상황 |
| --- | --- |
| `P006` | 지원하지 않는 이미지 형식(1단계 `contentType`) |
| `B001` | 2단계(S3 업로드)를 하지 않고 `certificateKey`로 제출함 |
| `B002` | 본인 외 사용자의 사업자 정보에 접근하려 함 |
| `B003` | 이미 제출했거나(`PENDING`) 승인된(`APPROVED`) 상태에서 다시 제출하려 함 |
| `O002` | 존재하지 않는 주문 |
| `I001` | 이미 발행된 세금계산서에 다시 발행을 시도함 |
| `I002` | 발행된 세금계산서가 없음(조회 시) |
| `I003` | 판매자가 사업자 인증(`APPROVED`)을 완료하지 않음(발행 시) |
| `I004` | 해당 주문의 구매자/판매자가 아닌 사용자가 접근하려 함 |

모든 엔드포인트는 인증 필요.

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "사업자(Businesses)" 태그(세금계산서 포함)
- `BE/src/main/java/com/ssafy/backend/business/controller/BusinessInfoController.java`
- `BE/src/main/java/com/ssafy/backend/order/controller/InvoiceController.java`
- 참고 선례: `docs/requests/FE/009-tryon-profile-presigned-upload.md`(동일한 presigned 2단계 흐름)

## FE 요청 사항

- 사업자 인증 온보딩 화면(`BUSINESS` 선택 후 이동):
  - **뒤로가기 버튼**을 달아줘. 누르면 이전 온보딩 단계(회원 유형 선택 화면)로 돌아간다.

## 처리 결과

(FE 반영 후 기입)
