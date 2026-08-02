# 사업자 정보 제출(BIZ-001) 확정 계약

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

사업자 인증 정보 제출/조회(BIZ-001)를 구현했다. FE 요청 문서(`docs/requests/BE/003-business-contract.md`)의 §3.1/§3.2가 요청한 계약과 실제 구현이 다르다 — 이 프로젝트의 다른 온보딩류 API와 동일하게 경로가 `/api/users/{userId}/business`로 확정됐고, `multipart/form-data` 한 번에 제출하는 대신 상품 이미지·시착 프로필과 동일한 **presigned 2단계 업로드**를 쓴다. 관리자 승인/거절 API는 이 프로젝트에 관리자 권한 체계 자체가 없어(회원 유형은 `GENERAL`/`BUSINESS`뿐) 이번 범위 밖이다 — 승인 상태 전환은 현재 DB를 직접 조작해야만 일어난다.

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

### 에러코드

| 코드 | 상황 |
| --- | --- |
| `P006` | 지원하지 않는 이미지 형식(1단계 `contentType`) |
| `B001` | 2단계(S3 업로드)를 하지 않고 `certificateKey`로 제출함 |
| `B002` | 본인 외 사용자의 사업자 정보에 접근하려 함 |
| `B003` | 이미 제출했거나(`PENDING`) 승인된(`APPROVED`) 상태에서 다시 제출하려 함 |

모든 엔드포인트는 인증 필요.

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "사업자(Businesses)" 태그
- `BE/src/main/java/com/ssafy/backend/business/controller/BusinessInfoController.java`
- 참고 선례: `docs/requests/FE/009-tryon-profile-presigned-upload.md`(동일한 presigned 2단계 흐름)

## 처리 결과

(FE 반영 후 기입)
