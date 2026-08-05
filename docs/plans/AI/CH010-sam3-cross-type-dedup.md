# SAM3 cross-defect-type 중복 검출 dedup — 프로덕션 + masking 노트북

> 대상 티켓: 에픽 `S15P11A108-211` [품질 검수]. 작업 키는 문서 히스토리 참고
> (309 세션에서 VLM 스파이크 검증 중 발견된 버그).

## Context

SAM3는 하자 유형(DefectType)마다 **독립된 영어 명사구 프롬프트**로 탐지한다
(`"a dirty mark"` → DIRT_MARK, `"a hole or tear in fabric"` → HOLE_TEAR 등,
`worker/models/sam3/prompts.py`의 `_DEFECT_PROMPTS`). 사용자가 `scratch.jpg` 실측
결과(`sam3_qc_test_masking.ipynb` 산출물, 11개 인스턴스)와 그 넘버링 bbox 오버레이
이미지를 대조하다가, **같은 실물 부위가 DIRT_MARK와 HOLE_TEAR 두 프롬프트 모두에
거의 동일한 bbox/mask로 잡혀 별도 Finding 2개가 되는 경우**를 발견했다(5쌍 확인,
bbox가 1px 이내로 겹침). 이 중복 쌍 중 confidence가 낮은 쪽이 numbering 순서상
나중에 그려져 먼저 그려진 쪽의 라벨을 시각적으로 덮어버려서, 오버레이 이미지에는
6~11번만 보이고 1~5번은 화면에서 사라진 것처럼 보였다 — "bbox 넘버링이 6부터
시작한다"는 사용자 관찰의 실제 원인이다.

탐색 결과 이 버그는 **검증 스파이크뿐 아니라 프로덕션(`worker/models/sam3/findings.py`)
에도 동일하게 존재**한다 — 같은 두 프롬프트 세트를 그대로 쓰고, `suppress_benign()`은
"양성(주름·그림자 등)" 카테고리하고만 비교할 뿐 서로 다른 하자 유형끼리는 비교하지
않는다. `findings.py` 모듈 docstring에는 이미 "실측에서 중복 검출이 관찰되면 후속
작업으로 병합 로직을 추가한다"는 미해결 TODO가 있다 — 이번이 그 후속 작업이다.

사용자가 범위를 명시적으로 정했다: **프로덕션 + `sam3_qc_test_masking.ipynb`(VLM
스파이크가 실제로 소비하는 노트북)만 고친다.** `sam3_qc_test.ipynb`/bbox_crop 변형/
CLIPSeg/hybrid 노트북은 이번 범위 밖(다운스트림에서 안 쓰는 PoC라 우선순위 낮음).
같은 실물 부위가 서로 다른 타입으로 중복 검출되면 confidence 높은 쪽을 남긴다(신뢰
등급 기반 우선순위는 채택 안 함 — 단순성 우선).

## 구현 내용

### 1. `worker/models/sam3/findings.py` (프로덕션 핵심)

- `_containment()` 옆에 `_mask_iou(a, b) -> float`(표준 IoU = `|a∩b|/|a∪b|`) private
  헬퍼 추가 — `AI/validation/QUAL/qc_shared.py`의 `mask_iou()`와 같은 계산, 다만
  프로덕션은 validation을 import하지 않으므로 로컬 사본을 둔다(기존 `_containment`도
  같은 방식으로 이미 중복돼 있다).
- 새 함수 `dedupe_cross_type_overlap(instances, min_iou) -> tuple[list[Instance], list[Instance]]`:
  - `(-confidence, defect_type.value)` 기준 정렬(동률일 때 결정적 tie-break —
    `_to_findings()`가 이미 쓰는 것과 같은 키를 재사용).
  - 이미 `kept`에 들어간 인스턴스 중 **다른 `defect_type`**이면서 `_mask_iou >= min_iou`인
    게 있으면 버린다. 같은 타입끼리는 비교하지 않는다(같은 프롬프트 내부 중복은 SAM3
    자체가 이미 걸렀다고 가정).
  - docstring에 알려진 단순화를 명시: 이건 "이미 kept된 것과만 비교"하는 그리디라
    IoU가 전이적이지 않은 경우(A-B 겹침, B-C 겹침, A-C는 안 겹침) 이론상 놓칠 수
    있음 — 실측 중복은 IoU가 매우 높아(거의 동일 bbox) 이 케이스가 실제로 발생할
    가능성은 낮다고 판단해 1차로는 그리디로 간다.
- `extract_findings()`의 per-image 루프에서 `suppress_benign` 결과(`final`)를 다시
  `dedupe_cross_type_overlap`에 통과시킨다 — **benign 억제 다음, `kept_by_image`/
  `kept_instances_by_image` 누적 전**:
  ```python
  if config["dedupe_cross_type"]:
      final, _cross_type_dupes = dedupe_cross_type_overlap(final, config["cross_type_iou_min"])
  ```
  이 순서가 중요한 이유: benign 억제가 먼저 실행돼 구조적 개구부 오탐(hole_tear)을
  먼저 제거해야, cross-type dedup이 "진짜 하자끼리의 중복"만 보게 된다.
  `kept_instances_by_image`는 `overlay.py`의 attention map 렌더링이 그대로 쓰는
  값이라(모듈 docstring에 이미 명시된 불변식), 여기서 제거하면 넘버링 bbox와
  attention map 양쪽에서 일관되게 중복이 사라진다 — 별도 예외 처리 불필요.
