# 온보딩 기본 정보 저장(ONBOARD-001) 실제 계약

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

`FE/docs/frontend/api/api-index.md`에 FE가 BE 구현 전 임시로 적어둔 계약(`PATCH /api/me/onboarding`)과
실제 구현이 다르다. `APIs.md`(공식 스펙)에 이미 명시된 대로 `PATCH /api/users/{id}`로 구현했다.
필드명은 FE 쪽(`SaveBasicInfoRequest`)과 대부분 맞춰뒀다.

## 요청 내용

- **엔드포인트**: `PATCH /api/me/onboarding`이 아니라 **`PATCH /api/users/{id}`**다. `{id}`는 로그인한
  본인 회원 ID(다르면 403).
- **요청 바디** — FE `SaveBasicInfoRequest`와 필드명 동일하게 맞췄다:
  ```json
  {
    "nickname": "빈티지헌터",
    "phoneNumber": "01012345678",
    "address": "서울시 강남구 테헤란로 123",
    "detailAddress": "3층",
    "postalCode": "06236",
    "gender": "MALE"
  }
  ```
  - `postalCode`만 선택 입력(직접 입력 주소면 `null` 가능), 나머지 5개는 전부 필수(매번 전체 값을 새로
    보내야 한다 — 부분 수정이 아니다). 온보딩 최초 완료든 마이페이지 수정(MY-001)이든 같은 엔드포인트,
    같은 필수 규칙이다.
  - `phoneNumber`는 숫자만 10~11자리.
  - `gender`는 `MALE`/`FEMALE` 중 하나만 받는다(FE와 동일, `OTHER` 없음).
- **응답(200)**: `{ "id", "email", "name", "nickname", "phoneNumber", "address", "detailAddress", "postalCode", "gender", "memberType", "status", "onboardingCompleted" }`
- **에러**: `400`(입력값 오류, `error.code = C001`), `401`(인증 필요), `403`(본인 아닌 회원 수정 시도,
  `MEMBER_FORBIDDEN`/`U013`), `404`(회원 없음), `409`(닉네임 중복, `NICKNAME_ALREADY_TAKEN`/`U012`).

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "회원(Users)" 태그, `PATCH /api/users/{id}`
- `BE/src/main/java/com/ssafy/backend/member/controller/UserController.java`
- `BE/src/main/java/com/ssafy/backend/member/dto/request/UpdateMemberRequest.java`

## FE 요청 사항

- `OnboardingBasicInfoView.vue`의 전화번호 입력 힌트("숫자와 하이픈(-)만 입력해 주세요.")와 에러
  예시("예: 010-1234-5678")에서 **하이픈 언급을 빼달라**. `phoneNumber`는 서버가 숫자만
  10~11자리로 검증한다(`^\d{10,11}$`) — 하이픈을 넣어 보내면 그대로 400으로 거부된다.

## 처리 결과

(FE 반영 후 기입)
