# 001 Auth API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: FE 인증 흐름에서 로그인 세션, 온보딩 진입 여부, SSAFY SSO 계정 연결 분기를 안정적으로 판단할 수 있도록 Auth API 계약을 정리한다.
- 우선순위: P0
- 시연 필수 여부: 이메일 인증/회원가입/로그인/세션 복구는 필수. SSAFY SSO는 시연 범위에 포함하지 않으면 보류 가능.

## 2. 현재 연동 상태

- 연동 완료 API
  - `POST /api/auth/email/check-duplicate`
  - `POST /api/auth/email/send-code`
  - `POST /api/auth/email/verify-code`
  - `POST /api/auth/signup`
  - `POST /api/auth/signin`
  - `POST /api/auth/reissue`
  - `POST /api/auth/logout`
- FE 구현 완료 범위
  - 이메일 중복 확인, 인증 코드 발송, 인증 코드 확인, 이메일 회원가입 화면 구현 완료
  - 로그인 화면 구현 및 `POST /api/auth/signin` 호출 연결 완료
  - 저장된 refreshToken 기반 `POST /api/auth/reissue` 세션 복구 구현 완료
  - 로그아웃 시 `POST /api/auth/logout` 호출 후 로컬 세션 정리 구현 완료
  - route guard에서 로그인 필요 화면과 guestOnly 화면 분기 구현 완료
  - SSAFY SSO 시작/콜백/계정 연결 화면 구현 완료
- 현재 임시 처리 또는 Mock 사용 여부
  - 로그인/재발급 응답에 `user`가 없으면 FE가 JWT payload의 `sub`, `email`만 파싱해 사용자 상태를 임시 복원한다.
  - `onboardingCompleted`가 없으면 온보딩 필요 여부를 안정적으로 판단할 수 없어 일부 guard가 완전하게 동작하지 않는다.
  - `GET /api/me`는 FE 사용처가 있으나 BE 구현이 확인되지 않아 아직 실제 호출로 연결하지 않았다.
  - SSAFY SSO endpoint는 FE 화면과 타입만 선행 구현되어 있고 BE 구현이 확인되지 않았다.

## 3. 추가 구현 요청

### 3.1 현재 사용자 조회

- Method / Endpoint: `GET /api/me`
- 요청 목적: 저장된 accessToken 또는 재발급된 accessToken으로 현재 로그인 사용자의 최신 상태를 조회한다.
- FE 사용처
  - 앱 시작 시 저장된 token 기반 세션 검증
  - route guard에서 온보딩 필요 여부 판단
  - 헤더/마이페이지에서 현재 사용자 표시
  - 사업자 인증, 상품 등록, 라이브 생성 가능 여부 판단
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
- 응답 데이터
  - `id`: number, 필수
  - `email`: string, 필수
  - `name`: string, 필수
  - `nickname`: string | null, 온보딩 전 null 가능
  - `phoneNumber`: string | null
  - `profileImageUrl`: string | null
  - `memberType`: `GENERAL` | `BUSINESS`
  - `onboardingCompleted`: boolean
  - `businessVerificationStatus`: `NONE` | `PENDING` | `APPROVED` | `REJECTED` | null
- 응답 예시

```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@example.com",
    "name": "홍길동",
    "nickname": "vintagelover",
    "phoneNumber": "010-1234-5678",
    "profileImageUrl": null,
    "memberType": "GENERAL",
    "onboardingCompleted": false,
    "businessVerificationStatus": "NONE"
  },
  "error": null
}
```

### 3.2 SSAFY SSO 시작

- Method / Endpoint: `GET /api/auth/sso/ssafy`
- 요청 목적: SSAFY SSO 인증 페이지로 이동할 시작 URL을 제공하거나 redirect를 수행한다.
- FE 사용처: `SsafySsoStartCard`, SSAFY 로그인/회원가입 진입 화면
- 요청 데이터: 없음
- 응답 데이터: BE 정책에 따라 redirect 또는 `{ "redirectUrl": string }`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "redirectUrl": "https://ssafy.example.com/oauth/authorize?client_id=..."
  },
  "error": null
}
```

### 3.3 SSAFY SSO 콜백 처리

- Method / Endpoint: `POST /api/auth/ssafy/callback`
- 요청 목적: SSO authorization code를 BE에서 검증하고, 기존 계정 연결 여부에 따라 로그인 또는 계정 연결 플로우로 분기한다.
- FE 사용처: `SsafySsoCallbackPage`
- 요청 데이터
  - `authorizationCode`: string
  - `redirectUri`: string
- 응답 데이터
  - `linked`: boolean
  - `accessToken`: string | null
  - `refreshToken`: string | null
  - `user`: object | null
  - `email`: string | null
  - `linkToken`: string | null
  - `nextStep`: `HOME` | `ONBOARD_PROFILE` | `LINK_ACCOUNT`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "linked": false,
    "email": "user@ssafy.com",
    "linkToken": "link-token",
    "nextStep": "LINK_ACCOUNT"
  },
  "error": null
}
```

