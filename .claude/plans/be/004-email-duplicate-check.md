# 004 - 이메일 중복 확인 엔드포인트 분리

## 배경/목표

현재는 `POST /api/auth/email/send-code`가 인증코드 발송의 부수 효과로만 이메일 중복을 확인한다. 회원가입 폼에서 이메일을 입력한 직후 인증코드 발송 없이 즉시 "사용 가능한 이메일인지"만 확인하고, 중복이 아닐 때만 인증코드 발송으로 넘어가고 싶다는 요구가 있어 별도 엔드포인트로 분리한다.

## 작업 내용

- `POST /api/auth/email/check-duplicate` 신규 추가. 기존 `EmailVerificationRequest`(email 단일 필드)를 그대로 재사용한다(새 DTO 불필요).
- 이미 가입된 이메일이면 기존 `ErrorCode.DUPLICATE_EMAIL`(409, U003)을 그대로 재사용해 던진다. 새 에러코드는 추가하지 않는다.
- 사용 가능하면 200 OK + `ApiResponse.success(null)` (기존 send-code 성공 응답과 동일한 형태).
- `AuthService`에 `checkEmailDuplicate(String email)` 메서드 추가 — 이메일 정규화(`normalizeEmail`) 후 `existsByEmail` 확인만 수행. 인증코드 발송/Redis 접근 없음.
- `sendEmailVerificationCode`의 기존 `existsByEmail` 체크는 그대로 유지한다(FE가 중복확인을 건너뛰고 바로 send-code를 호출하는 경로에 대한 방어).
- 새 엔드포인트는 이메일 발송이 없어 재발송 쿨다운/시간당 발송 횟수 제한 대상이 아니다. 별도의 rate limit은 추가하지 않는다 — 이미 send-code의 409 응답으로도 동일한 이메일 등록 여부 유추(enumeration)가 가능해, 이 엔드포인트가 새로운 노출을 만들지는 않는다.
- Swagger 어노테이션(`@Operation`/`@ApiResponses`) 추가 (`.claude/skills/swagger` 컨벤션).

## 구현 목록

- [x] `AuthService.checkEmailDuplicate(String email)` 추가
- [x] `AuthController`에 `POST /api/auth/email/check-duplicate` 추가 (`EmailVerificationRequest` 재사용, Swagger 어노테이션 포함)
- [x] `AuthServiceTest`에 테스트 추가: 이미 가입된 이메일이면 예외를 던진다 / 사용 가능한 이메일이면 예외 없이 통과한다
- [x] `.claude/skills/verify` 기준 `./gradlew build` 통과 확인