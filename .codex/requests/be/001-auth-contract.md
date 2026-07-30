# 인증 도메인 API 계약 보완 요청

## 요청자 파트 / 대상 파트

- 요청자: FE
- 대상: BE

## 배경/이유

FE는 메일 회원가입, 로그인, 토큰 저장, 재발급, 로그아웃을 실제 BE API에 붙일 수 있다. 다만 회원가입/로그인 직후 라우팅에 필요한 사용자 정보와 `nextStep`, 내 정보 조회, SSO 범위가 아직 확정되지 않아 인증 도메인 계약을 한 문서로 정리한다.

## 현재 BE에서 그대로 사용할 수 있는 계약

FE axios `baseURL`은 `VITE_API_BASE_URL ?? '/api'`이고 FE API 함수는 `/auth/...`를 호출하므로 실제 요청은 `/api/auth/...`로 나간다.

| 기능 | Method | Endpoint | 인증 | 현재 BE 구현 |
| --- | --- | --- | --- | --- |
| 이메일 중복 확인 | `POST` | `/api/auth/email/check-duplicate` | 불필요 | 구현됨 |
| 이메일 인증코드 발송 | `POST` | `/api/auth/email/send-code` | 불필요 | 구현됨 |
| 이메일 인증코드 확인 | `POST` | `/api/auth/email/verify-code` | 불필요 | 구현됨 |
| 메일 회원가입 | `POST` | `/api/auth/signup` | 불필요 | 구현됨 |
| 메일 로그인 | `POST` | `/api/auth/signin` | 불필요 | 구현됨 |
| 토큰 재발급 | `POST` | `/api/auth/reissue` | 불필요 | 구현됨 |
| 로그아웃 | `POST` | `/api/auth/logout` | 필요 | 구현됨 |
| SSAFY SSO 시작 | `GET` | `/api/auth/sso/ssafy` | 불필요 예상 | 미구현 |
| SSAFY SSO 콜백 | `POST` | `/api/auth/ssafy/callback` | 불필요 예상 | 미구현 |
| SSAFY 계정 연결 | `POST` | `/api/auth/ssafy/link-account` | 필요 예상 | 미구현 |

공통 응답 envelope는 현재 BE `ApiResponse<T>`를 그대로 사용한다.

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

오류 응답은 현재 BE `ErrorResponse` 구조를 그대로 사용한다.

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "C001",
    "message": "잘못된 입력값입니다.",
    "errors": [
      {
        "field": "email",
        "value": "bad-email",
        "reason": "올바른 형식의 이메일 주소여야 합니다."
      }
    ]
  }
}
```

## 현재 요청/응답 규격

### 이메일 중복 확인

```http
POST /api/auth/email/check-duplicate
Content-Type: application/json
```

```json
{
  "email": "user@example.com"
}
```

성공은 `200 OK`, `ApiResponse<null>`이다. 이미 가입된 이메일은 `409`, `U003`이다.

### 이메일 인증코드 발송

```http
POST /api/auth/email/send-code
Content-Type: application/json
```

```json
{
  "email": "user@example.com"
}
```

성공은 `200 OK`, `ApiResponse<null>`이다.

운영 정책은 현재 구현 기준으로 확정 가능하다.

- 인증코드 유효 시간: 5분
- 재발송 가능 간격: 60초
- 발송 제한: 5분 동안 최대 5회
- 인증 실패 허용 횟수: 5회
- 실패 횟수 초과 시 기존 인증코드 삭제
- 인증 성공 시 기존 인증코드와 실패 횟수 삭제
- 같은 이메일로 재발송하면 기존 `email:verify:code:{email}` 값은 새 코드로 대체

### 이메일 인증코드 확인

```http
POST /api/auth/email/verify-code
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

성공:

```json
{
  "success": true,
  "data": {
    "verificationToken": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  },
  "error": null
}
```

`verificationToken` 유효 시간은 30분이며 회원가입 성공 시 삭제되어 재사용할 수 없다.

### 메일 회원가입

```http
POST /api/auth/signup
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "password12!",
  "name": "홍길동",
  "verificationToken": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

현재 BE 성공 응답:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "name": "홍길동",
    "onboardingCompleted": false
  },
  "error": null
}
```

### 메일 로그인

```http
POST /api/auth/signin
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "password12!"
}
```

