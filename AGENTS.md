# S15P11A108 — Codex 작업 규율

프로젝트 배경, 리포지토리 구조, 기술 스택은 루트 `CLAUDE.md` 참고. 이 문서는 Codex가 지켜야 할 공통 규율만 다루며, 내용은 `CLAUDE.md`의 공통 규율과 동일하다 — 계획·요청 문서는 top-level `docs/plans/`·`docs/requests/`를 Claude와 공통으로 쓴다.

## 공통 규율

- 커밋 메시지·브랜치 전략은 `docs/commit-convention.md` 참고 (Notion "코딩 컨벤션" 기반).
  - **절대 직접 push하지 않는다.** 커밋까지만 하고 push는 항상 사용자가 직접 실행한다.
- 팀 간 공유 계약(API 스펙, 도메인 용어 등)이 바뀌면 관련 팀 CLAUDE.md/AGENTS.md/README에도 반영한다.
- 기능 정의서의 우선순위(필수/추가/운영 정책)를 벗어난 범위를 임의로 구현하지 않는다.
- **새 기능(신규 API/화면/도메인 로직 등)은 바로 구현하지 않는다.** 먼저 설계 계획을 세우고 `docs/plans/<파트>/`에 md 파일로 기록한 뒤, 사용자가 검토·승인하면 그 계획대로 구현한다. 파일 규칙(경로 구조, `<이니셜><번호>-slug.md` 형식, 계획 내용 구성)은 `docs/plans/README.md` 참고. 버그 수정 등 설계 판단이 필요 없는 변경에는 적용하지 않는다.
- **BE/FE/AI는 서로 다른 파트의 코드를 직접 수정하지 않는다.** 다른 파트의 변경이 필요하면 코드를 고치는 대신 `docs/requests/<대상 파트>/`(대상 파트: `BE`/`FE`/`AI` 대문자)에 md로 요청 문서를 남긴다. 형식은 `docs/requests/README.md` 참고. Claude·Codex 공통으로 이 `docs/requests/` 폴더를 쓴다.
- **`docs/requests/`에 요청 문서가 하나라도 생기면 `main` 배포 대상으로 본다.** 단, 실제 배포(merge/push)는 사용자 승인 후 사용자가 직접 실행한다. 규칙은 `docs/requests/README.md` 참고.

## 파트별 규율

각 파트 폴더에 `AGENTS.md`가 있으면 그 문서를 우선 적용한다. 없으면 해당 파트의 `CLAUDE.md`를 참고한다.