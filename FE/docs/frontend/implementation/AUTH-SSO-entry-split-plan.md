# AUTH SSO 로그인/회원가입 진입 분리 계획

작성일: 2026-07-26

## 범위

- 수정 가능 범위는 `FE/` 내부로 제한한다.
- `BE/`, `AI/`, `infra/` 및 루트 인프라 파일은 수정하지 않는다.
- SSAFY SSO API 시작 URL과 callback API 계약은 기존 후보를 유지한다.

## 배경

현재 `SsafySsoPage.vue`는 `from=login | signup` query를 받지만 화면 문구가 가입 중심으로 고정되어 있다.
그 결과 로그인 화면에서 `싸피어스로 로그인`을 눌러도 사용자는 가입 화면처럼 인식한다.

제품 흐름은 아래처럼 로그인 방식과 회원가입 방식을 각각 2개로 분리해야 한다.

- 로그인
  - 이메일 로그인
  - 싸피어스로 로그인
- 회원가입
  - 이메일 가입
  - 싸피어스 가입

## 결정

SSAFY SSO 진입 화면은 query 분기 재사용 대신 별도 페이지로 분리한다.

- `SsafyLoginPage.vue`: 싸피어스로 로그인
- `SsafySignupPage.vue`: 싸피어스로 가입하기

공통 SSO 시작 로직은 중복을 피하기 위해 도메인 컴포넌트로 분리한다.

- `SsafySsoStartCard.vue`

## 추천 라우트

```text
/auth/login
  이메일 로그인 화면

/auth/signup
  회원가입 방식 선택 화면

/auth/signup/email
  이메일 회원가입 화면

/auth/ssafy/login
  싸피어스로 로그인 화면

/auth/ssafy/signup
  싸피어스 가입 화면

/auth/ssafy/callback
  SSO callback 처리 화면
```

## 기존 라우트 처리

기존 `/auth/ssafy`는 직접 사용하지 않는 방향으로 전환한다.

- 호환 정책:
  - `/auth/ssafy?from=login`은 `/auth/ssafy/login`으로 redirect한다.
  - `/auth/ssafy?from=signup` 또는 query 없음은 `/auth/ssafy/signup`으로 redirect한다.
- 문서와 화면 링크는 새 라우트를 사용한다.
- 기존 외부 링크와 과거 FE 내부 링크 대응을 위해 legacy route와 `SsafySsoPage.vue` redirect wrapper는 유지한다.
- legacy route 제거는 외부 링크 사용 여부를 확인한 뒤 별도 작업으로 판단한다.

## 커밋 단위 구현 단계

### 1. SSO 진입 분리 계획 문서 작성

목표:

- SSAFY 로그인/가입을 별도 페이지로 분리하는 방향을 문서화한다.
- 라우트 구조와 기존 `/auth/ssafy` 호환 정책을 확정한다.

구현 방법:

- `FE/docs/frontend/implementation/AUTH-SSO-entry-split-plan.md`를 추가한다.
- 구현 단계별 목표와 변경 파일 후보를 기록한다.

### 2. 라우트 상수 및 SSO 진입 라우트 분리

목표:

- 로그인용 SSO route와 가입용 SSO route를 코드 상수와 라우터에 분리 등록한다.

구현 방법:

- `src/shared/constants/routes.ts`
  - `AUTH_SIGNUP_EMAIL` 추가: `/auth/signup/email`
  - `AUTH_SSAFY_LOGIN` 추가: `/auth/ssafy/login`
  - `AUTH_SSAFY_SIGNUP` 추가: `/auth/ssafy/signup`
- `src/router/routes.ts`
  - `/auth/signup`은 가입 방식 선택 화면으로 연결할 준비를 한다.
  - `/auth/signup/email`은 기존 `SignupPage.vue`로 연결한다.
  - `/auth/ssafy/login`은 `SsafyLoginPage.vue`로 연결한다.
  - `/auth/ssafy/signup`은 `SsafySignupPage.vue`로 연결한다.
  - 기존 `/auth/ssafy`는 query에 따라 새 route로 redirect한다.

### 3. 회원가입 방식 선택 화면 추가

목표:

- 로그인 화면에서 회원가입을 누르면 이메일 가입/싸피어스 가입 중 하나를 선택하게 한다.

구현 방법:

- `src/domains/auth/pages/SignupEntryPage.vue` 추가
  - `이메일로 가입하기` 버튼은 `AUTH_SIGNUP_EMAIL`로 이동한다.
  - `싸피어스로 가입하기` 버튼은 `AUTH_SSAFY_SIGNUP`으로 이동한다.
  - `로그인으로 돌아가기` 링크는 `AUTH_LOGIN`으로 이동한다.
