# 품질 검수 — 하자 탐지 결과 요약(summary) 상세화 — 설계

> 관련 JIRA: `S15P11A108-501`(검수 결과 시각화 개선)에 포함해 진행. 브랜치 `feat/211-quality-summary-detail`.

## 배경 / 목표

지금 `summarize()`(`worker/models/sam3/scoring.py`)는 유형별 개수만 나열한다 —
"오염 2건, 보풀 1건이 확인되었습니다." 위치도, 어떤 하자인지 설명도 없어서 판매자·구매자가
`findings[]`를 따로 안 보면 실제로 어디에 무슨 문제인지 알 수 없다.

이미 `Finding`에 있는데 요약문이 못 쓰고 있는 정보 3가지를 반영한다:
1. **부위 정보** — `Finding.section`(예: `SLEEVE_LEFT`)을 한글 라벨로.
2. **VLM 설명** — `Finding.description`(CH011, `include_descriptions=True`일 때만 채워짐).
3. **이미지별 구분** — `Finding.image_index`.

## 작업 내용

### 형식 변경 — 집계 문장 → 이미지별 넘버링 리스트

부위 정보가 생기면 "오염 2건"으로 뭉뚱그릴 이유가 없다 — 항목별로 펼쳐 쓸 수 있다.
`Finding.no`(CH007, 이미지 내 표시 번호 1부터, `annotated_images`의 bbox 숫자와 이미 일치)를
그대로 재사용해 아래 형식으로 바꾼다:

```
[이미지 1]
1. 왼쪽 소매 오염 — 옅은 갈색 얼룩이 소매 끝부분에 있습니다.
2. 밑단 중앙 보풀

[이미지 2]
1. 목깃 변색 (의심)
```

- 한 줄 = `{no}. {section_label} {defect_label}` + (`description`이 있으면 ` — {description}`)
  + (`status`가 `SUSPECTED`면 ` (의심)`).
- `[이미지 N]` 헤더(`image_index + 1`)는 **findings에 등장하는 image_index가 2개 이상일 때만**
  붙인다 — 이미지 1장에만 하자가 있으면 굳이 구분할 필요가 없다.
- 정렬은 `_to_findings()`가 이미 만든 순서(이미지 → 섹션 → confidence 내림차순, `no`와 동일
  기준)를 그대로 따른다 — 새 정렬을 만들지 않는다.
- 하자가 전혀 없으면 기존 `_NO_DEFECT_SUMMARY`("확인된 하자가 없습니다.") 그대로 유지.
- `summary` 필드 타입은 `str` 그대로다(스키마 변경 없음) — 여러 줄 문자열이 되는 것뿐이라
  `app/quality/schemas.py`/`worker/*/contracts.py`/BE 계약 문서를 건드릴 필요가 없다.
  다만 필드 docstring("한 줄 요약")은 실제 내용과 맞게 갱신한다.

### 부위 라벨 재사용

`worker/models/sam3/prompts.py`의 `SECTION_LABELS_KO`(CH009가 VLM 프롬프트용으로 이미 만든
"부위 의미의 정본 위치")를 `scoring.py`가 import해서 그대로 쓴다. 새로 정의하지 않는다.

### `summarize()` 시그니처

- 기존: `summarize(findings: Sequence[Finding]) -> str`.
- 변경 후에도 `findings`만 받는다 — `no`/`section`/`description`/`image_index`가 이미
  `Finding`에 다 있어서 추가 인자가 필요 없다. 호출부(`quality_check_worker_example.py`의
  `summarize(extracted.findings)`)는 수정 불필요.
- 내부에서 `image_index`로 group-by 한 뒤 그룹별로 문자열 조립. `_counts_by_label()`은
  더 이상 `summarize()`가 쓰지 않으므로 제거(다른 호출부 없음 확인 필요 — 있으면 유지).

## 영향받는 기존 코드

- `worker/models/sam3/scoring.py` — `summarize()` 재작성, `SECTION_LABELS_KO` import 추가.
- `AI/test/worker/sam3/test_sam3_scoring_config.py` 또는 신규
  `test_sam3_scoring_summary.py` — 요약 포맷 테스트 추가(개수 나열 대신 넘버링 리스트인지,
  description 유무별 분기, 이미지 1장/다중 이미지 헤더 유무, 하자 없음 케이스).
- CLIPSeg 경로 — CLIPSeg는 `Finding.no`/`section`을 채우지 않을 수 있어(CH007이 SAM3 전용으로
  적용됨) `no`가 `None`인 경우의 폴백이 필요하다. `no is None`이면 그 그룹 안에서 1부터 임시
  번호를 매겨 렌더링(표시만, `Finding.no` 필드 자체는 건드리지 않음).

## 구현 목록

- [ ] `worker/models/sam3/scoring.py`: `summarize()` 재작성(이미지별 그룹 + 넘버링 + 부위 +
      설명 + 의심 표기), `SECTION_LABELS_KO` import
- [ ] `_counts_by_label()` 미사용 확인 후 정리(다른 호출부 없으면 제거, 있으면 유지)
- [ ] 요약 필드 docstring 갱신(`app/quality/schemas.py`의 `InspectionResult.summary`,
      `scoring.py`의 `summarize()` 자체 — "한 줄 요약" 표현 수정)
- [ ] `AI/test/worker/sam3/` 요약 포맷 테스트 추가
- [ ] `ruff`/`black`/`pytest` 로컬 통과 확인 후 커밋 (push는 사용자)

## 확인이 필요한 미결정 사항

1. **집계 문장 완전 대체 여부** — 지금 제안은 개수 집계 문장을 넘버링 리스트로 **완전히
   대체**하는 것. 만약 맨 위에 한 줄 총평("오염 1건, 보풀 1건 확인")을 남기고 그 아래 상세
   리스트를 덧붙이는 형태를 원하면 그렇게 바꾼다.
2. **`description` 없을 때 문구** — description이 없으면(옵트인 안 함, 또는 SUSPECTED) 지금은
   `{section_label} {defect_label}`만 남긴다. 너무 밋밋하면 "확인이 필요합니다" 같은 짧은
   접미사를 붙이는 안도 가능.
