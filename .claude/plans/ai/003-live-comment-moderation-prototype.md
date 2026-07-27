# [AI] 라이브 댓글 관리 서비스 (프로토타입) — 설계

> 대상 티켓: `S15P11A108-192 [CHAT-001 | AI] 라이브 댓글 관리 서비스 구현`
> (에픽 `-208 [CHAT] 채팅`, 스토리 `-91 [CHAT-001] 라이브 실시간 채팅`에서 분할).
>
> 산출 범위(이번 라운드): **목업 데이터 기반 프로토타입 구현** — ① 욕설·스팸 분류/처리는 동작하게,
> ② 반복질문 RAG는 **모듈 인터페이스만 만들고 실제 검색·생성은 비워둔다**.
>
> **독립성**: 이 스코프는 `001-brand-similarity-graph.md` / `002-personalized-recommendation-mvp.md`
> (추천 도메인)와 완전히 독립이다. 접점은 `app/shared/` 승격 여부뿐이며 이번 라운드에서는 승격하지 않는다.
>
> ⚠️ **구현 세션 주의**: 모노레포 루트 세션은 하네스 훅(`.claude/settings.json` PreToolUse)으로
> 파트 코드(BE/FE/AI) 수정이 차단된다. 이 계획의 코드 구현은 **AI 스코프 세션에서** 수행한다
> (루트 세션은 `.claude/` 문서까지만).

---

## 배경 / 목표

라이브 방송 채팅은 상품 상태를 확인하는 유일한 실시간 통로인데, ⑴ 욕설·도배가 방송 품질을 직접
훼손하고 ⑵ "얼마예요?" "M 사이즈 있나요?" 같은 **동일 질문이 반복 유입**되어 판매자가 방송에
집중하지 못한다. Jira 192는 이 둘을 AI가 처리하도록 요구한다.

현재 자산은 `AI/test/model_selection/`의 **스파이크뿐**이다 — `chat_agent.py`가 도배 탐지 → 의도 분류
게이트 → 라우팅까지 만들었지만 downstream이 전부 스텁이고, 규약상 `test/`는 프로덕션에서 import할 수
없다. 동시에 분류 모델은 미확정(벤치마크상 baseline 교체가 유력)이고 BE 실시간 채팅·FE 화면도 개발
중이라 계약이 흔들린다.

따라서 이번 라운드의 목표는 **"동작하는 완결 파이프라인을 목업으로 먼저 세우고, 흔들리는 부분(모델·
BE 계약·RAG 백엔드)을 전부 교체 가능한 경계 뒤로 밀어 넣는 것"** 이다. 모델은 레지스트리 키 하나로,
BE 계약은 `schemas.py` 한 파일로, RAG는 ABC 구현체 한 줄로 갈아끼울 수 있어야 한다.

### 확정된 결정 (사용자 승인)

| 항목 | 결정 |
| --- | --- |
| 산출 범위 | 목업 데이터 기반 프로토타입. 욕설·스팸은 동작, 반복질문 RAG는 인터페이스 + Mock 구현만 |
| BE 연동 | **동기 판정 + 비동기 답변** — `POST /chat/moderate`가 즉시 판정 반환, 반복질문 답변은 별도 조회 경로 |
| 기본 분류기 | **규칙 기반 목업이 기본값** — CI(torch 미설치)에서 그대로 동작. HF 모델은 어댑터 등록 + 지연 import |
| 차단 집행 | **AI는 판정만, BE가 집행** (근거는 아래 절) |
| BE 요청 문서 | 이번엔 **작성하지 않는다.** 구현 후 필요 항목만 이 문서 말미에 남긴다 |

---

## 판정 위임 vs 직접 집행 — 속도·안정성 판단

두 방식을 비교하고 **판정 위임**을 채택한다.

