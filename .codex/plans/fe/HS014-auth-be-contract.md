# AUTH-001/002 로그인·회원가입 BE 연동 정리

## 배경/목표

현재 FE 로그인/회원가입 화면은 일부 API 연동 코드가 있으나, 로그인 endpoint와 응답 타입이 과거 후보 계약 기준으로 남아 있다. 실제 BE 구현 계약(`/api/auth/**`)에 맞춰 이메일 회원가입, 로그인, 토큰 저장, 인증 헤더, 홈 진입 분기를 정리한다.

## 기준 문서

- `BE/src/main/java/com/ssafy/backend/auth/controller/AuthController.java`
- `BE/README.md` 인증 방식
- `APIs.md` 인증 목록
- `.codex/requests/be/006-home-api-contract.md`
- `FE/docs/frontend/api/api-index.md`
- `FE/docs/frontend/screens/AUTH-001/requirements.md`
- `FE/docs/frontend/screens/AUTH-002/requirements.md`

## 확인된 BE 계약

- 공통 base URL은 FE axios 기준 `VITE_API_BASE_URL`이며, 기본값은 `/api`다.
- 따라서 FE API 함수에서는 `/auth/...` 경로를 호출하면 최종 URL이 `/api/auth/...`가 된다.
- 회원가입:
  - `POST /api/auth/email/check-duplicate`
  - `POST /api/auth/email/send-code`
  - `POST /api/auth/email/verify-code`
  - `POST /api/auth/signup`
- 로그인:
  - `POST /api/auth/signin`
  - 요청은 `email`, `password`만 보낸다. `rememberMe`는 FE 저장 정책에만 사용한다.
  - 응답은 `accessToken`, `refreshToken`만 내려온다. 현재 BE는 `user`, `nextStep`을 내려주지 않는다.
- 토큰:
  - Access Token은 `Authorization: Bearer <accessToken>` 헤더에 붙인다.
  - Refresh Token 재발급은 `POST /api/auth/reissue`에 `refreshToken` body로 호출한다.
  - 로그아웃은 `POST /api/auth/logout`이며 Access Token 인증이 필요하다.
- 홈:
  - `/api/home`은 비로그인 접근 가능하다.
  - `/api/home/following` 등 회원 기반 홈 API는 인증이 필요하다.
  - `.codex/requests/be/006-home-api-contract.md`의 홈 응답 계약은 아직 BE 확정 전이므로 이번 작업에서는 인증 상태에 따른 호출 준비까지만 한다.

## 작업 내용

기존 회원가입 API는 실제 BE 계약과 거의 맞으므로 누락된 이메일 중복 확인 함수와 문서 상태를 보강한다. 로그인은 endpoint를 `/auth/login`에서 `/auth/signin`으로 교체하고, 응답 타입을 실제 `TokenResponse` 기준으로 좁힌다. 로그인 성공 후 사용자 정보가 없다는 점을 고려해 온보딩 여부 기반 이동은 서버 응답에 의존하지 않고 보수적인 fallback으로 처리한다.

## 회원가입 선행 UX 변경

- [x] 이메일 입력 줄의 기존 `인증코드 발송` 버튼을 `중복 확인` 버튼으로 교체한다.
- [x] `POST /auth/email/check-duplicate` 호출 함수를 추가한다.
- [x] 중복 확인이 완료된 이메일에 대해서만 인증코드 입력창과 `인증코드 발송` 버튼을 사용할 수 있게 한다.
- [x] 이메일 값이 바뀌면 중복 확인, 인증코드 발송, 인증 완료, 회원가입용 `verificationToken` 상태를 초기화한다.
- [x] 중복 이메일이면 기존처럼 로그인 이동 CTA와 이메일 오류를 표시한다.
- [x] `npm run type-check`, `npm run build`로 검증한다.

## AUTH-001 회원가입 BE 연동 실행 계획

이번 단계는 로그인 연동을 제외하고 이메일 회원가입만 실제 BE 계약에 맞춰 마무리한다.

- [x] 회원가입 API 함수 경로를 최종 점검한다.
  - `checkEmailDuplicate`: `POST /auth/email/check-duplicate`
  - `sendEmailVerificationCode`: `POST /auth/email/send-code`
  - `verifyEmailCode`: `POST /auth/email/verify-code`
  - `signUp`: `POST /auth/signup`
- [x] 요청 payload를 BE DTO와 맞춘다.
  - 중복 확인/인증코드 발송: `{ email }`
  - 인증코드 확인: `{ email, code }`
  - 회원가입: `{ email, password, name, verificationToken }`
- [x] 응답 envelope 처리를 점검한다.
  - 모든 응답은 `ApiResponse<T>` 기준으로 처리한다.
  - `checkEmailDuplicate`, `sendEmailVerificationCode` 성공 `data`는 `null`로 처리한다.
  - `verifyEmailCode` 성공 시 `data.verificationToken`을 저장한다.
  - `signUp` 성공 시 `data.onboardingCompleted`가 `false`이면 온보딩 기본정보 화면으로 이동한다.
- [x] 회원가입 화면 상태 흐름을 실제 API 실패 케이스 기준으로 점검한다.
  - 중복 확인 성공 전에는 인증코드 발송/입력/확인 불가
  - 이메일 변경 시 중복 확인/인증코드/인증 토큰 초기화
  - 인증코드 재발송 시 기존 코드 입력값과 인증 토큰 초기화
  - 인증 완료 후 이메일 입력 잠금
