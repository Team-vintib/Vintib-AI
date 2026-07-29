# LangChain 생성기 + chat_rag 잡 큐 전환

`S15P11A108-444` [CHAT-002] LANG CHAIN 생성 검증 (에픽 `-208`)

## 배경/목표

반복질문 답변 생성을 완성하는 마지막 단계. 1단계(pgvector 저장소)까지는 완료됐고, 검색·
그라운딩 판단·생성을 **전부 `chat_rag` 워커 job 하나로 합치기**로 이미 결정했다(1단계 구현
중 재검토, `.claude/plans/glowing-wandering-hejlsberg.md` 단계 3). 이번에 그 결정을 실제로
구현한다.

**중요한 결정(착수 전 확인, 조사 중 정정됨)**: 처음엔 `Retriever`/`AnswerGenerator` 추상화
전체를 지우려 했으나, 조사해보니 `Retriever`(`MockRetriever`, `build_retriever`)와
`registry.EMBEDDER_BACKENDS`/`embedder_config()`는 **살아있는 CI 회귀 게이트**
(`AI/test/chat/test_chat_evaluation.py`, `S15P11A108-196`)와 오프라인 평가 리포트 도구
(`app/chat/evaluation.py`, `app/chat/pipeline/evaluate.py`)가 실제로 쓰고 있었다 — 클러스터링
정확도·근거 인용 정확도·환각 0건을 매번 검증하는 데 쓰인다. 반면 `AnswerGenerator`
(`TemplateAnswerGenerator`, `KananaAnswerGenerator`)는 평가 파이프라인이 전혀 안 쓴다
(`evaluate_faq()`는 검색·그라운딩까지만 평가하고 생성 품질은 안 본다).

그래서 최종 범위는:
- **삭제**: `AnswerGenerator`(ABC), `TemplateAnswerGenerator`, `KananaAnswerGenerator`,
  `build_generator`, `GENERATOR_BACKENDS`, `ACTIVE_GENERATOR`, `PgvectorRetriever`(스텁 —
  평가 파이프라인도 안 쓰고 프로덕션에서도 이제 안 씀), `RETRIEVER_BACKENDS`의 `"pgvector"`
  항목.
- **유지(평가 전용으로 재규정)**: `Retriever`(ABC), `RetrievedDoc`, `MockRetriever`,
  `build_retriever`, `KnowledgeBaseNotReady`, `RETRIEVER_BACKENDS`(`"mock"`만 남김),
  `EMBEDDER_BACKENDS`/`ACTIVE_EMBEDDER`/`embedder_config()`. `ChatModerationService`(실서비스)만
  이걸 더 이상 안 쓰게 바꾸고, `evaluation.py`/`pipeline/evaluate.py`/`test_chat_evaluation.py`는
  그대로 둔다.
- `EMBEDDER_BACKENDS`에서 `kanana_nano` 항목은 제거(Kanana 임베딩도 이미 배제하기로 함,
  `mock_bigram`/`kure_v1`만 후보로 남김).

## 작업 내용

### 1. 삭제 (프로덕션에서만 안 쓰는 것 — 평가 파이프라인 의존성은 위에서 확인 완료)

- `app/chat/faq.py`: `AnswerGenerator`(ABC), `TemplateAnswerGenerator`, `KananaAnswerGenerator`,
  `build_generator`, `PgvectorRetriever` 제거. `Retriever`/`RetrievedDoc`/`MockRetriever`/
  `build_retriever`/`KnowledgeBaseNotReady`/`QuestionDetector`/`Cluster`/`QuestionClusterer`/
  `embed`/`cosine`는 유지(평가 파이프라인이 씀).
- `app/chat/registry.py`: `GENERATOR_BACKENDS`, `ACTIVE_GENERATOR` 제거. `RETRIEVER_BACKENDS`는
  `"pgvector"` 항목만 제거(`"mock"`만 남김). `EMBEDDER_BACKENDS`에서 `kanana_nano` 제거.
- `mock_faq.json`/`MockRetriever` 관련 테스트는 그대로 둔다 — 여전히 평가 대상이다.

### 2. `worker/chat_rag_worker_example.py` 신설

- LangChain으로 `LiquidAI/LFM2.5-230M` 감싼 파이프라인 지연 로딩(instruction-tuned, ChatML
  포맷, 32k 컨텍스트, 한국어 지원). `STT_BACKEND=mock`과 같은 원칙으로
  `CHAT_RAG_BACKEND=mock`(기본값, GPU 불필요) / `lfm2_langchain`(실제 모델) 스왑 지원.
