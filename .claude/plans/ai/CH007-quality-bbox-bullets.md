# 품질 검수 — 넘버링 bbox 이미지 + 불릿 리스트 출력 추가 — 설계

## 배경 / 목표

지금 `InspectionResult`가 FE/BE에 주는 산출물은 `findings[]`(원본 좌표 데이터)와
`attention_maps[]`(하자유형별 연속 히트맵 오버레이 PNG, 넘버링 없음)뿐이다. FE가 실제로
필요한 건 두 가지다.

1. **숫자만 넘버링된 bbox 이미지** — 하자 위치에 박스 + 숫자만 그린 원본 이미지 1장.
2. **태그 달린 불릿 리스트** — "1. 오염", "2. 찢어짐" 처럼 번호+한글 태그. 짧은 설명은
   추후 sVLM을 붙여 채운다(이 계획 범위 밖 — findings 구조가 안정된 뒤 별도 계획).

CH006이 "sVLM 설명 생성은 이 계획 밖"이라고 명시적으로 미뤄 둔 다음 작업이 이것이다.

**적용 범위: 이번엔 SAM3(`worker/models/sam3/`)에만 구현한다.** CLIPSeg는 우선순위 밖 —
다만 스키마(`app/quality/schemas.py`)는 공용이라 필드 자체는 추가되고, `test_quality_contract.py`의
드리프트 가드 때문에 `worker/models/clipseg/contracts.py`도 필드는 따라가야 한다(아래
"영향받는 기존 코드" 참고, CLIPSeg의 실제 렌더링 로직은 손대지 않는다).

## 작업 내용

### 1. 스키마 확장 (`app/quality/schemas.py`, `worker/models/sam3/contracts.py`)

- `Finding`에 3개 필드 추가:
  - `no: int | None` — 이미지 내 표시 번호(1-based). bbox 이미지의 숫자와 불릿 리스트
    번호가 **정확히 일치**해야 하므로, 배열 순서에 암묵적으로 의존하지 않고 명시 필드로
    고정한다. 값은 `_to_findings()`가 이미 만드는 정렬 순서(이미지 → 섹션 → confidence
    내림차순)를 그대로 써서 이미지별 1부터 매긴다 — 기존 `key`(BE 소명 앵커용 안정 키)와는
    별개 목적이다.
  - `label: str | None` — 한글 태그(오염/얼룩/구멍·찢어짐/변색/보풀/올풀림). `scoring.py`의
    기존 `DEFECT_LABELS` 매핑을 재사용해 채운다.
  - `description: str | None = None` — sVLM이 나중에 채울 짧은 설명 자리. 지금은 항상
    `None`.
- 신규 `AnnotatedImage` 모델: `image_index`, `url`. `InspectionResult`에
  `annotated_images: list[AnnotatedImage] = []` 추가 — `attention_maps`와 나란히 두되
  개념은 다르다(히트맵 여러 장 vs 넘버링 이미지 1장/이미지).
- 전부 optional·기본값 있음 → **CLIPSeg 경로는 코드 수정 없이 그대로 유효**(그냥 `no`/
  `label`이 `None`, `annotated_images`가 빈 리스트로 나감).

### 2. `worker/models/sam3/findings.py` — `no`/`label` 채우기

`_to_findings()`가 이미 만드는 정렬 순서 안에서 `no`(이미지별 1부터)와 `label`
(`scoring.DEFECT_LABELS[defect_type]`)을 같이 채운다. 새 정렬 기준을 추가하지 않는다.

### 3. `worker/models/sam3/overlay.py` — 넘버링 이미지 렌더 함수 신규

- `qc_shared.draw_numbered_boxes()`를 참고하되 **더 단순하다** — 한글 라벨을 안 그리므로
  PIL 폰트 처리가 필요 없고, `cv2.rectangle` + `cv2.putText`(순수 숫자라 Hershey 폰트로
  충분)만으로 끝난다.
- **하자가 있는 이미지만** 생성한다(`attention_maps`와 같은 원칙 — 없으면 안 만듦).
- 반환 타입은 `contracts.AnnotatedImage` 리스트, 업로드는 기존 `upload` 콜백 재사용.

### 4. `worker/quality_check_worker_example.py` — sam3 분기에 배선 추가

`_render_attention_maps`처럼 `_render_annotated_images(results, extracted, upload_image)`
어댑터를 추가하고 `run_inference()`에서 호출, 응답에 `annotated_images` 채운다.

## 영향받는 기존 코드

- `worker/models/clipseg/contracts.py`의 `Finding`/`InspectionResult` 동형 dataclass —
  `test_quality_contract.py`의 `test_model_field_names_match`가 게이트웨이 스키마와
  **필드 이름 집합**을 대조하므로, 새 필드를 게이트웨이에 추가하면 CLIPSeg 사본도 같은
  필드 이름을 (기본값과 함께) 가져야 이 테스트가 안 깨진다. **CLIPSeg의 `findings.py`/
  `segmenter.py`/실제 렌더링 로직은 건드리지 않는다** — 단지 계약 사본에 필드만 늘어난다.
- `AI/test/quality/test_quality_contract.py` — 위 필드 세트 변경에 맞게 갱신 필요.
- `AI/test/worker/sam3/test_sam3_findings.py` — `_to_findings()`가 만드는 `Finding`에
  `no`/`label`이 기대대로 채워지는지 검증 추가.

## 구현 목록

- [ ] `app/quality/schemas.py`: `Finding.no`/`label`/`description`, `AnnotatedImage`,
      `InspectionResult.annotated_images` 추가
- [ ] `worker/models/sam3/contracts.py`: 동일 필드 미러링
- [ ] `worker/models/clipseg/contracts.py`: 필드 이름만 동기화(기본값, 로직 변경 없음)
- [ ] `worker/models/sam3/findings.py`: `no`/`label` 채우기
- [ ] `worker/models/sam3/overlay.py`: 넘버링 bbox 렌더 함수 신규
- [ ] `worker/quality_check_worker_example.py`: sam3 분기에 렌더 호출 배선
- [ ] `AI/test/quality/test_quality_contract.py` 갱신
- [ ] `AI/test/worker/sam3/` 테스트 추가/갱신 (no/label 채움, 넘버링 렌더 순수 로직)
- [ ] `ruff`/`black`/`pytest` 로컬 통과 확인 후 커밋 (push는 사용자)

## 확인이 필요한 미결정 사항

1. **`no` 정렬 기준** — 기존 `_to_findings()` 정렬(이미지→섹션→confidence 내림차순)을 그대로
   쓰자고 제안함. 스파이크의 `renumber()`(순수 confidence 내림차순)와는 다르다 — 문제 없으면
   이대로 진행.
2. **넘버링 이미지 생성 트리거** — `include_attention_maps`처럼 별도 요청 플래그
   (`include_annotated_images`)를 둘지, 아니면 하자가 있으면 항상 만들지. 기본은 "항상"으로
   제안(사용자가 "프론트나 백에 넘겨줄 것"이라 명시했으므로 옵션이 아니라 기본 산출물로 취급).
