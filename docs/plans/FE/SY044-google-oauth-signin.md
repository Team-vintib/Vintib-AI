# SY044 SSAFY SSO → 구글 로그인 교체

## 배경/목표

BE가 SSAFY SSO를 완전히 제거하고 구글 로그인으로 대체했다 — `AuthController.java`를 확인한 결과 SSAFY 관련 코드가 0건이고(`import`부터 없음), `POST /auth/google`/`POST /auth/google/link`만 존재한다. 즉 **FE의 현재 SSAFY SSO 플로우는 이미 전부 깨져 있다**(`/auth/sso/ssafy`, `/auth/ssafy/callback`, `/auth/ssafy/link-account` 전부 404). 계약은 `docs/requests/FE/036-google-oauth-signin-contract.md`(BE→FE)가 이미 확정해뒀다.

목표: SSAFY SSO 관련 FE 코드를 전부 걷어내고 구글 로그인/회원가입으로 교체한다.

## 핵심 차이 — SSAFY와 트리거 방식 자체가 다르다

- SSAFY: FE가 BE URL(`getSsafySsoStartUrl()` → `/api/auth/sso/ssafy`)로 리다이렉트하면 **BE가 실제 SSAFY 로그인 화면으로의 이동까지 대신 처리**했다.
- 구글: 036 문서에 따르면 **FE가 직접** 구글 동의 화면(`https://accounts.google.com/o/oauth2/v2/auth`)으로 리다이렉트해야 한다 — `client_id`/`redirect_uri`/`scope=openid email profile`/`response_type=code`를 쿼리로 실어서. `client_id`는 공개값이라 FE가 직접 들고 있어도 된다(`VITE_GOOGLE_CLIENT_ID` 환경변수).
- 콜백 이후 응답 모양도 다르다: SSAFY는 서버가 `nextStep`(`HOME`/`ONBOARD_PROFILE`/`LINK_ACCOUNT`)을 내려줘 FE가 그대로 분기했지만, 구글은 `status`(`LOGIN`/`LINK_REQUIRED`)와 `onboardingCompleted`(boolean)만 준다 — **온보딩으로 보낼지 홈으로 보낼지는 FE가 `onboardingCompleted` 값으로 직접 판단**해야 한다.

## 작업 내용

1. **라우트 교체**: `ROUTE_NAMES`/`ROUTE_PATHS`의 `AUTH_SSAFY`/`AUTH_SSAFY_LOGIN`/`AUTH_SSAFY_SIGNUP`/`AUTH_SSAFY_CALLBACK`(`/auth/ssafy/*`)를 `AUTH_GOOGLE_CALLBACK`(`/auth/google/callback`) 하나로 단순화한다 — 구글은 로그인/회원가입이 같은 API로 합쳐지므로(036 "신규 가입 시 처리") SSAFY처럼 login/signup 페이지를 따로 둘 필요가 없다. `router/index.ts`도 갱신.
2. **`auth.types.ts`**: `SsafySsoCallbackRequest`/`SsafySsoCallbackResponse` 제거. 신설:
   - `GoogleAuthRequest { code: string; redirectUri: string }`
   - `GoogleAuthResponse { status: 'LOGIN' | 'LINK_REQUIRED'; accessToken: string | null; refreshToken: string | null; onboardingCompleted: boolean | null; linkToken: string | null; email: string | null }`
   - `GoogleLinkRequest { linkToken: string; confirm: boolean }`(기존 `LinkAccountRequest`는 필드명이 `agree`라 재사용 불가, `GoogleAuthResponse`와 같은 응답 모양이라 응답 타입은 `GoogleAuthResponse` 재사용)
3. **`authApi.ts`**: `completeSsafySsoCallback`/`linkSsafyAccount`/`getSsafySsoStartUrl` 제거. 신설:
   - `signInWithGoogle({ code, redirectUri })` → `POST /auth/google`
   - `confirmGoogleLink({ linkToken, confirm })` → `POST /auth/google/link`
   - `getGoogleOAuthUrl()` — `client_id`/`redirect_uri`/`scope`/`response_type`을 조립해 구글 동의 화면 URL 문자열을 반환(호출부만 있고 실제 이동은 `window.location.assign`으로 호출부가 처리, 기존 `getSsafySsoStartUrl` 패턴과 동일).
