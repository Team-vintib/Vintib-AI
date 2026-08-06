# CH022 — 워커 VLM/FLUX 4bit 가중치 사전 양자화 캐싱

## 배경/목표

로컬 6GB GPU 워커는 VLM/FLUX/CatVTON이 동시에 상주할 수 없어(CH019) job마다 언로드 후
재로드한다. 실측 결과 가중치 자체는 이미 로컬 HF 캐시에 있어 네트워크 다운로드가 아니라,
Qwen VLM과 FLUX 텍스트 인코더가 `BitsAndBytesConfig(load_in_4bit=True, ...)`로 **매 job마다
런타임 4bit 양자화를 다시 계산**하는 게 로딩 시간(job당 1~2분)의 실제 병목이었다.

양자화 결과를 최초 1회만 계산해 디스크에 저장해두고, 그다음부터는 양자화 계산 없이 그
저장본을 그대로 로드해서 이 비용을 없앤다.

## 작업 내용

- `transformers`는 4bit 양자화된 모델을 `model.save_pretrained(path)`로 저장할 수 있고,
  저장된 체크포인트의 `config.json`에 `quantization_config`가 함께 기록되어 이후
  `from_pretrained(path)` 호출 시 `BitsAndBytesConfig`를 다시 안 줘도 자동으로 인식해서
  "이미 양자화된 가중치를 그대로 로드"만 한다(런타임 양자화 재계산 없음).
- `load_qwen_vl()`(`worker/models/quality_vlm/loader.py`)과 FLUX 텍스트 인코더 로딩부
  (`worker/models/tryon_flux/generator.py`의 `Flux2KleinGenerator._load()`)에 캐시 경로
  체크를 추가한다: 캐시 디렉터리가 있으면 거기서 바로 로드, 없으면 기존처럼 양자화한 뒤
  그 디렉터리에 `save_pretrained()`로 한 번 저장(최초 1회만 느림, 이후 job은 다 빠름).
- 캐시 경로는 env var(`WORKER_QUANT_CACHE_DIR`, 기본값 `worker/.cache/quantized/`)로
  관리하고 `.gitignore`에 추가한다(로컬 산출물, 커밋 대상 아님).
- 대상은 bnb 4bit 런타임 양자화가 실제로 일어나는 두 곳(Qwen VLM, FLUX 텍스트 인코더)만.
  FLUX transformer(GGUF, 이미 사전 양자화된 포맷)와 CatVTON(SD-inpainting bf16, 양자화
  없음)은 이 병목과 무관해서 범위 밖.
- 디스크 추가 용량: 모델당 수 GB 예상(로컬 개발 전용 워커라 문제 없음, EC2엔 GPU 워커
  없음 — `AI/docs/infra-architecture.md`).

## 구현 목록

- [ ] `quality_vlm/loader.py`: `load_qwen_vl()`에 캐시 디렉터리 존재 여부 체크 → 있으면
      `quantization_config` 없이 로드, 없으면 기존 로직대로 양자화 후 `save_pretrained()`
- [ ] `tryon_flux/generator.py`: `Flux2KleinGenerator._load()`의 text_encoder 로딩에
      동일 패턴 적용
- [ ] 두 곳 로직이 거의 같으면 공용 헬퍼로 묶고, 아니면 각자 구현(중복이 적으면 억지로
      추상화하지 않는다)
- [ ] `.env.example`/`worker/README`에 `WORKER_QUANT_CACHE_DIR` 설명 추가, `.gitignore`에
      캐시 디렉터리 추가
- [ ] 실측: 캐시 miss(최초 1회) vs hit(그다음부터) 로딩 시간 비교해서 실제로 줄었는지 확인

## 확인 필요

- 캐시 디렉터리 기본 위치를 `worker/.cache/quantized/`(프로젝트 스코프)로 둘지, HF 표준
  캐시 관례를 따라 `HF_HOME` 하위에 둘지 — 전자가 "워커 전용 산출물"이라는 의미가 더
  명확해서 기본값으로 제안.
