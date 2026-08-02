# 온보딩 완료 강제 (회원가입만으로는 서비스 이용 불가)

## 배경/목표

지금은 `ONBOARDING_REQUIRED`(U004, 403, "온보딩을 완료해야 이용할 수 있습니다.") 에러코드가
정의만 되어 있고 **코드 어디에서도 실제로 던져지지 않는다.** 회원가입(`AuthService`,
`POST /auth/signup`)은 이메일·비밀번호·이름만으로 끝나고, `nickname`이 `null`, `onboardingCompleted`가
`false`인 `Member`가 그대로 만들어진다. 이후 온보딩 API(`PATCH /users/{id}`, `S15P11A108-227`)를
호출하도록 강제하는 게이트가 백엔드에 없다 — FE가 가입 직후 온보딩 화면으로 보내주는 것에만 의존하는
상태라, 회원이 온보딩을 영영 안 하고 `nickname = null`인 채로 다른 기능을 계속 쓸 수 있다.

실제로 이 상태 때문에 라이브·채팅 쪽에서 "이름 없는 말풍선"(닉네임 없는 회원이 발언) 버그를
`nickname != null ? nickname : name`으로 임시 대체해 우회하고 있다. 원래
`docs/requests/BE/001-member-entity-schema-drift.md`(정윤→서윤, CHAT-001 응답 작성 중 발견)에서
추적하던 항목인데, 그 문서의 비밀번호 컬럼명 불일치 부분은 `S15P11A108-474`에서 해결되며 문서
전체가 삭제됐다 — 이 "표시명 대체 규칙" 항목만 아직 미해결이라 아래 미결정 사항으로 옮겨 둔다.

목표: **온보딩을 완료하지 않은 회원은 서비스의 다른 기능을 쓸 수 없게 만든다.** 회원가입
API 자체를 없애는 게 아니라, 아래 "결정된 방향"대로 로그인 이후 게이트로 막는 방식이다.

## 결정된 방향

- **회원가입/온보딩 단계 구성**: 위 미결정 사항 1번은 **2안(두 단계 유지)으로 확정**한다.
  `POST /auth/signup`은 지금처럼 이메일·비밀번호·이름만으로 끝나고 회원 row를 바로 만든다.
  그 대신 **로그인 이후 온보딩을 완료하기 전까지는 화이트리스트를 제외한 모든 기능을 막는다.**
- **게이트 방식**: "로그인 이후 모든 기능을 막는다"는 요건 자체가 기본값을 차단으로 두고
  예외만 허용하는 모양이라, 매 컨트롤러가 각자 체크하는 방식(빠뜨리기 쉬움)이 아니라
  **JWT 인증 필터/인터셉터 한 곳에서 일괄 처리하는 방식으로 확정**한다. 인증된 요청마다
  principal의 `onboardingCompleted`를 확인해, `false`면 아래 화이트리스트를 제외한 모든
  요청을 403 + `ONBOARDING_REQUIRED`(U004)로 막는다.
  - 이 게이트는 **인증된 요청에만 적용**된다. 로그인 전 공개 엔드포인트(`SecurityConfig.PUBLIC_ENDPOINTS`
    — 헬스체크, Swagger, `/auth/signup`, `/auth/signin`, `/api/categories`, `/api/brands` 등)는
    애초에 인증을 안 타므로 이 게이트와 무관하게 그대로 통과한다.

## 화이트리스트 (인증은 필요하지만 온보딩 미완료여도 허용)

- `POST /auth/reissue`(토큰 재발급) — **포함한다.** 온보딩은 여러 화면(001→002→003→004)을
  거치는 멀티스텝이라 완료까지 시간이 걸릴 수 있는데, 재발급까지 막으면 그 사이 액세스
  토큰이 만료되는 순간 화이트리스트에 있는 온보딩 API조차 호출할 방법이 없어져 재로그인
  말고는 복구 수단이 없어진다. 재발급 자체는 리프레시 토큰만 검증할 뿐 "다른 기능"에 해당하지
  않으므로 막을 이유도 없다.
- `POST /auth/logout` — 로그아웃은 항상 허용한다.
- 온보딩 API 자체: `PATCH /api/users/{id}`(ONBOARD-001), `PUT /api/users/{id}/interests`(ONBOARD-002),
  `PUT /api/me/tryon`(ONBOARD-003, 아직 미구현), `PATCH /api/users/{id}/member-type`(ONBOARD-004).
- 내 정보 조회(`GET /api/users/{id}` 또는 `/users/me`) — FE가 `onboardingCompleted` 상태를 보고
  화면 분기를 하려면 이 조회 자체는 막으면 안 된다.
- 이 외 나머지(상품/라이브/경매/채팅/찜/알림 등 도메인 API 전부)는 온보딩 미완료 시 차단 대상이다.

