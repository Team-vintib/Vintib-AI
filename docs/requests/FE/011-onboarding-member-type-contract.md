# 온보딩 회원 유형 저장·완료(ONBOARD-004) 실제 계약

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

`docs/requests/BE/002-onboarding-contract.md` 3.4절(온보딩 완료)에 적힌 `POST /api/me/onboarding/complete`와
실제 구현이 다르다. ONBOARD-001(`PATCH /users/{id}`)·ONBOARD-002(`PUT /users/{id}/interests`)와
같은 이유로, 클라이언트가 회원 ID를 몰라도 되는 `/api/me/...` 대신 로그인한 본인 ID를
path variable로 받는 `/api/users/{id}` 패턴을 그대로 따랐다. `{id}`가 로그인한 본인과
다르면 403(`MEMBER_FORBIDDEN`)이 온다.

## 요청 내용

- **엔드포인트**: `PATCH /api/users/{id}/member-type`
- **요청 바디**:
  ```json
  {
    "memberType": "GENERAL"
  }
  ```
  - `memberType`은 `GENERAL | BUSINESS` 중 하나이며 필수.
- **동작**:
  - 회원 유형을 저장하고 `onboardingCompleted`를 `true`로 바꾼다(온보딩 최종 완료 시점을
    ONBOARD-001이 아니라 이 API로 옮겼다 — 예전에는 `PATCH /users/{id}`만으로 바로
    완료 처리됐는데, 이제는 안 된다).
  - **재요청은 멱등 성공이다.** 이미 온보딩을 완료한 회원이 다시 호출해도 막지 않고
    회원 유형만 갱신하며 200을 반환한다.
- **응답(200)** — 저장 결과를 바로 확인할 수 있게 갱신된 프로필 전체를 돌려준다
  (요청 문서의 `data: null` 대신, interests 엔드포인트와 같은 이유):
  ```json
  {
    "success": true,
    "data": {
      "id": 1,
      "email": "user@example.com",
      "name": "홍길동",
      "nickname": "빈티지헌터",
      "phoneNumber": "01012345678",
      "address": "서울시 강남구 테헤란로 123",
      "detailAddress": "3층",
      "postalCode": "06236",
      "gender": "MALE",
      "memberType": "BUSINESS",
      "status": "ACTIVE",
      "onboardingCompleted": true
    },
    "error": null
  }
  ```
  - 요청 문서에 있던 `nextStep`(`HOME`/`BUSINESS_VERIFICATION`) 필드는 내려주지 않는다 —
    `memberType`만 보고 FE가 직접 분기(`GENERAL` → 홈, `BUSINESS` → 사업자 인증 화면)하면 된다.
- **에러**: `400`(`memberType` 누락/잘못된 값, `INVALID_INPUT_VALUE`/`C001`), `401`(인증 필요),
  `403`(본인 아닌 회원 수정 시도, `MEMBER_FORBIDDEN`/`U013`), `404`(회원 없음, `USER_NOT_FOUND`/`U001`).

## 참고 — 사업자 인증(BIZ-001)은 별도 스코프

`BUSINESS`를 선택해도 이 API는 사업자 인증 여부와 무관하게 `onboardingCompleted = true`로
처리한다. 사업자 인증서 제출·심사는 `business_info` 테이블(BIZ-001)로 이미 설계돼 있지만
이번 요청 범위가 아니다 — 별도로 진행한다.

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "회원(Users)" 태그, `PATCH /api/users/{id}/member-type`
- BE/src/main/java/com/ssafy/backend/member/controller/UserController.java
- BE/src/main/java/com/ssafy/backend/member/dto/request/UpdateMemberTypeRequest.java
- BE/src/main/java/com/ssafy/backend/member/service/UserService.java (completeOnboarding)
- docs/plans/BE/SY021-onboard-member-type.md
