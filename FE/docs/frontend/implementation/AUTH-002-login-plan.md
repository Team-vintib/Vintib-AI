# AUTH-002 이메일 로그인 구현 계획

작성일: 2026-07-26

## 범위

- 수정 가능 범위는 `FE/` 내부로 제한한다.
- `BE/`, `AI/`, `infra/` 및 루트 인프라 파일은 수정하지 않는다.
- 기존 `domains/auth` 구조와 `shared/api/http.ts`, `shared/constants/routes.ts` 패턴을 우선 사용한다.

## 기준 문서

- `docs/frontend/screens/AUTH-002/requirements.md`
- `docs/frontend/api/api-index.md`
- `docs/frontend/auth/permissions.md`
- `docs/frontend/flows/route-map.md`

## API 계약

Swagger 확정 전까지 아래 후보 계약을 사용한다.

```http
POST /auth/login
Content-Type: application/json
```

요청:

```json
{
  "email": "user@example.com",
  "password": "password123",
  "rememberMe": true
}
```

응답 후보:

```json
{
  "accessToken": "access-token",
  "refreshToken": "refresh-token",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "홍길동",
    "onboardingCompleted": false
  },
  "nextStep": "ONBOARD_PROFILE"
}
```

- 공통 응답 envelope는 기존 `ApiResponse<T>`를 사용한다.
- `nextStep`은 기존 SSO callback의 `AuthNextStep`과 맞춰 `HOME`, `ONBOARD_PROFILE`, `LINK_ACCOUNT` 후보를 허용한다.
- `refreshToken`, `user`, `nextStep`은 서버 구현 차이에 대비해 optional로 처리한다.

## 커밋 단위 구현 단계

### 1. AUTH-002 계획 문서 작성

목표:

- 코드 변경 전에 로그인 구현 범위, API 후보, 커밋 단위 작업 순서를 문서화한다.

구현 방법:

- `FE/docs/frontend/implementation/AUTH-002-login-plan.md`를 추가한다.
- 구현 단계별 목표와 구체적 변경 파일 후보를 기록한다.
- BE 계약 미확정 사항은 확정값처럼 쓰지 않고 optional 처리 방침을 남긴다.

### 2. 로그인 API 타입 및 인증 Store 추가

목표:

- 이메일 로그인 API 호출과 인증 상태 저장을 위한 기반을 만든다.
- 이메일 로그인과 SSO 로그인이 같은 인증 상태 저장 정책을 사용하게 준비한다.

구현 방법:

- `src/domains/auth/types/auth.types.ts`
  - `LoginRequest`를 추가한다.
  - `LoginResponse`를 추가한다.
  - `AuthUser` 타입을 추가한다.
  - `accessToken`, `refreshToken`, `user`, `nextStep`은 응답 후보 기준으로 optional 허용 범위를 정한다.
- `src/domains/auth/api/authApi.ts`
  - `login(request: LoginRequest)` 함수를 추가한다.
  - 기존 `http.post<ApiResponse<T>>()` 패턴을 유지한다.
- `src/domains/auth/stores/authStore.ts`
  - Pinia store를 추가한다.
  - 상태: `accessToken`, `refreshToken`, `user`
  - getter: `isAuthenticated`, `isOnboardingCompleted`
  - action: `setSession`, `clearSession`, `hydrateSession`
  - `rememberMe`가 true면 `localStorage`, false면 `sessionStorage`에 저장한다.
- `src/shared/api/http.ts`
  - 요청 interceptor가 store 정책과 같은 token key를 읽도록 정리한다.
  - 기존 SSO에서 쓰던 `vintib_access_token` key와 호환되게 처리한다.

### 3. 이메일 로그인 화면 및 입력값 검증 구현

목표:

- `/auth/login` 화면에서 이메일과 비밀번호로 로그인할 수 있는 UI를 구현한다.
- 클라이언트 입력 오류를 API 요청 전에 막는다.

구현 방법:

- `src/domains/auth/pages/LoginPage.vue`
  - 기존 `SignupPage.vue`와 같은 `AuthLayout`, logo, card 스타일을 사용한다.
  - 화면 제목은 `이메일 로그인`으로 둔다.
- `src/domains/auth/components/LoginForm.vue`
  - 이메일 입력 필드, 비밀번호 입력 필드, 비밀번호 보기/숨기기 버튼을 구현한다.
  - 로그인 상태 유지 checkbox를 구현한다.
  - 로그인 버튼은 submit 중 disabled 처리한다.
  - SSAFY 로그인 버튼은 `{ name: ROUTE_NAMES.AUTH_SSAFY, query: { from: 'login' } }`로 이동한다.
  - 회원가입 링크는 `ROUTE_NAMES.AUTH_SIGNUP`으로 이동한다.
  - 비밀번호 찾기는 세부 화면 미확정이므로 비활성 버튼 또는 안내 메시지로 처리한다.
- 검증:
  - 이메일은 `isRequired`, `isEmail`을 사용한다.
  - 비밀번호는 비어 있지 않은지만 검증한다.
  - blur 후 field error를 표시하고, submit 시 전체 field를 touched 처리한다.

