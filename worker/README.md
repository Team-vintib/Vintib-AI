# worker/ — 로컬 노트북 추론 워커

S15P11A108-27(인프라 세팅) / S15P11A108-210(CatVTON 모델 연결) 관련 코드.

이 폴더는 **팀원 노트북에서 직접 실행**하는 코드다. EC2(docker-compose) 배포 대상이 아니며, git으로 버전 관리만 하고 각자 로컬에서 `python`으로 실행한다.

## 왜 이런 구조인가

배포용 GPU 서버가 없어서, 팀원 노트북(GPU)을 추론 워커로 쓴다. 노트북은 공유기 뒤에 있어 외부에서 인바운드 접속이 불가능하므로, 워커가 EC2 쪽 AI 게이트웨이(`AI/app/gateway/`)를 아웃바운드로 폴링(HTTP GET/POST)하는 방식으로 동작한다. Redis에는 직접 접속하지 않는다.

```
[EC2] AI 게이트웨이 (/ai/workers/poll, /ai/workers/result, ...)
        ↑ HTTP (아웃바운드만 필요)
[노트북] worker/tryon_worker_example.py
```

## 파일 구성

| 파일 | 역할 |
|---|---|
| `base_worker.py` | 모든 워커가 상속하는 공통 골격. poll → 추론 → 결과 제출 → 실패 시 재시도를 처리한다. **이 파일은 기능이 늘어나도 수정할 필요가 거의 없다.** |
| `storage_utils.py` | 게이트웨이와 파일을 주고받는 유틸(`download_image`/`upload_image`/`download_bytes`). S3 권한이 없어 EC2 로컬 디스크 저장 방식을 쓰기 때문에, 워커가 직접 디스크에 쓰지 않고 HTTP로 전송한다. `tryon_worker_example.py`가 import하므로 이 파일 없이는 워커가 기동하지 않는다. |
| `tryon_worker_example.py` | 시착(CatVTON) 워커. 현재 `worker/models/catvton`의 검증 코드(`verify_fit_tryon.py`)를 기반으로 실제 모델이 연결되어 있다. |
| `quality_check_worker_example.py` | 품질검수(CLIPSeg) 워커. 판정 로직은 `models/clipseg/`에 있고 이 파일은 오케스트레이션만 한다. **`QUALITY_BACKEND=mock`이면 GPU 없이도 전 경로가 돈다.** |
| `stt_worker_example.py` | 라이브 발언 STT 워커. Whisper로 전사하고 같은 프로세스에서 KURE-v1 임베딩까지 계산해 게이트웨이엔 텍스트+벡터를 그대로 넘긴다(게이트웨이엔 torch가 없어서). **`STT_BACKEND=mock`(기본값)이면 GPU 없이도 전 경로가 돈다.** 실제 방송 오디오는 OpenVidu 설치 전이라 아직 없다. |
| `chat_rag_worker_example.py` | 반복질문 답변 생성 워커. 게이트웨이가 `live_id`로 가져온 문서 후보 + 질문을 받아 KURE-v1로 임베딩·랭킹하고, 그라운딩 임계치를 넘으면 LangChain + `LiquidAI/LFM2.5-230M`으로 답변까지 생성해 돌려준다(검색·판단·생성을 왕복 1회로 처리). **`CHAT_RAG_BACKEND=mock`(기본값)이면 GPU 없이도 전 경로가 돈다.** |
| `models/clipseg/` | 품질검수 판정 로직 — 세그멘테이션(목업/CLIPSeg) · 하자 항목화 · 점수 · 히트맵. 순수 로직은 `AI/test/worker/clipseg/`가 CI에서 검증한다. |
| `requirements.txt` | 워커 공통 의존성. `requests`, `Pillow`(storage_utils.py가 `PIL.Image`를 다룬다). CatVTON 등 모델 자체의 의존성(torch, diffusers 등)은 각자 기존에 구성해둔 conda 환경을 그대로 쓴다 — 이 파일에 포함하지 않는다. |
| `.env.example` | 워커 실행에 필요한 환경변수 예시. 필요한 값은 아래 "실행 방법" 참고. |

## 실행 방법

### 1. 환경변수 설정

```bash
export GATEWAY_URL=https://i15a108.p.ssafy.io/ai
export WORKER_API_KEY=<EC2 .env의 WORKER_API_KEY와 동일한 값>
```

CatVTON 워커는 추가로 아래 환경변수도 쓸 수 있다 (생략 시 기본값 사용):