| 관점 | A. AI는 판정만 (채택) | B. AI가 BE PATCH 직접 호출 |
| --- | --- | --- |
| 왕복 | BE→AI 1 RTT. BE가 응답 받고 곧바로 브로드캐스트 여부 결정 | BE→AI 1 RTT + AI→BE 1 RTT = **2 RTT** |
| 노출 위험 | 게시 **전** 인라인 판정이라 욕설이 화면에 뜨지 않음 | 콜백 도착 전 이미 브로드캐스트됨 → **사후 숨김**(잠깐 노출) |
| 장애 격리 | AI 타임아웃 시 BE가 fail-open/fail-closed를 **스스로** 결정 | AI 장애 = 숨김 누락. BE는 상태를 모름 |
| 결합도 | AI는 BE 스키마·인증을 모름. 계약은 응답 스키마 한 곳 | AI가 BE 인증 토큰·URL·`PATCH /lives/{id}/messages/{id}` 스키마에 결합 |
| 재시도 | BE가 자기 트랜잭션 안에서 처리 | AI가 BE 장애용 재시도 큐를 따로 가져야 함 |

**결론**: 속도(1 RTT)·안정성(장애 격리, 노출 없음)·결합도 모두 A가 우세하다. AI는 `verdict` + 권고
`action`(`PASS`/`HIDE`/`BLOCK`)만 돌려주고 `chat_message.is_blocked` 갱신은 BE가 수행한다.
단, 게이트가 채팅 지연 예산 안에 들어와야 하므로 **판정 경로 p95 목표를 300ms**로 잡는다
(스파이크 노트북의 설계 목표 <300~500ms, 분류기 벤치마크 실측 mean 11.7~20.0ms로 여유 충분).

---

## 아키텍처

```
                    POST /chat/moderate  (동기, p95 300ms 목표)
BE 채팅 서버 ─────────────────────────────────▶ ChatModerationService
   ▲                                                    │
   │  verdict + action                                  ├─ 1) SpamDetector      (규칙, StateStore 뒤)
   └────────────────────────────────────────────────────┤      윈도우 rate-limit + 근접중복
                                                        ├─ 2) AbuseClassifier   (ABC)
                                                        │      RuleBased(기본) / HF어댑터(스왑)
                                                        └─ 3) QuestionDetector  (규칙 B-1)
                                                                  │ 반복질문이면
                                                                  ▼
                                                             AnswerQueue (비동기 경로)
                                                                  │
     GET /chat/lives/{live_id}/answers ◀── AnswerStore ◀── FaqAnswerer
                    (폴링/조회)                            ├─ Clusterer  (코사인 ≥ 임계치, 세션 내)
                                                          ├─ Retriever ABC        ★RAG 비워둠
                                                          │     Mock / Pgvector(스텁 -184)
                                                          └─ AnswerGenerator ABC  ★생성 비워둠
                                                                Template(기본) / Kanana(스텁)
                                                                  │
                                                       grounding score < 임계치 → 무응답
```

**교체 지점은 3곳뿐이다.**

1. **모델** — `app/chat/registry.py`의 `ACTIVE_*` 키 한 줄
2. **BE 계약** — `app/chat/schemas.py` 한 파일
3. **RAG** — `app/chat/service.py`의 `@lru_cache` 팩토리에서 구현체 한 줄

---

## 모듈 구조

`AI/CLAUDE.md`의 도메인 우선 규약대로 `app/chat/` 자체완결 패키지로 만든다.

