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
| `tryon_worker_example.py` | 시착 워커. VLM 캡션(`models/quality_vlm`) → 신체 치수 근사(`models/catvton/body_estimate.py`) + 핏 계산 → FLUX worn-reference 생성(`models/tryon_flux`) → CatVTON 합성(`models/catvton`)을 순서대로 처리한다(`S15P11A108-504`). |
| `quality_check_worker_example.py` | 품질검수(SAM3) 워커. 판정 로직은 `models/sam3/`에 있고 이 파일은 오케스트레이션만 한다. **`QUALITY_BACKEND=mock`이면 GPU 없이도 전 경로가 돈다.** |
| `stt_worker_example.py` | 라이브 발언 STT 워커. Whisper로 전사하고 같은 프로세스에서 KURE-v1 임베딩까지 계산해 게이트웨이엔 텍스트+벡터를 그대로 넘긴다(게이트웨이엔 torch가 없어서). **`STT_BACKEND=mock`(기본값)이면 GPU 없이도 전 경로가 돈다.** 실제 방송 오디오는 OpenVidu 설치 전이라 아직 없다. |
| `chat_rag_worker_example.py` | 반복질문 답변 생성 워커. 게이트웨이가 `live_id`로 가져온 문서 후보 + 질문을 받아 KURE-v1로 임베딩·랭킹하고, 그라운딩 임계치를 넘으면 LangChain + `LiquidAI/LFM2.5-230M`으로 답변까지 생성해 돌려준다(검색·판단·생성을 왕복 1회로 처리). **`CHAT_RAG_BACKEND=mock`(기본값)이면 GPU 없이도 전 경로가 돈다.** |
| `garment_measurement_worker_example.py` | 의류 실측(cm) 측정 워커. 기준 물체(A4) 검출 → 원단 분할 → 랜드마크 검출 → cm 환산을 순서대로 처리하고, 앞 단계가 실패하면 뒷 단계(특히 GPU가 필요한 랜드마크 검출)를 아예 건너뛴다. 세 단계 모두 독립적으로 스왑 가능해 환경변수도 3개다. **전부 `mock`(기본값)이면 GPU/opencv 없이도 전 경로가 돈다.** |
| `models/sam3/` | 품질검수 판정 로직 — 세그멘테이션(목업/SAM3 PCS) · 하자 항목화 · 점수 · 히트맵 · 넘버링 bbox 이미지. **진짜 서브패키지**다(`__init__.py` 보유) — 이유는 아래 "왜 서브패키지인가" 참고. 순수 로직은 `AI/test/worker/sam3/`가 CI에서 검증한다. |
| `models/garment_measurement/` | 실측 판정 로직 — 기준물체 검출(목업/OpenCV) · 원단 분할(목업/GrabCut) · 랜드마크 검출(목업/HRNet) · cm 환산. `models/sam3/`와 같은 이유로 **진짜 서브패키지**다(`__init__.py` 보유) — 이유는 아래 "왜 서브패키지인가" 참고. 순수 로직은 `AI/test/worker/garment_measurement/`가 CI에서 검증한다. |
| `models/tryon_flux/` | FLUX.2-Klein worn-reference 생성(목업/`flux2_klein`). `models/sam3/`와 같은 이유로 **진짜 서브패키지**다. 원본(고객) 사진을 참조로 "이 사람에게 이 옷을 이 핏으로 입혀라" 프롬프트로 생성한다(`S15P11A108-504`, `AI/docs/tryon-advancement-strategy.md` §10.3). |
| `models/catvton/body_estimate.py` | 키/몸무게 → 평균 체형 치수(허리/가슴/어깨 등) 근사. 실측이 아니라 근사치다 — BE에 실측 컬럼이 생기면 우선순위가 밀린다. |
| `requirements.txt` | 워커 공통 의존성. `requests`, `Pillow`(storage_utils.py가 `PIL.Image`를 다룬다), `opencv-python-headless`(기준물체 검출·원단 분할, torch 불필요라 공용). CatVTON·HRNet 등 무거운 모델 자체의 의존성(torch, diffusers 등)은 각자 기존에 구성해둔 conda 환경을 그대로 쓴다 — 이 파일에 포함하지 않는다. |
| `.env.example` | 워커 실행에 필요한 환경변수 예시. 필요한 값은 아래 "실행 방법" 참고. |

