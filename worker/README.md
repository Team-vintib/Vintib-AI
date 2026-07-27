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
| `storage_utils.py` | 결과 이미지를 게이트웨이의 업로드 엔드포인트로 전송하는 유틸(`download_image`/`upload_image`). S3 권한이 없어 EC2 로컬 디스크 저장 방식을 쓰기 때문에, 워커가 직접 디스크에 쓰지 않고 HTTP로 전송한다. `tryon_worker_example.py`가 import하므로 이 파일 없이는 워커가 기동하지 않는다. |
| `tryon_worker_example.py` | 시착(CatVTON) 워커. 현재 `worker/models/catvton`의 검증 코드(`verify_fit_tryon.py`)를 기반으로 실제 모델이 연결되어 있다. |
| `quality_check_worker_example.py` | 품질검수 워커 예시. **모델 연결은 아직 TODO 상태.** 판정 로직(프롬프트·임계치·하자 항목화·점수·오버레이)은 `AI/app/quality/`에 이미 구현돼 있고, 비동기 전환 시 이쪽으로 옮겨온다. |
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

- `quality_check_worker_example.py`에 실제 ViT 모델 연결 (현재 TODO)
- 워커 여러 대(팀원별)를 동시에 띄웠을 때 동작 검증
- CatVTON 모델 로딩 시간이 길 경우, 워커 기동 시점에 미리 로딩해두는 방식(lazy 대신 eager)으로 바꿀지 검토