| 파일 | 책임 |
| --- | --- |
| `app/chat/schemas.py` | 요청/응답 pydantic 모델 + `Verdict`/`ModerationAction` `str, Enum`. **BE 계약 변경 시 여기만** |
| `app/chat/router.py` | `APIRouter()` 만 정의(prefix/tags는 `main.py`). 도메인 예외 → HTTP 매핑 |
| `app/chat/service.py` | 파이프라인 오케스트레이션 + `@lru_cache` DI 팩토리(= 스왑 지점) |
| `app/chat/registry.py` | `CLASSIFIER_BACKENDS`/`RETRIEVER_BACKENDS`/`GENERATOR_BACKENDS` + `ACTIVE_*` + 임계치 상수 |
| `app/chat/spam.py` | `StateStore` ABC → `InMemoryStateStore`(기본) / `RedisStateStore`(스텁, TODO -188) + `SpamDetector` |
| `app/chat/classifier.py` | `AbuseClassifier` ABC → `RuleBasedClassifier`(기본, 우회패턴 정규화) / `HuggingFaceClassifier`(지연 import) |
| `app/chat/faq.py` | `QuestionDetector`(B-1) / `QuestionClusterer`(B-2) / `Retriever` ABC / `AnswerGenerator` ABC / `FaqAnswerer` |
| `app/chat/answers.py` | `AnswerStore` ABC → `InMemoryAnswerStore`(기본) / `RedisAnswerStore`(스텁, -188) |
| `app/chat/data/mock_faq.json` | 목업 FAQ 지식베이스 (가격·재고·배송·사이즈·교환 등) — 커밋 |
| `app/chat/data/mock_comments.json` | 목업 댓글 세트 (정상/욕설/우회표현/도배/반복질문) — 커밋 |
| `app/chat/tests/` | 순수 로직 유닛테스트 + `TestClient` API 테스트 |

**재사용할 기존 자산** (새로 만들지 않는다):

- `app/recommend/personalize/signals.py`의 `SignalProvider` ABC + `Stub`/`Mock` 구현
  → `Retriever`/`AnswerGenerator`가 같은 형태를 따른다.
- `app/recommend/personalize/service.py`의 `get_personalize_service()` `@lru_cache` 팩토리 → 스왑 지점 패턴.
- `app/recommend/personalize/catalog.py`의 `_seeded_vector()`(sha256 → `np.random.default_rng`)
  → **torch 없이 결정적 목업 임베딩**을 만들어 CI에서 클러스터링·검색 테스트가 그대로 돌게 한다.
- `app/recommend/personalize/router.py`의 예외 → HTTP 매핑(503/404/422) 방식.
- `test/model_selection/chat_agent.py`의 `SpamDetector`·`_rule_based_faq_hint` → **복사 승격**
  (`test/`를 import하지 않는다는 규약 준수. `embed_catalog.py`가 모델 ID를 재선언한 선례와 동일).

---

## API 스펙

**1) `POST /chat/moderate` — 동기 판정** (BE가 메시지 게시 전 호출)

요청:
```jsonc
{
  "live_id": 12,
  "message_id": 9931,                  // BE 채번. AI는 에코만 함
  "user_id": 305,
  "content": "이거 사이즈 M도 있나요?",
  "sent_at": "2026-07-26T12:00:00Z"    // 선택. 없으면 서버 시각
}
```

응답:
```jsonc
{
  "message_id": 9931,
  "verdict": "REPEATED_QUESTION",      // NORMAL | ABUSIVE | SPAM | REPEATED_QUESTION
  "action": "PASS",                    // PASS | HIDE | BLOCK  ← 권고. 집행은 BE
  "reason": "question_detected",
  "scores": { "abuse": 0.03, "spam": 0.00 },
  "answer_ticket": "a_12_7f3c",        // 반복질문일 때만. 아니면 null
  "latency_ms": 8.4
}
```

**2) `GET /chat/lives/{live_id}/answers` — 비동기 답변 조회** (`?since=<ISO8601>` 선택)

```jsonc
{
  "live_id": 12,
  "answers": [
    {
      "ticket": "a_12_7f3c",
      "question": "이거 사이즈 M도 있나요?",
      "cluster_size": 3,                 // 같은 질문이 몇 번 들어왔는지
      "answer": "현재 M 사이즈 재고가 있습니다.",
      "grounded": true,
      "grounding_score": 0.62,
      "sources": [{ "doc_id": "faq_size_01", "score": 0.62 }],
      "created_at": "2026-07-26T12:00:01Z"
    }
  ]
}
```

**근거 없으면 응답하지 않는다** (Jira 결과물 "근거 있는 경우에만 응답", CHAT-02/03):
`grounding_score < GROUNDING_THRESHOLD`면 답변을 **생성하지 않고 목록에 넣지도 않는다**.

