# S15P11A108 — 빈티지·세컨핸드 의류 라이브 경매 플랫폼

라이브 방송으로 상품 상태를 확인하고, AI 가상 시착 후, 실시간 경매로 구매하는 C2C 의류 거래 플랫폼.
상세 기획은 Notion `프로/공통PJT/Wiki`의 문서를 참고한다 (작성 중, 수시 변경됨).

## 리포지토리 구조

모노레포이며 팀별로 최상위 디렉터리를 분리한다.

- `BE/` — 백엔드. 회원/인증, 상품, 라이브, 실시간 경매, 포인트/결제/배송/정산 API
- `FE/` — 프론트엔드. 라이브 시청/채팅, 실시간 경매 UI, AI 시착 UI, 마이페이지
- `AI/` — AI 모듈. 가상 시착 합성, 상품 설명 초안 생성, 라이브 발언 기반 정보 추출

각 팀 폴더는 자체 `README.md`(실행/구조 안내)와 `CLAUDE.md`(팀별 규율)를 가질 수 있다.

## 공통 규율

- 커밋 메시지·브랜치 전략은 `.claude/commit-convention.md` 참고 (Notion "코딩 컨벤션" 기반).
  - **절대 직접 push하지 않는다.** 커밋까지만 하고 push는 항상 사용자가 직접 실행한다.
  - **커밋 메시지에 Claude를 Co-Authored-By로 추가하지 않는다.**
- 팀 간 공유 계약(API 스펙, 도메인 용어 등)이 바뀌면 관련 팀 CLAUDE.md/README에도 반영한다.
- 기능 정의서의 우선순위(필수/추가/운영 정책)를 벗어난 범위를 임의로 구현하지 않는다.
- API 요청/응답 필드는 FE나 AI가 임의로 확정하지 않는다. Swagger, `APIs.md`, DB/기능 문서로 확인되지 않은 필드는 `임시 view model`, `Mock 전용`, `BE 확인 필요`처럼 표시하고, BE 판단이 필요하면 `.claude/requests/be/`에 요청 문서를 남긴다.
- **새 기능(신규 API/화면/도메인 로직 등)은 바로 구현하지 않는다.** 먼저 설계 계획을 세우고 `.claude/plans/`에 md 파일로 기록한 뒤, 사용자가 검토·승인하면 그 계획대로 구현한다. 규칙은 `.claude/plans/README.md` 참고. 버그 수정 등 설계 판단이 필요 없는 변경에는 적용하지 않는다.
- **BE/FE/AI는 서로 다른 파트의 코드를 직접 수정하지 않는다.** 다른 파트의 변경이 필요하면 코드를 고치는 대신 `.claude/requests/<대상 파트>/`에 md로 요청 문서를 남긴다. 형식은 `.claude/requests/README.md` 참고.

## 기술 스택

| 영역 | 스택 |
| --- | --- |
| FE | Vue.js 3.5.x, TypeScript, Vite, Pinia, SCSS |
| BE | Java 21, Spring Boot 4.1.0 |
| AI | Python 3.12+, FastAPI 0.139.0 |
| DB | PostgreSQL 18(alpine), Redis 8.8(alpine) |
| Infra | Docker / Docker Compose |

버전은 미확정. 확정되는 대로 이 표와 각 팀 폴더 CLAUDE.md를 함께 갱신한다.
(Spring Boot는 start.spring.io가 3.x 라인 제공을 중단해 4.1.0으로 세팅됨.)
