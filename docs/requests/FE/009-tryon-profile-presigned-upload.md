# 시착 프로필 전신사진 업로드 — presigned 2단계 업로드 연동 요청

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

AI 가상 시착 프로필(전신 사진 + 신체 치수) 등록/조회/수정/삭제 API를 구현했다(SY025). FE 요청 문서(`docs/requests/BE/002-onboarding-contract.md` §3.3, `007-live-tryon-contract.md` §3.4)는 `PUT /api/me/tryon`을 `multipart/form-data`로 요청했지만, 실제 구현은 두 가지가 다르게 확정됐다.

1. 경로: 이 프로젝트의 다른 온보딩 API들과 동일하게 `/api/me/...`가 아니라 `/api/users/{userId}/tryon`이다.
2. 업로드 방식: 서버가 파일을 직접 받는 multipart가 아니라, 상품 이미지와 동일한 **presigned 2단계**(브라우저가 S3에 직접 업로드)다. 전신 사진은 비공개 버킷에 저장되고 본인만 열람 가능한 presigned GET URL로만 노출된다.

FE가 이미 multipart 기준으로 화면을 구현해뒀다면(`OnboardingTryOnView.vue` 등) 아래 스펙에 맞춰 재작업이 필요하다.

## 요청 내용

### 1. 사진 업로드 (신규/교체 시에만, 파일당 아래 2단계)

1. **업로드 URL 발급** — `POST /api/users/{userId}/tryon/upload-url`
   - 요청: `{ "contentType": string }` (`image/jpeg`, `image/png`, `image/webp` 중 하나만 허용)
   - 응답: `{ "key": string, "uploadUrl": string, "expiresInSeconds": number }`(`expiresInSeconds`는 300, 즉 5분)
2. **S3 직접 업로드** — 1번 응답의 `uploadUrl`로 파일 바이트를 **PUT**(헤더 `Content-Type`을 1번에서 보낸 `contentType`과 동일하게 지정). 백엔드를 거치지 않고 브라우저가 S3(MinIO)에 직접 요청한다(상품 이미지 업로드와 완전히 동일한 흐름).

### 2. 프로필 등록/수정 — `PUT /api/users/{userId}/tryon`

- 요청 바디(전부 선택, 보낸 필드만 반영되는 **부분 병합** — 보내지 않은 필드는 기존 값 유지):
  ```json
  {
    "bodyPhotoKey": "tryon-profiles/1/abc123.jpg",
    "heightCm": 170,
    "weightKg": 60,
    "chest": 90,
    "waist": 70,
    "hip": 95
  }
  ```
  - `bodyPhotoKey`: 1단계에서 받은 `key`를 그대로 사용. 사진을 바꾸지 않으면 생략.
  - 온보딩에서 일부만 입력하고 라이브 시착 패널에서 나머지를 이어서 입력하는 흐름을 지원하기 위해 부분 병합으로 설계했다 — 신체 치수 하나만 보내도 나머지 필드가 사라지지 않는다.
- 성공(200) 응답:
  ```json
  {
    "bodyPhotoUrl": "https://s3.example.com/tryon-profiles/1/abc123.jpg?X-Amz-...",
    "heightCm": 170,
    "weightKg": 60,
    "chest": 90,
    "waist": 70,
    "hip": 95,
    "updatedAt": "2026-08-02T12:00:00"
  }
  ```
  `bodyPhotoUrl`은 짧은 만료시간(10분)의 presigned GET URL이다 — 화면에 오래 캐싱하지 말고 조회 시점 값을 그대로 쓸 것.

### 3. 프로필 조회 — `GET /api/users/{userId}/tryon`

- 성공(200): 위와 동일한 응답 구조.
- **아직 등록 전이면 404**(`error.code = "T001"`)가 정상 흐름이다 — 에러 토스트가 아니라 빈 입력 폼으로 처리해달라.

### 4. 프로필 삭제 — `DELETE /api/users/{userId}/tryon`

- 성공: 204. 사진과 신체 치수를 함께 삭제한다(부분 삭제 없음).
- 등록된 프로필이 없으면 404(`T001`).

### 에러코드

| 코드 | 상황 |
| --- | --- |
| `P006` | 지원하지 않는 이미지 형식(1단계 `contentType`) |
| `T001` | 등록된 프로필 없음 (조회/삭제) |
| `T005` | 2단계(S3 업로드)를 하지 않고 `bodyPhotoKey`로 3번을 호출함 |
| `T006` | 본인 외 사용자의 프로필에 접근하려 함 |

모든 엔드포인트는 인증 필요(본인만).

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "AI 가상 시착 프로필" 태그
- `BE/src/main/java/com/ssafy/backend/tryon/controller/TryOnProfileController.java`
- 참고 선례: `docs/requests/FE/001-product-image-presigned-upload.md`(상품 이미지, 동일한 3단계 흐름)

## 처리 결과

(FE 반영 후 기입)
