# AUTH-001 이메일 회원가입 구현

## 배경/목표

이메일 회원가입 화면을 구현하고, 이메일 인증/중복 확인, 입력값 검증, 회원가입 API 연동, 온보딩 이동까지 단계별로 진행한다. 각 단계는 커밋 가능한 단위로 분리한다.

## 작업 범위

- `FE/` 내부만 수정한다.
- `BE/`, `AI/`, `infra/`는 수정하지 않는다.
- 회원가입 성공 후 이동 대상은 현재 구현된 `ROUTE_NAMES.ONBOARD_PROFILE`(`/onboarding/basic-info`)이다.

## 단계별 구현 계획

### 1단계: 회원가입 화면 기본 구조

- `domains/auth/pages/SignupPage.vue` 생성
- `/auth/signup` 라우트 등록
- `AuthLayout` 적용
- 이름, 이메일, 인증코드, 비밀번호, 비밀번호 확인, 약관, CTA 영역 배치
- API 호출, 입력 상태, 검증은 포함하지 않음

### 2단계: 회원가입 입력 상태 관리

- `SignupForm.vue` 분리
- form state와 touched 기본 구조 작성
- 비밀번호 보기 토글
- 전체 약관 동의/개별 약관 동의 상태 구현
- 제출 버튼 disabled 조건 기본 틀 구성

### 3단계: 입력값 검증

- `shared/utils/validators.ts` 추가
- 이름, 이메일 형식, 비밀번호 정책, 비밀번호 확인, 필수 약관 검증
- blur 시 필드 검증, submit 시 전체 검증
- 필드별 오류 메시지 표시

### 4단계: 이메일 인증/중복 확인 UI

- `EmailVerificationField.vue` 작성
- 인증코드 발송/확인 UI와 loading 상태 구현
- 이메일 변경 시 인증 상태 초기화
- 중복 이메일, 재발송 제한, 인증 실패 메시지 표시

### 5단계: 이메일 인증 API 연동

- `authApi.ts`, `auth.types.ts` 작성
- `sendEmailVerificationCode`, `verifyEmailCode` 연동
- 인증 성공 시 `verificationToken` 저장

### 6단계: 회원가입 API 연동

- `signUp` API 연동
- 요청 중 loading, 중복 제출 방지
- 서버 검증 오류와 네트워크 오류 처리

### 7단계: 온보딩 이동 처리

- 가입 성공 시 `ROUTE_NAMES.ONBOARD_PROFILE` 이동
- 응답의 `onboardingCompleted` 값에 따른 이동 기준 정리

### 8단계: 문서 및 검증 정리

- AUTH-001 요구사항/API/구현 상태 문서 갱신
- `npm run type-check`
- `npm run build-only`

## 구현 체크리스트

- [x] 1단계 회원가입 화면 기본 구조
- [x] 2단계 회원가입 입력 상태 관리
- [x] 3단계 입력값 검증
- [x] 4단계 이메일 인증/중복 확인 UI
- [x] 5단계 이메일 인증 API 연동
- [x] 6단계 회원가입 API 연동
- [ ] 7단계 온보딩 이동 처리
- [ ] 8단계 문서 및 검증 정리