- 기존 `LoginForm.vue`
  - 회원가입 링크는 기존 `AUTH_SIGNUP`을 유지한다.
  - `AUTH_SIGNUP`의 대상이 선택 화면으로 바뀐다.
- 기존 `SignupForm.vue`
  - 하단 로그인 링크는 `RouterLink`로 정리하고 `AUTH_LOGIN`을 사용한다.

### 4. SSO 시작 공통 컴포넌트 작성

목표:

- SSAFY 로그인/가입 페이지가 같은 SSO 시작 로직과 카드 UI를 공유하게 한다.

구현 방법:

- `src/domains/auth/components/SsafySsoStartCard.vue` 추가
  - props:
    - `source`: `login | signup`
    - `title`
    - `description`
    - `primaryLabel`
    - `returnLabel`
    - `returnTo`
  - SSO 시작 시 `vintib_ssafy_sso_source`에 `source`를 저장한다.
  - `getSsafySsoStartUrl()`로 이동한다.
  - query error/cancelled 메시지를 표시한다.
- 기존 `SsafySsoPage.vue`의 SSO 시작 로직은 이 컴포넌트로 이동한다.

### 5. SSAFY 로그인/가입 전용 페이지 추가

목표:

- SSAFY 로그인 화면과 SSAFY 가입 화면을 별도 파일로 제공한다.

구현 방법:

- `src/domains/auth/pages/SsafyLoginPage.vue`
  - `SsafySsoStartCard`에 `source="login"` 전달
  - title: `싸피어스로 로그인`
  - primaryLabel: `싸피어스로 로그인`
  - returnTo: `AUTH_LOGIN`
- `src/domains/auth/pages/SsafySignupPage.vue`
  - `SsafySsoStartCard`에 `source="signup"` 전달
  - title: `싸피어스로 가입하기`
  - primaryLabel: `싸피어스로 가입하기`
  - returnTo: `AUTH_SIGNUP`
- 기존 `SsafySsoPage.vue`
  - 직접 화면으로 유지하지 않고 legacy redirect page로 축소하거나 제거 후보로 둔다.
  - 삭제는 팀 합의 전까지 하지 않고 redirect 역할로 유지한다.

### 6. SSO 진입 링크와 callback fallback 정리

목표:

- 로그인/가입 화면의 SSO 진입 링크가 각각 전용 페이지로 이동하게 한다.
- callback 실패 시 사용자가 원래 흐름으로 돌아가게 한다.

구현 방법:

- `src/domains/auth/components/LoginForm.vue`
  - 싸피어스 로그인 버튼 이동 대상을 `AUTH_SSAFY_LOGIN`으로 변경한다.
- `src/domains/auth/pages/SignupEntryPage.vue`
  - 싸피어스 가입 버튼 이동 대상을 `AUTH_SSAFY_SIGNUP`으로 둔다.
- `src/domains/auth/pages/SsafySsoCallbackPage.vue`
  - `source === login` fallback은 `AUTH_LOGIN`
  - `source === signup` fallback은 `AUTH_SIGNUP`
  - retry route는 `AUTH_SSAFY_LOGIN` 또는 `AUTH_SSAFY_SIGNUP`으로 분기한다.

### 7. 문서 갱신 및 검증

목표:

- 새 라우트와 화면 구조를 FE 문서에 반영하고 빌드 가능 상태를 확인한다.

구현 방법:

- `docs/frontend/screens/screen-inventory.md`
  - AUTH-002, AUTH-003, AUTH-001 상태와 route 설명 갱신
- `docs/frontend/flows/route-map.md`
  - 회원가입 방식 선택과 SSO 로그인/가입 route 반영
- `docs/frontend/implementation/current-structure.md`
  - 새 페이지/컴포넌트 반영
- `docs/frontend/implementation/status.md`
  - SSO 진입 분리 상태 반영
- 검증 명령:
  - `npm run type-check`
  - `npm run build`

## 미확정 사항

- SSAFY 가입 완료 후 별도 성공 안내 화면을 둘지, callback 처리 화면에서 바로 이동할지
- SSO 시작 API가 로그인/가입 intent를 서버에 별도로 전달해야 하는지 여부

## 구현 원칙

- 기존 SSO callback API 계약은 변경하지 않는다.
- SSO source는 기존 `vintib_ssafy_sso_source` session storage key를 유지한다.
- 새 라이브러리는 추가하지 않는다.
- FE 외 폴더는 수정하지 않는다.
