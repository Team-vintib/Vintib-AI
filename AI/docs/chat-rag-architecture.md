# 라이브 채팅 RAG — 전체 플로우와 설계 근거

`S15P11A108-375`(pgvector 저장소), `-443`(STT 워커), `-444`(chat_rag 생성기)를 거쳐 완성된
반복질문 자동 답변 기능의 전체 그림과, 그 과정에서 내린 설계 결정들을 왜 그렇게 했는지
한곳에 모았다. 각 결정의 세부 근거는 개별 문서(`chat-rag-storage.md`,
`worker-url-transport.md`, `api-reference.md`)에 있고, 이 문서는 그것들을 하나의 흐름으로
엮는다.

## 전체 플로우

```
[OpenVidu] 방송 녹화 → MinIO/오브젝트 스토리지에 저장
    │
    ▼ (BE가 녹화 완료 시 호출)
POST /ai/stt {audio_url, live_id}
    │
    ▼ Redis 큐(job만, 바이트 없음)
[워커] faster-whisper 전사 + 같은 프로세스에서 KURE-v1 임베딩 계산
    │
    ▼ 결과 제출(텍스트 + 벡터)
[게이트웨이] 계산 없이 그대로 저장 → chat_rag_document(pgvector, live_id 스코프)

──────────────────────────────────────────────────────────────

[FE/BE] 채팅 메시지 → POST /chat/moderate  (동기, p95 300ms 목표)
    │
    ▼ 스팸 → 욕설 → 질문 게이트 (전부 가벼운 규칙 기반)
반복질문 감지(cluster.size >= 2)
    │
    ▼ 응답은 티켓만 즉시 반환, 아래는 BackgroundTasks로 응답 이후 실행
이미 답변됨? / 이미 워커에 보낸 상태(pending)? → 예면 스킵
    │
    ▼ 아니오
rag_store.fetch_documents(live_id, limit=200)  ── 벡터 연산 없는 plain SQL
    │
    ▼ 후보가 없으면 조용히 스킵(침묵)
enqueue_job("chat_rag", {ticket, live_id, question, docs})
    │
    ▼ Redis 큐
[워커] KURE-v1로 질문·후보 임베딩 → 코사인 랭킹 → 임계치 미만이면 무응답
    │                              → 임계치 이상이면 LangChain + LFM2.5-230M 생성
    ▼ 결과 제출(grounded, answer, sources)
[게이트웨이] FaqAnswer 조립 → AnswerStore 저장

[FE/BE] GET /chat/answers/{ticket} 로 폴링 조회
```

## 왜 이렇게 짰나 — 결정 하나씩

### 1. Redis는 절대 검색(retriever)에 안 쓴다 — 순수 job 큐

Redis가 하는 일은 `queue:{feature}`(대기열)와 `result:{job_id}`(상태) 두 가지뿐이다. RAG
근거 문서 저장·검색은 전부 pgvector(`chat_rag_document`) 쪽 일이고, 실제 랭킹은 워커 안에서
일어난다(아래 3번). Redis에 벡터나 대량 바이너리를 올리지 않는 건 원래부터 있던 원칙이고
(`infra-architecture.md` §3.3 — "이미지 등 큰 바이너리는 절대 담지 않는다"), 이번 기능도
그대로 따랐다.

### 2. 게이트웨이는 임베딩을 계산하지 않는다 — torch가 없어서

EC2의 `ai` 컨테이너는 `mem_limit: 1g`이고 torch가 설치돼 있지 않다(`quality_check`가 원래
동기였다가 이 제약 때문에 워커로 옮겨간 선례가 있음, `.claude/requests/be/001-*.md`). 그래서
KURE-v1 임베딩 계산은 **STT 워커**(전사 시점, Whisper 때문에 이미 torch를 들고 있음)와
**chat_rag 워커**(생성 시점)에서만 일어나고, 게이트웨이는 텍스트/벡터를 그대로 통과시키기만
한다. 자세한 이유는 `AI/docs/chat-rag-storage.md` 참고.

