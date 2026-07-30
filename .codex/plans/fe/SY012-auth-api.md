# 인증 도메인 API 연동 계획

## 배경/목표

AUTH API 연동은 시연 전 안정성을 기준으로 BE에 이미 구현된 메일 회원가입, 로그인, 토큰 재발급, 로그아웃을 우선 붙인다. 회원가입/로그인 화면과 auth store는 이미 구현되어 있으므로, 현재 BE `/api/auth/**` 계약에 맞춰 실제 요청/응답 처리와 성공 후 이동 정책을 정리한다.

## 현재 확인한 BE 계약

FE axios 기본 `baseURL`은 `VITE_API_BASE_URL ?? '/api'`다. 따라서 FE API 함수에서는 `/auth/...` 경로를 사용하고, 실제 요청은 `/api/auth/...`로 나간다.

| 기능 | FE 호출 경로 | 실제 BE endpoint | 요청 | 성공 응답 |
| --- | --- | --- | --- | --- |
| 이메일 중복 확인 | `/auth/email/check-duplicate` | `POST /api/auth/email/check-duplicate` | `{ email }` | `ApiResponse<null>` |
| 인증코드 발송 | `/auth/email/send-code` | `POST /api/auth/email/send-code` | `{ email }` | `ApiResponse<null>` |
| 인증코드 확인 | `/auth/email/verify-code` | `POST /api/auth/email/verify-code` | `{ email, code }` | `ApiResponse<{ verificationToken: string }>` |
| 회원가입 | `/auth/signup` | `POST /api/auth/signup` | `{ email, password, name, verificationToken }` | `ApiResponse<SignUpResponse>` |
| 로그인 | `/auth/signin` | `POST /api/auth/signin` | `{ email, password }` | `ApiResponse<{ accessToken, refreshToken }>` |
| 토큰 재발급 | `/auth/reissue` | `POST /api/auth/reissue` | `{ refreshToken }` | `ApiResponse<{ accessToken, refreshToken }>` |
| 로그아웃 | `/auth/logout` | `POST /api/auth/logout` | body 없음 | `ApiResponse<null>` |

현재 `SignUpResponse`:

```ts
{
  id: number
  email: string
  name: string
  onboardingCompleted: boolean
}
```

## 회원가입 작업 내용

- `authApi.ts`의 메일 회원가입 관련 함수가 현재 BE 계약과 일치하는지 최종 점검한다.
- 회원가입 폼의 요청 순서를 실제 API 기준으로 확정한다.
  - 이메일 입력
  - 중복 확인
  - 인증코드 발송
  - 인증코드 입력/확인
  - `verificationToken` 저장
  - 이름/비밀번호/약관 검증 후 회원가입 요청
- 이메일 값이 바뀌면 중복 확인, 인증코드 발송 상태, 인증 완료 상태, `verificationToken`을 초기화한다.
- 인증코드 재발송 시 기존 코드 입력값과 인증 완료 상태를 초기화한다.
- BE 에러 응답을 필드별 UI에 매핑한다.
  - `email`
  - `code` 또는 `verificationCode`
  - `verificationToken`
  - `password`
  - `name`
- 회원가입 성공 후 이동 정책을 목표 BE 응답 기준으로 정한다.
  - 목표 계약은 `accessToken`, `refreshToken`, `user`, `nextStep`을 받아 즉시 로그인 상태로 전환하는 것이다.
  - `nextStep`이 `ONBOARD_PROFILE`이면 온보딩 시작 화면으로 이동한다.
  - 온보딩 저장/수정/완료 API는 별도 온보딩 도메인 작업으로 분리한다.
  - BE 반영 전까지 응답에 토큰이 없으면 fallback으로 로그인 페이지로 이동한다.
- SSAFY SSO 연동은 이번 범위에서 제외한다.
- 필요 시 화면 문서와 API 문서를 현재 실제 계약 기준으로 갱신한다.

## 로그인/세션 작업 내용

- `LoginRequest`에서 `rememberMe`를 BE payload와 분리한다.
  - 화면 상태에는 유지한다.
  - API 요청 body에는 `email`, `password`만 보낸다.
- `LoginResponse` 타입을 현재 BE `TokenResponse` 중심으로 안전하게 처리한다.
  - `accessToken`
  - `refreshToken`
  - `user`와 `nextStep`은 BE 확장 전까지 optional fallback으로 둔다.
- 로그인 성공 시 auth store에 토큰을 저장한다.
  - `rememberMe=true`: localStorage
  - `rememberMe=false`: sessionStorage
- 로그인 성공 후 이동 정책을 정리한다.
  - `redirect` query가 유효하면 최우선 이동
  - BE 응답에 `nextStep` 또는 `user.onboardingCompleted`가 있으면 해당 정보로 분기
  - 현재처럼 토큰만 있으면 기본 홈으로 이동
- 로그아웃은 기존 정책을 유지한다.
  - BE `POST /auth/logout` 호출
  - 실패해도 FE 로컬 세션 정리
