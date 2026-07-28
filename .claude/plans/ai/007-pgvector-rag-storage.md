# pgvector RAG 저장소 (AI 전용 컨테이너)

`S15P11A108-375` [INFRA | AI] AI 게이트웨이 구조 검증 (에픽 `-27`)

## 배경/목표

`AI/app/chat/faq.py`의 반복질문 RAG 검색은 지금 `MockRetriever`(목업 FAQ JSON + bigram 해싱)뿐이고,
`PgvectorRetriever`는 `NotImplementedError` 스텁이다. 실 지식베이스로 전환하기 위해 pgvector
기반 저장소를 붙인다. 이 작업은 "라이브 채팅 RAG 완성"(pgvector 저장소 + STT 워커 +
LangChain/LFM2.5-230M 생성기) 3단계 중 1단계이며, 나머지 두 단계는 별도 티켓·브랜치로 진행한다.

**BE 소유 공유 Postgres는 건드리지 않는다.** `postgres:18-alpine`엔 pgvector 확장이 없어
이미지 교체나 소스 빌드가 필요한데, 둘 다 BE 운영 DB에 손대는 일이라 위험도가 높다고 판단해
**AI 전용 별도 Postgres+pgvector 컨테이너**를 추가한다. 기존 공유 스키마(`schema.sql`)는
전혀 건드리지 않고, 이 새 DB의 스키마는 AI가 전적으로 소유·관리한다.

임베딩 모델은 Kanana 계열(생성·임베딩 둘 다)을 배제하고 `nlpai-lab/KURE-v1`을 쓴다.

## 작업 내용

1. `docker-compose.yml`에 신규 서비스 추가(`postgres-vector`, `image: pgvector/pgvector:pg18`,
   전용 볼륨, `mem_limit` 지정). 기존 `postgres` 서비스는 한 줄도 안 바뀐다.
2. AI 게이트웨이 의존성에 `sqlalchemy`, `psycopg[binary]`, `pgvector`(파이썬 클라이언트) 추가.
3. `app/core/config.py`에 이 전용 DB 접속 설정 추가(기존 `db_*`는 BE 공유 DB용 자리라 이름을
   분리해 혼동을 막는다). `app/core/db.py`에 엔진/세션 팩토리 신설.
4. 스키마는 AI가 직접 관리: `CREATE EXTENSION vector`, `chat_rag_document` 테이블(id, live_id,
   source_type[`stt`|`seed`], content, embedding vector(N), created_at). 차원 N은 KURE-v1을
   실제로 로드해서 출력 차원을 확인한 뒤 확정한다.
5. **범위 축소(구현 중 재설계)**: 처음엔 이 단계에 `PgvectorRetriever.search()`(KURE-v1 질의
   임베딩 + `ORDER BY embedding <=> :q` 벡터 검색)까지 포함하려 했으나, 게이트웨이(`ai`
   컨테이너)엔 torch가 없고(`mem_limit: 1g`) 워커는 DB에 직접 접속 못 하는 제약이 부딪혀서
   재검토했다. 방송 하나당 문서 수가 많지 않다는 점(수십~수백 건)을 감안해, **검색·그라운딩
   판단·생성을 전부 3단계 `chat_rag` 워커 job 하나로 합치기**로 했다 — 워커가 `live_id`로 받은
   후보 문서 텍스트 + 질문을 그 자리에서 임베딩·랭킹·생성까지 처리한다. 그래서 게이트웨이는
   KURE-v1을 전혀 몰라도 되고, 이 단계는 **저장 인프라(컨테이너+스키마+DAO)만** 만들면 된다.
   `registry.py` 임베더 스왑, `PgvectorRetriever`, KURE-v1 지연 로딩은 전부 3단계로 이동.
6. 단순 DAO(가칭 `app/chat/rag_store.py`): `save_document(live_id, source_type, content,
   embedding=None)`(2단계 STT 워커가 KURE-v1로 미리 계산한 벡터를 채워 저장 — 지금 당장 검색엔
   안 쓰지만 나중 대규모 검색을 위해 미리 저장해 둔다), `fetch_documents(live_id, limit) ->
   list[...]`(3단계 워커에 넘길 후보 텍스트를 `live_id`로 가져오기만 함, 벡터 연산 없음).
7. BE에 컨테이너 추가 승인은 이미 구두로 받음. 요청 문서 대신 `AI/docs/chat-rag-storage.md`에
   "왜 별도 컨테이너인지 / 왜 지금 벡터 검색을 안 쓰는지" 설계 근거를 기록(참조 문서 원칙,
   `AI/docs/README.md`에 등록).

## 구현 목록

- [x] `docker-compose.yml`에 `postgres-vector` 서비스 추가
- [x] AI 의존성 추가(`sqlalchemy==2.0.44`, `psycopg[binary]==3.2.4`, `pgvector==0.5.0`) —
      torch/sentence-transformers는 게이트웨이에 불필요(임베딩 계산은 전부 워커 쪽, 3단계에서 다룸)
- [x] `app/core/config.py` — 전용 DB 접속 설정(`vector_db_*`)
- [x] `app/core/db.py` — 엔진/세션 팩토리
- [x] 스키마 초기화(`rag_store.init_schema()`) — `CREATE EXTENSION vector` + `chat_rag_document`
- [x] `app/chat/rag_store.py` — `save_document()` / `fetch_documents()` DAO
- [x] `AI/docs/chat-rag-storage.md` 작성 + `AI/docs/README.md` 등록
- [x] 검증: `cd AI && ruff check . && black --check . && pytest -q` — 440 passed, 2 skipped
- [x] 검증: 로컬 `docker compose up -d postgres-vector` 띄워서 DAO 왕복(한글 콘텐츠 저장→조회,
      `live_id` 스코핑) 통합 테스트 완료, 컨테이너는 다시 stop해 둠

## 미결정 사항

- `chat_rag_document`의 정확한 임베딩 차원 — 구현 중 KURE-v1 로드해서 확인.
- `postgres-vector` 컨테이너 리소스 제한값 — BE 요청 문서 작성 시 EC2 여유 용량 확인 후 산정.
- 클러스터링/그라운딩 임계치 재스윕 여부 — mock_bigram 대비 KURE-v1 실측 필요.
- **(3단계로 이관) 답변 캐시**: 워커 호출 전에 "이미 비슷한 질문에 답한 적 있는지" 캐시로
  걸러서 워커 호출을 줄이자는 아이디어. `AnswerStore.list_for_live(live_id)`가 이미 있어 새
  자료구조 없이 `FaqAnswer`에 임베딩 필드만 추가하면 재사용 가능. 게이트웨이 쪽 임베딩 계산은
  ONNX Runtime(torch 불필요)으로. **반드시 같은 `live_id` 안에서만 비교한다** — 방송마다
  정답이 달라질 수 있어(재고·정책 등) 방송을 넘나드는 캐시 재사용은 하지 않는다. 상세 설계는
  3단계 계획 문서에서.

## 관련 자료

- 전체 설계: `.claude/plans/glowing-wandering-hejlsberg.md`(승인된 3단계 계획 — 세션 임시 경로,
  구현 완료 후 이 문서가 단일 근거가 된다)
- 선례: `.claude/plans/ai/005-quality-inspection-prototype.md`, `.claude/plans/ai/003-live-comment-moderation-prototype.md`
