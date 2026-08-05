# VLM 하자 설명 — 프로덕션 파이프라인 연결 (CH009 "3. 프로덕션 연결")

> 대상 티켓: `S15P11A108-309`(하자 설명 sVLM 선정·검증·연결) 이어서. 브랜치는 기존과
> 동일 `feat/211-vlm-defect-description` 유지.

## Context

`Finding.description`(`worker/models/sam3/contracts.py`, `AI/app/quality/schemas.py`)은
CH007부터 스키마에 있었지만 항상 `None`이었다 — "sVLM이 나중에 채울 자리"로 남겨둔
필드다. 이번 세션에서 CH009 계획의 1~2단계(후보 선정·검증)를 실제로 끝냈다:

- `Qwen/Qwen3-VL-4B-Instruct`를 4bit 양자화로 SAM3와 같은 conda 환경(`qual`)에서 동시
  구동 가능함을 실측 확인(VRAM 여유 충분, 의존성 충돌 없음).
- 프롬프트에서 위치(부위)를 물으면 hallucination이 생기는 걸 발견 → **위치는 VLM에게
  묻지 않고, bbox 기반으로 별도 계산**하는 방식으로 확정(`build_defect_prompt()` +
  `bbox_grid_position()`/`compose_finding_bullet()`, `AI/validation/QUAL/vlm-description-check/`).
- SAM3 cross-type 중복 검출 버그를 프로덕션에서 수정 완료(CH010) — findings 품질이
  안정된 상태.

이제 이 검증된 코드를 **프로덕션 워커 파이프라인에 연결**해서, 검수 결과 JSON의
`findings[].description`이 실제 문장으로 채워지게 한다. 요구사항: ① API/메서드를
파일별로 적절히 분리 ② 모델을 나중에 파인튜닝하거나 다른 모델로 바꿀 때 설정 하나만
바꿔 갈아끼울 수 있게 ③ 프롬프트 엔지니어링/One-shot·Few-shot 실험을 위한 TODO 영역을
만들어 `vlm_description_check.ipynb`에서 먼저 검증 후 반영하는 흐름을 유지.

**결정 사항(사용자 확인 완료)**:
- 지연시간이 커서(finding당 3~9초, 이미지 1장에 6~16건 가능) `InspectionRequest`에
  `include_descriptions: bool = False` **옵트인 플래그**를 추가한다(`include_attention_maps`와
  같은 패턴).
- 설명 생성 대상은 **`FindingStatus.detected`만**(SUSPECTED 제외) — 호출 수를 줄인다.

## 구현 내용

### 1. `worker/models/sam3/prompts.py` — 부위 한글 라벨 추가

- `SECTION_LABELS_KO: dict[GarmentSection, str]`(16개 값: 어깨/목깃/소매/가슴/밑단/허리/
  허벅지/사타구니/정강이 계열) 추가. `GarmentSection`/`section_label()`이 이미 있는
  파일이라 "부위 의미"의 정본 위치를 유지한다 — `quality_vlm` 쪽에 새로 두지 않는다.
  `Finding.section`이 이미 카테고리별로 정확히 계산돼 있으므로, VLM이 만든
  `bbox_grid_position()`(카테고리 무관 3×3 격자, 스파이크 전용)은 프로덕션에서 재사용하지
  않는다 — 더 정확한 신호가 이미 있다.

### 2. 신규 패키지 `worker/models/quality_vlm/`

`worker/models/sam3/`와 같은 "진짜 서브패키지" 관례(`__init__.py` 보유, `worker/models/`를
sys.path에 넣고 `quality_vlm.xxx`로 접근)를 따른다.

- **`registry.py`** — `SegmenterConfig`/`segmenter_config()` 패턴을 그대로 미러링:
  - `VlmConfig(TypedDict)`: `model_id: str | None`, `description: str`,
    `quantization: str`, `max_new_tokens: int`.
  - `VLM_BACKENDS: dict[str, VlmConfig]` — `"mock"`(model_id=None, 정적 문구),
    `"qwen3_vl"`(`Qwen/Qwen3-VL-4B-Instruct`, `quantization="4bit"`, `max_new_tokens=80`).
    **파인튜닝/모델 교체 시 여기 항목만 추가하고 `ACTIVE_VLM_BACKEND`(또는
    `QUALITY_VLM_BACKEND` 환경변수)만 바꾸면 된다** — 요구사항 ②를 이 레지스트리 하나로
    만족.
  - `ACTIVE_VLM_BACKEND = "mock"`, `vlm_config(key=None)` 리졸버(같은 try/except/ValueError
    형태).