```bash
export CATVTON_CODE_PATH=/path/to/worker/models/catvton   # 기본값: worker/ 기준 models/catvton
```

품질검수 워커는 아래를 쓴다:

```bash
export QUALITY_BACKEND=mock                    # 기본값. GPU 불필요 — 목업 시나리오로 전 경로 검증
export QUALITY_BACKEND=clipseg_rd64_refined    # 실제 CLIPSeg. torch/transformers 필요
export CLIPSEG_CODE_PATH=/path/to/worker/models/clipseg   # 기본값: worker/ 기준 models/clipseg
```

`mock` 백엔드는 `models/clipseg/data/mock_inspections.json`의 시나리오(오염 명확 / 미세 오염 /
찢어짐 / 깨끗함 / 프린트)로 확률 마스크를 **결정적으로 합성**한다. GPU가 없는 팀원도 워커를 띄워
게이트웨이 큐 왕복부터 리포트 JSON까지 그대로 확인할 수 있다.

STT 워커는 아래를 쓴다:

```bash
export STT_BACKEND=mock             # 기본값. GPU 불필요 — 결정적 더미 텍스트+임베딩으로 전 경로 검증
export STT_BACKEND=faster_whisper   # 실제 Whisper(small) + KURE-v1. torch/faster-whisper/sentence-transformers 필요
```

chat_rag 워커는 아래를 쓴다:

```bash
export CHAT_RAG_BACKEND=mock             # 기본값. GPU 불필요 — 결정적 임베딩 + 최상위 근거 그대로 반환
export CHAT_RAG_BACKEND=lfm2_langchain   # 실제 KURE-v1 + LangChain/LFM2.5-230M. torch/sentence-transformers/langchain_huggingface/transformers 필요
```

### 2. 실행

CatVTON 관련 패키지(torch, diffusers, huggingface_hub 등)가 이미 구성된 conda 환경에서:

```bash
cd worker
python tryon_worker_example.py
```

정상 기동 시 아래와 같은 로그가 주기적으로 찍힌다 (poll 주기 5초):

```
[호스트명-tryon] polling https://i15a108.p.ssafy.io/ai/workers/poll for feature=tryon
```

첫 job을 받으면 파이프라인 로딩 로그가 한 번 뜨고, 이후 요청부터는 로딩된 파이프라인을 재사용한다:

```
[호스트명-tryon] CatVTON 파이프라인 로딩 중...
[호스트명-tryon] CatVTON 파이프라인 로딩 완료
```

## CatVTON 워커 동작 방식

기존 `worker/models/catvton/verify_fit_tryon.py`(검증 스크립트)를 워커 구조에 맞게 옮긴 것이다. 로직 자체는 동일하고, 아래 세 가지만 다르다.

| 항목 | 검증 스크립트 | 워커 |
|---|---|---|
| 모델 초기화 시점 | 스크립트 실행 시 매번 | 워커 프로세스 시작 후 첫 job 처리 시 1회, 이후 재사용 |
| fit_type 처리 | regular/oversized/cropped 3종 한 번에 반복 | job의 `payload["fit_type"]` 하나만 처리 |
| 입출력 | 로컬 이미지 파일 읽기/저장 | URL로 다운로드, 결과는 게이트웨이로 업로드 후 URL 반환 |

### job payload 형식

```json
{
  "user_image_url": "https://.../person.jpg",
  "product_image_url": "https://.../cloth.jpg",
  "fit_type": "regular"
}
```

`fit_type`은 `regular`, `oversized`, `cropped` 중 하나. 생략 시 `regular`.

### 결과 형식

```json
{
  "image_url": "https://i15a108.p.ssafy.io/results/tryon-results/xxx.png",
  "mask_preview_url": "https://i15a108.p.ssafy.io/results/tryon-masks/xxx.png",
  "fit_type": "regular"
}
```

`mask_preview_url`은 마스크가 어디에 적용됐는지 시각화한 참고용 이미지로, 디버깅에 유용해 같이 업로드하도록 추가했다. 필요 없으면 `tryon_worker_example.py`의 해당 부분만 제거하면 된다.

## STT 워커 동작 방식

라이브 채팅 반복질문 RAG(`S15P11A108-443`)의 근거 문서를 채우는 워커다. 게이트웨이는 임베딩을
계산하지 않고 워커가 보낸 텍스트+벡터를 그대로 `chat_rag_document`(AI 전용 `postgres-vector`)에
저장만 한다 — 자세한 이유는 `AI/docs/chat-rag-storage.md` 참고.