**3) `GET /chat/answers/{ticket}` — 단건 조회.** 미생성/근거부족이면 404.

| 상황 | 응답 | 근거 |
| --- | --- | --- |
| 요청 필드 누락/범위 위반 | 422 | FastAPI 기본 검증 |
| 목업 지식베이스 미로딩 | 503 | `KnowledgeBaseNotReady` — `CatalogNotReady` 선례 |
| 티켓 없음 / 근거부족으로 미생성 | 404 | — |

기존 도메인과 동일하게 `{success,data,error}` 봉투로 감싸지 않는다.

---

## 판정 규칙 (프로토타입 기본값)

우선순위대로 단락 평가하고, 하나라도 걸리면 즉시 반환한다.

| 순서 | 판정 | 기본 규칙 | 상수 (`registry.py` 노출) |
| --- | --- | --- | --- |
| 1 | `SPAM` → `HIDE` | 사용자별 슬라이딩 윈도우 rate-limit + 근접중복(`SequenceMatcher`) | `SPAM_WINDOW_SECONDS=10.0`, `SPAM_MAX_MESSAGES=4`, `SPAM_SIMILARITY=0.85` |
| 2 | `ABUSIVE` → `BLOCK` | `RuleBasedClassifier` — 욕설/혐오 사전 + **우회패턴 정규화**(초성체·공백삽입·자모반복·웃음접미사 제거 후 매칭) | `ABUSE_THRESHOLD=0.5` |
| 3 | `REPEATED_QUESTION` → `PASS` | B-1 규칙: 물음표 + 키워드 정규식 | — |
| 4 | `NORMAL` → `PASS` | 그 외 | — |

반복질문 경로(비동기) 상수:

| 상수 | 값 | 근거 / 주의 |
| --- | --- | --- |
| `CLUSTER_SIMILARITY` | `0.8` | 노션 `[AI] 반복질문 판정 정책 기준`(LAB-8) 제안값. **단 `chat_agent.ipynb` 5.3 결론상 임베딩 모델마다 유사도 스케일이 달라 모델 무관 재사용 불가** — 백엔드 교체 시 반드시 재스윕 |
| `MIN_CLUSTER_SIZE` | `2` | 같은 질문 2회 이상 유입 시에만 답변. 세션(`live_id`) 내에서만 누적, 클러스터 최초 도달 시 1회만 생성 |
| `GROUNDING_THRESHOLD` | `0.35` | **근거 약함** — 타 프로젝트 문서에서 차용된 값. CHAT-003에서 확정. 상수로만 노출하고 값 확정을 주장하지 않는다 |

우회패턴 정규화를 기본 규칙에 넣는 이유: 벤치마크에서 현 baseline `kor_unsmile`이 초성체/띄어쓰기
우회를 절반 가까이 놓쳤다(악성 recall 58.3%). 규칙 기반 목업이라도 이 전처리가 있어야 데모가 의미를 갖는다.

---

## 모델 스왑 설계 (핵심 요구사항)

`registry.py`는 `test/model_selection/model_registry.py`와 **같은 모양**으로 만들되 프로덕션용이다.

```python
CLASSIFIER_BACKENDS = {
    "rule_based": "app.chat.classifier:RuleBasedClassifier",   # 기본 — 의존성 없음
    "kcelectra_base_hate": "beomi/beep-KcELECTRA-base-hate",   # 벤치마크 1위(acc 99.5%, 악성 recall 98.8%)
    "kor_unsmile": "smilegate-ai/kor_unsmile",                 # 기존 baseline
}
ACTIVE_CLASSIFIER = "rule_based"   # <- 여기 키만 바꾸면 스왑
```

`RETRIEVER_BACKENDS`(`mock`/`pgvector`), `GENERATOR_BACKENDS`(`template`/`kanana`)도 동일 형태.

