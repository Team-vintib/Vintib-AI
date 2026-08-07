# CH023 — 라이브 채팅 욕설 필터링 + 반복질문 자동답변 BE/FE 연동

에픽 `S15P11A108-217`, 커밋 키 `S15P11A108-571`, 브랜치 `feat/217-chat-moderation-rag`.

## 배경

AI 쪽은 두 기능 다 구현·검증이 끝나 있고, BE/FE 연동만 안 돼 있다(`ChatMessageService`
주석: "AI 채팅 매니저(CHAT-002/003/004)는 보류다"). FE/BE가 바빠서 이번 것도 AI가
직접 BE/FE까지 작성해서 실제 워커로 테스트한다(-517과 동일한 예외).

- **욕설/스팸 판정 + 반복질문 감지**: `POST /chat/moderate`(AI 게이트웨이, 동기, 모델 불필요 —
  `rule_based` 분류기라 워커도 필요 없다) 하나만 부르면 끝난다. 판정 결과(`action`:
  PASS/HIDE/BLOCK)는 권고이고 실제 집행은 BE가 한다(`docs/requests`로 넘어온 적 없음 —
  AI 라우터 docstring/스키마 자체가 계약).
- **반복질문 자동답변**: AI가 이미 `docs/requests/BE/036-chat-rag-answer-public-api.md`로
  BE에 요청해둔 상태(공개 API 없이 CHAT-001 파이프라인에 얹는 설계). `GET
  /chat/lives/{id}/answers?since=...`를 폴링해서 근거 있는(`grounded:true`) 답변만
  `sender_type=AI`인 `chat_message`로 저장하면 된다. AI 쪽은 `chat_rag` job으로
  워커(`worker/chat_rag_worker_example.py`)에 위임하는 구조라, **이 기능만 실제 워커가
  필요하다.**
  - 답변 생성은 방송 발언 STT 전사문(`chat_rag_document`, `postgres-vector`)이 근거인데,
    이건 별도 `worker/stt_worker_example.py`가 채운다 — 로컬 테스트하려면 이것도 같이
    띄워야 한다(둘 다 mock 백엔드로 먼저 파이프라인부터 확인).
- FE 쪽엔 이미 참고용 요청 문서(`docs/requests/FE/032-repeated-question-answer-ui.md`)가
  가 있다 — "AI 자동답변" 배지로 구분 표시 권장.

## 범위 (MVP)

### 1. BE — 욕설/스팸 동기 판정

- `AiClient`에 `moderateChatMessage(ModerateChatRequest)` 추가 → `POST /chat/moderate`,
  응답(`verdict`/`action`/`reason`/`answerTicket`) 파싱. 타임아웃을 짧게 잡는다(예: 2초) —
  AI 게이트웨이가 느려지거나 죽어도 채팅 전체가 막히면 안 된다.
- `ChatMessageService.send()`에서 메시지 저장 직후(브로드캐스트 전) 동기 호출:
  - `action=PASS` → 그대로 브로드캐스트.
  - `action=HIDE`/`BLOCK` → `ChatMessage`에 신규 `block()` 메서드 추가해 `is_blocked=true`로
    표시하고, STOMP 브로드캐스트는 생략한다(MVP는 HIDE/BLOCK을 동일하게 취급 — 세분화는
    범위 밖).
  - AI 호출 자체가 실패(타임아웃/네트워크 오류)하면 판정 없이 그냥 통과시킨다(보조 기능,
    등록 AI 착용컷 job 트리거와 동일한 try/catch 패턴).

### 2. BE — 반복질문 자동답변 폴링

- `AiClient`에 `getLiveAnswers(liveId, since)` 추가 → `GET /chat/lives/{id}/answers`,
  `FaqAnswer` 리스트 파싱.
- `ChatMessage`에 `aiMessage(Live, String content, LocalDateTime)` 정적 팩토리 추가
  (`sender=null`, `senderType=AI` — `systemMessage()`와 같은 패턴).
- 신규 `@Scheduled` 컴포넌트(예: `ChatAnswerPollingScheduler`, 5초 간격): 진행 중인 방송
  전부(`LiveRepository.findByStatusOrderByStartedAtDesc(LiveStatus.LIVE, ...)`)에 대해
  `getLiveAnswers(liveId, since)` 호출 → 새 답변을 `aiMessage()`로 저장 + STOMP
  `/topic/lives/{liveId}/chat`로 브로드캐스트. `since`는 그 방송의 마지막 AI 메시지
  `created_at`(없으면 방송 `startedAt`).
- 실패한 방송 하나 때문에 나머지 방송 폴링이 멈추면 안 된다 — 방송 단위로 예외를 잡는다.

### 3. FE — AI 자동답변 배지

- 채팅 메시지 렌더링 컴포넌트에서 `senderType === 'AI'`면 일반 메시지와 구분되는 배지(예:
  "AI 자동답변") 표시. 판매자 메시지처럼 보이면 안 된다(`032` 요청 문서 권장사항).

### 4. 로컬 테스트

- `docker-compose up -d`(postgres/postgres-vector/redis/minio/backend/ai).
- 로컬 워커 2개: `stt_worker_example.py`(mock) + `chat_rag_worker_example.py`(mock) 둘 다
  띄운다 — 실측 라이브 하나에서 같은 질문 2번 이상 채팅으로 올려서 "AI 자동답변" 메시지가
  뜨는지, 욕설성 문구를 보내서 차단(브로드캐스트 안 됨)되는지 브라우저로 직접 확인.
- 파이프라인 확인되면 `CHAT_RAG_BACKEND=lfm2_langchain`(실 모델)으로 전환해 재확인은
  선택(GPU 자원 상황에 따라 나중 과제로 남겨도 됨).

## 확인 필요

- HIDE/BLOCK을 지금처럼 동일 취급할지, 나중에 실제로 구분할지(운영 정책 미정이면 MVP대로
  단순 처리하고 넘어가는 게 맞아 보임).
- 동기 판정 호출 타임아웃 구체값(2초 제안, 확정 필요).
- 폴링 주기 구체값(5초 제안, 확정 필요).