- **`loader.py`** — `AI/validation/QUAL/vlm-description-check/loaders.py`에서 검증된
  `VLMBundle`/`load_qwen_vl()`/`generate_from_image()`를 거의 그대로 승격. 무거운 import
  (torch/transformers/bitsandbytes)는 함수 내부 지연 import 유지 — mock 경로는 이 파일을
  아예 건드리지 않는다.
- **`prompts.py`** — 검증된 `build_defect_prompt()`(위치 언급 금지, 시각 특징만) +
  `compose_finding_bullet()` 승격. 상단에 명시적 TODO 블록:
  ```python
  # TODO: 프롬프트 엔지니어링 — AI/validation/QUAL/vlm-description-check/vlm_description_check.ipynb
  #       §4/§5(PROMPT_VARIANTS)에서 먼저 검증한 뒤 이 함수에 반영한다.
  # TODO: One-shot / Few-shot 프롬프팅 — 텍스트 기반 예시로 답변 형식을 고정하는 실험도
  #       같은 노트북에서 먼저 검증한다(이미지 few-shot은 지연시간 비용이 커서 텍스트
  #       예시부터 시도).
  ```
- **`describer.py`** — SAM3의 `segmenter.py`(`DefectSegmenter(ABC)` + `build_segmenter()`)
  패턴을 그대로 미러링:
  - `DefectDescriber(ABC)`: 추상 메서드 `describe(image: Image, finding: Finding) -> str`.
  - `MockDescriber(DefectDescriber)`: `f"{finding.label} 발견"` 같은 정적 문구, torch 불필요.
  - `Qwen3VlDescriber(DefectDescriber)`: `__init__`에서 `load_qwen_vl()` 즉시 로드(SAM3
    세그멘터와 동일하게 워커 프로세스당 1회), `describe()`는 `build_defect_prompt()` +
    `generate_from_image()` + `compose_finding_bullet(SECTION_LABELS_KO[finding.section], ...)`.
  - `build_describer(key: str, config: VlmConfig) -> DefectDescriber` 팩토리(`build_segmenter()`
    미러) — 키로 분기하지, `model_id is None` 같은 구조 추론으로 분기하지 않는다.
  - `attach_descriptions(results, findings, describer) -> list[Finding]`:
    - `FindingStatus.detected`인 것만 처리(SUSPECTED는 건너뜀 — 원본 그대로 유지).
    - `finding.image_index`로 `SegmentationResult`를 찾아 `base_image`+`size`로 bbox를
      절대 픽셀로 역정규화해 크롭.
    - **각 finding 호출을 개별 `try/except Exception`으로 감싼다** — 하나 실패해도
      `description=None`으로 남기고 계속 진행(`inspection_logger`의 "best-effort, 응답을
      막지 않는다" 원칙과 동일).
    - `dataclasses.replace(finding, description=text)`로 새 리스트 반환(frozen dataclass).
- **`requirements.txt`** — `bitsandbytes>=0.50`만(SAM3와 같은 `qual` conda 환경 재사용,
  이번 세션에 호환 확인됨 — 별도 환경 불필요).

### 3. `worker/quality_check_worker_example.py` 배선

- import 추가: `from quality_vlm import registry as vlm_registry`,
  `from quality_vlm.describer import attach_descriptions, build_describer`.
- `QUALITY_VLM_BACKEND = os.getenv("QUALITY_VLM_BACKEND", vlm_registry.ACTIVE_VLM_BACKEND)`.
- `__init__`: `self._describer = None`, `self._vlm_config = vlm_registry.vlm_config(QUALITY_VLM_BACKEND)`.
- 신규 `_ensure_vlm_loaded()`(`_ensure_loaded()` 미러): `build_describer(...)` 호출을
  `try/except`로 감싸 **로드 실패 시 `"mock"`으로 폴백**(작업 전체를 실패시키지 않는다 —
  `run_inference`를 감싸는 `BaseWorker`의 예외 처리는 job 전체를 `"failed"`로 만들어
  `result` 자체가 사라지므로, description 하나 때문에 검수 전체를 잃으면 안 된다).
- `run_inference()`: 기존 `score_findings`/`build_notes`/`build_attention_maps`/
  `build_annotated_images` 호출은 **그대로 둔다**(이 함수들은 description을 안 본다).
  `payload.get("include_descriptions")`가 True일 때만, **`build_annotated_images` 다음,
  `result = {...}` 조립 직전**에:
  ```python
  findings = extracted.findings
  if payload.get("include_descriptions"):
      self._ensure_vlm_loaded()
      findings = attach_descriptions(results, extracted.findings, self._describer)
  ```
  그리고 `result["findings"] = [f.to_dict() for f in findings]`로 바꾼다(다른 곳은
  `extracted.findings` 그대로). 이 위치를 고른 이유: bbox 오버레이(필수 산출물)가 VLM
  실패로 절대 막히면 안 되므로, VLM 단계를 그 뒤에 둔다.

### 4. `AI/app/quality/schemas.py` — 옵트인 플래그 추가

- `InspectionRequest`에 `include_descriptions: bool = False` 필드 추가
  (`include_attention_maps`와 같은 자리·같은 스타일).
- `worker/models/sam3/contracts.py`/`AI/app/quality/schemas.py`의 `Finding.description`
  docstring 갱신("sVLM이 나중에 채울 자리" → 실제로 채워짐, 조건 명시).

### 5. BE 계약 문서

- `.claude/requests/be/` 에 신규 문서(예: `002-quality-inspection-descriptions.md`) —
  `include_descriptions` 옵트인 필드 추가를 BE에 알림. 기존
  `.claude/requests/be/001-quality-inspection-async.md`와 같은 형식.

### 6. `vlm_description_check.ipynb` — TODO 실험 백로그

- §4/§5 근처에 마크다운 셀 추가:
  ```
  ## TO-DO: 프롬프트 실험 백로그

  - [ ] 프롬프트 엔지니어링 — 문구 변형을 계속 실험(현재 PROMPT_VARIANTS 확장)
  - [ ] One-shot 프롬프팅 — 텍스트 예시 1개로 답변 형식(문장 길이·순서) 고정
  - [ ] Few-shot 프롬프팅 — 예시 2~3개, 이미지 없이 텍스트만으로 형식 고정
  - [ ] 위 실험에서 좋은 결과가 나오면 worker/models/quality_vlm/prompts.py의
        build_defect_prompt()에 반영
  ```

## 성능/안정성 메모 (v1 범위로 명시)

- v1은 finding마다 순차 호출(배치/병렬화 없음) — 이미지당 수십 초~수 분 걸릴 수 있음을
  `include_descriptions` 플래그 도입으로 흡수한다. 배치/병렬화는 후속 과제로 남긴다.
- 모델 로드 실패·개별 finding 생성 실패 둘 다 "작업 전체 실패"로 이어지지 않게
  best-effort 처리(위 2/3 참고).

## 테스트 계획

`AI/test/worker/quality_vlm/` 신규(`AI/test/worker/sam3/`와 같은 위치 규약):
- `build_describer("mock", ...)`가 `MockDescriber`를 반환하고 torch 없이 동작하는지.
- `attach_descriptions`가 SUSPECTED를 건너뛰는지, 실패한 finding은 `description=None`
  유지하고 나머지는 계속 처리하는지(mock으로 강제 실패 주입).
- `dataclasses.replace` 결과가 원본 리스트를 변경하지 않는지(불변성).
- `worker/quality_check_worker_example.py`의 `_ensure_vlm_loaded()` 로드 실패 시 mock
  폴백 동작(있다면 기존 `_ensure_loaded()` 테스트 패턴 참고).
- `AI/app/quality/schemas.py`의 `InspectionRequest.include_descriptions` 기본값 테스트.

## 검증 방법

1. `cd AI && ruff check . && black --check . && pytest -q` — 전부 통과.
2. `QUALITY_BACKEND=mock QUALITY_VLM_BACKEND=mock python worker/quality_check_worker_example.py`
   로 목업 경로 스모크 테스트(torch 불필요) — `include_descriptions=true` 요청 시
   findings에 정적 문구가 채워지는지 확인.
3. 실 GPU(`qual` conda 환경)에서 `QUALITY_VLM_BACKEND=qwen3_vl`로 1회 수동 스모크
   테스트는 **사용자가 직접 실행**(무거운 다운로드/GPU 리소스).

## 커밋 계획

1. `docs:` 이 계획 문서
2. `feat:` `worker/models/quality_vlm/` 패키지 신설 + `sam3/prompts.py` SECTION_LABELS_KO
3. `feat:` 워커 배선(`quality_check_worker_example.py`) + 스키마 옵트인 플래그
4. `test:` 신규 단위 테스트
5. `docs:` BE 요청 문서 + 노트북 TODO 섹션
