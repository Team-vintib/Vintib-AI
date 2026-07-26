# AUTH-004 계정 연결 API 계약 기반 정리

## 배경/목표

SSO 회원가입 중 동일 이메일 계정이 발견됐을 때 FE가 계정 연결 대기 상태를 타입 안정적으로 다룰 수 있도록 API 타입, API 함수, sessionStorage payload 구조를 먼저 정리한다. 이 단계에서는 연결 안내 화면의 동의 UI나 실제 연결 실행 흐름은 구현하지 않는다.

## 작업 범위

- `FE/` 내부 인증 도메인만 수정한다.
- `BE/`, `AI/`, `infra/`는 수정하지 않는다.
- 실제 계정 연결 endpoint는 우선 FE 계약 후보로 추가하고, BE 계약 확정 시 path 또는 필드명을 조정한다.
- 기존 SSO callback과 계정 연결 안내 화면의 동작 변경은 최소화한다.

## 단계별 구현 계획

### 1단계: 기존 인증 타입과 흐름 확인

- `AuthNextStep`에 `LINK_ACCOUNT`가 포함되어 있는지 확인
- `SsafySsoCallbackResponse`의 현재 응답 필드 확인
- `SsafySsoCallbackPage.vue`와 `AuthLinkAccountPage.vue`의 sessionStorage 사용 방식 확인

### 2단계: SSO callback 응답 타입 확장

- `SsafySsoCallbackResponse`에 계정 연결용 임시 토큰 필드 추가
- 필드명은 우선 `linkToken?: string`로 정의
- 기존 로그인/온보딩 분기 응답 타입과 충돌하지 않도록 optional로 추가

### 3단계: 계정 연결 요청/응답 타입 추가

- `LinkAccountRequest` 타입 추가
- `LinkAccountResponse` 타입 추가
- 응답은 기존 인증 세션 처리와 맞게 `accessToken`, `refreshToken`, `user`, `nextStep`을 포함할 수 있도록 정의

### 4단계: 계정 연결 API 함수 추가

- `authApi.ts`에 `linkSsafyAccount` 함수 추가
- 요청/응답 타입을 명시한다
- endpoint 후보는 `/auth/ssafy/link-account`로 둔다

### 5단계: 계정 연결 sessionStorage 구조 공통화

- 연결 대기 payload 타입을 정의한다
- payload는 `{ email?: string, linkToken: string }` 구조로 둔다
- 중복된 storage key 상수를 공통 위치로 분리한다
- JSON parse 실패 시 안전하게 `null`을 반환하는 read helper를 준비한다
- write/clear helper를 함께 준비해 후속 작업에서 callback/page 양쪽이 같은 함수를 사용하게 한다

### 6단계: 기존 파일의 storage 참조 최소 정리

- `SsafySsoCallbackPage.vue`의 link account storage key 참조를 공통 상수 또는 helper 기반으로 바꾼다
- `AuthLinkAccountPage.vue`의 link account storage key 참조를 공통 상수 또는 helper 기반으로 바꾼다
- 실제 `linkToken` 저장 검증과 동의 UI 처리는 다음 단계 작업으로 남긴다

## 구현 체크리스트

- [x] 기존 인증 타입과 SSO 계정 연결 흐름 확인
- [x] `SsafySsoCallbackResponse`에 `linkToken` 필드 추가
- [x] `LinkAccountRequest` 타입 추가
- [x] `LinkAccountResponse` 타입 추가
- [x] `linkSsafyAccount` API 함수 추가
- [x] link account sessionStorage payload 타입 정의
- [x] link account sessionStorage read/write/clear helper 추가
- [x] 기존 callback/page의 storage key 중복 제거
- [x] `npm run type-check` 실행

## 최종 검증

- `cd FE && npm run type-check`
- 필요 시 `cd FE && npm run build`

## 확인이 필요한 미결정 사항

- BE 최종 endpoint가 `/auth/ssafy/link-account`가 맞는지 확인 필요
- SSO callback의 연결용 임시 토큰 필드명이 `linkToken`이 맞는지 확인 필요
- 계정 연결 요청에 `agree: boolean`을 보낼지, 동의 여부는 FE에서만 검증할지 확인 필요
