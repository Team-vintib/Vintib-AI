# SY021 - 회원 유형 선택 및 온보딩 완료 API (ONBOARD-004, S15P11A108-261)

## 배경/목표

FE가 ONBOARD-004(일반/사업자 선택 화면)를 구현하고 BE 구현을 요청했다(원 요청은
`.codex/requests/be/004-onboarding-member-type-completion-api.md`였고, `plans`/`requests` 폴더를
`docs/` 아래로 통합하면서 이제는 `docs/requests/BE/002-onboarding-contract.md` 3.4절에 해당
요청이 들어 있다). DB 컬럼(`member.member_type`)과 엔티티 필드(`Member.memberType`), enum(`MemberType`)은
이미 있지만, 회원이 유형을 **선택해서 저장하는 API가 없다.**

이 작업은 동시에 `docs/plans/BE/SY019-onboarding-enforcement.md`에 걸려 있던 미결정 사항 중
하나("`onboardingCompleted`가 정확히 언제 true가 되어야 하는가")를 확정한다 — 현재는 ONBOARD-001(기본
정보 저장) 시점에 바로 true가 되는데, FE 화면 흐름(001→002→003→004)상 004(회원 유형 선택)까지
마친 시점으로 옮긴다.

**스코프 밖**: SY019의 나머지 부분(온보딩 미완료 회원의 다른 API 접근을 막는 인터셉터/화이트리스트)은
이 계획에 포함하지 않는다. "언제 완료 플래그가 true가 되는가"만 여기서 정하고, "미완료 상태를 실제로
막을지"는 SY019에 남겨둔다. 사업자 인증(BIZ-001, `business_info` 테이블)도 별도 스코프 — `BUSINESS`를
선택해도 인증 여부와 무관하게 이 API에서 `onboardingCompleted = true`로 처리한다.

## 설계

### 엔드포인트 경로 — FE 요청과 다르게 결정

FE 요청 문서는 `POST /api/me/onboarding/complete`를 제안했지만, ONBOARD-001(`PATCH /users/{id}`)·
ONBOARD-002(`PUT /users/{id}/interests`)가 이미 `/users/{id}` + `requesterId == targetId` 403 체크
패턴을 쓰고 있어 그대로 따른다(`005-onboarding-interests-contract.md`에서 FE 초안 `/api/me/interests`를
같은 이유로 `/users/{id}/interests`로 바꾼 선례와 동일). FE에는 구현 후 `docs/requests/FE/`에
계약 문서로 확정 스펙을 전달한다.

- `PATCH /api/users/{id}/member-type`
- 요청: `UpdateMemberTypeRequest(MemberType memberType)` — `@NotNull`
- 응답: `MemberProfileResponse`(기존 재사용) — 저장된 `memberType`과 `onboardingCompleted = true`를
  바로 확인할 수 있게, FE 요청 문서의 `data: null` 대신 갱신된 프로필을 돌려준다(interests
  엔드포인트와 동일한 이유).

### 엔티티 — `Member`

- `updateBasicInfo(...)`에서 `this.onboardingCompleted = true;` 줄을 제거한다(ONBOARD-001은 더 이상
  온보딩을 완료시키지 않는다).
- 새 메서드 `completeOnboarding(MemberType memberType)` 추가 — `this.memberType = memberType;
  this.onboardingCompleted = true;`

### 서비스 — `UserService`에 메서드 추가

- `completeOnboarding(Long requesterId, Long targetId, UpdateMemberTypeRequest request): MemberProfileResponse`
  - `requesterId != targetId` → `MEMBER_FORBIDDEN`
  - 회원 없으면 `USER_NOT_FOUND`
  - `member.completeOnboarding(request.memberType())` 호출 후 `MemberProfileResponse.from(member)` 반환
  - **재요청 정책(멱등 성공)**: 이미 `onboardingCompleted = true`인 회원이 다시 호출해도 막지 않고
    유형을 갱신하며 성공 처리한다 — 별도 가드 없음(FE 요청 문서의 "미결정 사항 3" 해소).

### 컨트롤러 — `UserController`에 엔드포인트 추가

- `PATCH /api/users/{id}/member-type` — `@SecurityRequirement(name = "bearerAuth")`, Swagger
  `@Operation`/`@ApiResponses`(200/400/401/403/404), `.claude/skills/swagger` 컨벤션.

### 테스트

- `UserServiceTest`에 케이스 추가:
  - 정상 저장 시 `memberType`이 반영되고 `onboardingCompleted() == true`
  - 본인 아닌 회원 요청 → `MEMBER_FORBIDDEN`
  - 존재하지 않는 회원 → `USER_NOT_FOUND`
  - 이미 완료한 회원이 다시 호출해도 정상 처리(멱등)
- 기존 `기본_정보를_정상_저장하면_온보딩완료_응답을_반환한다` 테스트는 동작이 바뀌므로 수정 필요
  (`updateBasicInfo` 후 `onboardingCompleted()`는 이제 `false`) — 테스트명/단언 갱신.

## 구현 목록

- [x] `Member.updateBasicInfo`에서 `onboardingCompleted = true` 제거, `completeOnboarding(MemberType)` 추가
- [x] `UpdateMemberTypeRequest` (`member/dto/request`)
- [x] `UserService.completeOnboarding`
- [x] `UserController`: `PATCH /api/users/{id}/member-type` + Swagger
- [x] `UserServiceTest`: 기존 온보딩완료 단언 수정 + 신규 케이스 추가
- [x] `APIs.md`에 ONBOARD-004 행 추가(인증 필요 ✓, 구현 완료 ✓)
- [x] `docs/requests/FE/011-onboarding-member-type-contract.md` 작성 (엔드포인트 경로가 FE 초안과 다름을 안내)
- [x] `docs/requests/BE/002-onboarding-contract.md`의 3.1/3.2/3.4절 반영 정리 — 3.3(AI 시착)만 남김
- [x] `docs/plans/BE/SY019-onboarding-enforcement.md`에 "완료 시점은 SY021로 확정"으로 갱신,
      남은 인터셉터/화이트리스트 이슈만 남기기
- [ ] BE:verify로 최종 검증

## 확인이 필요한 미결정 사항

- 없음 — DB/엔티티/enum은 이미 있고, 나머지는 기존 ONBOARD-001/002 패턴을 그대로 따르는 결정이라
  바로 구현 가능하다고 판단.
