# AUTH-004 동일 이메일 계정 연결 안내 및 처리

## 배경/목표

이메일 회원가입과 SSO 회원가입에서 동일 이메일 계정이 발견되는 경우를 서로 다른 정책으로 처리한다. 이메일 회원가입은 로그인 화면으로 유도하고, SSO 회원가입은 기존 VinTib 계정과 싸피어스 계정을 연결하는 안내/동의/API 처리 흐름을 구현한다.

## 작업 범위

- `FE/` 내부 인증 도메인만 수정한다.
- `BE/`, `AI/`, `infra/`는 수정하지 않는다.
- 관련 Jira:
  - `S15P11A108-267` `[AUTH-004 | FE] 동일 이메일 계정 연결 안내 및 동의 처리 구현`
  - `S15P11A108-268` `[AUTH-004 | FE] 기존 이메일 계정 연결 API 및 결과 처리`
- 실제 계정 연결 endpoint와 응답 필드는 BE 계약 확정 시 조정한다.

## 단계별 구현 계획

### 1단계: 계정 연결 API 계약 기반 정리

- `AuthNextStep`에 `LINK_ACCOUNT`가 포함되어 있는지 확인
- `SsafySsoCallbackResponse`의 현재 응답 필드 확인
- `SsafySsoCallbackPage.vue`와 `AuthLinkAccountPage.vue`의 sessionStorage 사용 방식 확인
- `SsafySsoCallbackResponse`에 계정 연결용 임시 토큰 필드 추가
- 필드명은 우선 `linkToken?: string`로 정의
- 기존 로그인/온보딩 분기 응답 타입과 충돌하지 않도록 optional로 추가
- `LinkAccountRequest` 타입 추가
- `LinkAccountResponse` 타입 추가
- 응답은 기존 인증 세션 처리와 맞게 `accessToken`, `refreshToken`, `user`, `nextStep`을 포함할 수 있도록 정의
- `authApi.ts`에 `linkSsafyAccount` 함수 추가
- 요청/응답 타입을 명시한다
- endpoint 후보는 `/auth/ssafy/link-account`로 둔다
- 연결 대기 payload 타입을 정의한다
- payload는 `{ email?: string, linkToken: string }` 구조로 둔다
- 중복된 storage key 상수를 공통 위치로 분리한다
- JSON parse 실패 시 안전하게 `null`을 반환하는 read helper를 준비한다
- write/clear helper를 함께 준비해 후속 작업에서 callback/page 양쪽이 같은 함수를 사용하게 한다
- `SsafySsoCallbackPage.vue`의 link account storage key 참조를 공통 상수 또는 helper 기반으로 바꾼다
- `AuthLinkAccountPage.vue`의 link account storage key 참조를 공통 상수 또는 helper 기반으로 바꾼다

### 2단계: SSO 계정 연결 안내 및 동의 플로우

- callback 응답에서 `email`, `linkToken`을 sessionStorage payload로 저장한다
- `LINK_ACCOUNT`인데 `linkToken`이 없으면 callback 화면에서 오류를 표시한다
- SSO source storage는 기존처럼 callback 처리 후 제거한다
- `/auth/link-account`로 이동하는 기존 라우팅은 유지한다
- `AuthLinkAccountPage.vue` 진입 시 link account sessionStorage를 읽는다
- payload가 없거나 `linkToken`이 없으면 잘못된 접근으로 처리한다
- 잘못된 접근 시 안내 메시지와 재인증/회원가입 선택 복귀 동선을 제공한다
- 기존 “이미 가입된 계정입니다” 중심 문구를 “기존 계정 연결 안내” 문맥으로 변경한다
- 계정 연결 필수 동의 체크박스를 추가한다
- 동의하지 않으면 연결 진행 버튼은 비활성화한다
- “다시 인증하기”, “회원가입 선택으로 돌아가기”, “로그인으로 이동” 동선에서 sessionStorage 제거 기준을 정리한다
- alert 영역, checkbox label, button disabled 상태를 명확히 표시한다

### 3단계: 계정 연결 API 호출 및 결과 처리

- 연결 버튼 submit handler를 구현한다
- 중복 클릭을 방지한다
- 동의 여부와 `linkToken` 존재 여부를 검증한다
- `linkSsafyAccount({ linkToken, agree: true })`를 호출한다
- 성공 시 `authStore.setSession(response.data)`를 호출한다
- 성공 후 link account sessionStorage를 제거한다
- `nextStep` 기준으로 다음 화면으로 이동한다
  - `HOME`은 홈으로 이동
  - `ONBOARD_PROFILE`은 온보딩 기본정보로 이동
  - `user.onboardingCompleted === false`는 온보딩 기본정보로 이동
