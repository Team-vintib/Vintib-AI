# 라우팅 및 화면 이동 초안

출처: `docs/notion/화면 기반 개발 요구 문서.md`

## 인증 흐름

```mermaid
flowchart TD
  SignupEntry["AUTH-001-0 /auth/signup"]
  SignupEmail["AUTH-001 /auth/signup/email"]
  Login["AUTH-002 /auth/login"]
  SsafyLogin["AUTH-003 /auth/ssafy/login"]
  SsafySignup["AUTH-003-1 /auth/ssafy/signup"]
  SsafyCallback["AUTH-004-2 /auth/ssafy/callback"]
  LinkAccount["AUTH-004 /auth/link-account"]
  OnboardProfile["ONBOARD-001 /onboarding/basic-info"]
  Home["HOME /"]

  Login --> SignupEntry
  Login --> Home
  Login --> SsafyLogin
  SignupEntry --> SignupEmail
  SignupEntry --> SsafySignup
  SignupEntry --> Login
  SignupEmail --> OnboardProfile
  SignupEmail --> Login
  SsafyLogin --> SsafyCallback
  SsafySignup --> SsafyCallback
  SsafyCallback --> LinkAccount
  SsafyCallback --> OnboardProfile
  SsafyCallback --> Home
  LinkAccount --> Login
  LinkAccount --> OnboardProfile
  LinkAccount --> Home
```

## 온보딩 흐름

```mermaid
flowchart TD
  Profile["ONBOARD-001 /onboarding/basic-info"]
  Interests["ONBOARD-002 /onboarding/interests"]
  TryOn["ONBOARD-003 /onboarding/try-on"]
  MemberType["ONBOARD-004 /onboarding/member-type"]
  Biz["BIZ-001 /business/verification"]
  Home["HOME /"]

  Profile --> Interests
  Interests --> TryOn
  TryOn --> MemberType
  MemberType --> Home
  MemberType --> Biz
  Biz --> Home
```

## 라우트 메타 초안

| 라우트                    | 화면        | requiresAuth | guestOnly | 비고                                           |
| ------------------------- | ----------- | ------------ | --------- | ---------------------------------------------- |
| `/auth/login`             | AUTH-002    | false        | true      | 이메일 로그인, SSAFY 로그인 진입               |
| `/auth/signup`            | AUTH-001-0  | false        | true      | 회원가입 방식 선택                             |
| `/auth/signup/email`      | AUTH-001    | false        | true      | 회원가입 성공 후 `/onboarding/basic-info` 이동 |
| `/auth/ssafy`             | Legacy      | false        | true      | query 기준 SSO 로그인 또는 가입 route로 redirect |
| `/auth/ssafy/login`       | AUTH-003    | false        | true      | SSAFY 로그인 시작 화면                         |
| `/auth/ssafy/signup`      | AUTH-003-1  | false        | true      | SSAFY 가입 시작 화면                           |
| `/auth/ssafy/callback`    | AUTH-004-2  | false        | false     | SSO callback 처리                              |
| `/auth/link-account`      | AUTH-004    | false        | true      | 계정 연결 후보가 있을 때만 접근                |
| `/onboarding/basic-info`  | ONBOARD-001 | true         | false     | 가입 후 필수/보완 흐름                         |
| `/onboarding/interests`   | ONBOARD-002 | true         | false     | 건너뛰기 가능                                  |
| `/onboarding/try-on`      | ONBOARD-003 | true         | false     | 건너뛰기 가능                                  |
| `/onboarding/member-type` | ONBOARD-004 | true         | false     | 일반/사업자 선택                               |
| `/business/verification`  | BIZ-001     | true         | false     | 사업자 회원 정보 제출                          |
