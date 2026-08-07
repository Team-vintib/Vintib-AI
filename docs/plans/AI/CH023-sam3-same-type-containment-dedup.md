# CH023 — SAM3 같은 유형(defect_type) 인스턴스의 "박스 안에 박스" 병합

## 배경/목표

`AI/validation/QUAL/vlm-description-check/batch_pipeline_check.ipynb`로 검증하던 중,
같은 defect_type의 인스턴스 여러 개가 서로 심하게 겹치거나 한쪽이 다른 쪽에 거의 완전히
포함되는("박스 안에 박스") 사례가 실측됐다(`small_pro.jpg`: STAIN bbox 3건이 서로 97~100%
포함, 실제로는 같은 하자 하나로 보임).

기존 `dedupe_cross_type_overlap()`은 **다른 defect_type끼리만** 비교한다(같은 타입 중복은
"SAM3 자체 후처리가 이미 걸렀다"고 가정하고 의도적으로 건너뜀 — `test_dedupe_cross_type_
overlap_ignores_same_type_overlap` 회귀 테스트로 그 전제가 문서화돼 있음). 실측상 그 전제가
깨지는 경우가 있어, 같은 유형 인스턴스 전용 병합 단계를 별도로 추가한다.

## 작업 내용

- `findings.py`에 `dedupe_same_type_containment(instances, min_containment)` 함수를
  신설한다(기존 `dedupe_cross_type_overlap`을 고치지 않음 — 그 함수의 "same-type 무시"
  계약과 회귀 테스트를 그대로 보존).
  - 비교 대상: **같은 defect_type**끼리만.
  - 지표: `_mask_iou`(대칭)가 아니라 `_containment`(비대칭) — "박스 안에 박스"는 두 박스
    크기가 크게 다를 수 있어 IoU로는 못 잡는다(작은 박스가 큰 박스에 거의 다 들어가도
    합집합 기준 IoU는 낮게 나옴). A가 B에 담긴 비율과 B가 A에 담긴 비율 중 **큰 쪽**을
    써서 방향에 관계없이 잡는다.
  - 병합 시 남기는 쪽: confidence 내림차순, 동률이면 마스크 면적(`mask.sum()`) 큰 쪽 —
    작은 중복 박스를 큰 박스 쪽으로 흡수한다는 물리적 직관에 맞춘다.
  - 그리디 비교(이미 kept에 들어간 것과만 비교)는 `dedupe_cross_type_overlap`과 동일한
    단순화(전이성 미보장, 실측상 거의 완전 포함이라 문제 안 됨).
- `registry.SegmenterConfig`에 `dedupe_same_type`(on/off)·`same_type_containment_min`
  (임계치) 두 키를 추가하고 두 프리셋(`mock`/`sam3_pcs`) 모두에 값을 채운다.
  - 임계치 기본값 **0.8**: 실측 사례(0.97/1.00)를 확실히 잡으면서, 부분적으로만 겹치는
    "진짜 다른 두 하자"까지 합쳐버릴 위험은 낮추는 여유값(cross_type_iou_min=0.7을 잡을
    때 쓴 것과 같은 논리). 라벨링된 검증셋이 없어 스윕 대상이라는 점은 기존 임계치들과
    동일.
- `extract_findings()` 파이프라인에 편입 — benign 억제 다음, cross-type dedup **이전**에
  둔다(같은 타입 중복을 먼저 줄여야 cross-type dedup이 더 적은 후보로 깨끗하게 동작).
- 이번 스코프는 **프로덕션(`worker/models/sam3/`)만** — validation 스파이크 쪽은 반영하지
  않는다(요청 범위).

## 구현 목록

- [ ] `registry.py`: `SegmenterConfig`에 `dedupe_same_type`/`same_type_containment_min`
      추가, `mock`/`sam3_pcs` 값 채움(0.8)
- [ ] `findings.py`: `dedupe_same_type_containment()` 신설, `extract_findings()` 파이프라인에
      편입(benign 억제 다음, cross-type dedup 이전)
- [ ] `test/worker/sam3/test_sam3_findings.py`: 단위 테스트(포함 병합/임계치 미달 시 유지/
      cross-type엔 영향 없음) + `extract_findings` 통합 테스트
- [ ] `AI/` 전체 `pytest -q`/`ruff`/`black` 통과 확인