- job payload: `{"ticket": ..., "live_id": ..., "question": ..., "cluster_size": ...,
  "docs": [{"id": ..., "content": ...}, ...]}` — `docs`는 게이트웨이가
  `rag_store.fetch_documents(live_id)`로 미리 가져와 그대로 실어 보낸 것(벡터 연산 없음).
- `run_inference()`: KURE-v1로 질문·후보 문서 임베딩 → 코사인 랭킹 → 최고 점수가
  그라운딩 임계치 미만이면 `{"grounded": false}` 반환(생성 안 함) → 임계치 이상이면
  LangChain+LFM2.5-230M으로 답변 생성 → `{"grounded": true, "answer": ..., "grounding_score":
  ..., "sources": [{"doc_id": ..., "score": ...}, ...]}` 반환.
- mock 백엔드: 결정적 임베딩(bigram 해싱 재사용 가능) + 최상위 문서 내용을 그대로 반환(환각
  없음, 기존 `TemplateAnswerGenerator`와 같은 안전한 기본값 역할).

### 3. `AI/app/gateway/schemas.py` — `FeatureType`에 `"chat_rag"`는 이미 있음(변경 불필요, 지금까지 미사용이었을 뿐).

### 4. `app/chat/service.py` 재작성

- `ChatModerationService.__init__`에서 `retriever`/`generator`/`grounding_threshold` 파라미터
  제거(그라운딩 판단이 워커로 옮겨가 게이트웨이는 그 임계치를 모른다). 새로 `self._pending:
  set[str]`(진행 중인 티켓 추적, 아래 참고) 추가.
- `generate_answer(cluster)` → `_try_enqueue_chat_rag(cluster)`로 재작성:
  1. 이미 답변된 티켓이면 스킵(기존 로직 유지)
  2. **신규**: `cluster.ticket`이 이미 `self._pending`에 있으면 스킵 — 워커 처리에 poll 주기
     (수 초)만큼 지연이 생기므로, 그사이 같은 클러스터에 메시지가 더 들어오면
     `moderate()`가 매번 `cluster.size >= min_cluster_size` 조건을 다시 통과해 **중복 job이
     쌓일 수 있다.** 이 가드가 없으면 동기 시절엔 없던 문제가 새로 생긴다.
  3. `rag_store.fetch_documents(cluster.live_id, limit=registry.RETRIEVE_TOP_K)`로 후보 텍스트
     확보 → 없으면 조용히 스킵.
  4. `self._pending.add(cluster.ticket)` → `enqueue_job("chat_rag", {...})` 호출하고 끝.
- `save_generated_answer(answer: FaqAnswer)` 신설: `self._answers.save(answer)` +
  `self._pending.discard(answer.ticket)`.
- `mark_chat_rag_ungrounded(ticket: str)` 신설: 근거 부족으로 워커가 포기했을 때
  `self._pending.discard(ticket)`만 한다(무응답 유지).
- `get_chat_service()` 조립부에서 `retriever`/`generator`/`grounding_threshold` 인자 제거.

### 5. `AI/app/gateway/router.py` — `chat_rag` 결과 적재

- `submit_result()`에 `job.type == "chat_rag"` 분기 추가: `job.payload`(원래 enqueue할 때 실은
  ticket/live_id/question/cluster_size)와 `result`(워커가 돌려준 grounded/answer/
  grounding_score/sources)를 합쳐 `FaqAnswer`를 조립. `result["grounded"]`가 true면
  `get_chat_service().save_generated_answer(answer)`, false면
  `get_chat_service().mark_chat_rag_ungrounded(job.payload["ticket"])`.

### 6. 답변 캐시는 이번 티켓 범위 밖

1단계 논의 때 나온 "워커 호출 전 캐시(ONNX 임베더로 같은 `live_id` 안 유사 질문 재사용)"는
티켓 제목(`LANG CHAIN 생성 검증`)의 핵심이 아니라서 이번엔 안 만든다 — 핵심 생성 파이프라인이
먼저 검증돼야 캐시도 의미가 있다. 별도 후속 작업으로 남긴다.

## 구현 목록

- [x] `app/chat/faq.py` — `AnswerGenerator`/`TemplateAnswerGenerator`/`KananaAnswerGenerator`/
      `build_generator`/`PgvectorRetriever` 삭제. `Retriever`/`MockRetriever`/`build_retriever`는
      평가 파이프라인용으로 유지.
