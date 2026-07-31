# SY018 — ONBOARD-001 기본 정보 입력 API

## 배경/목표

가입 직후 온보딩 화면에서 닉네임·전화번호·주소·성별을 저장하는 `PATCH /api/users/{id}` 엔드포인트가 없어
온보딩 완료 처리가 불가능한 상태였다(APIs.md 미구현). 마이페이지 수정(MY-001)도 같은 엔드포인트를
재사용할 수 있도록 함께 구현한다.
추가로 `Member` 엔티티와 `schema.sql`이 여러 군데 어긋나는 문제(.claude/requests/be/001)를
이번 작업에서 함께 보강한다.

## 작업 내용

- `Member` 엔티티에 누락 필드(`memberType`, `status`, `deletedAt`, `profileImageUrl`) 추가.
  `nickname` unique 제약 설정, `password` nullable 변경(SSO 대응).
- `MemberType`, `MemberStatus` enum 추가.
- 요청 DTO(`UpdateMemberRequest`)는 닉네임·전화번호·주소를 필수, 성별을 선택으로 받는다.
  기능정의서(ONBOARD-001)에 따라 프로필 이미지는 받지 않는다.
- 서비스(`UserService`)에서 IDOR 방지(본인만 수정 가능)와 닉네임 중복 처리를 담당한다.
- `ErrorCode`에 `NICKNAME_ALREADY_TAKEN(U012, 409)` 추가.
- `.claude/requests/be/001-member-entity-schema-drift.md`은 일부만 반영됐다 — 남은 항목(닉네임
  NOT NULL vs nullable, 비밀번호/전화번호 컬럼명, 성별·주소가 schema.sql에 없음)을 남기고 트리밍.

## 구현 목록

- [x] `MemberType.java` enum 생성 (GENERAL / BUSINESS)
- [x] `MemberStatus.java` enum 생성 (ACTIVE / SUSPENDED / WITHDRAWN)
- [x] `Member.java` 엔티티 필드 추가 및 `updateBasicInfo()` 메서드 추가
- [x] `ErrorCode` — `NICKNAME_ALREADY_TAKEN(U012)` 추가
- [x] `UpdateMemberRequest.java` — 요청 DTO
- [x] `MemberProfileResponse.java` — 응답 DTO
- [x] `UserService.java` — 온보딩/마이페이지 기본 정보 수정 로직
- [x] `UserController.java` — `PATCH /api/users/{id}`
- [x] `UserServiceTest.java` — 5케이스 단위 테스트 (모두 통과)
- [x] `APIs.md` — PATCH /users/{id} 구현 완료 + 인증 필요 여부 ✓ 표시

## 리뷰에서 찾아 고친 것

- **`memberType`/`status` 컬럼이 로컬 DB에 추가되지 않던 문제**: 이미 row가 485건 있는 `member`
  테이블에 `nullable=false`인데 DB 레벨 `DEFAULT`가 없는 컬럼을 `ddl-auto=update`로 추가하려 하면
  Postgres가 ALTER TABLE 자체를 거부한다. `@Column(columnDefinition = "VARCHAR(20) DEFAULT '...'")`을
  추가해서 해결 — 이게 없으면 auction/chat/live 통합 테스트 73개가 이 컬럼 부재로 전부 깨졌었다.
- **잘못된 에러코드**: 본인 아닌 타인의 정보를 수정하려 할 때 `ONBOARDING_REQUIRED`("온보딩을
  완료해야 이용할 수 있습니다")를 반환하고 있었다 — 상황과 메시지가 안 맞는다. 전용
  `MEMBER_FORBIDDEN(U013, 403, "본인의 정보만 수정할 수 있습니다.")`으로 교체.
- **성별 null-safe 처리 누락**: `Member.updateBasicInfo()`가 `gender`를 무조건 덮어써서, 마이페이지
  수정(MY-001) 때 성별을 안 보내면 기존 값이 조용히 지워지는 버그였다. DTO 주석은 "null이면 유지"라고
  써 있었는데 실제로는 그렇게 동작하지 않았다 — `if (gender != null)` 가드 추가, 테스트 추가.
- **요청 문서 조기 삭제**: `.claude/requests/be/001` 전체를 삭제했는데 실제로는 일부(프로필
  이미지/회원구분/상태/탈퇴)만 반영됐고 나머지(닉네임 nullable 여부의 schema.sql 미반영,
  비밀번호/전화번호 컬럼명 불일치, 성별·주소가 schema.sql에 없음)는 그대로다. `.claude/requests/README.md`
  규칙대로 삭제 대신 반영된 항목만 덜어내고 남은 항목만 남기는 식으로 되돌렸다.