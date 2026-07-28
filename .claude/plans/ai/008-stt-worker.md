# STT 워커 (라이브 발언 전사 → pgvector 적재)

`S15P11A108-443` [CHAT-002] STT 워커 설계 및 개발 (에픽 `-208`)

## 배경/목표

라이브 채팅 반복질문 RAG의 근거 문서(`chat_rag_document`, 1단계에서 완성)를 채우는 두 번째
단계. 방송 오디오를 Whisper 계열로 전사하고, 같은 워커 프로세스 안에서 KURE-v1로 임베딩까지
계산해 게이트웨이에 제출한다. 게이트웨이는 계산 없이 그대로 저장만 한다 — `ai` 컨테이너엔
torch가 없고(`mem_limit: 1g`), 워커는 이미 Whisper 때문에 torch를 들고 있어서 같은 프로세스
안에서 임베딩까지 끝내는 게 자연스럽다(`AI/docs/chat-rag-storage.md` 참고).

**선행 조건이 아직 안 갖춰졌다**: OpenVidu v3(방송 녹화)가 로드맵상 2주차라 아직 미설치다.
그래서 이번 단계는 워커 코드와 게이트웨이 적재 훅까지만 만들고, **진짜 방송 음성으로 하는
E2E는 못 한다** — 로컬 임의 오디오 파일로 워커 단독 동작만 확인한다. BE에 WebRTC 기술 의견은
이미 `.claude/requests/be/002-live-webrtc-candidates.md`로 전달해 뒀다.

## 작업 내용

1. `AI/app/gateway/schemas.py`의 `FeatureType`에 `"stt"` 추가.
2. `worker/storage_utils.py`에 `download_bytes(url) -> bytes` 추가(오디오는 `download_image`
   처럼 PIL로 열 수 없으니 별도 함수 필요 — 기존 함수는 안 건드림).
3. `worker/stt_worker_example.py` 신설(`base_worker.py` 상속, `tryon_worker_example.py` 패턴):
   - `_ensure_loaded()`: `faster-whisper`(small, 한국어) + `sentence-transformers`
     (`nlpai-lab/KURE-v1`) 지연 로딩, 프로세스당 1회.
   - `run_inference(payload)`: `audio_url`을 내려받아(MP4든 오디오든 그대로 — faster-whisper가
     내부 ffmpeg로 오디오 트랙만 디코딩) 전사 → 텍스트를 KURE-v1로 임베딩 → 반환.
   - payload: `{"audio_url": ..., "live_id": ...}`
   - 반환: `{"text": ..., "embedding": [...], "live_id": ...}`
4. `AI/app/gateway/router.py`의 `submit_result()`에 분기 추가: `job.type == "stt"`이고
   `status == "success"`면 `rag_store.save_document(live_id=result["live_id"],
   source_type="stt", content=result["text"], embedding=result.get("embedding"))` 호출.
   계산은 안 하고 워커가 보낸 값을 그대로 저장만 한다.
5. `worker/README.md`에 STT 워커 실행 방법(필요 conda 환경, 모델 크기 선택지 등) 추가.

## 구현 목록

- [x] `AI/app/gateway/schemas.py` — `FeatureType`에 `"stt"` 추가
- [x] `worker/storage_utils.py` — `download_bytes()` 추가
- [x] `worker/stt_worker_example.py` 신설 — `STT_BACKEND=mock`(기본값, GPU 불필요) /
      `faster_whisper`(실제 모델) 스왑 지원
- [x] `AI/app/gateway/router.py` — `submit_result()`에 `_ingest_stt_result()` 분기 추가
      (저장 실패해도 job 제출 자체는 실패시키지 않음)
- [x] `worker/README.md` 갱신
- [x] 검증: `cd AI && ruff check . && black --check . && pytest -q` — 440 passed, 2 skipped
- [x] 검증: `worker/stt_worker_example.py` 정적 문법 확인(`ast.parse`)
- [x] 검증: `STT_BACKEND=mock`으로 `SttWorker.run_inference()` 단독 호출 — 텍스트/임베딩
      차원(1024)/결정성 확인
- [x] 검증: 로컬 `postgres-vector` 컨테이너에 `router._ingest_stt_result()` 직접 호출 —
      저장 성공 케이스 + 저장 실패(잘못된 payload)해도 예외 안 던지는 케이스 둘 다 확인
- [ ] 검증(보류): 실제 Whisper 모델(`STT_BACKEND=faster_whisper`)과 실제 방송 오디오 E2E —
      OpenVidu 설치 이후로 지연

## 미결정 사항

- Whisper 백엔드/모델 크기(`small` vs `base` 등) — 실측 없이 우선 `small`로 시작, 정확도·속도
  보고 조정.
- 실제 오디오 E2E는 OpenVidu 설치 후로 지연 — 그때 `.claude/requests/be/002-*.md`에서 논의한
  청크 단위 녹화 방식이 정해지면 이 문서에 반영.

## 관련 자료

- 전체 설계: `.claude/plans/glowing-wandering-hejlsberg.md` (단계 2)
- 선례: `.claude/plans/ai/007-pgvector-rag-storage.md`, `worker/tryon_worker_example.py`
- BE 의견 공유: `.claude/requests/be/002-live-webrtc-candidates.md`