### 4. 로그인 결과 처리 및 화면 이동 구현

목표:

- 로그인 성공 시 토큰과 사용자 정보를 저장하고 적절한 화면으로 이동한다.
- 로그인 실패 시 필드 오류 또는 공통 오류를 구분해서 보여준다.

구현 방법:

- `LoginForm.vue`
  - submit 시 `login()` API를 호출한다.
  - 성공 응답에 `accessToken`이 없으면 공통 오류로 처리한다.
  - 성공 시 `authStore.setSession(response.data, form.rememberMe)`를 호출한다.
  - submit 중 중복 클릭을 막는다.
- 오류 처리:
  - `normalizeApiError()`를 사용한다.
  - 인증 실패 계열은 `이메일 또는 비밀번호를 확인해 주세요.`로 표시한다.
  - `C001`은 입력값 확인 메시지로 표시한다.
  - 네트워크/타임아웃은 공통 API 오류 메시지를 사용한다.
- 이동 정책:
  - 내부 `redirect` query가 있으면 우선 이동한다.
  - `nextStep === 'HOME'`이면 `ROUTE_PATHS.HOME`으로 이동한다.
  - `nextStep === 'ONBOARD_PROFILE'`이면 `ROUTE_NAMES.ONBOARD_PROFILE`로 이동한다.
  - `user.onboardingCompleted === false`이면 `ROUTE_NAMES.ONBOARD_PROFILE`로 이동한다.
  - 그 외에는 `ROUTE_PATHS.HOME`으로 이동한다.

### 5. 라우트 등록 및 인증 상태 연동

목표:

- 로그인 페이지를 라우터에 연결하고, 추후 보호 화면에서 사용할 인증 가드를 도입한다.

구현 방법:

- `src/router/routes.ts`
  - `ROUTE_PATHS.AUTH_LOGIN` route를 추가한다.
  - 인증 화면에는 `meta: { guestOnly: true }`를 붙인다.
  - 온보딩 화면에는 `meta: { requiresAuth: true }`를 붙인다.
- `src/router/index.ts`
  - `beforeEach` guard를 추가한다.
  - guard 시작 시 `authStore.hydrateSession()`으로 저장된 세션을 복원한다.
  - `requiresAuth`인데 미로그인이면 `/auth/login?redirect=<현재경로>`로 보낸다.
  - `guestOnly`인데 로그인 상태면 홈 또는 온보딩으로 보낸다.
- `src/shared/constants/routes.ts`
  - 기존 `AUTH_LOGIN` 상수가 있으므로 누락된 상수만 점검한다.

### 6. SSO 인증 저장 방식 정합성 정리

목표:

- 이메일 로그인과 SSO callback이 같은 인증 상태 저장 방식을 사용하게 만든다.

구현 방법:

- `src/domains/auth/pages/SsafySsoCallbackPage.vue`
  - 직접 `localStorage.setItem('vintib_access_token', ...)` 하는 부분을 auth store 호출로 교체한다.
  - SSO 응답에 `refreshToken` 또는 `user`가 없을 수 있으므로 optional로 저장한다.
- `src/domains/auth/pages/SsafySsoPage.vue`
  - 기존 `from=login` source 처리를 유지한다.
  - 로그인 화면에서 SSO로 진입하면 callback fallback이 로그인 화면을 바라보도록 한다.
- 로그인 후 이동 helper가 중복되면 `domains/auth` 내부 함수로 분리한다.

### 7. 검증 및 구현 상태 문서 갱신

목표:

- AUTH-002 구현 완료 기준을 확인하고 문서 상태를 갱신한다.

구현 방법:

- `docs/frontend/implementation/status.md`
  - 인증 화면 상태에 AUTH-002 구현 내용을 반영한다.
- `docs/frontend/screens/screen-inventory.md`
  - AUTH-002 상태를 미구현에서 구현 또는 부분 구현으로 갱신한다.
- 검증 명령:
  - `npm run type-check`
  - `npm run build`
- 수동 확인 항목:
  - 빈 값 제출 시 필드 오류 표시
  - 잘못된 이메일 형식 오류 표시
  - 로그인 중 버튼 disabled 처리
  - API 성공 후 홈 또는 온보딩 이동
  - API 실패 시 오류 메시지 표시
  - SSAFY 로그인 이동
  - 회원가입 이동

## 미확정 사항

- refresh token의 실제 저장 위치와 만료 처리 정책
- 토큰 갱신 API 사용 시점
- 비밀번호 찾기 화면 또는 외부 정책
- 로그인 성공 후 서버가 `nextStep`을 내려주는지 여부
- 로그인 응답의 `user` 필드 상세 구조

## 구현 원칙

- Swagger 또는 BE 계약이 확정되면 `docs/frontend/api/api-index.md`와 타입을 먼저 갱신한다.
- 미확정 응답 필드는 optional로 처리하고, 화면 이동은 보수적인 fallback을 둔다.
- 새 라이브러리는 추가하지 않는다.
- FE 외 폴더는 수정하지 않는다.
