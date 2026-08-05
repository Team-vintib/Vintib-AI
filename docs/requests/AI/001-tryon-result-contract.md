# 시착 합성 결과 전달 방식 제안

**요청자 파트**: BE
**대상 파트**: AI

## 배경/이유

상품 이미지·시착 결과 이미지를 S3에 저장하는 작업(SY008)을 하면서, BE에는 시착 결과를 **저장/조회/삭제**하는 API(`/api/users/{id}/tryons`)와 `tryon_result` 테이블까지는 만들었다. 하지만 실제로 "시착 이미지를 생성하는" `POST /api/users/{id}/tryons`는 AI 쪽에 합성 엔드포인트 자체가 아직 없어(`AI/main.py`에 `/health`만 존재) 이번 범위에서 뺐다. AI↔BE 계약이 아직 어디에도 문서화되어 있지 않아, BE 쪽 제안을 먼저 남긴다.

## 요청 내용

시착 합성 결과를 AI가 BE에 넘길 때, **AI가 S3에 직접 업로드하지 말고 이미지 바이트를 BE에 동기 응답으로 반환**하고, BE가 S3 업로드와 DB 저장을 맡는 방식을 제안한다.

- 이유 1: AI 쪽에 별도 AWS 자격증명을 발급/관리하지 않아도 된다 — S3 접근은 BE만 갖는다.
- 이유 2: 루트 `CLAUDE.md`의 "Spring은 FastAPI만 바라본다" 원칙과 방향이 맞는다(BE→AI 단방향 호출, AI가 별도로 외부 스토리지를 호출하지 않음).

구체적으로는 BE가 `AI_BASE_URL` 기준으로 합성 요청을 보내면(입력: 상품 이미지 URL/키, 사용자 시착 프로필 사진 URL/키 등 — 정확한 요청 필드는 AI 쪽 모델 입력 방식에 맞춰 AI가 정하면 됨), AI가 합성된 이미지를 **응답 바디에 바이너리(또는 base64)로 담아 동기 반환**하는 형태를 제안한다. BE는 그 응답을 받아 private 버킷에 업로드하고 `tryon_result` row를 만든 뒤, presigned GET URL로 결과를 내려준다(이미 구현됨 — `TryOnResultService.saveResult(memberId, productId, imageBytes, contentType)`).

합성이 오래 걸려 동기 응답이 어렵다면(Celery+Redis 비동기 처리 등) 콜백/폴링 방식이 필요할 수 있는데, 이 경우의 계약은 AI 쪽 처리 방식이 확정된 뒤 별도로 협의가 필요하다.

## 확인 필요

- 합성 요청/응답의 정확한 필드(입력 이미지 전달 방식, Content-Type, 실패 시 에러 형식)
- 동기 처리가 가능한지, 오래 걸리면 비동기/콜백이 필요한지
- 위 내용이 정해지면 BE가 `POST /api/users/{id}/tryons`(생성 API)를 별도 계획(SY009 예정)으로 이어서 구현한다.
