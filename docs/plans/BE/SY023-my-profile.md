# SY023 - 내 정보 조회 API (MY-001, `GET /api/users/me`)

## 배경/목표

`docs/requests/BE/001-auth-contract.md`, `011-user-mypage-contract.md` 두 문서가 독립적으로
`GET /api/me`(내 정보 조회)를 요청했고, `docs/requests/BE/012-be-request-index.md`에도 미해결로
남아 있다. 엔드포인트 경로는 사용자 확인대로 `GET /api/users/me`로 확정한다 — `APIs.md`에 이미
"내 정보 조회 | GET | `/users/me` | | MY-001 |" 행으로 예고돼 있고, 기존 `UserController`가
`/api/users` 베이스라 그 관례를 그대로 따른다(FE 요청 문서의 `/api/me` 초안과 다르게 결정 —
ONBOARD-001/002/004와 같은 이유).

**SY019(온보딩 강제 게이트)와의 연결**: 지금 FE는 로그인 직후 이 회원이 온보딩을 완료했는지
확인할 방법이 없다(로그인 응답엔 토큰만 있고 JWT에도 안 담김). 이 API가 있어야 FE가 무작정
아무 API나 불러 403을 받아보지 않고도 온보딩 화면으로 보낼지 판단할 수 있다. `OnboardingRequiredFilter`의
화이트리스트(`/api/users/*` 패턴)에 `/api/users/me`가 이미 포함돼 있어 — 온보딩 미완료 상태에서도
이 조회는 막히지 않는다(추가 변경 불필요, 이미 맞게 돼 있음).

## 스코프 밖

- **로그인/회원가입 응답에 `user`/`nextStep` 포함**(001-auth-contract.md 4절의 별도 요청) —
  `AuthService`/`AuthController` 변경이 필요한 다른 스코프라 이번 계획에 넣지 않는다. 필요하면
  별도 계획으로 진행.
- **`GET /api/users/{id}`(회원 상세 조회, 비회원 공개)** — `APIs.md`에 별도 행으로 예고돼 있지만
  "본인 조회"가 아니라 "임의 회원의 공개 프로필 조회"라 노출 필드 범위(이메일·전화번호 등 개인정보를
  가릴지)가 다른 설계 문제다. 이번엔 다루지 않는다.
- **`businessVerificationStatus`** — `business_info` 테이블은 스키마에만 있고 엔티티/레포지토리가
  없다(BIZ-001 미착수). 이번 응답에는 필드 자체는 넣되(FE 계약과 맞추기 위해) 항상 `null`을
  반환한다 — BIZ-001 구현 후 실제 값으로 채운다.

## 설계

### 응답 — 기존 `MemberProfileResponse` 재사용 + 필드 보강

`MemberProfileResponse`(`PATCH /users/{id}`, `PATCH /users/{id}/member-type` 응답으로 이미 사용 중)에
`profileImageUrl`(`Member` 엔티티에 이미 있는 컬럼, 지금까지 응답에 노출 안 됐음)과
`businessVerificationStatus`(항상 `null`, BIZ-001 전까지)를 추가한다. 새 DTO를 만들지 않고
기존 걸 확장해 세 엔드포인트가 계속 같은 모양을 공유하게 한다.

### 서비스 — `UserService.getMyProfile(Long memberId): MemberProfileResponse`

- `memberRepository.findById(memberId).orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND))`
- `requesterId`/`targetId` 구분이 필요 없다 — path param 자체가 없어 IDOR 여지가 없다(항상 인증된
  본인 조회).

### 컨트롤러 — `UserController`에 엔드포인트 추가

- `GET /api/users/me` — `@SecurityRequirement(name = "bearerAuth")`, Swagger 문서화.
  **주의**: Spring MVC 라우팅에서 `/api/users/me`와 `/api/users/{id}`(PATCH만 있어 지금은 충돌
  없음)가 같은 세그먼트를 두고 겹칠 수 있으니, 나중에 `GET /api/users/{id}`(회원 상세 조회)를
  추가할 때는 `/me`를 먼저 매칭하도록 선언 순서에 주의해야 한다는 점만 계획에 남겨둔다(이번 범위
  아님).

### 테스트

- `UserServiceTest`: 정상 조회(모든 필드 매핑 확인, `businessVerificationStatus == null`),
  존재하지 않는 회원 → `USER_NOT_FOUND`(원칙적으로 JWT principal이 항상 유효한 회원을 가리키므로
  실무에서는 거의 발생하지 않지만 방어적으로 유지).

## 구현 목록

- [ ] `MemberProfileResponse`에 `profileImageUrl`, `businessVerificationStatus` 필드 추가(항상 `null`),
      `from(Member)` 갱신
- [ ] `UserService.getMyProfile(Long memberId)`
- [ ] `UserController`: `GET /api/users/me` + Swagger
- [ ] `UserServiceTest` 케이스 추가
- [ ] `APIs.md` — "내 정보 조회" 행 인증 필요 ✓, 구현 완료 ✓ 표시
- [ ] `docs/requests/BE/001-auth-contract.md`, `011-user-mypage-contract.md`, `012-be-request-index.md` —
      `GET /api/me` 반영 정리(엔드포인트가 `/api/users/me`로 다름을 안내). 001 문서엔 `user`/`nextStep`
      항목이 아직 남으므로 전체 삭제하지 않고 해당 절만 덜어낸다. 011은 이 항목만 있었다면 삭제 가능
      (문서 확인 후 판단).
- [ ] `docs/requests/FE/`에 확정 계약 문서 작성(엔드포인트 경로, `businessVerificationStatus`는
      당분간 `null`이라는 점 안내)
- [ ] `BE:verify` 통과 확인

## 확인이 필요한 미결정 사항

- 없음 — 응답 모양은 기존 `MemberProfileResponse`를 확장하는 것으로 충분하고, 나머지(로그인 응답
  보강, 공개 프로필 조회, 사업자 인증 상태)는 명시적으로 스코프 밖으로 뺐다.