- `POST /auth/reissue` 함수 추가를 검토한다.
  - 시연 전 범위에서는 명시 함수 준비까지만 진행
  - 401 자동 재발급 interceptor는 내일 이후 별도 계획으로 분리
  - 만료 안내 UI는 필수 구현이 아니며, 장시간 입력/주문 같은 중요 플로우에서 별도로 검토한다.
- 인증 필요한 요청에 bearer token이 붙는지 `http.ts` 기준으로 확인한다.
- 로그인 실패/네트워크 실패/서버 validation 실패 메시지를 정리한다.
- SSAFY SSO 버튼과 API는 이번 메일 인증 범위에서 건드리지 않는다.

## 구현 목록

### 회원가입

- [ ] `FE/src/domains/auth/api/authApi.ts` 메일 회원가입 함수 경로/타입 최종 확인
- [ ] `FE/src/domains/auth/types/auth.types.ts`의 `SignUpRequest`, `SignUpResponse`, `VerifyEmailCodeResponse`가 BE DTO와 일치하는지 확인
- [ ] `SignupForm.vue`에서 중복 확인 전에는 인증코드 발송을 막는 흐름 확인
- [ ] 이메일 변경 시 중복 확인/인증/토큰 상태 초기화 확인
- [ ] 인증코드 확인 성공 시 `verificationToken` 저장 확인
- [ ] 회원가입 요청 payload가 `{ email, password, name, verificationToken }`만 보내도록 확인
- [ ] 회원가입 성공 후 자동 로그인하지 않고 로그인 페이지로 이동하는 정책 반영
- [ ] BE error field를 FE field로 매핑하는 로직 점검
- [ ] 네트워크 오류, 중복 이메일, 인증코드 오류, 인증 토큰 만료 케이스의 사용자 메시지 점검

### 로그인/세션

- [ ] `FE/src/domains/auth/types/auth.types.ts`에서 로그인 요청 타입을 화면 form 타입과 API payload 타입으로 분리
- [ ] `FE/src/domains/auth/api/authApi.ts`의 `login`이 BE에 `{ email, password }`만 보내도록 수정
- [ ] `FE/src/domains/auth/api/authApi.ts`에 `reissue` API 함수 추가 검토
- [ ] `LoginResponse`를 현재 BE 응답인 `accessToken`, `refreshToken` 기준으로 안전하게 처리
- [ ] `LoginForm.vue`에서 `rememberMe`는 `authStore.setSession` 저장소 선택에만 사용
- [ ] `LoginForm.vue`의 성공 후 이동 정책 점검
- [ ] `authStore.ts`가 `user` 없는 세션도 정상 저장/복구하는지 확인
- [ ] `logoutSession`이 BE 실패와 무관하게 로컬 세션을 정리하는지 확인
- [ ] 인증 에러 메시지 매핑 점검
- [ ] SSAFY SSO API/화면은 이번 범위에서 건드리지 않도록 확인

### 검증

- [ ] `npm run type-check` 실행
- [ ] `npm run build` 실행

## BE 요청 문서

인증 도메인 연동 중 BE에 확인/보완이 필요한 내용은 아래 문서에 정리한다.

- `.codex/requests/be/015-auth-contract.md`

요청 핵심:

- 회원가입 성공 응답은 B안으로 확정: `accessToken`, `refreshToken`, `user`, `nextStep`
- 회원가입 직후 `nextStep` 기본값은 `ONBOARD_PROFILE`
- 온보딩 저장/수정/완료 API는 별도 온보딩 도메인으로 분리
- 로그인 응답에 `user`, `onboardingCompleted`, `nextStep` 포함 여부는 추가 안정화 항목
- refresh token 저장/무효화, 이메일 인증 운영 정책, 인증 에러 코드는 현재 BE 구현 기준으로 1차 연동 가능
- SSAFY SSO는 이번 범위에서 제외하고 FE에서도 건드리지 않음

## 범위 제외

- SSAFY SSO 시작/콜백/계정 연결 API 연동
- refresh token 자동 재발급 interceptor
- 토큰 만료 안내 UI
- 온보딩 API 연동
- BE 코드 수정

## 확인이 필요한 미결정 사항

- BE가 회원가입 성공 응답에 토큰을 포함하면, 성공 후 이동 정책은 온보딩 진입을 기본값으로 둔다.
- BE 반영 전까지 회원가입 응답에 토큰이 없으면 로그인 페이지 이동 fallback을 둔다.
- 로그인 성공 후 사용자 정보가 없을 때는 기본 홈으로 이동한다.
- `rememberMe`는 로그인 전용 상태이므로 회원가입 API payload에는 포함하지 않는다.
- 시연 전에는 자동 갱신/만료 안내 없이도 충분하다. 내일 이후 refresh token 자동 재발급을 구현하되, 중복 요청 처리와 무한 루프 방지가 필요하므로 별도 작업으로 분리한다.
