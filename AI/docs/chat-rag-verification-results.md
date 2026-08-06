# 라이브 채팅 RAG — 로컬 검증 결과 정리

`S15P11A108-443`(STT 워커), `S15P11A108-444`(chat_rag 생성기). EC2 배포 검증이 인프라 문제로
막혀서([`003-caddy-route-divergence.md`](../../.claude/requests/be/003-caddy-route-divergence.md)),
실 모델(KURE-v1, LFM2.5-230M, faster-whisper)로 로컬에서 검증한 결과를 정리한다. 세 갈래를
따로 확인했다: ① 판정 정확도(회귀 게이트), ② STT 워커 실동작, ③ chat_rag 워커 실동작.

## 1. 판정 정확도 — 기존 평가 파이프라인 재실행

새 더미 데이터를 만드는 대신 기존 라벨셋 평가 파이프라인(`python -m app.chat.pipeline.evaluate`,
`S15P11A108-196`)을 그대로 돌렸다 — 목적은 이번 세 단계 작업이 판정 로직에 회귀를 일으키지
않았는지 확인하는 것. `app/chat/artifacts/eval_report.md`(생성물) 결과가 기존 문서화된
베이스라인과 정확히 일치했다:

| 항목 | 결과 |
| --- | --- |
| 비매너 판정 Set A(210건, 우회 변형 포함) | accuracy 66.7% · precision 100.0% · recall 16.7% · FP 0 / FN 70 |
| 비매너 판정 Set B(31건, 수제 확장셋) | accuracy 32.3% · FP 8 / FN 13 |
| 반복질문 클러스터링(325쌍, 임계치 0.30) | precision 87.5% · recall 95.5% |
| 반복질문 근거 적절성(그라운딩) | 근거 정확도 100%(18/18) · 환각 0건(8/8 정상 침묵) |

`rule_based` 분류기의 낮은 recall(Set A 16.7%)은 새로 생긴 문제가 아니라 이미 알려진 한계고
(`kcelectra_base_hate` 후보 대비 회귀 표), Set B의 오탐 8건도 사전 매칭 방식의 구조적 한계다.
**결론: 이번 작업(pgvector 저장소/STT 워커/chat_rag 생성기 추가)이 기존 판정 로직에 영향을
주지 않았다.**

## 2. STT 워커 — 실 오디오 E2E

로컬 `rag-worker` conda 환경(Python 3.11, torch/faster-whisper/sentence-transformers)에서
`STT_BACKEND=faster_whisper`로 진짜 음원 파일 하나를 로컬 HTTP 서버로 URL 서빙 →
`POST /ai/stt` → 워커가 poll·전사·KURE-v1 임베딩 → 결과 제출 → `postgres-vector` 저장까지
실제 인프라(Redis, `postgres-vector`, uvicorn 게이트웨이, 워커 프로세스)로 전부 확인했다.

- 전사 결과: 문자 수 1,731자(저작권 있는 음원이라 본문은 기록하지 않는다)
- 임베딩 차원: 1024 (KURE-v1 출력과 `chat_rag_document.embedding vector(1024)` 컬럼 일치 확인)
- `rag_store`에 `source_type="stt"`로 저장 성공, `live_id` 스코핑 정상

### 발견한 이슈 2건 (둘 다 Windows 로컬 환경 문제, 해결됨)

1. `ModuleNotFoundError: No module named 'faster_whisper'` — 패키지가 애초에 설치 안 돼
   있었음. `pip install faster-whisper`로 해결.
2. `RuntimeError: Library cublas64_12.dll is not found` — torch는 CUDA 13(cu130)으로 깔려
   있는데 CTranslate2(faster-whisper 백엔드)는 CUDA 12 cuBLAS/cuDNN을 요구해서 발생.
   `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` 설치 후 그 패키지들의 DLL 디렉터리를
   `PATH`에 추가해서 해결.

## 3. chat_rag 워커 — 실 모델 E2E + 버그 2건 발견/수정

같은 `rag-worker` 환경에서 `CHAT_RAG_BACKEND=lfm2_langchain`으로 워커를 띄우고,
`POST /chat/moderate`를 같은 질문으로 2회 호출(반복질문 성립) → Redis에 `chat_rag` job 적재
확인 → 워커가 KURE-v1로 랭킹 + LangChain/LFM2.5-230M으로 생성 → `GET /chat/answers/{ticket}`
로 최종 답변 조회까지 전부 성공했다. 이 과정에서 버그 3건을 발견해 전부 고쳤다.

### 버그 1 — 프롬프트 에코

