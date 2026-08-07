# CH028 품질 검수 — 검증 vs 프로덕션 추론 일치 점검

## 배경

품질 검수는 `AI/validation/QUAL/` 아래 여러 접근을 스파이크했다(`sam3-condition-check`,
`sam3-parts-segment-check`, `sam3-border-overlay-check`, `clipseg-condition-check`,
`clipseg-sam3tracker-hybrid-check`, `winclip-condition-check`, `garment-mask-finetune-check`,
`vlm-description-check`). 최종적으로 `worker/models/sam3/registry.py`의
`ACTIVE_SEGMENTER = "mock"`(커밋 기본값, 실행 시 `sam3_pcs`로 전환)와
`worker/models/quality_vlm/registry.py`의 `qwen3_vl`이 프로덕션 경로로 굳어졌다.

**코드 실행 경로 자체(모델 교체 지점)는 이번에 `worker/quality_check_e2e_validation.ipynb`로
검증했다** — 이 노트북은 로직을 복제하지 않고 `worker/models/sam3/`·`worker/models/quality_vlm/`를
그대로 import해서 단계별로 돌린다. 이 계획은 그 다음 단계다: **레지스트리에 박혀 있는 개별
임계치·파라미터 하나하나가 실제로 어느 검증에서 나왔는지, 아니면 그냥 육안 추정값인지**를
정리한다. `registry.py`를 직접 읽어보면 이미 다수 항목이 스스로 이렇게 표시하고 있다:

- `sam3/registry.py:55,61,89,95` — "라벨링된 검증셋 없이 잡은 값 — 스윕 대상"
  (`cross_type_iou_min`/`same_type_containment_min` 등)
- `sam3/registry.py:73-75` — dedup 계열 임계치 전반이 "육안 판단으로 조정" 상태
- `sam3/registry.py:122` — `DEFECT_TAXONOMY`의 `weight`가 "근거 없는 임의값"
- `sam3/registry.py:172` — 점수·등급 상수가 "전부 미확정 임의값"

반대로 **출처가 명확한 값도 있다** — `quality_vlm/describer.py:30-34`의
`_CROP_PAD_RATIO=0.6`/`_MIN_CROP_SIZE=160`은 `vlm-description-check/vlm_description_check.ipynb`
실측(크롭 14~46px일 때 VLM이 라벨을 그대로 재진술)에서 나온 값이라고 코드 주석에 직접 인용돼
있다. 이게 "일치"가 뭘 뜻하는지 보여주는 기준선이다 — 나머지 값들도 이런 식으로 출처를
붙일 수 있어야 한다.

## 목표

`registry.py`(SAM3)와 `quality_vlm/registry.py`의 파라미터 전부를 훑어, 각각을
"어느 QUAL 스파이크 산출물에서 실측으로 나온 값"과 "출처 없는 추정값"으로 나눈 표를
만든다. 추정값 중 실제 서비스 판정 정확도에 영향이 큰 것(예: `confident_threshold`,
`score_threshold`, `dedupe` 계열)을 우선순위로 표시해, 다음에 라벨셋을 확보하면 어디부터
스윕할지 바로 알 수 있게 한다. 이 계획 자체는 재측정을 하지 않는다 — 출처 정리와 우선순위
표시까지가 범위다.

## 작업 내용

1. **`sam3/registry.py` 전체 파라미터 인벤토리**: `SEGMENTER_BACKENDS["sam3_pcs"]`의 14개
   키(`score_threshold`부터 `max_defect_area_ratio`까지) 각각에 대해, 관련 QUAL 스파이크
   노트북/스크립트에서 같은 값이 등장하는지 검색한다. 등장하면 그 노트북 경로를 출처로
   기록하고, 값이 실제로 일치하는지(복사 과정에서 어긋나지 않았는지) 확인한다.
2. **`DEFECT_TAXONOMY`/점수·등급 상수 인벤토리**: `weight`/`grade_for` 등 채점 관련 상수도
   같은 방식으로 출처를 찾는다. `evidence` 필드가 이미 "LAB-12/LAB-46 실측"이라고 적힌
   것과 "미검증"이라고 적힌 것을 구분해 표로 정리한다(이미 반쯤 되어 있다 — 빠진 것만
   채운다).
3. **대안 백엔드 재확인**: `clipseg`/`winclip`/hybrid 스파이크들이 SAM3 단독보다 못하다고
   결론 낸 근거(007 비교 계획, `sam3-condition-check` REPORT류)를 다시 훑어, 지금
   `ACTIVE_SEGMENTER`가 그 결론과 여전히 일치하는지 확인한다(모델이 바뀌었거나 새 실측이
   나왔으면 재확인 필요).
4. **VLM 파라미터 재확인**: `_CROP_PAD_RATIO`/`_MIN_CROP_SIZE`/`max_new_tokens` 등이
   `vlm-description-check/` 노트북의 **최신** 실행 결과와 여전히 일치하는지(노트북이 그
   뒤 갱신됐다면 코드가 안 따라갔을 수 있다) 확인한다.
5. **우선순위 표 작성**: "출처 없음 + 판정에 큰 영향" 조합만 상위로 추려 다음 스윕 대상
   후보를 정리한다(스윕 자체는 라벨셋 확보 이후 별도 작업).

## 구현 목록

- [ ] `sam3/registry.py` 14개 세그멘터 파라미터 출처 표 작성(스파이크 경로 또는 "출처 없음")
- [ ] `DEFECT_TAXONOMY`/점수·등급 상수 출처 표 작성(`evidence` 필드 보완)
- [ ] 대안 백엔드(clipseg/winclip/hybrid) 대비 SAM3 단독 채택 근거 최신 여부 재확인
- [ ] `quality_vlm` crop/생성 파라미터가 `vlm-description-check/` 최신 실측과 일치하는지 재확인
- [ ] 출처 없는 값 중 우선 스윕 후보 목록 작성(문서로 남김, 실제 스윕은 후속 작업)

## 확인이 필요한 미결정 사항

- 라벨링된 검증셋 자체가 아직 없다(여러 곳에서 반복 언급) — 이 점검으로 "출처 없음"이
  드러나도 즉시 고칠 방법은 없고, 검증셋 확보가 선행 조건이다. 검증셋 확보를 별도 작업으로
  분리할지 이 계획에 포함할지는 점검 결과를 본 뒤 정한다.
- QUAL 스파이크 폴더가 8개라 전수 대조에 시간이 걸릴 수 있다 — 필요하면 영향도가 큰
  `sam3-condition-check`/`vlm-description-check` 먼저 보고 나머지는 후순위로 미룬다.
