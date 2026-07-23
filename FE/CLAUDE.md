# FE — Claude 작업 규율

담당 범위·기술 스택·실행 방법은 `README.md` 참고. 이 문서에는 에이전트가 지켜야 할 규율만 적는다.
루트 `CLAUDE.md`의 공통 규율(커밋 컨벤션, push 금지 등)은 이 폴더 작업에도 그대로 적용된다.

## 새 기능 계획

신규 화면/기능 등 새 기능은 바로 구현하지 않는다. 먼저 계획을 세워 `.claude/plans/fe/`(루트 기준)에 md로 기록하고, 사용자 승인 후 그 계획대로 구현한다. 형식은 루트 `.claude/plans/README.md` 참고. 버그 수정 등에는 적용하지 않는다.

## 다른 파트 코드 수정 금지

BE/AI 코드는 직접 수정하지 않는다. BE나 AI 쪽 변경이 필요하면 `.claude/requests/be/` 또는 `.claude/requests/ai/`(루트 기준)에 md로 요청 문서를 남긴다. 형식은 루트 `.claude/requests/README.md` 참고.