`transformers.pipeline("text-generation", ...)`가 기본값(`return_full_text=True`)이라 생성된
"답변"에 입력 프롬프트 지시문이 그대로 섞여 나왔다. `return_full_text=False` 추가로 해결
(`worker/chat_rag_worker_example.py`).

### 버그 2 — 그라운딩 임계치 과소평가

`GROUNDING_THRESHOLD=0.35`는 `mock_bigram` 임베더 기준(무관한 문장 간 최고 유사도 0.334)으로
잡은 값인데, KURE-v1로 바꾸니 무관한 질문("오늘 날씨가 어떤가요?")도 코사인 0.4232가 나와
임계치를 그냥 넘어버렸다. bigram과 실제 의미 임베딩은 "무관한 문장 간 기본 유사도" 자체가
달라서 그대로 재사용할 수 없었다. 정식 스윕 전까지 오탐을 줄이는 쪽으로 `0.70`으로 올려
뒀다(`registry.py`에 잠정치임을 명시).

수정 후 재검증: 관련 질문 → `grounding_score=0.858` → 정상 그라운딩 + "정확히는
프리사이즈입니다." 같은 깨끗한 답변. 무관 질문 → `grounded: false`로 정상 무응답.

### 버그 3 — 후보 문서 개수 제한이 평가용 상수를 잘못 재사용 (`S15P11A108-444` 최종 수정)

위 두 버그를 고친 뒤 통합 테스트를 반복하다가, 방송 하나에 STT 문서가 4건 이상 쌓인 상태에서
방송 초반에만 언급된 정보(사이즈)를 근거로 한 질문이 갑자기 무응답으로 떨어지는 걸 발견했다.
원인은 `_try_enqueue_chat_rag()`가 워커에 넘길 후보 문서 개수 제한으로
`registry.RETRIEVE_TOP_K=3`을 재사용하고 있었던 것 — 이 상수는 원래 "평가 파이프라인이 이미
순위 매긴 결과 중 상위 3개"라는 의미인데, `rag_store.fetch_documents()`는 "최근 N개"를
가져오는 함수라 의미가 완전히 다르다. 방송 초반(가장 오래된) 문서가 최근 3개 밖으로 밀려나면
영영 후보에 못 들었다.

`registry.CHAT_RAG_CANDIDATE_LIMIT = 200`을 새로 만들어 `candidate_limit` 기본값을 이걸로
바꿔 해결했다(`AI/app/chat/registry.py`, `AI/app/chat/service.py`). 워커가 인메모리로 후보를
전부 랭킹하는 설계([`chat-rag-architecture.md`](./chat-rag-architecture.md) §3)라 방송당
문서 수가 애초에 크지 않다는 전제 위에서, 상한은 두되 넉넉하게 잡았다.

### 최종 확인 — Q&A 데모

- 질문: "이 니트 사이즈 프리사이즈인가요?"
- 답변: "네, 네옷이 있습니다." (grounding_score 0.8174)
- 근거: 후보 문서 랭킹 결과에서 해당 STT 문서가 최상위로 선택됨을 확인

생성 품질(반복되는 어색한 표현 등)은 `LiquidAI/LFM2.5-230M`이 230M 파라미터의 경량 모델이라
당연히 한계가 있다 — 이번 검증의 목적은 "파이프라인이 실제로 끝까지 도는지"와 "근거
없는데 답하거나, 근거 있는데 침묵하지 않는지"였고 둘 다 확인됐다. 생성 품질 자체의 개선은
범위 밖이다.

## 종합

세 갈래 모두 실 모델로 최소 1회 이상 실제 인프라(Redis + `postgres-vector` + 게이트웨이 +
워커) 전체 왕복을 거쳐 검증했다. 남은 건 진짜 방송 오디오/채팅 데이터로 하는 검증인데,
이건 OpenVidu 설치 이후에나 가능하다(`AI/docs/chat-rag-storage.md` 하단 참고). `GROUNDING_
THRESHOLD=0.70`, `CLASSIFIER`/`EMBEDDER` 임계치들은 전부 실측 데이터가 쌓이기 전까지의
잠정치라는 점은 변하지 않았다.

## 관련 자료

- 아키텍처/설계 근거: [`chat-rag-architecture.md`](./chat-rag-architecture.md)
- 상세 이슈 로그: `.claude/plans/ai/008-stt-worker.md`, `.claude/plans/ai/009-chat-rag-generator.md`
- 회귀 게이트 리포트 원본: `AI/app/chat/artifacts/eval_report.md`(생성물, gitignore)