## 실행 방법

### 1. 환경변수 설정

```bash
export GATEWAY_URL=https://i15a108.p.ssafy.io/ai
export WORKER_API_KEY=<EC2 .env의 WORKER_API_KEY와 동일한 값>
```

시착(tryon) 워커는 추가로 아래 환경변수도 쓸 수 있다 (생략 시 기본값 사용):

```bash
export CATVTON_CODE_PATH=/path/to/worker/models/catvton   # 기본값: worker/ 기준 models/catvton
export TRYON_MODEL_CODE_PATH=/path/to/worker/models       # 기본값: worker/ 기준 models (tryon_flux/quality_vlm의 부모)

export TRYON_VLM_BACKEND=mock       # 기본값. GPU 불필요 — 상품 캡션을 "garment" 고정 문구로 대체
export TRYON_VLM_BACKEND=qwen3_vl   # 실제 Qwen3-VL-4B(4bit). worker/models/quality_vlm/requirements.txt 필요

export TRYON_FLUX_BACKEND=mock         # 기본값. GPU/다운로드 불필요 — 참조(고객) 사진을 그대로 반환
export TRYON_FLUX_BACKEND=flux2_klein  # 실제 FLUX.2-Klein-4B(GGUF Q4_0). worker/models/tryon_flux/requirements.txt 필요, ~5-6GB VRAM
```

`TRYON_VLM_BACKEND=mock`/`TRYON_FLUX_BACKEND=mock`(둘 다 기본값)이면 CatVTON만 실제로
돌고 VLM/FLUX 단계는 GPU 없이 통과한다 — CatVTON 자체는 이 워커의 원래 기능이라 여전히
GPU가 필요하다(mock 백엔드 없음). 세 모델(VLM/FLUX/CatVTON) 전부 실제 백엔드로 돌릴 때는
**동시에 상주하지 않고 단계별로 순차 로드/언로드**한다(프로덕션엔 GPU 서버가 없고 팀원
노트북이 워커로 붙는 구조라 6GB급에서도 들어가게 하려는 설계, `AI/docs/
tryon-advancement-strategy.md` §10 참고).

품질검수 워커는 아래를 쓴다:

```bash
export QUALITY_BACKEND=mock          # 기본값. GPU 불필요 — 목업 인스턴스로 전 경로 검증
export QUALITY_BACKEND=sam3_pcs      # 실제 SAM3(facebook/sam3, gated repo). torch/transformers>=5.0 필요
export QUALITY_MODEL_CODE_PATH=/path/to/worker/models   # 기본값: worker/ 기준 models (sam3의 부모)
```

`mock` 백엔드는 `(product_id, image_index)` 해시로 하자 인스턴스(마스크+박스+score)를
**결정적으로 합성**한다(`worker/models/sam3/segmenter.py`의 `MockSegmenter`). GPU가 없는
팀원도 워커를 띄워 게이트웨이 큐 왕복부터 리포트 JSON까지 그대로 확인할 수 있다.

`sam3_pcs`로 전환하려면 ① https://huggingface.co/facebook/sam3 에서 gated 라이선스 동의 ②
`worker/models/sam3/requirements.txt` 설치(별도 conda 환경 권장, `validation/
requirements-test.txt`와 같은 환경에 섞지 말 것 — transformers 버전이 충돌한다) ③ `HF_TOKEN`
환경변수 또는 `huggingface-cli login`으로 승인된 계정 로그인이 먼저 필요하다.

STT 워커는 아래를 쓴다:

```bash
export STT_BACKEND=mock             # 기본값. GPU 불필요 — 결정적 더미 텍스트+임베딩으로 전 경로 검증
export STT_BACKEND=faster_whisper   # 실제 Whisper(small) + KURE-v1. torch/faster-whisper/sentence-transformers 필요
```

**`faster_whisper` 백엔드를 GPU로 돌리면 겪을 수 있는 문제(실측, `S15P11A108-443`)**:

- `pip install faster-whisper`가 별도로 필요하다 — `worker/requirements.txt`엔 없다(무거운 모델
  의존성은 conda 환경에서 개별 설치하는 원칙).