4. **구글 로고**: Google 공식 브랜딩 가이드(`developers.google.com/identity/branding-guidelines`)가 제공하는 다운로드 자산(`signin-assets.zip`)에서 받았다. 자산의 SVG는 `foreignObject`+conic-gradient 조합(Figma 내보내기 특유의 구조)이라 브라우저 렌더링 신뢰도가 불확실해, 이미 확정 렌더링된 PNG(다크 테마, 아이콘 전용, `Show text=No, Shape=Square, @2x`)를 `FE/src/assets/images/google-logo.png`로 받아 정적 이미지 자산으로 쓴다(인라인 SVG 대신). 버튼 텍스트는 한글(예: "Google로 로그인")이 필요해 자산의 텍스트-포함 버전 대신 아이콘 전용 버전 위에 직접 라벨을 붙인다.
5. **`GoogleSsoStartCard.vue`**(구 `SsafySsoStartCard.vue` 대체): 로그인/회원가입 공용 진입 카드. 버튼 클릭 시 `getGoogleOAuthUrl()`로 리다이렉트.
6. **`GoogleSsoCallbackPage.vue`**(구 `SsafySsoCallbackPage.vue` 대체): `?code=`/`?error=` 처리는 동일한 패턴 유지. `signInWithGoogle` 호출 후:
   - `status === 'LOGIN'` → `authStore.setSession()` → `onboardingCompleted === false`면 온보딩으로, 아니면 홈으로.
   - `status === 'LINK_REQUIRED'` → `writeLinkAccountSession({ email, linkToken })`(기존 유틸 재사용) 후 `AuthLinkAccountPage`로 이동.
7. **`AuthLinkAccountPage.vue`**: `linkSsafyAccount` 호출부만 `confirmGoogleLink`로 교체(`agree` → `confirm` 필드명 대응). 나머지 UI/흐름은 provider-agnostic이라 그대로 재사용.
8. **`LoginForm.vue`/`SignupEntryPage.vue`**: "싸피어스로 로그인"/SSAFY 링크를 "Google로 로그인/시작하기"(구글 로고 아이콘 포함) 버튼으로 교체, 이동 대상을 구글 플로우로.
9. **삭제**: `SsafyLoginPage.vue`, `SsafySignupPage.vue`, `SsafySsoPage.vue`, `SsafySsoCallbackPage.vue`, `SsafySsoStartCard.vue` — BE가 없어져 더 이상 도달할 수 없는 죽은 화면.

## 구현 목록

- [x] `routes.ts`: SSAFY 라우트 4종 제거, `AUTH_GOOGLE_CALLBACK` 하나로 교체
- [x] `router/routes.ts`: 라우트 등록 교체(SSAFY 3개 → 구글 콜백 1개, 시작 페이지 자체를 없앰)
- [x] `auth.types.ts`: `SsafySso*`/`LinkAccountRequest`/`LinkAccountResponse` 제거, `GoogleAuthRequest`/`GoogleAuthResponse`/`GoogleLinkRequest` 신설
- [x] `authApi.ts`: SSAFY 함수 3종 제거, `signInWithGoogle`/`confirmGoogleLink`/`getGoogleOAuthUrl` 신설
- [x] `.env.example`에 `VITE_GOOGLE_CLIENT_ID` 추가(값은 비워둠 — 확인 필요 항목)
- [x] 구글 공식 브랜딩 자산에서 `google-logo.png`(다크 테마 아이콘) 추출 → `FE/src/assets/images/`
- [x] **설계 변경**: 별도 "시작 카드" 페이지(`GoogleSsoStartCard.vue`) 없이, 로그인/가입 버튼 클릭 시 `startGoogleOAuth()`가 바로 구글 동의 화면으로 리다이렉트하도록 단순화(`googleOAuth.ts` 유틸 신설 — source sessionStorage 기록, redirectUri 일원화, 재시도 트리거)
- [x] `GoogleSsoCallbackPage.vue` 신설(`onboardingCompleted` 기반 온보딩/홈 분기), `SsafySsoCallbackPage.vue`/`SsafySsoPage.vue`/`SsafySsoStartCard.vue` 삭제
- [x] `AuthLinkAccountPage.vue`: `confirmGoogleLink`로 교체, 에러코드 `U016` 대응, `onboardingCompleted` 기반 분기
- [x] `SsafyLoginPage.vue`/`SsafySignupPage.vue` 삭제
- [x] `LoginForm.vue`/`SignupForm.vue`/`SignupEntryPage.vue`: SSAFY 버튼/링크 → Google 로고+버튼 교체
- [x] `authStore.ts`: `AuthSession` 타입을 구조적 타입으로 단순화(구글 응답엔 `user` 객체가 없어 `Partial<AuthUser>` 조립 방식으로 전달)
- [x] `npm run type-check`, `npm run lint` 통과
- [x] 잔여 SSAFY 참조 전수 검색 — 0건 확인

## 확인이 필요한 미결정 사항

- `VITE_GOOGLE_CLIENT_ID` 실제 값 — 036 문서에 "클라이언트 ID/시크릿은 이미 발급돼 있다"고만 돼 있고 구체 값은 없다. 로컬 `.env`에 값을 넣어야 실제 리다이렉트가 동작한다(사용자 확인 필요).
- 구글 콘솔에 등록된 콜백 리다이렉트 URI(`/auth/google/callback`)가 정확히 이 경로와 일치하는지 확인 필요 — 다르면 구글이 토큰 교환을 거부한다(036 §3 경고).
