# VinTib BE Codex 작업 규칙

담당 범위·기술 스택·실행 방법은 `README.md` 참고. 코드 컨벤션과 팀 간 계약은 `CLAUDE.md`를 그대로 따른다 — 이 문서에는 Codex 전용 프로세스 규율만 적는다.
루트 `AGENTS.md`의 공통 규율(새 기능 계획 선승인, 파트 간 요청 문서, push 금지 등)은 이 폴더 작업에도 그대로 적용된다.

## 작업 완료 전 검증

코드를 변경했다면 커밋 전에, 루트 `.gitlab-ci.yml`의 `be-test` job 스크립트를 로컬에서 그대로 실행해 통과를 확인한다(`cd BE` 후 실행). 명령어는 그 파일이 단일 소스이므로 여기서 따로 적지 않는다 — CI 스크립트가 바뀌면 자동으로 최신 검증 기준을 따르게 된다. 상세 절차는 `.claude/skills/verify/SKILL.md`를 참고한다.

- `@SpringBootTest` 등 Postgres/Redis가 필요한 테스트가 있다면 루트에서 `docker compose up -d postgres redis`로 먼저 띄운다.
- 작업 중 빠르게 반복할 때는 `./gradlew compileJava compileTestJava`나 `./gradlew test`로 좁혀도 되지만, 최종적으로는 CI와 동일한 스크립트가 통과해야 완료로 본다.

## 새 기능 계획

신규 API/도메인 로직 등 새 기능은 바로 구현하지 않는다. 먼저 계획을 세워 `.codex/plans/be/`(루트 기준)에 md로 기록하고, 사용자 승인 후 그 계획대로 구현한다. 파일 규칙(경로, `<이니셜><번호>-slug.md` 형식, 계획 내용 구성)은 루트 `.claude/plans/README.md`를 그대로 따르되 저장 위치만 `.codex/plans/be/`를 쓴다. 버그 수정 등 설계 판단이 필요 없는 변경에는 적용하지 않는다.

계획이 승인되면 패키지/파일 뼈대는 `.claude/skills/scaffold/SKILL.md`의 컨벤션을 따라 구성한다. 새 엔드포인트에는 `.claude/skills/swagger/SKILL.md` 컨벤션에 맞춰 문서화 어노테이션(`@Tag`/`@Operation`/`@ApiResponses`/`@Schema`)을 함께 채운다.

## 다른 파트 코드 수정 금지

FE/AI 코드는 직접 수정하지 않는다. FE나 AI 쪽 변경이 필요하면 `.codex/requests/fe/` 또는 `.codex/requests/ai/`(루트 기준)에 md로 요청 문서를 남긴다. 형식은 루트 `.claude/requests/README.md`를 그대로 따르되 저장 위치만 `.codex/requests/<대상 파트>/`를 쓴다.