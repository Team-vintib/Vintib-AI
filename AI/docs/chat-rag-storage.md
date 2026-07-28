# 라이브 채팅 RAG 저장소 (`postgres-vector`)

`S15P11A108-375` [INFRA | AI] AI 게이트웨이 구조 검증 (에픽 `-27`)

라이브 채팅 반복질문 RAG 기능(`LIVE-007` STT 연동 포함)을 위한 저장소를 왜 이렇게 구성했는지
기록한다. 구현 체크리스트는 `.claude/plans/ai/007-pgvector-rag-storage.md`.

## 왜 별도 Postgres 컨테이너인가

STT로 전사된 방송 발언을 저장할 곳이 필요했다. 기존 공유 `postgres`(BE 소유, `schema.sql`)에
넣는 방법도 검토했는데, 순정 `postgres:18-alpine`엔 pgvector 확장이 없어서 이미지를 바꾸거나
소스 빌드가 필요했다 — 둘 다 BE 운영 DB에 손대는 일이라 위험도가 높다고 판단했다. 그래서
**AI 전용 별도 `postgres-vector` 컨테이너**(`pgvector/pgvector:pg18`)를 추가했다. 기존
`postgres` 서비스·스키마(`BE/docs/db/schema.sql`)는 전혀 건드리지 않고, 이 새 DB의 스키마는
AI가 전적으로 소유·관리한다(`app/chat/rag_store.py`).

호스트 포트는 노출하지 않는다(`docker-compose.yml` 상단 원칙과 동일) — 로컬 개발용 포트
매핑(`5433`)은 `docker-compose.override.yml`에만 있다.

## 왜 지금 당장은 벡터 검색을 안 쓰는가

`chat_rag_document` 테이블에 `embedding vector(1024)` 컬럼이 있지만, 지금 구현(`rag_store.py`)은
`live_id`로 후보 문서를 가져오기만 하고 pgvector의 `<=>` 연산자로 검색하지 않는다. 이유:

- 방송 하나당 문서 수가 많지 않다(수십~수백 건 수준) — pgvector의 ANN 검색이 주는 이점이
  이 규모에서는 크지 않다.
- 임베딩 계산(KURE-v1, torch 필요)은 게이트웨이(`ai` 컨테이너, torch 없음·`mem_limit: 1g`)가
  아니라 3단계 `chat_rag` 워커가 담당한다. 워커는 `live_id`로 받은 후보 텍스트 + 질문을 그
  자리에서 임베딩·랭킹·그라운딩 판단·생성까지 한 번에 처리한다(왕복 1회로 단순화).

`embedding` 컬럼은 그래도 채워 둔다(2단계 STT 워커가 저장 시점에 미리 계산) — 나중에 여러
방송을 넘나드는 대규모 검색이 필요해지면 백필 없이 바로 pgvector 검색으로 전환할 수 있게
하기 위해서다.

## 구성

```yaml
postgres-vector:
  image: pgvector/pgvector:pg18
  container_name: vintib-postgres-vector
  environment:
    POSTGRES_DB: ${VECTOR_DB_NAME:-vintib_rag}
    POSTGRES_USER: ${VECTOR_DB_USERNAME:-postgres}
    POSTGRES_PASSWORD: ${VECTOR_DB_PASSWORD:-postgres}
  volumes:
    - postgres-vector-data:/var/lib/postgresql
  mem_limit: 512m
```

`ai` 서비스에 `VECTOR_DB_*` 환경변수와 `depends_on: postgres-vector(healthy)`가 붙어 있다.
`.env.example`에 기본값이 있다 — 운영 EC2 `.env`(GitLab CI/CD Variables)에도 같은 키를
추가해야 한다.

로컬 검증: `docker compose up -d postgres-vector`로 기동 후 `rag_store.init_schema()` →
`save_document()`/`fetch_documents()` 왕복 테스트 완료(한글 콘텐츠 저장·조회, `live_id`
스코핑 정상 확인).

## 향후 단계와의 관계

- **2단계(STT 워커)**: 전사 텍스트를 `save_document(source_type="stt", embedding=...)`로 저장.
- **3단계(`chat_rag` 워커)**: `fetch_documents(live_id)`로 후보를 받아 임베딩·랭킹·생성.
  **답변은 반드시 같은 `live_id` 안에서만 참고한다** — 방송마다 재고·정책이 달라 다른 방송의
  답변을 재사용하면 안 된다. 워커 호출 전 캐시(같은 `live_id` 안에서 이미 답변한 유사 질문
  재사용)도 이 단계에서 함께 설계한다.
