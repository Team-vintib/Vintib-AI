# 001 - 이메일 인증 후 회원가입

## 배경/목표

현재 회원가입(`POST /api/auth/signup`)은 이메일 소유 여부를 확인하지 않아 타인의 이메일로도 가입할 수 있다. 가입 전에 이메일 인증코드를 발송·확인하는 절차를 추가해, 인증된 이메일만 회원가입을 완료할 수 있도록 한다.

## 작업 내용

- 인증코드 발송: 이메일을 받아 이미 가입된 이메일이면 거절하고, 아니면 6자리 숫자 코드를 생성해 Redis에 TTL 5분으로 저장한 뒤 메일로 발송한다.
- 코드 확인: 이메일+코드가 일치하면 코드를 즉시 삭제하고, 인증 완료를 나타내는 토큰(UUID)을 발급해 Redis에 TTL 30분으로 저장한다(토큰→이메일 매핑).
- 회원가입 수정: 요청에 인증 토큰 필드를 추가한다. 토큰이 유효하고 매핑된 이메일이 요청 이메일과 일치할 때만 가입을 진행하며, 사용 후 토큰은 즉시 삭제한다.
- 메일 발송을 위해 `spring-boot-starter-mail` 의존성과 SMTP 설정(`spring.mail.*`, env var 기반)이 필요하다.

## 구현 목록

- [x] `build.gradle`에 `spring-boot-starter-mail` 추가 (springdoc-openapi 3.0.3도 함께 추가 — Swagger 어노테이션에 필요)
- [x] `application.yml`에 `spring.mail.*` 설정 추가 (host/port/username/password는 env var), 루트 `.env.example`에 `MAIL_HOST`/`MAIL_PORT`/`MAIL_USERNAME`/`MAIL_PASSWORD` 추가
- [x] `ErrorCode`에 `INVALID_VERIFICATION_CODE`(400), `EMAIL_VERIFICATION_REQUIRED`(400), `TOO_MANY_VERIFICATION_ATTEMPTS`(400), `TOO_MANY_VERIFICATION_REQUESTS`(429) 추가
- [x] `auth` 도메인에 `EmailVerificationService` 추가 — 코드 생성/Redis 저장/메일 발송(쿨다운·시간당 발송 횟수 제한 포함), 코드 검증(오답 횟수 제한 포함) 후 토큰 발급, 토큰 검증(및 소모) 로직
- [x] `AuthController`에 `POST /api/auth/email/send-code`, `POST /api/auth/email/verify-code` 엔드포인트 추가
- [x] `SignUpRequest`에 `verificationToken` 필드 추가(`@NotBlank`), `AuthService.signUp`에서 토큰 검증 후 가입 진행하도록 수정
- [x] 새 컨트롤러 메서드에 Swagger 어노테이션(`@Tag`/`@Operation`/`@ApiResponses`), DTO에 `@Schema` 예시값 추가
- [x] 서비스 단위 테스트 작성 (`EmailVerificationServiceTest` — 쿨다운/시간당 발송 초과/발송 실패 시 상태 미반영/코드 불일치/토큰 발급/시도 초과/토큰 불일치 7건, Mockito 단위 테스트로 통과 확인)
- [x] `BE/README.md` 디렉터리 구조 섹션 갱신
- [x] `EmailVerificationService.sendVerificationCode` 순서 수정 — 메일 발송(`mailSender.send`) 성공 후에만 코드 저장/쿨다운/발송횟수를 Redis에 반영하도록 변경. 기존에는 발송 실패해도 쿨다운·횟수가 먼저 소모돼 코드 없이 사용자가 묶이는 문제가 있었음
- [x] **CI 동등 검증 완료** — GitLab CI `be-test` 잡(`./gradlew build`, Postgres/Redis services 연동)이 이후 스프린트에서 지속적으로 통과 확인됨. `BackendApplicationTests` context load 포함 전체 green.

## 확정된 값

- 인증코드 TTL: 5분
- 인증코드 재발송 쿨다운: 60초 (연속 클릭 방지)
- 인증코드 발송 횟수 제한: 이메일당 시간당 최대 5회
- 인증코드 확인 시도 제한: 코드당 최대 5회 오답 시 코드 무효화(재발송 필요) — brute-force 방지용으로 추가
- 인증 완료 토큰 TTL: 30분 (회원가입 폼 작성 시간 고려)

## 확인이 필요한 미결정 사항

- 메일 발신 SMTP 정보(어떤 계정/서비스를 쓸지)가 아직 없다. 자격증명이 없으면 이번 세션에서는 실제 메일 발송까지는 검증하지 못하고, 코드 경로(컴파일/유닛테스트)까지만 확인 가능하다.