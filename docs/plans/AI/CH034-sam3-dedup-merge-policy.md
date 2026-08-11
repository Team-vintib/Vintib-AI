# CH034 — SAM3 하자 인스턴스 중복 처리: 드롭 → 병합/유지 전환

## 배경/목표

`worker/models/sam3/findings.py::extract_findings()`는 현재 두 종류의 중복 인스턴스를
**드롭**한다 — 겹치는 후보 중 하나를 통째로 버려서, 사용자가 보는 박스 개수가 실제 탐지
개수보다 적어진다.

- `dedupe_same_type_containment()`(포함비율 ≥0.8) — 같은 defect_type이 "박스 안에 박스"로
  겹치면 confidence 낮은 쪽을 버림(small_pro.jpg 실측 근거: 같은 STAIN이 97~100% 포함).
- `dedupe_cross_type_overlap()`(mask IoU ≥0.7) — 다른 defect_type이 겹치면 confidence
  낮은 쪽을 버림(scratch.jpg 실측 근거: DIRT_MARK/HOLE_TEAR가 거의 동일 위치를 중복 검출).

요청: 사용자에게 더 많은 탐지 정보를 그대로 보여주도록 정책을 바꾼다.

- **같은 유형**: 드롭하지 않고 **병합**해서 더 큰 박스 하나로 그린다.
- **다른 유형**: 드롭하지 않고 **둘 다 유지**해서 박스를 각각 그린다(같은 자리에 중복 표시되는
  것을 허용).

⚠️ 이 변경은 `dedupe_cross_type_overlap`을 도입했던 실측 근거(같은 자리 다른 타입 중복 표시가
실제로 관측됨)를 되돌리는 것이다 — 사용자 확인 결과 감수하기로 함(2026-08-09).

## 작업 내용

### 1. 같은 유형 병합 (`dedupe_same_type_containment` → 병합 로직으로 교체)

`Instance`(`worker/models/sam3/segmenter.py:64`)는 `mask`(H,W uint8)와 `bbox`(정규화 xyxy)를
들고 있고, `bbox`는 `mask`에서 파생된 값이다(`_mask_bbox()`+`_bbox_to_normalized()`,
segmenter.py 비공개 함수). 병합 시:

- `mask`: 두 인스턴스 마스크의 논리합(OR) — `_section_no_of()`(무게중심)·`area_ratio`
  (`inst.mask.mean()`)·attention map(`overlay.py::render_overlay`)이 전부 이 mask를 그대로
  쓰므로, 박스만 키우고 mask를 안 합치면 셋이 서로 어긋난다.
- `bbox`: 두 bbox를 좌표별 min/max로 합집합(정규화 좌표라 mask 재계산 없이 바로 가능 —
  `(min(x1,x1'), min(y1,y1'), max(x2,x2'), max(y2,y2'))`).
- `confidence`: **둘 중 최댓값**(사용자 결정, 2026-08-09) — 병합은 "같은 실물 하자를 중복
  탐지했다"는 뜻이므로, 더 확신했던 쪽의 신뢰도를 그대로 쓴다. `_status_of()`의
  DETECTED/SUSPECTED 강등 로직(0.55 임계)에 자연스럽게 들어맞는다.
- `defect_type`/`prompt`: 같은 타입이므로 confidence가 더 높은 인스턴스 것을 그대로 쓴다.

함수명을 `dedupe_same_type_containment` → `merge_same_type_containment`로 바꾸고
(반환 타입도 `(kept, dropped)`가 아니라 `(merged, absorbed)`쯤으로), `extract_findings()`
호출부의 변수명/주석도 맞춰 갱신한다.

### 2. 다른 유형은 드롭하지 않음 (`dedupe_cross_type_overlap` 비활성화)

함수 자체는 지우지 않고 `registry.py`의 `SegmenterConfig["dedupe_cross_type"]`를
`mock`/`sam3_pcs` 두 백엔드 모두 `True` → `False`로 바꾼다. `extract_findings()`가 이미
`if config["dedupe_cross_type"]:` 분기로 켜고 끄는 구조라(`suppress_benign`과 같은 관례)
findings.py 쪽 제어 흐름은 손댈 필요가 없다 — 회귀 테스트(`test_dedupe_cross_type_overlap_*`)도
함수 자체 단위 테스트로 그대로 남겨 향후 재활성화 여지를 보존한다.

### 3. 테스트

`AI/test/worker/sam3/test_sam3_findings.py`:
- 기존 `test_dedupe_same_type_containment_*` 4개를 `merge_same_type_containment` 기준으로
  다시 쓴다 — "드롭됐는지"가 아니라 "병합된 인스턴스의 mask가 두 마스크의 합집합인지",
  "bbox가 합집합인지", "confidence가 max인지"를 검증하도록.
- `test_dedupe_same_type_containment_ignores_different_types`(다른 타입은 비교 안 함)는
  로직 변경과 무관하므로 이름만 맞춰 유지.
- cross-type dedup 테스트 8개는 함수 자체는 그대로라 수정 불필요. 대신
  `test_sam3_taxonomy.py`류에 있는 "config 기본값" 검증 패턴처럼,
  `registry.py`의 `dedupe_cross_type` 기본값이 `False`인지 확인하는 테스트를 추가한다
  (`test_committed_defaults_are_mock`처럼 커밋 기본값을 고정하는 관례).
- `extract_findings()` 통합 테스트(있다면)에서 "다른 타입 중복이 findings 두 개로 남는지",
  "같은 타입 중복이 병합된 하나로 남는지" 케이스 추가.

## 구현 목록

- [x] `worker/models/sam3/findings.py`: `dedupe_same_type_containment` → `merge_same_type_containment`로 교체(mask 유니온 + bbox 유니온 + confidence=max)
- [x] `worker/models/sam3/findings.py`: `extract_findings()`가 새 함수명/반환 의미를 쓰도록 갱신
- [x] `worker/models/sam3/registry.py`: `mock`/`sam3_pcs` 두 백엔드의 `dedupe_cross_type` 기본값을 `False`로 변경
- [x] `AI/test/worker/sam3/test_sam3_findings.py`: 병합 동작 테스트로 교체 + cross-type 기본값 off 테스트 추가(`test_sam3_backends.py`에도 추가)
- [x] `ruff check .` / `black --check .` / `pytest -q` (AI 폴더 기준) 통과 확인 — 1259 passed, 7 skipped

## 리스크 (승인 전 확인 필요)

- Cross-type dedup을 끄면 scratch.jpg류 사례(같은 자리를 다른 타입으로 중복 탐지)가 다시
  finding 2건으로 노출된다 — `condition_score` 감점이 중복 반영되고, 판매자가 사실상 같은
  하자에 소명을 두 번 입력해야 할 수 있다. 사용자가 이 트레이드오프를 인지하고 승인함.
- Same-type 병합은 라벨링된 검증셋 없이 설계한 로직이라(다른 임계치들과 같은 한계)
  병합된 박스가 실제로 "적절한 크기"인지는 실사진으로 추가 확인이 필요하다.
