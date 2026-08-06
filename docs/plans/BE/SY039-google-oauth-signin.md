# SY039 - 구글 소셜 로그인 (SSAFY SSO 대체)

## 배경/목표

`docs/requests/BE/001-auth-contract.md`가 요청했던 SSAFY SSO(§3.2~3.4)는 BE에 실제로 구현된 적이
없다(코드 전무 확인). 이번 기획 변경으로 SSAFY SSO 대신 **구글 로그인**을 붙인다. 클라이언트
ID/시크릿은 이미 발급받아 둔 상태(Authorization Code 흐름 전제)이고, FE 콜백 페이지도 구글
콘솔에 등록 완료.

목표: 구글 계정으로 로그인하면 기존 이메일/비밀번호 회원과 동일하게 우리 JWT(accessToken/
refreshToken)를 발급받는다. 신규 구글 사용자는 계정이 자동 생성되고(프로필 사진은 구글 것으로
바로 채움), **이미 같은 이메일로 가입된 계정이 있으면 자동 연동하지 않고 사용자에게 연동
여부를 확인받는다**("이미 가입된 계정이 있습니다. 연동하시겠습니까?").

## 작업 내용

### 1. 흐름 — Authorization Code(서버 교환) 방식 + 연동 확인 2단계

```
FE → accounts.google.com 동의 화면 (client_id, redirect_uri, scope=openid email profile)
구글 → FE 콜백 페이지로 redirect (?code=...)
FE → POST /api/auth/google { code, redirectUri }
BE → 구글과 토큰 교환 + id_token 검증 → email/name/picture/sub(googleId) 확보
BE → 이메일로 회원 조회
  ├─ 없음                        → 신규 회원 생성(googleId·profileImageUrl 채움) → 토큰 발급 → status=LOGIN
  ├─ 있고 googleId 이미 연동됨    → 그대로 로그인 → 토큰 발급 → status=LOGIN
  └─ 있고 googleId 미연동(비어있음) → 토큰 미발급, linkToken 발급 → status=LINK_REQUIRED
                                        (연동 대기 정보를 Redis에 TTL로 저장 — EmailVerificationService와 같은 패턴)
FE(LINK_REQUIRED) → "이미 가입된 계정이 있습니다. 연동하시겠습니까?" 확인 UI
FE → POST /api/auth/google/link { linkToken, confirm }
  ├─ confirm=true  → 그 회원에 googleId 연동 → 토큰 발급
  └─ confirm=false → 연동 대기 정보만 폐기, 로그인 없이 종료(사용자는 기존 비밀번호로 로그인)
```

`redirectUri`는 FE가 구글 콘솔에 등록한 값을 그대로 요청 body로 보내 BE가 토큰 교환 시 그대로
넘긴다(구글이 등록값과 정확히 일치해야 검증하므로) — BE가 별도로 값을 들고 있을 필요는 없다.

### 2. 계정 연동 정책

- 이메일로 기존 회원 없음 → `Member` 신규 생성(`password=null`, 기존 SSO 계정 null 허용 설계
  그대로 재사용 — `Member.java:32` 주석 "SSO 전용 계정은 null 허용 (AUTH-003)" 참고), `googleId`와
  `profileImageUrl`(구글 `picture`)을 채운다.
- 이메일로 기존 회원 있고 `googleId` 비어있음 → **바로 연동하지 않는다.** 연동 대기 정보(이메일,
  googleId, name, picture)를 Redis에 `linkToken` 키로 TTL 5분 저장하고, `status=LINK_REQUIRED` +
  `linkToken`을 응답한다. 실제 연동은 `POST /api/auth/google/link`에서 사용자 확인 후에만
  일어난다. **이 케이스에서는 기존 회원의 `profileImageUrl`을 덮어쓰지 않는다** — 이미 본인이
  올린 사진이 있을 수 있으므로 신규 가입 때만 구글 사진을 채운다.
- 이메일로 기존 회원 있고 `googleId` 이미 채워짐(재로그인) → 그대로 로그인.

### 3. 설정/클라이언트 (TossPaymentsConfig·DeliveryApiConfig 패턴을 그대로 따름)

- `application.yml`에 `google-oauth:` 섹션 추가 — `client-id`, `client-secret`을
  `${GOOGLE_OAUTH_CLIENT_ID:}`/`${GOOGLE_OAUTH_CLIENT_SECRET:}` 형태로.
- `global/config/GoogleOAuthConfig.java`: 인증 헤더가 필요 없는 평범한 `RestClient` 빈(구글
  토큰/tokeninfo 엔드포인트는 파라미터로 인증하지 헤더가 아니다).
- `global/client/GoogleOAuthClient.java`: `exchangeCode(code, redirectUri)` → `id_token` 반환,
  `verifyIdToken(idToken)` → `{email, name, picture, sub}` 반환. 둘 다 실패하면 예외를 삼키지 않고
  `CustomException(GOOGLE_AUTH_FAILED)`로 전파한다(로그인 실패를 조용히 넘기면 안 됨 — 결제
  연동과 같은 이유).