- `RuntimeError: Library cublas64_12.dll is not found or cannot be loaded`가 날 수 있다.
  `faster-whisper`(CTranslate2)는 **CUDA 12용** cuBLAS/cuDNN을 찾는데, torch가 CUDA 13(cu130)
  빌드면 시스템에 그 라이브러리가 없어서 발생한다. 해결:
  ```bash
  pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
  # 설치된 DLL 경로를 PATH에 추가하고 실행 (Windows, Git Bash 기준)
  export PATH="$CONDA_PREFIX/Lib/site-packages/nvidia/cublas/bin:$CONDA_PREFIX/Lib/site-packages/nvidia/cudnn/bin:$PATH"
  python stt_worker_example.py
  ```

chat_rag 워커는 아래를 쓴다:

```bash
export CHAT_RAG_BACKEND=mock             # 기본값. GPU 불필요 — 결정적 임베딩 + 최상위 근거 그대로 반환
export CHAT_RAG_BACKEND=lfm2_langchain   # 실제 KURE-v1 + LangChain/LFM2.5-230M. torch/sentence-transformers/langchain_huggingface/transformers 필요
```

실측 워커는 3단계 각각 독립적인 환경변수를 쓴다(`worker/models/garment_measurement/registry.py`의
`*_BACKENDS` 딕셔너리 키):

```bash
export REFERENCE_BACKEND=mock            # 기본값. GPU/opencv 불필요
export REFERENCE_BACKEND=opencv_contour  # 실제 A4 검출. opencv-python-headless만 필요(torch 불필요)

export SEGMENTATION_BACKEND=mock         # 기본값. GPU/opencv 불필요
export SEGMENTATION_BACKEND=grabcut      # 실제 GrabCut. opencv-python-headless만 필요(torch 불필요)

export LANDMARK_BACKEND=mock             # 기본값. GPU/torch 불필요
export LANDMARK_BACKEND=hrnet_deepfashion2   # 실제 HRNet. torch/torchvision/yacs/opencv-python 필요

# hrnet_deepfashion2를 쓸 때만 필요. 체크포인트는 HuggingFace가 아니라 OneDrive 수동 다운로드다.
export HRNET_CHECKPOINT_PATH=/path/to/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth
# 기본값: worker/models/garment_measurement/hrnet/models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth
```