- 연결 토큰 만료, 이미 연결된 계정, 네트워크 오류, 알 수 없는 오류를 화면에서 처리한다
- 실패 시 사용자가 다시 시도하거나 재인증할 수 있게 한다

### 4단계: 이메일 회원가입 중복 이메일 로그인 유도

- 이메일 인증코드 요청 중 `U003` 처리 방식을 변경한다
- 최종 회원가입 중 `U003` 처리 방식을 변경한다
- 이메일 회원가입에서 중복 이메일이 발견되면 `/auth/link-account`로 보내지 않는다
- 이미 가입된 이메일 안내와 로그인 이동 버튼을 제공한다
- 중복 이메일 발생 시 인증코드/토큰 상태를 초기화한다
- 사용자가 다른 이메일을 입력하면 정상 재시도 가능하게 한다

### 5단계: 검증 및 라우팅/문구 마무리

- `/auth/link-account` 라우트 접근 조건과 guestOnly guard 충돌 여부를 확인한다
- 연결 성공 후 토큰 저장과 라우팅 순서를 확인한다
- 이메일 신규 가입, 이메일 중복 가입, SSO 신규 가입, SSO 중복 이메일 연결, 취소, linkToken 없음/만료, 연결 API 실패 시나리오를 확인한다
- 버튼 disabled 상태, alert 영역, 체크박스 label, 모바일 레이아웃을 확인한다

## 구현 체크리스트

### 1단계: 계정 연결 API 계약 기반 정리

- [x] 기존 인증 타입과 SSO 계정 연결 흐름 확인
- [x] `SsafySsoCallbackResponse`에 `linkToken` 필드 추가
- [x] `LinkAccountRequest` 타입 추가
- [x] `LinkAccountResponse` 타입 추가
- [x] `linkSsafyAccount` API 함수 추가
- [x] link account sessionStorage payload 타입 정의
- [x] link account sessionStorage read/write/clear helper 추가
- [x] 기존 callback/page의 storage key 중복 제거
- [x] `npm run type-check` 실행

### 2단계: SSO 계정 연결 안내 및 동의 플로우

- [x] `LINK_ACCOUNT` 응답의 `linkToken` 필수 검증 추가
- [x] callback에서 link account sessionStorage 저장 보강
- [x] 연결 안내 화면 진입 시 payload 검증 추가
- [x] 잘못된 접근 상태 UI 추가
- [x] 기존 계정 연결 안내 문구로 화면 개편
- [x] 계정 연결 필수 동의 체크박스 추가
- [x] 연결 진행 버튼의 disabled 상태 추가
- [x] 취소/재인증 시 sessionStorage 제거 처리
- [x] 모바일/접근성 상태 확인
- [x] `npm run type-check` 실행

### 3단계: 계정 연결 API 호출 및 결과 처리

- [x] 연결 버튼 submit handler 구현
- [x] 중복 제출 방지 구현
- [x] 동의 여부와 `linkToken` 검증 구현
- [x] `linkSsafyAccount` API 호출 구현
- [x] 성공 시 auth store 세션 저장
- [x] 성공 후 link account sessionStorage 제거
- [x] `nextStep` 기준 라우팅 구현
- [x] API 실패 오류 처리 구현
- [x] `npm run type-check` 실행

### 4단계: 이메일 회원가입 중복 이메일 로그인 유도

- [x] 이메일 인증코드 요청 중 `U003` 로그인 유도 처리
- [x] 최종 회원가입 중 `U003` 로그인 유도 처리
- [x] 이메일 회원가입 중복과 SSO 계정 연결 흐름 분리 확인
- [x] 중복 이메일 발생 시 이메일 인증 상태 초기화
- [x] `npm run type-check` 실행

### 5단계: 검증 및 마무리

- [ ] 라우트 guard 확인
- [ ] `npm run type-check` 실행
- [ ] `npm run build` 실행
- [ ] 주요 수동 시나리오 확인

## 최종 검증

- `cd FE && npm run type-check`
- 필요 시 `cd FE && npm run build`

## 확인이 필요한 미결정 사항

- BE 최종 endpoint가 `/auth/ssafy/link-account`가 맞는지 확인 필요
- SSO callback의 연결용 임시 토큰 필드명이 `linkToken`이 맞는지 확인 필요
- 계정 연결 요청에 `agree: boolean`을 보낼지, 동의 여부는 FE에서만 검증할지 확인 필요