- [x] `app/chat/registry.py` — `GENERATOR_BACKENDS`/`ACTIVE_GENERATOR` 삭제,
      `RETRIEVER_BACKENDS`는 `"mock"`만 남김, `EMBEDDER_BACKENDS`에서 `kanana_nano` 제거.
- [x] `worker/chat_rag_worker_example.py` 신설 — `CHAT_RAG_BACKEND=mock`(기본값)/
      `lfm2_langchain` 스왑 지원.
- [x] `app/chat/service.py` — `generate_answer` → `_try_enqueue_chat_rag` 재작성,
      `self._pending` 가드 추가, `save_generated_answer`/`mark_chat_rag_ungrounded` 신설,
      생성자에서 retriever/generator/grounding_threshold 제거. `_ensure_knowledge_base()`/
      `KnowledgeBaseNotReady` 관련 503 경로도 함께 제거(더 이상 의미 없음 — `app/chat/router.py`도
      갱신).
- [x] `AI/app/gateway/router.py` — `submit_result()`에 `chat_rag` 결과 적재 분기(
      `_ingest_chat_rag_result`) 추가. 순환 import 방지를 위해 `app.chat.service`는 함수 안에서
      지연 import.
- [x] `AI/test/chat/test_chat_faq.py` — Retriever/Generator 관련 테스트 중 Generator만 삭제,
      Retriever/평가 관련은 유지.
- [x] `AI/test/chat/test_chat_service.py` — `_FakeRedis`(`test/quality/test_quality_router.py`와
      동일 패턴)로 `gateway_router.r`을 갈아끼우고, 워커 응답은
      `gateway_router._ingest_chat_rag_result()`를 직접 호출해 흉내 냄. 중복 job 방지(`_pending`)
      테스트, 근거 문서 없을 때 스킵 테스트 신규 추가.
- [x] `worker/README.md` 갱신
- [x] 검증: `cd AI && ruff check . && black --check . && pytest -q` — 437 passed, 2 skipped
      (평가 파이프라인 CI 게이트 포함 전부 통과)
- [x] 검증: `chat_rag` 워커를 `CHAT_RAG_BACKEND=mock`으로 단독 호출 — 근거 없음/있음(동일 텍스트로
      코사인 1.0 강제) 양쪽 경로 확인
- [x] 검증: `test_chat_service.py`의 job 큐 왕복 테스트로 확인(진짜 Redis/워커는 안 띄움 — fake
      Redis + 직접 호출로 충분히 검증됨)

## 구현 중 드러난 이슈 (알아두면 좋음)

- **`get_chat_service()` 싱글턴 의존**: `_ingest_chat_rag_result()`는 `Depends()` 주입이 아니라
  `get_chat_service()`를 직접 호출한다 — 프로덕션(단일 프로세스)에선 `@lru_cache` 덕에 항상
  같은 인스턴스라 문제없지만, 테스트처럼 매번 새 `ChatModerationService`를 만드는 상황에서는
  `get_chat_service`를 몽키패치해야 워커 결과가 같은 곳에 쌓인다(`test_chat_service.py`의
  `_stub_singleton` 참고). 다중 게이트웨이 프로세스 환경에서도 이 싱글턴 가정이 깨진다 —
  `InMemoryAnswerStore`/`_pending`과 같은 한계선상(`S15P11A108-188`).

## 미결정 사항

- 답변 캐시(같은 `live_id` 안 유사 질문 재사용, ONNX 임베더) — 별도 후속 작업.
- 클러스터링/그라운딩 임계치는 여전히 mock_bigram 기준 — 실측 재스윕은 각 임베더가 실제
  검증된 뒤로 계속 미룬다.
- `worker/chat_rag_worker_example.py`의 `GROUNDING_THRESHOLD`(0.35, 정책 제안치)는 KURE-v1
  실측 후 재조정 필요.

## 관련 자료

- 전체 설계: `.claude/plans/glowing-wandering-hejlsberg.md` (단계 3)
- 선례: `.claude/plans/ai/007-pgvector-rag-storage.md`, `.claude/plans/ai/008-stt-worker.md`
- 원본 설계: `.claude/plans/ai/003-live-comment-moderation-prototype.md`(지금 삭제할 구조가
  원래 어떤 의도로 만들어졌는지 참고)