### 3. pgvector의 벡터 검색(`<=>`)을 안 쓴다 — 워커가 인메모리로 랭킹

원래 계획은 `PgvectorRetriever`가 `ORDER BY embedding <=> :q`로 직접 검색하는 것이었다. 구현
중 재검토했다: 방송 하나당 문서 수가 수십~수백 건 수준이라 pgvector의 ANN 검색이 주는 이점이
크지 않고, 워커가 DB에 직접 못 붙는 제약(인바운드 불가·Redis와 같은 이유)까지 겹쳐서 "질의
임베딩 job" + "생성 job" 2회 왕복이 필요해지는 문제가 있었다. 그래서 **게이트웨이가 plain
SQL로 `live_id` 기준 후보를 통째로 가져와 job payload에 실어 보내고, 워커가 그 자리에서
임베딩·랭킹·그라운딩 판단·생성을 전부 처리**하는 구조로 바꿨다 — 왕복 1회로 끝난다.

이 결정 때문에 후보 개수 제한(`registry.CHAT_RAG_CANDIDATE_LIMIT`)을 넉넉하게(200) 잡아야
한다는 게 실측으로 드러났다 — 자세한 사고 경위는 `chat-rag-verification-results.md` 참고.

### 4. `Retriever`/`AnswerGenerator`는 평가 전용으로만 남겼다

`app/chat/faq.py`의 `Retriever`(`MockRetriever`)는 여전히 존재하지만, 프로덕션
(`ChatModerationService`)은 더 이상 이걸 안 쓴다 — `app/chat/evaluation.py`와
`test/chat/test_chat_evaluation.py`(`S15P11A108-196`, CI 회귀 게이트)가 여전히 이 인터페이스로
클러스터링·그라운딩 정확도를 측정하기 때문에 남겨뒀다. 반대로 `AnswerGenerator`
(`TemplateAnswerGenerator`, `KananaAnswerGenerator`)는 평가 파이프라인도 안 쓰는 걸 확인하고
완전히 삭제했다 — 생성 품질은 이 평가 도구가 애초에 측정하지 않는 영역이라서다.

### 5. 워커 호출 전 중복 방지 — `_pending` 가드

동기 시절엔 없던 문제다. job이 큐에서 처리되기까지 poll 주기(수 초)만큼 지연이 생기는데,
그사이 같은 클러스터에 메시지가 더 들어오면 `moderate()`가 매번 `cluster.size >=
min_cluster_size` 조건을 다시 통과시킨다. `ChatModerationService._pending`(프로세스 인메모리
집합)으로 "이미 워커에 보낸 티켓"을 추적해 중복 job을 막는다. `InMemoryAnswerStore`와 같은
한계(다중 게이트웨이 프로세스에선 안 맞음, `S15P11A108-188`)를 그대로 안고 있다.

### 6. 채팅 메시지 자체는 지식베이스에 안 넣는다

pgvector가 검색하는 건 STT 전사문(판매자 발언)뿐이다. 반복질문 판정(`QuestionClusterer`)이
쓰는 클러스터는 방송 하나가 진행되는 동안만 메모리에 있다가 버려지는 별개의 휘발성 데이터고,
채팅 메시지나 AI가 생성한 답변을 다시 지식베이스에 넣는 것도 범위 밖이다(자기 강화로 인한
오답 누적 위험 — 필요해지면 별도 결정).

## 관련 문서

- `chat-rag-storage.md` — 왜 별도 `postgres-vector` 컨테이너인지, BE 공유 DB를 안 건드리는 이유
- `worker-url-transport.md` — 워커 입출력이 왜 전부 URL인지(오디오도 이미지와 같은 이유)
- `api-reference.md` — BE↔AI 엔드포인트 계약
- `chat-rag-verification-results.md` — 실 모델(KURE-v1, LFM2.5-230M, faster-whisper)로 검증한
  결과와 그 과정에서 발견한 버그
- 계획 문서: `.claude/plans/ai/007-pgvector-rag-storage.md`,
  `.claude/plans/ai/008-stt-worker.md`, `.claude/plans/ai/009-chat-rag-generator.md`