현재 BE 성공 응답:

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ..."
  },
  "error": null
}
```

FE의 `rememberMe`는 BE로 보내지 않고 localStorage/sessionStorage 선택에만 사용한다.

### 토큰 재발급

```http
POST /api/auth/reissue
Content-Type: application/json
```

```json
{
  "refreshToken": "eyJ..."
}
```

현재 BE 성공 응답은 `accessToken`, `refreshToken`만 포함한다.

현재 구현 기준:

- refresh token은 Redis `auth:refresh:{memberId}` 키로 저장된다.
- 회원 1명당 refresh token 1개만 저장된다.
- 새 로그인 또는 재발급 시 기존 refresh token은 새 값으로 덮어써진다.
- body refresh token의 JWT 검증과 Redis 저장값 일치 검증을 통과해야 새 토큰을 발급한다.
- 로그아웃은 Redis refresh token을 삭제한다.
- 로그아웃 후 access token은 JWT 만료 전까지 형식상 유효할 수 있으나 refresh token은 재발급에 사용할 수 없다.

## BE에 요청하는 보완 사항

### 1. 회원가입 성공 후 로그인 정책

회원가입 직후 사용자를 로그인 상태로 만들고 온보딩 시작 화면으로 진입시키는 정책으로 확정 요청한다.

요청 응답 `data` 후보:

```json
{
  "accessToken": "eyJ...",
  "refreshToken": "eyJ...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "홍길동",
    "nickname": "vintagelover",
    "onboardingCompleted": false
  },
  "nextStep": "ONBOARD_PROFILE"
}
```

필드 규칙:

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `accessToken` | string | 필수 | Bearer access token |
| `refreshToken` | string | 필수 | refresh token |
| `user.id` | number | 필수 | 회원 ID |
| `user.email` | string | 필수 | 가입 이메일 |
| `user.name` | string | 필수 | 가입 이름 |
| `user.nickname` | string/null | 선택 | 온보딩 전이면 null 가능 |
| `user.onboardingCompleted` | boolean | 필수 | 온보딩 완료 여부 |
| `nextStep` | enum | 필수 | `HOME`, `ONBOARD_PROFILE`, `LINK_ACCOUNT` |

### 2. 로그인 응답 또는 내 정보 조회

로그인 성공 직후 FE가 온보딩 분기를 판단할 수 있어야 한다.

- `POST /api/auth/signin` 응답에 `user`, `nextStep`을 포함하거나
- 별도 `GET /api/users/me` 또는 `GET /api/me`를 제공한다.

내 정보 조회 응답 `data` 최소 필드:

```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "홍길동",
  "nickname": "vintagelover",
  "memberType": "GENERAL",
  "onboardingCompleted": false
}
```

`memberType`은 온보딩 통합 요청의 `GENERAL | BUSINESS`와 같은 enum을 사용한다.

### 2-1. FE 세션 복구 검증용 내 정보 조회

FE는 브라우저 `localStorage`/`sessionStorage`에 남은 토큰만으로 로그인 상태를 확정하지 않도록 수정했다. 현재는 저장된 `refreshToken`으로 `POST /api/auth/reissue`를 1회 호출해 Redis refresh token과 회원 존재 여부를 검증하고, 실패하면 로컬 세션을 정리한다.

다만 이 방식은 앱 진입 시 refresh token을 회전시키므로, 장기적으로는 아래 중 하나가 필요하다.

- `GET /api/users/me` 또는 `GET /api/me` 제공
- 해당 endpoint는 access token의 서명/만료와 회원 존재 여부를 모두 검증
- 성공 시 최소 사용자 정보 반환
- 실패 시 `401`과 `U010` 또는 `U011` 반환

이 endpoint가 확정되면 FE는 앱 시작 세션 검증을 `reissue` 대신 내 정보 조회로 교체할 수 있다.

### 3. 토큰 만료 정보

현재 `TokenResponse`의 `accessToken`, `refreshToken`만으로 1차 연동은 가능하다. 추후 자동 갱신 정확도를 높이려면 `accessTokenExpiresIn` 또는 `accessTokenExpiresAt` 추가 여부를 확정 요청한다.

### 4. 에러 코드와 필드명 문서화

현재 BE `ErrorCode` 기준으로 FE가 매핑할 주요 코드는 아래와 같다. Swagger 또는 별도 문서에 HTTP status와 함께 노출 요청한다.

| 코드 | 의미 | FE 처리 |
| --- | --- | --- |
| `C001` | validation 실패 | `errors[].field` 기준 필드 표시 |
| `U003` | 이미 가입된 이메일 | email 필드 오류 |
| `U005` | 인증코드 불일치/만료 | code 필드 오류 |
| `U006` | 이메일 인증 필요 | verificationToken/공통 오류 |
| `U007` | 인증 시도 횟수 초과 | code 공통 오류 |
| `U008` | 인증코드 요청 과다 | email 공통 오류 |
| `U009` | 이메일 또는 비밀번호 불일치 | 로그인 공통 오류 |
| `U010` | 유효하지 않은 토큰 | 세션 정리/재로그인 |
| `U011` | 만료된 토큰 | refresh 재시도 후보 |

FE가 매핑하기 쉬운 필드명은 `email`, `code`, `verificationToken`, `password`, `name`이다.

### 5. SSAFY SSO

시연 전 범위에서는 SSAFY SSO를 보류한다. 이후 구현 시 FE 예상 endpoint는 아래와 같다.

- `GET /api/auth/sso/ssafy`
- `POST /api/auth/ssafy/callback`
- `POST /api/auth/ssafy/link-account`

## FE 관련 파일

- `FE/src/domains/auth/api/authApi.ts`
- `FE/src/domains/auth/types/auth.types.ts`
- `FE/src/domains/auth/stores/authStore.ts`
- `.codex/plans/fe/SY012-auth-api.md`

## 2026-07-31 최신 BE 확인 결과

### 반영 확인

| 항목 | 현재 BE 상태 |
| --- | --- |
| 이메일 중복 확인 | `POST /api/auth/email/check-duplicate` 구현됨 |
| 이메일 인증코드 발송 | `POST /api/auth/email/send-code` 구현됨 |
| 이메일 인증코드 확인 | `POST /api/auth/email/verify-code` 구현됨. `verificationToken` 반환 |
| 이메일 회원가입 | `POST /api/auth/signup` 구현됨. 토큰은 반환하지 않음 |
| 이메일 로그인 | `POST /api/auth/signin` 구현됨. `accessToken`, `refreshToken` 반환 |
| 토큰 재발급 | `POST /api/auth/reissue` 구현됨 |
| 로그아웃 | `POST /api/auth/logout` 구현됨 |

### 남은 요청

- SSAFY SSO 시작/callback/account-link API는 아직 BE에 없다.
- 로그인 또는 회원가입 직후 FE route guard에 필요한 `user`, `nextStep`이 없다. 로그인 응답 확장 또는 `GET /api/me` 제공이 필요하다.
- access token 만료 시 자동 재발급 정책과 주요 오류 코드(`U010`, `U011`)를 Swagger에 고정해 달라.