- HF 어댑터는 **함수 내부 지연 import**(`transformers`는 `requirements-pipeline.txt`, CI 미설치).
- 어댑터 없는 백엔드 키를 고르면 기동 시점이 아니라 **첫 호출 시** 명확한 에러를 던진다.
- 모델 ID는 `test/`에서 import하지 않고 재선언한다(`embed_catalog.py` 선례).
- `app/shared/` 승격은 이번 라운드에서 하지 않는다 — chat과 recommend가 임베딩 로더를 실제로 함께
  쓰게 되는 시점(RAG 실구현, -184)에 판단한다.

---

## 목업 데이터

- `mock_comments.json` — 정상 / 욕설(직접) / 욕설(우회: 초성체·공백·자모반복) / 도배 / 반복질문
  paraphrase 그룹을 라벨과 함께. `chat_agent.py`의 `SAMPLES`와 `chat_agent.ipynb`의 `FAQ_CANDIDATES`를 확장.
- `mock_faq.json` — `{doc_id, question, answer, tags}` 형태. 가격/재고/배송/사이즈/교환·반품/결제.
- `MockRetriever`는 `_seeded_vector()` 방식 결정적 임베딩으로 코사인 검색 → **torch 없이 CI에서 검증
  가능**하고, 나중에 `PgvectorRetriever`로 바꿔도 인터페이스가 동일하다.

---

## 검증 방법

```bash
cd AI
pip install -r requirements-dev.txt
ruff check . && black --check . && pytest -q
uvicorn app.main:app --reload --port 8000
```

- `GET /health` → 200, `GET /docs`에 `/chat/*` 3개 노출 확인.
- 목업 E2E: `mock_comments.json`을 순서대로 `POST /chat/moderate`에 흘려보내
  ① 욕설/우회표현이 `ABUSIVE`+`BLOCK` ② 동일 문장 연속 게시가 `SPAM`+`HIDE`
  ③ 반복질문 3건이 한 클러스터로 묶여 `GET /chat/lives/{id}/answers`에 답변 1건만 생성되는지 확인.
- 근거 부족 케이스: 지식베이스에 없는 질문("매장 위치 어디예요?")은 답변이 **생성되지 않음**을 확인.
- 유닛테스트: 스팸 윈도우 경계, 우회패턴 정규화, 클러스터링 임계치, 그라운딩 게이트,
  백엔드 스왑(`ACTIVE_*`를 바꿔도 서비스가 조립되는지), API 422/503/404.

---

## 구현 목록

- [x] 본 계획을 리포 `.claude/plans/ai/003-live-comment-moderation-prototype.md`로 저장(프로젝트 컨벤션)
- [x] `app/chat/schemas.py` — 요청/응답 모델 + `Verdict`/`ModerationAction` enum
- [x] `app/chat/registry.py` — 백엔드 딕셔너리 + `ACTIVE_*` + 임계치 상수(근거 주석 포함)
- [x] `app/chat/spam.py` — `StateStore` ABC + `InMemoryStateStore` + `RedisStateStore` 스텁, `SpamDetector` 승격
- [x] `app/chat/classifier.py` — `AbuseClassifier` ABC + `RuleBasedClassifier` + `HuggingFaceClassifier`(지연 import)
- [x] `app/chat/faq.py` — `QuestionDetector` / `QuestionClusterer` / `Retriever` ABC / `AnswerGenerator` ABC + 그라운딩 게이트
- [x] `app/chat/answers.py` — `AnswerStore` ABC + `InMemoryAnswerStore` + `RedisAnswerStore` 스텁
- [x] `app/chat/service.py` — 파이프라인 오케스트레이션 + `@lru_cache` 팩토리
- [x] `app/chat/router.py` — `POST /chat/moderate`, `GET /chat/lives/{live_id}/answers`, `GET /chat/answers/{ticket}`
- [x] `app/main.py`에 chat 라우터 등록(`prefix="/chat"`, `tags=["chat"]`) — 기존 recommend 등록 유지
- [x] `app/chat/data/mock_faq.json`(6건), `mock_comments.json`(16건) — `.gitignore`에 걸리는 규칙 없음(커밋됨)
- [x] `app/chat/tests/` — 4개 파일 72 테스트. torch 불필요, CI에서 전부 실행
- [x] 목업 E2E 시나리오 확인 — uvicorn 기동 후 16건 전부 예상 판정과 일치, 최대 지연 8.2ms
- [x] `ruff check .` / `black --check .` / `pytest -q` 로컬 통과(110 passed, 2 skipped) 후 커밋

