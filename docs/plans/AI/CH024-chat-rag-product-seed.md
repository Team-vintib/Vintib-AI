# CH024 — 상품 정보를 반복질문 근거 문서로 seed

에픽 `S15P11A108-217`, 커밋 키 `S15P11A108-571`.

## 배경/목표

CH023에서 만든 반복질문 자동답변은 판매자 실시간 발언(STT)을 근거로 삼는데, STT 오디오
캡처 파이프라인(LiveKit 녹화)이 아직 인프라에 없다 — `worker/stt_worker_example.py` 자체
docstring에도 "아직 실제 방송 오디오로는 검증할 수 없다"고 적혀 있었다. 그 결과 "가격
얼마예요?" 같은, 사실 방송 중 상품 편성 정보만 있으면 바로 답할 수 있는 질문도 근거
문서가 하나도 없어 항상 무응답이었다(실측 확인).

`AI/app/chat/rag_store.py`의 `save_document()`는 애초에 `source_type: "stt" | "seed"`
두 종류를 구분하게 설계돼 있었다 — STT 없이도 문서를 채우는 경로가 이미 열려 있다. 라이브에
상품이 편성될 때 그 상품의 제목/가격/상태/소재 등을 자연어 한 줄로 만들어 `seed` 문서로
저장해두면, STT 없이도 가격·사이즈 같은 반복질문에 바로 그라운딩될 수 있다.

## 범위 (MVP)

- STT 실연동(LiveKit Egress)은 범위 밖으로 남긴다 — 별도 더 큰 작업.
- 상품 하나당 문서 하나, 편성 시점에 1회 생성한다(재편성/가격 변경 시 갱신은 범위 밖 —
  지금은 "아예 없는 것보다 낫다"가 목표).
- mock 임베딩(해시 기반)은 의미 기반 매칭이 안 되므로, 이 기능이 실제로 "가격 얼마예요"
  같은 자유 질문에 답하는 걸 보려면 `CHAT_RAG_BACKEND=lfm2_langchain`(실 모델)로 워커를
  돌려야 한다 — mock은 파이프라인 배선 확인용으로만 유효하다.

## 작업 내용

### AI

- `AI/app/chat/router.py`: `POST /chat/lives/{live_id}/documents` 신규(body: `content:
  str`) — `rag_store.save_document(live_id, source_type="seed", content=content)` 호출.
  BE 전용 동기 엔드포인트라 인증 헤더 불필요(`/chat/moderate`와 동일 원칙).
- `AI/app/chat/service.py`(또는 얇은 wrapper)에 위임해서 router는 요청 검증만 하게 유지.

### BE

- `AiClient.seedChatRagDocument(Long liveId, String content)` 추가 → 위 엔드포인트 호출.
- `LiveProductService.linkProductsOnCreate()`/`linkProduct()`에서 상품이 편성될 때마다
  `ProductCard`(제목/브랜드/가격/상태등급/소재/실측치수)를 자연어 한 줄로 조립해 seed —
  실패해도 편성 자체는 막지 않는다(try/catch, 로그만 — 등록 AI 착용컷 트리거와 동일 패턴).
- 경매 상품(`price == null`)은 "가격은 경매로 진행됩니다" 같은 대체 문구를 쓴다.

## 확인 필요

- 자연어 블러브 문구 형식(간단 템플릿으로 시작, 나중에 다듬어도 됨).
- 재편성/가격 변경 시 문서 갱신은 이번엔 안 함 — 필요해지면 별도 티켓.