- [x] BE 오류 코드별 메시지를 회원가입 화면에 매핑한다.
  - `U003`: 이메일 필드 오류 + 로그인하기 CTA
  - `U005`: 인증코드 오류
  - `U006`: 인증 토큰 만료/불일치로 인증 상태 초기화
  - `U007`: 인증 시도 횟수 초과, 재발송 안내
  - `U008`: 이메일 필드 또는 상태 메시지에 재요청 제한 안내
  - `C001`: 서버 검증 실패, field errors가 있으면 해당 필드에 표시
- [x] API 문서를 실제 회원가입 흐름에 맞춰 갱신한다.
  - `FE/docs/frontend/api/api-index.md` 인증 표에 이메일 중복 확인 행 추가
  - 이메일 회원가입 섹션에 중복 확인 단계를 추가
  - `FE/docs/frontend/screens/AUTH-001/requirements.md`에 현재 UX 흐름 반영
- [ ] 로컬 수동 검증 시나리오를 확인한다.
  - BE 미기동 상태에서 네트워크 오류 표시
  - 중복 이메일이면 로그인 CTA 표시
  - 사용 가능한 이메일이면 인증코드 발송 버튼 활성화
  - 인증코드 발송 성공 후 코드 입력/확인 가능
  - 인증 성공 후 가입하기 가능
  - 가입 성공 후 `/onboarding/basic-info` 이동
- [x] 최종 검증을 실행한다.
  - `npm run type-check`
  - `npm run build`

## 구현 목록

- [ ] `FE/src/domains/auth/api/authApi.ts`의 로그인 endpoint를 `/auth/signin`으로 변경한다.
- [x] `checkEmailDuplicate` API 함수를 추가해 `POST /auth/email/check-duplicate`를 호출하도록 한다.
- [ ] `LoginRequest`에서 BE로 전송하지 않는 `rememberMe`를 API request payload와 화면 form state로 분리한다.
- [ ] `LoginResponse`를 실제 BE 응답인 `accessToken`, `refreshToken` 중심으로 정리하고 `user`, `nextStep` 의존 로직을 fallback 처리한다.
- [ ] 로그인 성공 시 `authStore.setSession`에는 토큰만 저장하고, `rememberMe` 값은 storage 선택에만 사용한다.
- [ ] 로그인 성공 후 이동 정책을 정리한다.
  - `redirect` query가 있으면 우선 이동한다.
  - 사용자 정보가 없으면 기본 목적지는 홈으로 둔다.
  - 온보딩 강제 분기는 `내 정보 조회` 또는 로그인 응답 확장 계약이 생긴 뒤 반영한다.
- [ ] `POST /auth/reissue`, `POST /auth/logout` API 함수를 추가한다.
- [ ] 필요 시 axios response interceptor에서 401 처리와 refresh token 재발급 정책을 최소 범위로 도입한다.
  - 자동 재발급은 중복 요청/무한 루프 방지가 필요하므로, 구현 복잡도가 커지면 이번 범위에서는 함수만 추가하고 호출 지점은 별도 계획으로 분리한다.
- [ ] 인증 오류 메시지를 BE 오류 코드 기준으로 정리한다.
  - `U003`: 중복 이메일
  - `U005`: 인증코드 불일치 또는 만료
  - `U006`: 이메일 인증 필요
  - `U008`: 인증코드 요청 과다
  - `U009`: 이메일 또는 비밀번호 불일치
  - `U010`, `U011`: 토큰 오류
- [ ] `FE/docs/frontend/api/api-index.md`에서 로그인 endpoint `/api/auth/login`을 `/api/auth/signin`으로, 토큰 갱신 `/api/auth/refresh`를 `/api/auth/reissue`로 갱신한다.
- [ ] 홈 API 연동 예정 문서 또는 주석에는 `.codex/requests/be/006-home-api-contract.md`가 아직 확정 계약이 아니라는 점을 유지한다.
- [ ] 검증을 실행한다.
  - `npm run type-check`
  - `npm run build`

## 구현 시 주의 사항

- FE 작업은 `FE/` 내부만 수정한다.
- BE 코드는 수정하지 않는다. 계약 추가가 필요하면 `.codex/requests/be/`에 요청 문서를 남긴다.
- `APIs.md`에는 `/auth/...`로 적힌 항목이 있으나 실제 컨트롤러는 `/api/auth/...`다. FE axios baseURL 기본값이 `/api`이므로 FE 코드에서는 `/auth/...`를 사용한다.
- BE 로그인 응답에는 현재 `onboardingCompleted`가 없다. 로그인 직후 온보딩 여부를 정확히 분기하려면 `GET /api/users/me` 또는 로그인 응답 확장이 필요하다.

## 확인이 필요한 미결정 사항

- 로그인 성공 후 항상 홈으로 보낼지, 사용자 정보 조회 API 구현 전까지 온보딩 진입 버튼/가드에서 처리할지 결정이 필요하다.
- Refresh Token 자동 재발급을 이번 범위에 포함할지, 명시 호출 함수만 먼저 둘지 결정이 필요하다.
- 로그아웃 성공 후 Access Token이 만료 전까지 BE에서 유효할 수 있으므로, FE는 로컬 세션 삭제와 화면 이동을 기준으로 처리한다.
- 홈 로그인 섹션의 실제 API 계약은 `.codex/requests/be/006-home-api-contract.md`에 대한 BE 답변 이후 별도 반영한다.