### 구현 중 계획과 달라진 점

1. **`AnswerQueue` ABC를 만들지 않았다.** 지연 실행은 FastAPI `BackgroundTasks`가 이미 해 주므로
   큐 추상화는 층만 늘린다. 실제로 갈아끼워야 하는 건 다중 워커 간 공유 상태이므로
   `answers.py`는 `AnswerStore` ABC(+`RedisAnswerStore` 스텁)만 둔다.
2. **임계치를 전역 상수에서 백엔드별 설정으로 옮겼다.** `chat_agent.ipynb` 5.3의 결론이
   "임베딩 모델마다 유사도 스케일이 달라 고정 임계치를 재사용하면 안 된다"였는데, 전역 상수로 두면
   그 함정을 코드가 그대로 반복한다. `registry.EMBEDDER_BACKENDS[key]`에 `cluster_similarity` /
   `grounding_threshold`를 함께 넣어 **임베더를 바꾸면 임계치가 따라오게** 했다. LAB-8 제안값은
   `POLICY_*` 상수로 남겨 참조만 한다.
3. **판정 경로는 절대 503을 내지 않는다.** 지식베이스가 깨져도 채팅 자체가 막히면 안 되므로,
   `POST /moderate`는 정상 판정하고 답변 생성만 조용히 건너뛴다(로그 남김). 지식베이스 장애는
   답변 조회 엔드포인트에서 503으로 드러난다.
4. **목업 임계치는 실측으로 잡았다** — 클러스터 0.30(패러프레이즈 최저 0.308 vs 무관 최고 0.224),
   그라운딩 0.35(지식베이스 내 0.52~0.85 vs 밖 최고 0.334). `test_chat_faq.py`가 이 분리를 고정한다.

### 작업 종료 후 수행 — 노션 `프로/Vintib 기록` 페이지 기록

구현·검증이 끝난 뒤 아래 구조로 기록 페이지를 작성한다. **What / How / Why가 모두 드러나야 한다.**

- [ ] **What — 무엇을 만들었나**: 라이브 댓글 관리 프로토타입(`app/chat/`). 동기 판정 API 1개 +
      답변 조회 2개. 욕설·스팸은 동작, 반복질문 RAG는 인터페이스 + Mock까지.
- [ ] **Why — 무엇을 위해서인가**: 방송 품질 훼손(욕설·도배)과 판매자의 반복질문 응대 부담 해소.
      더불어 모델·BE 계약·RAG 백엔드가 전부 미확정인 시점에 **완결 파이프라인을 목업으로 먼저 세워**
      확정될 때마다 경계 뒤만 교체하려는 의도.
- [ ] **How — 어떻게 만들었나**: 3-스테이지 동기 파이프라인(스팸 → 악성 → 질문 게이트) + 비동기 FAQ 경로.
      교체 지점 3곳(`registry.py` 키 / `schemas.py` / `service.py` 팩토리 한 줄)을 명시.