**HRNet 체크포인트 받는 법**: [OneDrive](https://shanghaitecheducn-my.sharepoint.com/:f:/g/personal/qianshh_shanghaitech_edu_cn/Eo1g551GvWpHtrXxdeYptH4BGUqWCI81fbT1prL93e0z2Q?e=cj6phH)의
`models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth`만 받으면 된다(같은 폴더의
`data/`·`checkpoints/`는 학습·평가용이라 필요 없다). `HRNET_CHECKPOINT_PATH`로 위치를
지정하거나, 위 기본 경로에 그대로 두면 된다 — `worker/models/garment_measurement/hrnet/.gitignore`가
`models/`를 무시하므로 실수로 커밋될 걱정은 없다.

**왜 `models/garment_measurement/`·`models/sam3/`가 서브패키지인가**: 여러 워커 패키지의
`contracts.py`/`registry.py`/`segmenter.py` 등을 flat하게 sys.path에 바로 두면, 서로 다른
폴더가 같은 이름의 파일을 가지고 있어서(AI의 pytest 세션처럼 여러 패키지가 동시에 sys.path에
들어가는 상황) `import contracts`가 어느 쪽을 가져올지 꼬인다(먼저 import된 모듈이 전역
캐시에 남음 — `S15P11A108-339` 구현 중 삭제 전 `models/clipseg/`와 겪었던 실제 버그). 그래서
이 둘은 `__init__.py`를 둬서 진짜 패키지로 만들고, `MEASUREMENT_CODE_PATH`/
`QUALITY_MODEL_CODE_PATH`(기본값: `worker/models/`, 즉 이 폴더의 **부모**)를 sys.path에 넣어
`from garment_measurement.xxx import ...`/`from sam3.xxx import ...` 형태로만 접근한다.

```bash
export MEASUREMENT_CODE_PATH=/path/to/worker/models   # 기본값: worker/ 기준 models (garment_measurement의 부모)
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

## 시착 워커 동작 방식 (`S15P11A108-504`)

VLM 캡션 → 신체 치수 근사/핏 계산 → FLUX worn-reference 생성 → CatVTON 합성, 4단계를
순서대로 처리한다(`AI/docs/tryon-advancement-strategy.md` §9~§10에서 검증한 fit-aware
worn-reference 기법의 프로덕션 버전). **최종 결과에는 실제 고객 사진(`user_image_url`)이
나온다** — FLUX가 그 고객 사진을 참조로 worn-reference를 생성하므로, 재사용/캐싱 대상이
아니라 매 요청마다 새로 생성한다.

`fit_type`엔 `cropped`가 없다 — 옷을 짧게 만들어 마스크 하단을 제외하면 그 자리에
diffusion이 맨살을 새로 생성해야 하는데, AI 가드레일상 정책적으로 피해서 뺐다
(`AI/app/tryon/schemas.py`의 `MaskFitType` 참고). 실제로 핏(타이트/루즈 정도)은 이제
`fit_type` 3단계가 아니라, 신체/상품 치수 비율을 FLUX 프롬프트에 반영하는 방식으로
연속적으로 조절된다 — `fit_type`은 치수 데이터가 전혀 없을 때만 쓰이는 최후 폴백이다.

### job payload 형식

```json
{
  "user_image_url": "https://.../person.jpg",
  "product_image_url": "https://.../cloth.jpg",
  "mask_type": "upper",
  "fit_type": "regular",
  "num_inference_steps": 50,
  "guidance_scale": 3.0,
  "body_height_cm": 170.0,
  "body_weight_kg": 65.0,
  "body_waist_cm": null,
  "garment_measurements": {"WAIST_WIDTH": 42.0}
}
```

`mask_type`은 `upper`/`lower` 중 하나(생략 시 `upper`). `fit_type`은 `regular`/`oversized`
중 하나(생략 시 `regular`). `body_waist_cm`(BE 컬럼 미확정, 항상 `null`일 수 있음)이 있으면
그 실측값을, 없고 `body_height_cm`/`body_weight_kg`가 있으면 `body_estimate.py`의 근사치를
쓴다. `garment_measurements["WAIST_WIDTH"]`까지 있어야 실제로 핏이 계산된다 — 그 전엔
"regular fit" 고정으로 worn-reference를 생성한다.

### 결과 형식

```json
{
  "image_url": "https://i15a108.p.ssafy.io/results/tryon-results/xxx.png",
  "mask_preview_url": "https://i15a108.p.ssafy.io/results/tryon-masks/xxx.png",
  "worn_reference_url": "https://i15a108.p.ssafy.io/results/tryon-worn-references/xxx.png",
  "fit_type": "regular",
  "adaptive_masking_used": false
}
```

`worn_reference_url`은 FLUX가 생성한 중간 산출물(디버깅/고객 확인용)이다.
`adaptive_masking_used`는 신체/상품 치수 비율로 실제 핏 계산이 이뤄졌는지를 나타낸다.

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

## 실측 워커 동작 방식

의류 실측(cm) 측정(`S15P11A108-339`)의 3단계를 전부 이 워커 안에서 순서대로 처리한다: 기준
물체(A4) 검출 → (실패 시 즉시 재촬영 사유 반환) → 원단 분할 → (실패 시 즉시 반환) → 랜드마크
검출 → cm 환산. 원단 분할이 찾은 bbox를 랜드마크 검출에 그대로 넘겨서 크롭 영역으로 쓴다.

카테고리는 DeepFashion2 13종 중 실사진 + 공식 정의도로 대조 검증된 3개만 지원한다
(`SHORT_SLEEVE_TOP`/`TROUSERS`/`LONG_SLEEVE_DRESS`) — 나머지는 검증 전까지 범위 밖이다
(`worker/models/garment_measurement/registry.py`의 `DF2_CATEGORY_RANGES` 참고).

### job payload 형식

```json
{
  "product_id": 1042,
  "image_url": "https://.../scan.jpg",
  "category": "SHORT_SLEEVE_TOP",
  "reference_object": "A4_PAPER"
}
```

### 결과 형식

```json
{
  "measurement_id": "scan_1042_...",
  "product_id": 1042,
  "model": {"reference_backend": "opencv_contour", "segmentation_backend": "grabcut", "landmark_backend": "hrnet_deepfashion2"},
  "reference_object_found": true,
  "pixel_to_cm_ratio": 0.2645,
  "landmarks": [{"type": "SHOULDER_LEFT", "pixel_x": 320.0, "pixel_y": 210.0, "confidence": 0.93}, ...],
  "measurements": [{"type": "SHOULDER_WIDTH", "value_cm": 52.0, "confidence": 0.9}, ...],
  "overall_confidence": 0.87,
  "needs_retake": false,
  "retake_reason": null,
  "notes": [],
  "latency_ms": 340.5
}
```

`needs_retake=true`면 `landmarks`/`measurements`가 비어 있다 — `retake_reason`으로 어느 단계에서
막혔는지(`REFERENCE_NOT_FOUND`/`GARMENT_NOT_FOUND`/`LOW_LANDMARK_CONFIDENCE`) 알 수 있다.

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

`TryonWorker`의 `_ensure_*_loaded()`류 메서드와 `run_inference()` 안, 딱 이 두 곳만
모델별로 갈아끼우면 된다(CatVTON은 `_ensure_catvton_loaded()`, VLM/FLUX는 각각
`_ensure_vlm_loaded()`/`_generate_worn_reference()` 안에서 지연 로드). `base_worker.py`,
게이트웨이(`AI/app/gateway/`), job/result 스키마는 전혀 건드릴 필요가 없다 — 이게 처음부터
이 구조를 이렇게 짠 이유다.

## 남은 작업 (시착 워커, `S15P11A108-504`)

- `TRYON_VLM_BACKEND=qwen3_vl TRYON_FLUX_BACKEND=flux2_klein`로 실제 GPU 노트북에서 4단계
  전체(VLM 캡션 → FLUX worn-reference → CatVTON 합성) 엔드투엔드 스모크 테스트 — 지금까지는
  단위 함수(신체 치수 근사, 핏 계산, 프롬프트 생성)와 CatVTON 파이프라인 자체만 개별
  검증했고, 세 모델을 한 프로세스 안에서 순차로 로드/언로드하는 전체 흐름은 아직 실측
  전이다. 피크 VRAM이 6GB 안에 들어오는지도 이때 같이 확인한다.
- 카테고리(하의/상의/아우터/액세서리) 정보가 BE에서 아직 안 넘어와 `mask_type`을 요청값
  그대로 신뢰한다 — BE 요청 문서(`.claude/requests/be/`) 회신 후 자동 판별 추가.

## 남은 작업

- 품질검수 워커를 실제 GPU 노트북에서 `QUALITY_BACKEND=sam3_pcs`로 돌려보기 (지금까지는 `mock`으로만 검증했다 — 절차는 위 "실행 방법" 참고)
- 워커 여러 대(팀원별)를 동시에 띄웠을 때 동작 검증
- CatVTON 모델 로딩 시간이 길 경우, 워커 기동 시점에 미리 로딩해두는 방식(lazy 대신 eager)으로 바꿀지 검토
- STT 워커를 실제 GPU 노트북에서 `STT_BACKEND=faster_whisper`로 돌려보기 (지금까지는 `mock`으로만 검증했다)
- OpenVidu 설치 후 실제 방송 오디오로 STT 워커 E2E 검증
- chat_rag 워커를 실제 GPU 노트북에서 `CHAT_RAG_BACKEND=lfm2_langchain`으로 돌려보기 (지금까지는 `mock`으로만 검증했다)
- 워커 호출 전 답변 캐시(같은 `live_id` 안 유사 질문 재사용, ONNX 임베더) — 별도 후속 작업
- 실측 워커: `opencv_contour`/`grabcut`의 임계치(Canny, GrabCut 초기 사각형 마진 등)를 실제
  판매자 촬영 사진으로 계속 보정 — 지금까지는 합성 이미지로만 검증했다
  (`AI/test/worker/garment_measurement/`)
- 실측 워커: DeepFashion2 나머지 10개 카테고리(긴팔상의/아우터 2종/조끼/슬링/반바지/치마/
  반팔원피스/조끼원피스/슬링원피스) — 실사진 확보되는 대로 `AI/validation/garment-landmark-check/
  verify_hrnet_landmarks.py`로 눈으로 대조 검증 후 `registry.py`에 추가