### 3.4 SSAFY 기존 계정 연결

- Method / Endpoint: `POST /api/auth/ssafy/link-account`
- 요청 목적: SSO에서 받은 linkToken을 기존 이메일 계정과 연결하고 로그인 세션을 발급한다.
- FE 사용처: `AuthLinkAccountPage`
- 요청 데이터
  - `linkToken`: string
  - `agree`: boolean
- 응답 데이터
  - `accessToken`: string
  - `refreshToken`: string
  - `user`: object
  - `nextStep`: `HOME` | `ONBOARD_PROFILE`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "accessToken": "eyJ...",
    "refreshToken": "eyJ...",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "name": "홍길동",
      "onboardingCompleted": false
    },
    "nextStep": "ONBOARD_PROFILE"
  },
  "error": null
}
```

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - `POST /api/auth/signin`과 `POST /api/auth/reissue`의 현재 BE 응답은 `accessToken`, `refreshToken`만 포함한다.
  - FE route guard와 온보딩 자동 이동을 위해 `user`, `nextStep`을 함께 내려주기 바란다.
  - `POST /api/auth/signup`은 현재 `id`, `email`, `name`, `onboardingCompleted`를 내려준다. 회원가입 직후 자동 로그인까지 BE 정책으로 포함한다면 `accessToken`, `refreshToken`, `user`, `nextStep` 구조로 맞춰주기 바란다. 자동 로그인하지 않는 정책이면 현재처럼 가입 성공 후 로그인 화면으로 이동해도 된다.
- 추가할 필드
  - `user.id`: number
  - `user.email`: string
  - `user.name`: string
  - `user.nickname`: string | null
  - `user.memberType`: `GENERAL` | `BUSINESS`
  - `user.onboardingCompleted`: boolean
  - `nextStep`: `HOME` | `ONBOARD_PROFILE` | `LINK_ACCOUNT`
- 변경 영향 범위
  - `authStore.setSession`
  - `router.beforeEach` guestOnly/auth guard
  - 로그인 후 이동 처리
  - 온보딩 완료 전 사용자 redirect
  - 사업자 인증/상품 등록/라이브 생성 접근 제어

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - SSAFY SSO가 시연 범위가 아니면 `GET /api/auth/sso/ssafy`, `POST /api/auth/ssafy/callback`, `POST /api/auth/ssafy/link-account`는 보류 가능
  - 회원가입 직후 자동 로그인은 정책 미확정이면 보류 가능
- 추후 구현 예정 기능
  - 현재 사용자 프로필 수정
  - 소셜 계정 연결 해제
  - refreshToken rotation 상세 정책 고도화

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - 회원가입 성공 후 자동 로그인할지, 로그인 페이지로 이동할지 결정 필요
  - `GET /api/me`를 Auth 범위로 둘지 Member 범위로 둘지 결정 필요
  - `memberType` 기본값과 온보딩 완료 시점 결정 필요
  - 사업자 인증 상태를 `GET /api/me`에 포함할지, 별도 사업자 API에서만 조회할지 결정 필요
  - SSAFY SSO 시작 API가 HTTP redirect인지 JSON `redirectUrl` 응답인지 결정 필요
- 아직 확정되지 않은 응답 구조나 정책
  - SSO 미연결 사용자 응답의 `linkToken` 만료 시간
  - `nextStep` enum 유지 여부
  - 로그인/재발급 응답의 `user` 필수 여부
  - accessToken 만료 시 FE가 자동으로 `reissue`를 재시도해도 되는 정책

## 7. 추가 요청 없음

- 이미 정상 연동된 API
  - `POST /api/auth/email/check-duplicate`
  - `POST /api/auth/email/send-code`
  - `POST /api/auth/email/verify-code`
  - `POST /api/auth/logout`
- 기존 규격을 유지하면 되는 기능
  - 이메일 인증 코드 확인 응답의 `verificationToken`
  - 로그인 요청의 `email`, `password`
  - 재발급 요청의 `refreshToken`
  - 공통 응답 envelope `{ success, data, error }`