- 모듈 docstring의 "실측에서 중복 검출이 관찰되면 후속 작업으로 병합 로직을 추가한다"
  TODO를 이번에 구현한 내용으로 갱신(더 이상 미해결 아님, 이 계획 문서 참조 추가).

### 2. `worker/models/sam3/registry.py`

- `SegmenterConfig` TypedDict에 필드 2개 추가:
  - `dedupe_cross_type: bool` — on/off 스위치(`suppress_benign` 필드와 대칭, 롤백/테스트
    편의).
  - `cross_type_iou_min: float` — dedup 임계치.
- `"mock"`/`"sam3_pcs"` 두 백엔드 모두에 `"dedupe_cross_type": True, "cross_type_iou_min": 0.7`
  추가. **0.7을 쓰는 이유**: 실측 중복 쌍은 bbox가 1px 이내로 거의 동일해 IoU가
  0.9대로 매우 높다 — 0.5보다 여유 있게 0.7로 잡아야 "진짜 인접했지만 서로 다른
  하자"를 잘못 합칠 위험이 줄어든다. `confident_threshold`와 같은 스타일로 "⚠️ 라벨링된
  검증셋 없이 잡은 값, 스윕 대상" 주석을 남긴다.

### 3. `AI/test/worker/sam3/test_sam3_findings.py`

기존 헬퍼(`_instance()`, `_mask_at()`, `_full_mask()`) 재사용. 추가할 테스트:

- `dedupe_cross_type_overlap()` 직접 테스트(기존 `filter_by_garment`/`suppress_benign`처럼
  단위 + 통합 둘 다):
  - 같은 위치, 다른 타입, 겹침 큼 → confidence 높은 쪽만 남음.
  - 같은 위치, 다른 타입, confidence 동률 → `defect_type.value` tie-break로 결정적 결과.
  - 겹침 작음(임계치 미만) → 둘 다 생존.
  - 같은 타입, 같은 위치 → 이 함수 대상 아님(둘 다 생존 확인).
- `extract_findings()` 통합 테스트: 중복 쌍을 넣었을 때 (a) `no` 넘버링에 공백이 없고
  1부터 시작하는지, (b) 버려진 인스턴스가 `kept_instances_by_image`에도 없는지(오버레이
  버그의 핵심 불변식 — `test_extract_findings_keeps_only_post_filter_instances_for_overlay`
  패턴 재사용).

### 4. `AI/validation/QUAL/qc_shared.py` + `sam3_qc_test_masking.ipynb`

- `qc_shared.py`에 `CROSS_TYPE_IOU_MIN = 0.7`(모듈 상수, `BENIGN_CONTAINMENT` 옆) +
  `dedupe_cross_type(instances, min_iou=CROSS_TYPE_IOU_MIN)` 추가 — 기존 `mask_iou()`
  재사용, 프로덕션과 동일한 정렬/그리디 로직(dict 기반 인스턴스 스키마에 맞춰
  `inst["type"]`/`inst["mask"]`/`inst["confidence"]` 사용).
- `sam3_qc_test_masking.ipynb`의 `inspect_image()`에서 `suppress_benign(...)` 호출
  직후, `renumber(final)` 호출 직전에 `dedupe_cross_type` 삽입.
- 이 노트북을 다시 실행하면 `outputs/masking/<stem>_qc.json`이 갱신되고, VLM
  스파이크(`AI/validation/QUAL/vlm-description-check/vlm_description_check.ipynb`)는
  코드 변경 없이 정리된 finding 목록을 그대로 읽게 된다.

## 검증 방법

1. `cd AI && source .venv/Scripts/activate && ruff check . && black --check . && pytest -q`
   — AI/CLAUDE.md CI 규칙과 동일하게 전부 통과해야 한다.
2. 새 테스트(`dedupe_cross_type_overlap` 단위/통합)가 의도대로 통과하는지 확인.
3. `qual` conda 환경에서 `sam3_qc_test_masking.ipynb`를 처음부터 다시 실행 —
   `outputs/masking/scratch_qc.json`이 6개 이하 인스턴스로, 1부터 공백 없이 번호가
   매겨지는지, 오버레이 PNG에 1~N번이 전부 보이는지(더 이상 라벨이 겹쳐 사라지지
   않는지) 육안 확인.
4. `vlm_description_check.ipynb`를 `IMAGE_STEM="scratch"`로 재실행해 VLM 입력 목록이
   중복 없이 나오는지 확인.

## 커밋 계획

스코프별로 나눈다:
1. `worker/models/sam3/findings.py` + `registry.py` — 프로덕션 dedup 구현
2. `AI/test/worker/sam3/test_sam3_findings.py` — 테스트 추가
3. `AI/validation/QUAL/qc_shared.py` + `sam3_qc_test_masking.ipynb` — 검증 스파이크 반영
