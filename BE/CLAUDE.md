# BE — Claude 작업 규율

담당 범위·기술 스택·실행 방법은 `README.md` 참고. 이 문서에는 에이전트가 지켜야 할 규율만 적는다.
루트 `CLAUDE.md`의 공통 규율(커밋 컨벤션, push 금지 등)은 이 폴더 작업에도 그대로 적용된다.

## 작업 완료 전 검증 (하네스)

코드를 변경했다면 커밋 전에, 루트 `.gitlab-ci.yml`의 `be-test` job 스크립트를 로컬에서 그대로 실행해 통과를 확인한다(`cd BE` 후 실행). 명령어는 그 파일이 단일 소스이므로 여기서 따로 적지 않는다 — CI 스크립트가 바뀌면 자동으로 최신 검증 기준을 따르게 된다. `.claude/skills/verify`(이 폴더 범위 스킬)로 실행해도 된다.

- `@SpringBootTest` 등 Postgres/Redis가 필요한 테스트가 있다면 루트에서 `docker compose up -d postgres redis`로 먼저 띄운다.
- 작업 중 빠르게 반복할 때는 `./gradlew compileJava compileTestJava`나 `./gradlew test`로 좁혀도 되지만, 최종적으로는 CI와 동일한 스크립트가 통과해야 완료로 본다.

## 새 기능 계획

신규 API/도메인 로직 등 새 기능은 바로 구현하지 않는다. 먼저 계획을 세워 `docs/plans/BE/`(루트 기준)에 md로 기록하고, 사용자 승인 후 그 계획대로 구현한다. 형식은 루트 `docs/plans/README.md` 참고. 버그 수정 등에는 적용하지 않는다.

계획이 승인되면 `.claude/skills/scaffold`(이 폴더 범위 스킬)로 패키지/파일 뼈대를 만든다. 새 엔드포인트에는 `.claude/skills/swagger` 컨벤션에 맞춰 문서화 어노테이션(`@Tag`/`@Operation`/`@ApiResponses`/`@Schema`)을 함께 채운다.

## 다른 파트 코드 수정 금지

FE/AI 코드는 직접 수정하지 않는다. FE나 AI 쪽 변경이 필요하면 `docs/requests/FE/` 또는 `docs/requests/AI/`(루트 기준)에 md로 요청 문서를 남긴다. 형식은 루트 `docs/requests/README.md` 참고.

## 코드 컨벤션

- 도메인 패키지 구조는 `com.ssafy.backend.<domain>.{controller,service,entity,repository,dto}`를 기본으로 한다(도메인 코드는 AUTH, PROD, LIVE, AUCT 등 — README 참고). 엔티티 서브패키지명은 `entity`를 쓰고 `domain`은 쓰지 않는다 — 상세 규칙과 이유는 `.claude/skills/scaffold` 참고. 새 도메인 패키지를 만들면 README 디렉터리 구조 섹션에 반영한다.
- Lombok 사용 가능(`@Getter`, `@Builder` 등). 단 엔티티에 `@Setter`를 습관적으로 붙이지 않는다 — 상태 변경은 의도가 드러나는 메서드로 한다.
- 요청 DTO는 Bean Validation(`@Valid` + `jakarta.validation` 애너테이션)으로 검증한다.
- 새 도메인 로직을 추가하면 최소 하나 이상의 테스트를 함께 작성한다(서비스 단위 테스트 또는 `@WebMvcTest`/`@SpringBootTest`). 테스트 메서드명은 한글로 작성해 검증 의도를 그대로 드러낸다 (예: `인증코드가_일치하면_토큰을_발급한다()`). 자바 식별자는 유니코드를 허용하므로 컴파일·테스트 리포트 모두 문제없다.
- 경매(AUCT) 등 동시성이 걸리는 로직은 Redis 분산 락/Pub-Sub 설계가 아직 미확정이므로, 구현 전 접근 방식을 사용자와 먼저 확인한다.

## 팀 간 계약

- API 스펙(엔드포인트, 요청/응답 DTO)이 바뀌면 FE가 참고할 수 있게 관련 문서에 반영한다.
- AI 서버(FastAPI) 연동 스펙이 바뀌면 `AI/README.md` 또는 `AI/CLAUDE.md`에도 알린다.