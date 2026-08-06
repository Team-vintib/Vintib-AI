# 반복질문 자동답변(CHAT-002) — 채팅 메시지로 편입 요청

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 티켓**: `S15P11A108-208` 에픽 하위, `S15P11A108-444`(chat_rag 생성기)
- **상태**: 요청 — AI 쪽 구현/검증은 끝났고, 테스트를 위해 이제 BE 연동을 요청드립니다.

## 배경

`기능 정의서.md`의 CHAT-002(반복 질문 자동 답변, **필수**)는 이미 `POST /lives/{id}/messages`
같은 채널로 CHAT-001과 함께 매핑돼 있고(`APIs.md`), `chat_message.sender_type`에도 `AI` 값이
미리 예약돼 있습니다(`BE/docs/db/data-dictionary.md`: `"AI(자동 답변, CHAT-002)"`,
`SenderType.java` 주석: `"현재 보류 상태"`). 즉 설계 방향 자체는 이미 BE 쪽에 잡혀 있고,
지금까지는 우선순위상 보류돼 있던 상태로 이해하고 있습니다.

AI 쪽은 이번에 준비가 끝났습니다 — `worker/chat_rag_worker_example.py`(라이브 방송 중 같은
질문이 `MIN_CLUSTER_SIZE`(2)번 이상 반복되면, 판매자 STT 발언을 근거로 답변 생성)를
mock 모드로 grounded=True/False 두 경로 다 실제 실행까지 검증했습니다. 이제 테스트해보려면
BE 연동이 필요해 요청드립니다.

## 요청 내용

BE가 아래 AI 게이트웨이 내부 API를 폴링(또는 워커 결과 콜백)해서, 근거가 있는(`grounded:
true`) 답변만 `sender_type=AI`인 `chat_message`로 저장해 주시면 됩니다. 저장 이후에는
기존 `POST/GET /lives/{id}/messages`(CHAT-001) 파이프라인을 그대로 타므로 FE는 새
엔드포인트를 몰라도 됩니다 — CHAT-002가 별도 API 없이 CHAT-001에 얹혀 가는 설계와
일치합니다.

```http
GET /chat/lives/{live_id}/answers?since={ISO8601}   # 마지막 조회 이후 새로 생성된 답변만
GET /chat/answers/{ticket}                          # 답변 1건 단건 조회
```

응답 예시:

```json
{
  "live_id": 42,
  "answers": [
    {
      "ticket": "a_42_ab12cd",
      "live_id": 42,
      "question": "이거 프리사이즈인가요?",
      "cluster_size": 2,
      "answer": "네, 프리사이즈이며 신축성이 좋습니다.",
      "grounded": true,
      "grounding_score": 0.82,
      "sources": [{"doc_id": "17", "score": 0.82}],
      "created_at": "2026-08-05T13:20:11+09:00"
    }
  ]
}
```

- `grounded=false`인 답변은 애초에 목록에 안 나옵니다(CHAT-003 "근거 없으면 무응답" 정책이
  AI 쪽에서 이미 적용된 결과라, BE가 따로 걸러낼 필요는 없습니다).
- `question`은 특정 발신자를 지칭하지 않습니다 — 같은 질문을 한 모두에게 공통으로 노출되는
  메시지로 저장하면 됩니다.
- `sender_type=AI` 메시지는 FE에서 "AI 답변" 배지로 구분 표시하는 게 좋다는 내용을
  `.claude/requests/fe/001-repeated-question-answer-ui.md`에 미리 공유드렸습니다 — 이번
  문서와 함께 참고해 주세요.

## 참고

- AI 라우터: `AI/app/chat/router.py`, 스키마: `AI/app/chat/schemas.py`(`FaqAnswer`,
  `AnswerListResponse`)
- 워커: `worker/chat_rag_worker_example.py`
- BE 쪽 기존 설계 흔적: `BE/src/main/java/com/ssafy/backend/chat/entity/SenderType.java`,
  `BE/src/main/java/com/ssafy/backend/chat/service/ChatMessageService.java`(주석: "AI 채팅
  매니저(CHAT-002/003/004)는 보류다")