- [ ] **왜 그 기술인가 + 비교군** (표로):
  - 차단 집행 주체: **판정 위임** vs AI 직접 PATCH → 1 RTT·노출 없음·장애 격리로 위임 채택(위 표 재사용)
  - 응답 형태: **동기 판정 + 비동기 답변** vs 단일 동기 REST vs 메시지 큐 소비형 → 생성 지연이 채팅을
    막지 않으면서 BE 의존성은 최소
  - 기본 분류기: **규칙 기반 목업** vs HF 모델 기본값 → CI(torch 미설치)에서 전 테스트 실행 가능
  - 분류기 벤치마크(210건): `kcelectra_base_hate` acc 99.5% / 악성 recall 98.8% / mean 20.0ms
    vs baseline `kor_unsmile` 악성 recall 58.3% → 실모델 채택 시 1순위
  - 스팸 탐지: 규칙(rate-limit + 근접중복) vs 모델 → 텍스트 분류기로는 구조적으로 판정 불가
  - 상태 저장: 인메모리 vs Redis → 프로토타입은 인메모리, `StateStore` ABC 뒤로(-188)
  - RAG 백엔드: Mock 결정적 임베딩 vs pgvector vs FAISS/Chroma → BE가 이미 PostgreSQL이라 pgvector 유력(-184)
- [ ] **고찰 사항**:
  - 클러스터링 임계치 `0.8`은 임베딩 모델마다 유사도 스케일이 달라 **모델 무관 재사용이 불가**하다는
    점이 스파이크의 가장 확실한 시사점 — 백엔드 교체 시 재스윕 필요.
  - 그라운딩 임계치 `0.35`는 타 프로젝트에서 차용된 값이라 근거가 약하다(CHAT-003에서 확정).
  - 현재 검증은 전부 소규모 스모크(문장 5~210건) — 실제 방송 로그 확보 후 재검증 필요.
  - "근거 없으면 무응답" 정책이 사용자 체감상 "AI가 아무것도 안 한다"로 보일 수 있음 — FE 표현 방식 논의 필요.
- [ ] 관련 노션 문서(`라이브 댓글 관리 — 분산 Agent 아키텍처 설계`, `[AI] 반복질문 판정 정책 기준`,
      `[AI] 실시간 라이브 채팅봇 검증문서`)는 **링크로 참조**하고 내용을 중복 서술하지 않는다(001 선례).

### 구현 후 BE 확인 필요 (요청 문서는 작성하지 않음 — 사용자 지시)

`.claude/requests/be/`에 문서를 만들지 않고 여기에만 남긴다.

- BE가 메시지 게시 **전** `POST /chat/moderate`를 호출하는 흐름이 가능한지(사후 숨김 회피)
- AI 타임아웃 시 fail-open / fail-closed 정책
- `action` 값(`PASS`/`HIDE`/`BLOCK`)과 `chat_message.is_blocked`(CHAT-004) 매핑
- 반복질문 답변을 채팅에 어떤 화자로 노출할지(봇 계정? 시스템 메시지?) — FE 포함

---

## 확인이 필요한 미결정 사항

- **노션 설계 문서 대조 미완료 (차단 원인: 커넥터 페이지 권한).** 계정 인증은 정상이지만 Notion
  커넥터는 **페이지 단위로 접근이 부여**되는 구조라 `프로/공통PJT/실험실/` 트리가 통합에 공유돼 있지
  않다(검색 인덱스 미포함, 페이지 ID 직접 조회 404). 해소: 노션 `프로` 페이지 → `⋯` → 연결 → Claude 추가.
  현재 계획은 Jira 192 + `chat_agent.py` / `chat_agent.ipynb` / `classifier_benchmark.ipynb`
  (노션 설계를 인용·검증한 스파이크)에서 역추적했다. 권한 부여 후 아래 3개 문서와 대조해 라우팅 단계·
  용어·임계치를 보정할 것: `라이브 댓글 관리 — 분산 Agent 아키텍처 설계`,
  `[AI] 반복질문 판정 정책 기준`(LAB-8), `[AI] 실시간 라이브 채팅봇 검증문서`.
- 반복질문 답변 전달 방식: 폴링(`GET .../answers`) 잠정. BE가 SSE/WebSocket을 열어주면 전환.
- `answer_ticket` 채번 주체(현재 AI) — BE 메시지 ID 체계와 정합 필요.
- 그라운딩 임계치 `0.35` 확정(CHAT-003).
- `app/shared/` 승격 시점 — chat·recommend가 임베딩 로더를 함께 쓰게 될 때.
