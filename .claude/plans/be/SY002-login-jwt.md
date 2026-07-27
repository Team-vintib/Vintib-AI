# 002 - 로그인(JWT 발급) 및 인증 필터

## 배경/목표

회원가입(`signup`)은 있지만 로그인이 없다. 이메일/비밀번호로 로그인하면 JWT를 발급하고, 이후 요청은 그 토큰으로 인증하도록 한다.
비밀번호 암호화 저장(BCrypt)은 `AuthService.signUp`에 이미 구현되어 있어(`PasswordEncoder.encode`) 이번 범위에는 포함하지 않는다 — 로그인 시 검증(`matches`)과 토큰 발급이 실제 신규 범위다.

`SecurityConfig`의 기존 주석에도 "실제 인증/인가(JWT 필터)는 토큰 발급이 나온 뒤 얹는다"고 명시돼 있어, 이번 작업이 그 다음 단계에 해당한다.

## 결정 필요 사항에 대한 가정 (구현 전 확인 요망)

사용자 확인을 받지 못해 아래는 일반적인 방식으로 가정하고 계획을 세웠다. 승인 전에 다르게 하고 싶은 부분이 있으면 알려달라.

- **토큰 구조**: Access Token(단명) + Refresh Token(장기, Redis 저장) 조합
- **전달 방식**: Access Token은 `Authorization: Bearer <token>` 헤더. Refresh Token은 로그인/재발급 응답 바디에 함께 내려주고, 재발급 요청 시 바디로 받음(쿠키 미사용 — FE 쿠키 처리 부담을 줄이기 위함)
- **로그아웃**: Refresh Token은 Redis에서 즉시 삭제. Access Token은 만료 전 즉시 무효화까지는 하지 않고(블랙리스트 미도입) 짧은 TTL로 자연 만료에 맡김 — 범위를 최소화하기 위한 가정
- **JWT 라이브러리**: `io.jsonwebtoken:jjwt-api` + `jjwt-impl` + `jjwt-jackson` (Spring Security OAuth2 Resource Server 없이 직접 필터 구현)

## 작업 내용

- 로그인: 이메일로 회원 조회 → 존재하지 않거나 비밀번호 불일치 시 동일한 `INVALID_CREDENTIALS` 에러(이메일 존재 여부 노출 방지) → 일치하면 Access/Refresh Token 발급, Refresh Token은 Redis에 `refresh:{memberId}` 키로 TTL만큼 저장
- 토큰 재발급: Refresh Token 검증(서명 + Redis 저장값과 일치) 후 새 Access Token(+ 필요 시 Refresh Token 회전) 발급
- 로그아웃: Redis에서 `refresh:{memberId}` 삭제
- 인증 필터: `Authorization` 헤더의 Access Token을 검증해 `SecurityContext`에 인증 정보 설정. 실패 시 401
- `SecurityConfig` 갱신: 공개 엔드포인트(`/api/auth/signup`, `/api/auth/signin`, `/api/auth/email/**`, `/api/auth/reissue`, swagger, actuator health)만 `permitAll`, 나머지는 인증 필요로 전환
- Access Token payload: `memberId`(subject), `email` 정도로 최소화

## 구현 목록

- [x] `build.gradle`에 `io.jsonwebtoken:jjwt-api`, `jjwt-impl`, `jjwt-jackson` 추가
- [x] `application.yml`에 `jwt.secret`, `jwt.access-token-validity`, `jwt.refresh-token-validity` 추가 (env var 기반), 루트/BE `.env.example`에 `JWT_SECRET`/`JWT_ACCESS_TOKEN_EXPIRATION`/`JWT_REFRESH_TOKEN_EXPIRATION` 추가
- [x] `ErrorCode`에 `INVALID_CREDENTIALS`(401), `INVALID_TOKEN`(401), `EXPIRED_TOKEN`(401) 추가
- [x] `MemberRepository`에 `findByEmail` 추가
- [x] `auth` 도메인에 `JwtTokenProvider` 추가 — Access/Refresh 토큰 생성, 파싱, 서명 검증, 만료 검증
- [x] `AuthService`에 `signIn` 메서드 추가 — 이메일/비밀번호 검증(`PasswordEncoder.matches`) 후 토큰 발급 + Refresh Token Redis 저장
- [x] `AuthService`에 `reissue`, `logout` 메서드 추가
- [x] `SignInRequest`, `TokenResponse`(accessToken/refreshToken) DTO 추가
- [x] `AuthController`에 `POST /api/auth/signin`, `POST /api/auth/reissue`, `POST /api/auth/logout` 엔드포인트 추가 (Swagger 어노테이션 포함)
- [x] `JwtAuthenticationFilter` 추가 (`OncePerRequestFilter`) — Bearer 토큰 검증 후 `SecurityContextHolder`에 인증 정보 설정
- [x] `SecurityConfig` 갱신 — 공개 엔드포인트 목록 정리, 나머지 `authenticated()`, 필터 체인에 `JwtAuthenticationFilter` 등록
- [x] `AuthServiceTest` 추가 — 로그인 성공/비밀번호 불일치/존재하지 않는 이메일/재발급 성공·실패/로그아웃 후 재발급 거부 등
- [x] `JwtTokenProviderTest` 추가 — 토큰 생성/파싱/만료 검증
- [x] `BE/README.md`에 인증 방식(Bearer 토큰) 간단히 반영

## 확인이 필요한 미결정 사항 (해소됨)

- 토큰 구조/전달 방식/로그아웃 정책/라이브러리 — 위 "가정" 그대로 구현 완료
- Access/Refresh Token TTL: Access 15분, Refresh 14일로 확정
- Refresh Token 회전: 재발급마다 새 Refresh Token을 발급해 Redis에 덮어쓰는 방식으로 구현(회전함)