- 연동 대기 티켓은 새 컴포넌트를 만들지 않고 `AuthService`에서 기존
  `StringRedisTemplate`(refreshToken 저장에 이미 씀)을 그대로 써서 `auth:google-link:{linkToken}`
  키에 `email:googleId:name:pictureUrl`을 직렬화해 저장한다(이미 있는 `EmailVerificationService`
  토큰 발급 방식과 동일한 결).

### 4. Member 스키마

- `member.google_id VARCHAR(100)` 컬럼 추가, nullable + unique. 여러 provider를 지원하는
  범용 테이블은 지금 필요 없다(구글 하나만 대체하는 것이므로 과설계 지양).
- `docs/db/schema.sql` 갱신.

### 5. API

- `POST /api/auth/google`
  - 요청: `{ code: string, redirectUri: string }`
  - 응답(`GoogleAuthResponse`): `{ status: "LOGIN" | "LINK_REQUIRED", accessToken?, refreshToken?,
    onboardingCompleted?, linkToken?, email? }` — status에 따라 필요한 필드만 채워진다.
- `POST /api/auth/google/link`
  - 요청: `{ linkToken: string, confirm: boolean }`
  - 응답: 항상 `GoogleAuthResponse` 하나로 통일(`status`로 구분) — `confirm=true`면
    `status=LOGIN`(+ accessToken/refreshToken/onboardingCompleted), `confirm=false`면
    `status=LINK_DECLINED`(추가 필드 없음). 응답 타입을 하나로 유지하는 게 FE 처리가 더
    간단해 계획 대비 이렇게 구현했다.
  - `linkToken`이 없거나 만료됐으면 `CustomException(GOOGLE_LINK_EXPIRED)`.
- 둘 다 `SecurityConfig` `PUBLIC_ENDPOINTS`에 추가(로그인 자체이므로 JWT 인증 대상 아님).
- `AuthService.signInWithGoogle(code, redirectUri)` / `AuthService.confirmGoogleLink(linkToken, confirm)`
  두 메서드로 나누고, 토큰 발급은 기존 `issueTokens()`를 그대로 재사용한다.

### 6. 문서

- `docs/requests/BE/001-auth-contract.md`의 SSAFY SSO 관련 항목(§3.2~3.4, §5의 SSO 보류 문구)을
  구글 로그인으로 대체됐다고 갱신.
- `docs/requests/FE/`에 신규 계약 문서 작성 — 두 엔드포인트 스펙, `LINK_REQUIRED` 시 보여줄 확인
  문구·플로우, 온보딩 라우팅 기준(`onboardingCompleted`).

## 구현 목록

- [x] `application.yml`에 `google-oauth` 설정 추가, `.env.example`/`docker-compose.yml`/
      `infra/ci/deploy.sh`에 `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET`
      (prod는 `PROD_GOOGLE_OAUTH_CLIENT_ID`/`SECRET`) 추가 — Delivery와 같은 이유로 필수
      변수(REQUIRED_VARS)에는 넣지 않음
- [x] `GoogleOAuthConfig`(RestClient 빈), `GoogleOAuthClient`(exchangeCode, verifyIdToken) + 테스트
- [x] `ErrorCode`에 `GOOGLE_AUTH_FAILED`, `GOOGLE_LINK_EXPIRED` 추가 — 기존 미구현 `SSO_LOGIN_FAILED`(U002)를
      리네임해 재사용(다른 곳에서 참조 없음 확인 후)
- [x] `Member`에 `googleId` 컬럼 + 구글 가입용 정적 팩토리(`ofGoogle`) + `linkGoogleAccount(googleId)`
      메서드(프로필 이미지는 신규 가입 때만 채우고, 연동 시 덮어쓰지 않음)
- [x] `MemberRepository`: 계획에서는 `findByGoogleId` 추가를 적었으나 실제로 쓰이지 않아(이메일로만
      조회하고 googleId는 in-memory 비교) 추가하지 않음 — 안 쓰는 쿼리 메서드를 만들지 않기 위함
- [x] `AuthController`에 `POST /api/auth/google`, `POST /api/auth/google/link` 추가(Swagger 포함)
- [x] `AuthService.signInWithGoogle`/`confirmGoogleLink` 구현 — Redis 연동 대기 티켓 발급/조회/폐기
      포함 + 테스트 6종(신규 가입/기연동 재로그인/연동 필요/연동 확인 후 로그인/연동 거부/토큰 만료)
- [x] `SecurityConfig` PUBLIC_ENDPOINTS에 두 경로 추가
- [x] `docs/db/schema.sql`·`comments.sql`·`erd.md` 갱신 — 미구현 상태였던 범용
      `member_social_account`(AUTH-003/004, SSAFY 전용) 테이블도 함께 제거하고 `data-dictionary.md`
      재생성(`regen.sh`). `img/erd-full.svg`는 관계선 하나만 빠지는 것이라 재생성은 보류(필요 시
      `export-erd.sh` 실행)
- [x] `docs/APIs.md`에 두 엔드포인트 추가
- [x] `docs/requests/BE/001-auth-contract.md` SSAFY SSO 항목(§3.2~3.4, §5, §6) 갱신
- [x] `docs/requests/FE/036-google-oauth-signin-contract.md` 작성
- [x] `./gradlew build`(compile + 전체 테스트) 통과 확인