### job payload 형식

```json
{
  "audio_url": "https://.../chunk.mp4",
  "live_id": 42
}
```

`audio_url`은 오디오만이어도 비디오가 섞여 있어도 상관없다 — faster-whisper가 내부 ffmpeg로
오디오 트랙만 디코딩한다.

### 결과 형식

```json
{
  "text": "이 옷은 프리사이즈이고...",
  "embedding": [0.0123, -0.0456, ...],
  "live_id": 42
}
```

`embedding`은 KURE-v1 출력(1024차원)이다. `mock` 백엔드에서는 텍스트 해시 기반 결정적 벡터로
대체된다(`app/chat/faq.py`의 bigram 해싱과 같은 착상) — 실제 검색 품질과는 무관하고 왕복 검증용.

### 실제 방송 오디오는 아직 없다

OpenVidu(방송 녹화)가 로드맵상 미설치라 `audio_url`을 채워줄 곳이 없다. 지금은 로컬 오디오
파일을 아무 파일 서버에 올려서 URL로 넘기는 식으로만 단독 검증할 수 있다.

## chat_rag 워커 동작 방식

라이브 채팅 반복질문 RAG(`S15P11A108-444`)의 마지막 단계 — 검색·랭킹·그라운딩 판단·생성을
전부 이 워커 안에서 한 번에 처리한다. 방송 하나당 문서 수가 많지 않아 pgvector의 ANN 검색
없이 후보 텍스트를 통째로 받아 인메모리로 비교하는 게 충분하다(`AI/docs/chat-rag-storage.md`).

### job payload 형식

```json
{
  "ticket": "a_42_ab12cd",
  "live_id": 42,
  "question": "이거 프리사이즈인가요?",
  "cluster_size": 2,
  "docs": [{"id": 1, "content": "이 니트는 프리사이즈이며..."}, {"id": 2, "content": "..."}]
}
```

`docs`는 게이트웨이가 `rag_store.fetch_documents(live_id)`로 벡터 연산 없이 가져온 후보다.

### 결과 형식

근거 부족(무응답):

```json
{"grounded": false}
```

근거 있음:

```json
{
  "grounded": true,
  "answer": "네, 프리사이즈로 나왔습니다.",
  "grounding_score": 0.62,
  "sources": [{"doc_id": "1", "score": 0.62}]
}
```

## 전체 흐름 테스트

```bash
# 1. job 생성 (백엔드 또는 curl로)
curl -X POST https://i15a108.p.ssafy.io/ai/tryon \
  -H "Content-Type: application/json" \
  -d '{"user_image_url": "...", "product_image_url": "...", "fit_type": "regular"}'
# → {"job_id": "..."}

# 2. 워커가 poll로 가져가서 처리 (worker 터미널 로그로 진행 확인)

# 3. 결과 조회
curl https://i15a108.p.ssafy.io/ai/jobs/{job_id}
# → status가 "success"로 바뀌고 result.image_url이 채워지면 성공
```

## 모델 교체 시 손댈 곳

`TryonWorker._ensure_loaded()`와 `run_inference()` 안, 딱 이 두 곳만 모델별로 갈아끼우면 된다. `base_worker.py`, 게이트웨이(`AI/app/gateway/`), job/result 스키마는 전혀 건드릴 필요가 없다 — 이게 처음부터 이 구조를 이렇게 짠 이유다.

## 남은 작업

- 품질검수 워커를 실제 GPU 노트북에서 `QUALITY_BACKEND=clipseg_rd64_refined`로 돌려보기 (지금까지는 `mock`으로만 검증했다)
- 워커 여러 대(팀원별)를 동시에 띄웠을 때 동작 검증
- CatVTON 모델 로딩 시간이 길 경우, 워커 기동 시점에 미리 로딩해두는 방식(lazy 대신 eager)으로 바꿀지 검토
- STT 워커를 실제 GPU 노트북에서 `STT_BACKEND=faster_whisper`로 돌려보기 (지금까지는 `mock`으로만 검증했다)
- OpenVidu 설치 후 실제 방송 오디오로 STT 워커 E2E 검증
- chat_rag 워커를 실제 GPU 노트북에서 `CHAT_RAG_BACKEND=lfm2_langchain`으로 돌려보기 (지금까지는 `mock`으로만 검증했다)
- 워커 호출 전 답변 캐시(같은 `live_id` 안 유사 질문 재사용, ONNX 임베더) — 별도 후속 작업
