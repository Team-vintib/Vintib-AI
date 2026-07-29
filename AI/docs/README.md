# AI 문서

AI 파트의 참조 문서 모음. 실행 방법·디렉터리 구조는 `../README.md`, 에이전트 작업 규율은
`../CLAUDE.md`를 본다.

## 무엇부터 읽나

| 목적 | 문서 |
| --- | --- |
| EC2에 올려서 **직접 테스트**하고 싶다 | [`testing-guide.md`](./testing-guide.md) — SSH 접속, 배포 절차, API 확인 체크리스트, 트러블슈팅 |
| 게이트웨이·워커·큐가 **어떻게 엮여 있는지** 알고 싶다 | [`infra-architecture.md`](./infra-architecture.md) — 전체 구조, 컴포넌트별 상세, 보안 설계, Job/Result 스키마 |
| 워커 입출력이 **왜 전부 URL인지**(바이트를 직접 안 주고받는 이유) 알고 싶다 | [`worker-url-transport.md`](./worker-url-transport.md) — 워커 인바운드 제약, Redis 바이너리 금지 원칙 |
| 가상 시착의 **다음 개선 방향**을 알고 싶다 | [`tryon-advancement-strategy.md`](./tryon-advancement-strategy.md) — 현재 한계, 적용 가능 기법, 로드맵 (`S15P11A108-195`) |
| 라이브 댓글 관리의 **다음 개선 방향**을 알고 싶다 | [`chat-advancement-strategy.md`](./chat-advancement-strategy.md) — 실측 기반 한계점, 기법 우선순위, 스프린트 계획 (`S15P11A108-197`) |
| 브랜드 유사도 그래프의 **다음 개선 방향**을 알고 싶다 | [`recommendation-advancement-strategy.md`](./recommendation-advancement-strategy.md) — 크롤링 텍스트 임베딩, 다면 유사도, FE 그래프 전달 설계 (`S15P11A108-199`) |
| BE가 **AI 게이트웨이 API를 호출**해야 한다(`AiClient.java` 등) | [`api-reference.md`](./api-reference.md) — 엔드포인트 목록, 기능별 job payload/result 필드, `APIs.md`(FE↔BE)와의 관계 (`S15P11A108-371`) |
| 결과/입력 이미지 URL의 **접근 제어**를 검토해야 한다 | [`results-access-control.md`](./results-access-control.md) — 서명된 URL / JWT 인증 / 보관기간 정책 비교, 미결정 상태 (`S15P11A108-371`) |
| 라이브 채팅 RAG **저장소 설계 근거**가 궁금하다 | [`chat-rag-storage.md`](./chat-rag-storage.md) — AI 전용 `postgres-vector` 컨테이너를 왜 별도로 뒀는지, 지금 벡터 검색을 안 쓰는 이유 (`S15P11A108-375`) |
| 라이브 채팅 RAG **저장소 설계 근거**가 궁금하다 | [`chat-rag-storage.md`](./chat-rag-storage.md) — AI 전용 `postgres-vector` 컨테이너를 왜 별도로 뒀는지, 지금 벡터 검색을 안 쓰는 이유 (`S15P11A108-375`) |
| 라이브 채팅 RAG **전체 플로우와 아키텍처 결정 이유**가 궁금하다 | [`chat-rag-architecture.md`](./chat-rag-architecture.md) — STT→저장→판정→생성 전체 흐름, Redis를 검색에 안 쓰는 이유, 벡터 검색을 워커가 인메모리로 하는 이유 (`S15P11A108-444`) |
| 라이브 채팅 RAG를 **실 모델로 검증한 결과**가 궁금하다 | [`chat-rag-verification-results.md`](./chat-rag-verification-results.md) — 판정 정확도 회귀 확인, STT/chat_rag 실 모델 E2E, 발견한 버그와 수정 내역 (`S15P11A108-443`, `-444`) |
| 가격 책정이 **왜 워커 큐가 아닌지** 알고 싶다 | `infra-architecture.md` §6 — 자원이 아웃바운드 외부 API면 인바운드 제약이 없어 컨테이너 내 백그라운드로 간다. 설계 전문은 `.claude/plans/ai/CH003-pricing-service-prototype.md` (`S15P11A108-338`) |

> ⚠️ `infra-architecture.md`의 "7. 저장소 디렉토리 구조" 절은 `app/` 패키지 재구성 이전 상태로
> 남아 있다. 현재 구조는 `../README.md`의 디렉터리 구조 절을 본다.

## 여기에 두는 것 / 두지 않는 것

| | 성격 | 위치 |
| --- | --- | --- |
| **참조 지식** | 런북, 아키텍처 설계, 고도화 전략 — 필요할 때 찾아 읽는다 | `AI/docs/` (이 폴더) |
| **구현 계획** | 승인 게이트를 거치는 사전 설계 — "이대로 구현한다" | 루트 `.claude/plans/ai/` |
| **생성물** | 평가 리포트 등 스크립트 산출물 | `AI/app/<도메인>/artifacts/` (gitignore) |

구현 계획을 `.claude/plans/ai/`에 두는 건 루트 `CLAUDE.md`의 공통 규율이다. 소스 파일들이
`설계: .claude/plans/ai/00N-*.md` 형태로 직접 인용하고 있으므로 그 경로를 바꾸지 않는다.

## 파일 규칙

- 파일명은 kebab-case(`chat-advancement-strategy.md`).
- 문서를 새로 추가하면 위 "무엇부터 읽나" 표에 한 줄 등록한다. 등록하지 않으면 아무도(사람도
  에이전트도) 그 문서를 찾지 못한다 — 이 폴더가 생긴 이유가 그것이다.
- 티켓 산출물인 문서는 제목 아래에 Jira 키를 적어 둔다.
