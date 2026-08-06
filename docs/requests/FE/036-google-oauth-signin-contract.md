# 036 구글 로그인 API 계약 (SSAFY SSO 대체)

## 요청자 파트 / 대상 파트

BE → FE

## 배경/이유

기획 변경으로 SSAFY SSO(`001-auth-contract.md` §3.2~3.4)를 구글 로그인으로 대체했다(SY039).
설계는 `docs/plans/BE/SY039-google-oauth-signin.md` 참고. 클라이언트 ID/시크릿은 이미 발급돼
있고, FE 콜백 페이지도 구글 콘솔에 등록 완료 상태로 안다.

## 요청 내용

### 흐름

1. FE가 구글 동의 화면(`accounts.google.com/o/oauth2/v2/auth`)으로 리다이렉트한다.
   `client_id`, `redirect_uri`(콘솔에 등록한 콜백 페이지), `scope=openid email profile`,
   `response_type=code`를 쿼리로 싣는다. `client_id`는 공개값이라 FE가 직접 들고 있어도 된다.
2. 구글이 콜백 페이지로 `?code=...`를 실어 리다이렉트한다.
3. FE가 `POST /api/auth/google`에 `{ code, redirectUri }`를 보낸다. `redirectUri`는 1번에서
   실제로 사용한 값과 **정확히 같아야** 한다(다르면 구글이 토큰 교환 자체를 거부한다).
4. 응답의 `status`로 분기한다.

### `POST /api/auth/google`

요청:
```json
{ "code": "4/0AY0e-g7...", "redirectUri": "https://i15a108.p.ssafy.io/auth/google/callback" }
```

응답(`status: "LOGIN"` — 신규 가입 또는 이미 연동된 계정 재로그인, 둘 다 동일 처리):
```json
{
  "success": true,
  "data": {
    "status": "LOGIN",
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "onboardingCompleted": false,
    "linkToken": null,
    "email": null
  },
  "error": null
}
```

응답(`status: "LINK_REQUIRED"` — 이미 같은 이메일로 가입된 계정이 있어 자동 로그인하지 않음.
**이 경우 토큰이 발급되지 않는다** — accessToken/refreshToken 없이 그대로 로그인 화면처럼 두고,
아래 확인 UI를 띄운다):
```json
{
  "success": true,
  "data": {
    "status": "LINK_REQUIRED",
    "accessToken": null,
    "refreshToken": null,
    "onboardingCompleted": null,
    "linkToken": "3f29b1e2-...",
    "email": "user@example.com"
  },
  "error": null
}
```

`LINK_REQUIRED`를 받으면 "이미 가입된 계정(`{email}`)이 있습니다. 연동하시겠습니까?" 확인 UI를
띄운다. `linkToken`은 5분간만 유효 — 그 안에 아래 API를 호출해야 한다.

### `POST /api/auth/google/link`

요청:
```json
{ "linkToken": "3f29b1e2-...", "confirm": true }
```

- `confirm: true` → `status: "LOGIN"`(위와 같은 형태로 토큰 발급)
- `confirm: false` → `status: "LINK_DECLINED"`(토큰 없음, 그냥 로그인 화면에 남아 기존
  비밀번호로 로그인하면 된다)
- `linkToken`이 만료/무효면 400(`errorCode: "U016"`) — 처음부터 다시 시도해야 한다는 안내를
  보여주면 된다.

### 신규 가입 시 처리

이메일로 기존 회원이 없으면 그 자리에서 계정이 생성된다(가입/로그인이 한 API로 합쳐짐).
구글 프로필 사진이 있으면 `profileImageUrl`에 바로 채워지고, 기존 계정에 연동하는 경우에는
프로필 사진을 덮어쓰지 않는다(이미 본인이 올렸을 수 있어서).

## 관련 자료

- 설계: `docs/plans/BE/SY039-google-oauth-signin.md`
- 원 요청: `docs/requests/BE/001-auth-contract.md` §3.2~3.4(SSAFY SSO, 대체됨)
- 구현: `AuthController`(`POST /api/auth/google`, `POST /api/auth/google/link`),
  `AuthService#signInWithGoogle`/`confirmGoogleLink`
