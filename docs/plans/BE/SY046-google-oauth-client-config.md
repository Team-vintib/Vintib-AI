# SY046 - 구글 로그인 client_id 공개 조회 API

## 배경/목표

[[SY039-google-oauth-signin]]에서 FE는 구글 동의 화면 리다이렉트용 `client_id`를 자체
`VITE_GOOGLE_CLIENT_ID` 빌드 환경변수로 따로 들고 있었다. 이 값이 BE의
`GOOGLE_OAUTH_CLIENT_ID`와 동일한 값인데도 두 곳에 중복 관리되다 보니, FE 쪽 배포 빌드에서
값이 비어 있는 채로 나가 구글 동의 화면 진입 자체가 `invalid_client`로 실패하는 사고가 있었다
(`FE/.env.production`에 키 자체가 누락됨).

`client_id`는 애초에 공개값(비밀 아님 — OAuth 스펙상 클라이언트 시크릿과 달리 브라우저에
노출돼도 안전)이므로, BE가 이미 정확히 설정해 둔 값을 FE가 API로 읽어가게 하면 값을 한 곳(BE
환경변수)에서만 관리하면 된다. FE 빌드 시점 값 누락 사고 자체가 구조적으로 사라진다.

## 작업 내용

- `GET /api/auth/google/config` 추가 — 인증 불필요(`SecurityConfig` PUBLIC_ENDPOINTS).
- 응답: `{ clientId: string }`. `GoogleOAuthConfig.GoogleOAuthProperties.clientId()`를 그대로
  내려준다 — 별도 가공 없음.
- `AuthService`에 `getGoogleOAuthConfig()` 추가(기존 패턴대로 컨트롤러가 서비스를 거치게 함).
  `GoogleOAuthConfig.GoogleOAuthProperties`를 `AuthService`에 새로 주입.
- FE는 `VITE_GOOGLE_CLIENT_ID` 빌드 환경변수를 제거하고, 리다이렉트 직전에 이 API를 호출해
  받은 `clientId`를 쓰도록 바꾼다. 원래는 FE 쪽 변경을 요청 문서로 넘길 계획이었으나, 사용자
  승인 하에 이번 세션에서 BE가 FE 코드까지 함께 반영했다(예외적 처리 — 팀 간 코드 미수정
  원칙의 일반 예외는 아님).

## 구현 목록

- [x] `GoogleOAuthConfigResponse(String clientId)` DTO 추가
- [x] `AuthService.getGoogleOAuthConfig()` 추가 + `GoogleOAuthProperties` 주입
- [x] `AuthController`에 `GET /api/auth/google/config` 추가(Swagger 포함)
- [x] `SecurityConfig` PUBLIC_ENDPOINTS에 `/api/auth/google/config` 추가
- [x] 서비스 단위 테스트(설정된 clientId를 그대로 반환하는지)
- [x] `docs/APIs.md`에 엔드포인트 추가
- [x] FE 반영(사용자 승인 하 예외적으로 BE가 직접 수정) — `authApi.ts`/`googleOAuth.ts`가
      `GET /api/auth/google/config`를 호출하도록, `LoginForm`/`SignupForm`/`SignupEntryPage`/
      `AuthLinkAccountPage`/`GoogleSsoCallbackPage`의 구글 로그인 진입점에 실패 처리 추가,
      `.env.example`의 `VITE_GOOGLE_CLIENT_ID` 제거
- [x] `docs/requests/FE/036-google-oauth-signin-contract.md` 갱신 후 반영 완료로 삭제
- [x] `./gradlew build`, FE `npm run type-check`/`eslint` 통과 확인
