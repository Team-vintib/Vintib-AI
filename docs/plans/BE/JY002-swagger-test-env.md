# Swagger 연동 및 테스트 환경 세팅 (S15P11A108-294)

## 배경/목표

API 문서 자동화(springdoc-openapi)와 통합 테스트 기반을 세운다. FE가 명세를 눈으로 확인하고, 이후 도메인 개발이 테스트 위에서 진행되도록 하는 토대.

의존: -47(뼈대, 완료). 착수 시점 상태 — springdoc·Testcontainers 모두 미도입, 테스트는 `BackendApplicationTests`(컨텍스트 로드) 1개뿐.

## 작업 내용

- **springdoc-openapi**: Spring Boot 4.x 호환 버전 추가. `SwaggerConfig`에서 문서 기본 메타데이터(제목·설명·버전) 설정. 엔드포인트 애노테이션은 `BE/.claude/skills/swagger` 컨벤션(`@Tag`/`@Operation`/`@ApiResponses`/`@Schema`)을 따른다.
- **노출 범위**: local·prod 모두 노출한다(아래 결정 사항 2). 초안은 운영 비활성이었으나 뒤집혔다.
- **통합 테스트**: `HealthController`를 대상으로 샘플 통합 테스트 1건. **CI가 이미 `postgres:18-alpine`/`redis:8.8-alpine`을 services로 붙여주므로**(`.gitlab-ci.yml`), `@SpringBootTest`가 그 컨테이너에 붙는다 — 운영과 동일 DB 엔진으로 통합 테스트가 성립한다.
- **CI 연결**: `be-test`는 이미 `./gradlew build`로 테스트를 실행한다. 별도 stage 추가 없이 새 테스트가 자동으로 CI에 태워진다. 통과만 확인.

## 구현 목록

- [x] `build.gradle`: springdoc-openapi 의존성 추가 (`springdoc-openapi-starter-webmvc-ui:3.0.3` — Boot 4는 v3.x부터 지원)
- [x] `SwaggerConfig` — 문서 기본 메타데이터(제목·설명·버전). API 그룹핑은 도메인이 적어 두지 않았다
- [x] `application-local.yml` / `application-prod.yml` — 양쪽 모두 swagger-ui·api-docs 노출
- [x] `HealthController`에 swagger 애노테이션 (swagger 스킬 컨벤션)
- [x] 샘플 통합 테스트 2건 (`HealthControllerIntegrationTest`, `@SpringBootTest`) — AI 서버는 `@MockitoBean`으로 대체
- [x] 로컬 verify(`be-test` 스크립트 동일) 통과 + `/swagger-ui` 육안 확인
- [x] FE용 Swagger 사용 가이드 (`BE/docs/api/swagger-guide.md`)

## 결정 사항 (2026-07-24 사용자 승인)

1. **통합 테스트는 기존 CI services 사용** (Testcontainers 미도입). CI가 이미 prod와 동일한 `postgres:18-alpine`을 services로 제공하므로 목적을 달성한다. 티켓 문구의 "Testcontainers"와는 다르나, 불필요한 러너 설정 변경을 피한다. 로컬은 기존 패턴(`docker compose up -d postgres redis`).
2. **swagger-ui는 prod에서도 노출한다.** 티켓 원문은 "운영 비활성"이나, 서버가 EC2 1대뿐이라 FE가 참조할 별도 개발 서버가 없다. API 구조 공개를 감수하고 FE 협업을 택한다.

## Spring Boot 4에서 달라진 점 (이후 테스트 작성 시)

- `@AutoConfigureMockMvc` 사용 불가 — 모듈러 테스트 스타터에 미포함. `MockMvcBuilders.webAppContextSetup(context)`로 직접 구성한다.
- `@MockBean` 제거됨 — `@MockitoBean`(`org.springframework.test.context.bean.override.mockito`)을 쓴다.

## 후속 필요

- **CORS 미설정** — `CorsConfigurationSource` 빈이 없어 FE가 브라우저에서 호출하면 차단된다. Swagger의 `Try it out`은 동일 출처라 정상 동작해 원인을 알아채기 어렵다. FE 주소(로컬 포트·Vercel 도메인) 확정 후 허용 설정 필요.
- **Swagger `Authorize` 버튼 없음** — JWT 인증은 붙었으나 `SwaggerConfig`에 `SecurityScheme`이 없어 UI에서 토큰을 넣을 수 없다. 인증이 필요한 API를 FE가 Swagger에서 직접 호출하려면 추가해야 한다.