## 작업 내용

- JWT 인증 처리 경로에 온보딩 완료 체크를 추가한다(필터/인터셉터 — 정확한 위치는 기존 JWT
  인증 필터 구현을 보고 그 안에 넣을지 별도 인터셉터로 둘지 구현 시 정한다).
- 위 화이트리스트를 상수로 명확히 정의한다(경로 목록, `PUBLIC_ENDPOINTS`와 유사한 위치에).
- FE에는 온보딩 미완료 상태에서 화이트리스트 밖 API를 호출하면 403 + `ONBOARDING_REQUIRED`가
  온다는 걸 알리는 요청 문서가 필요하다(화면 전환 로직에 영향).
- **온보딩 순서 보장**: `UserService.completeOnboarding`(ONBOARD-004)이 `member.getNickname() ==
  null`이면 완료 처리를 거부하도록 검증을 추가한다 — 새 에러코드 `ONBOARDING_BASIC_INFO_REQUIRED`
  (`U014`, 400, "기본 정보를 먼저 등록해주세요.") 신설. 화이트리스트 설계상 ONBOARD-004는
  onboardingCompleted가 false여도 호출 가능한 API라, 이 검증이 없으면 001(기본 정보, 닉네임 저장)을
  건너뛰고 004부터 호출해 **닉네임이 null인 채로 onboardingCompleted만 true가 되는** 경우를 막을
  수 없다. 이 검증까지 있어야 "온보딩을 완료한 회원은 항상 닉네임이 있다"는 보장이 확실해지고,
  아래 표시명 대체 규칙 제거가 안전해진다.

## 확인 필요한 미결정 사항

- 없음. **기존 회원 마이그레이션** — 현재 `nickname = null`인 기존 회원은 없고, 게이트 적용 전
  혹시 있더라도 정리(삭제)하기로 확정했다. 별도 마이그레이션 스크립트나 유예 기간을 두지 않는다.

## 표시명 대체 규칙 — 게이트 구현 후 제거 대상으로 확정

닉네임이 없는 회원의 표시명을 라이브·채팅에서 `nickname != null ? nickname : name`으로 임시
대체하던 우회는, 위 게이트(온보딩 미완료 시 채팅 등 다른 기능 자체 차단) + 온보딩 순서 보장
(닉네임 없이는 completeOnboarding 불가) 두 가지가 함께 구현되면 **더 이상 발생할 수 없는
상황이 된다.** 다른 기능을 쓸 수 있는 시점(=onboardingCompleted가 true인 시점)엔 항상
닉네임이 있다는 게 보장되기 때문이다. 게이트·순서 보장 구현 완료 후 이 우회 코드를 제거한다
(라이브·채팅 쪽 코드라 실제 제거는 해당 도메인 담당자와 확인 후 진행).

## 관련 요청 문서

~~`onboardingCompleted`가 정확히 언제 `true`로 바뀌어야 하는지~~ — **해결됨.**
`docs/plans/BE/SY021-onboard-member-type.md`에서 ONBOARD-001(기본 정보 저장) 시점이 아니라
ONBOARD-004(회원 유형 저장, `PATCH /api/users/{id}/member-type`) 시점으로 완료 처리를 옮겼다.
이제 미결정 사항이 전부 해소됐다 — 게이트 방식·화이트리스트·회원가입 단계 구성·온보딩 순서
보장·표시명 대체 규칙 제거·기존 회원 마이그레이션까지 모두 방향이 확정됐고, 구현만 남았다.

## 구현 목록

- [x] `ErrorCode.ONBOARDING_BASIC_INFO_REQUIRED`(U014) 추가
- [x] `UserService.completeOnboarding` — 닉네임 없으면 `ONBOARDING_BASIC_INFO_REQUIRED`로 거부(온보딩 순서 보장)
- [x] `OnboardingRequiredFilter` 신규 (`auth/jwt`) — 인증된 요청 중 화이트리스트 제외하고
      `onboardingCompleted == false`면 403 `ONBOARDING_REQUIRED`, `SecurityConfig`에 `JwtAuthenticationFilter` 바로 뒤로 등록
- [x] 표시명 대체 규칙 제거 — `ChatMessage.senderDisplayName`, `LiveReactionService`,
      `LiveVideoService.displayName`의 `nickname != null ? nickname : name` 우회 제거
- [x] `docs/requests/FE/007-onboarding-required-gate.md` 작성
- [x] 테스트: `OnboardingRequiredFilterTest`(신규), `UserServiceTest`(닉네임 선행 검증 케이스 추가),
      `ChatMessageTest`(표시명 대체 제거 반영)
- [x] `BE:verify` 통과 확인