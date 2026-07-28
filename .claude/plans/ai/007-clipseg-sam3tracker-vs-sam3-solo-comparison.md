# CLIPSeg+SAM3Tracker 하이브리드 vs SAM3 단독 — 실측 비교

## Context

품질 검수 하자 탐지 백엔드를 **SAM3 단독**으로 교체할지, 기존 **CLIPSeg + SAM3Tracker(마스크
정제)** 조합으로 갈지 결정하기 위한 아키텍처 검토를 Notion에 정리했다
([LAB-46] `[AI] 시스템 아키텍처 — CLIPSeg+SAM Tracker vs SAM3 단독`,
실험실 > [QUAL] 품질 검수 하위). 그 문서의 종합 의견은 "지금 시점 증거로는 CLIPSeg+Tracker가
더 안전하다"였지만, **두 가지 구멍을 열린 질문으로 남겼다**:

1. 라벨링된 검증셋이 없어 전부 육안 판단이었다 — 정량 비교가 아니다.
2. **CLIPSeg+Tracker 조합을 실제로 돌려본 적이 없다.** SAM3 PCS 자체 마스크를 Tracker로
   정제하는 `sam3_qc_test.ipynb` §9는 설계만 하고 게이트 승인 전이라 실행 안 됐고, CLIPSeg
   박스를 Tracker에 먹이는 조합은 코드로 존재하지 않는다.

이번 작업은 구멍 2번을 메운다 — **CLIPSeg가 찾은 박스를 SAM3Tracker에 넣어 마스크를 정제하는
경로를 실제로 코드화**하고, 지금 있는 SAM3 단독 파이프라인(`sam3_qc_test.ipynb`)과 같은
이미지·같은 기준으로 나란히 비교한다. 구멍 1번(라벨링 검증셋)은 이번 스코프 밖이다 — 여전히
`sample_images/`의 실제 상품 사진을 육안으로 비교하는 수준이지만, "실행해본 적 없다"를
해소하는 게 목적이다.

## 범위

- **한다**: CLIPSeg 박스 → SAM3Tracker 정제 파이프라인을 새 노트북(또는 기존
  `clipseg_qc_test.ipynb`의 새 섹션)으로 구현. 같은 이미지 세트로 SAM3 단독과 나란히 실행하고
  결과를 비교.
- **안 한다**: 라벨링된 검증셋 구축, 프로덕션(`worker/`) 코드 변경, 임계치 최종 확정. 이번
  라운드는 "돌아가는지, 방향이 맞는지"를 보는 스파이크다.

## 설계

### 1. 정제 파이프라인 — 어디에 둘 것인가

`clipseg_qc_test.ipynb`에 새 섹션(예: §8 "SAM3Tracker 마스크 정제 실험")으로 추가한다.
CLIPSeg 노트북 쪽에 두는 이유: CLIPSeg의 224px 히트맵 기반 마스크가 SAM3 PCS의 1008px
마스크보다 구조적으로 거칠어서, 정제로 얻을 이득이 이 쪽이 더 크다(LAB-46 문서 §3 근거).

새 모델 로드가 필요하다 — `sam3_qc_test.ipynb` §9가 이미 검증한 패턴을 그대로 재사용:

```python
from transformers import Sam3TrackerModel, Sam3TrackerProcessor

tracker_model = Sam3TrackerModel.from_pretrained("facebook/sam3", dtype=DTYPE).to(DEVICE).eval()
tracker_processor = Sam3TrackerProcessor.from_pretrained("facebook/sam3")
```

CLIPSeg(~150MB)와 SAM3Tracker(fp16 ~1.7GB) 동시 적재는 8GB에서 여유 있다(LAB-46 §4 실측
근거) — §9처럼 OOM 폴백(`del`+`empty_cache()`+재시도)까지는 필요 없을 가능성이 높지만,
안전장치로 그대로 가져온다.

### 2. 박스 변환 — CLIPSeg 인스턴스 → Tracker 입력

CLIPSeg의 `probs_to_instances()`가 이미 각 blob의 `bbox`(xyxy, 절대 픽셀)를 갖고 있다.
`sam3_qc_test.ipynb` §9의 변환을 그대로 재사용한다:

```python
inputs = tracker_processor(images=pil_image, input_boxes=[boxes], return_tensors="pt")
outputs = tracker_model(**inputs, multimask_output=False)
refined = tracker_processor.post_process_masks(
    outputs.pred_masks.detach().cpu().float(), inputs["original_sizes"].cpu()
)[0]
```

`qc_shared.py`의 기존 유틸(`containment`, `KOREAN_LABELS`)을 재사용해 정제 전/후 마스크
picel 수와 IoU를 계산한다 — §9와 동일한 비교 방식.

### 3. 해석 주의 (§9에서 이미 확인된 함정)

- Tracker는 **class-agnostic**(SAM2 계열)이다. CLIPSeg 박스 안의 "물체"를 분할하므로, 하자
  박스를 주면 하자가 아니라 원단 표면 전체를 잡을 수 있다. 정제 전/후 IoU가 지나치게 낮거나
  마스크 픽셀 수가 급증하면 "정제"가 아니라 "대상이 바뀐" 것으로 읽는다.
- CLIPSeg의 blob이 이미 노이즈(초소형·경계 흐림)면 Tracker에 넘겨도 정제가 의미 없다 —
  `MIN_AREA_RATIO` 통과한 blob만 넘긴다(이미 `probs_to_instances`가 필터링함).

### 4. 비교 대상 — 두 파이프라인을 같은 기준으로

| | 이번 실험(신규) | SAM3 단독(기존, `sam3_qc_test.ipynb`) |
| --- | --- | --- |
| 탐지+분류 | CLIPSeg (`bare`/`fabric`/`garment` 세트 중 하나) | SAM3 PCS |
| 마스크 정제 | SAM3Tracker (박스 프롬프트) | 없음(§9는 기본 OFF) |
| 배경/양성 억제 | `qc_shared.filter_by_garment`/`suppress_benign` (둘 다 공유) | 동일 |
| 이미지 세트 | `sample_images/`의 8장 전체(공유 경로) | 동일 |

LAB-46 문서의 점검 기준 7개 중 이번에 실측 가능한 것:
- **1(유형별 탐지 정확도)** — 정제 전/후로 인스턴스 개수·타입이 달라지는지
- **3(마스크 경계 품질)** — IoU, 픽셀 수 변화, 눈으로 본 경계 타이트함
- **4(자원)** — CLIPSeg+Tracker 동시 적재 시 실측 VRAM(추정치 1.85GB가 맞는지)

나머지(2 오탐 유계성, 5 자산 재사용성, 6 신뢰도 정책, 7 운영 복잡도)는 이번 실측 대상이 아니다
— 이미 코드/설계 검토로 답한 항목이라 재실험 불필요.

## 변경 파일

| 파일 | 작업 |
| --- | --- |
| `AI/validation/clipseg-condition-check/clipseg_qc_test.ipynb` (빌더: 세션 스크래치패드의 `build_clipseg_nb.py`) | 새 섹션 추가 — Tracker 로드, 박스 변환, 정제 전/후 비교 시각화, VRAM 실측 |
| `AI/validation/qc_shared.py` | 필요시 IoU 계산 등 공용 유틸만 추가(중복 방지) — 새 아키텍처 상수는 만들지 않는다 |

`sam3_qc_test.ipynb`, `sam3_qc_test_seg_ver.ipynb`, 프로덕션(`worker/`)은 건드리지 않는다.

## 검증 방법

```bash
cd AI
./.venv/Scripts/python.exe <스크래치패드>/build_clipseg_nb.py
./.venv/Scripts/python.exe -m ruff check .
./.venv/Scripts/python.exe -m black --check .
./.venv/Scripts/python.exe -m pytest -q
```

실행은 `qual` conda 환경(RTX 4070 8GB)에서 사용자가 직접 한다 — SAM3 게이트 접근이 필요하고
이쪽 세션은 GPU/모델 접근이 없다. 확인 항목:

- CLIPSeg+Tracker 동시 적재 시 VRAM 실측값이 추정(1.85GB)과 맞는지
- 8장 중 정제로 마스크가 눈에 띄게 타이트해지는 사례가 있는지, 반대로 대상이 바뀐(class-agnostic
  함정) 사례가 있는지
- 결과를 LAB-46 Notion 문서의 "다음 단계" 체크박스 중 "CLIPSeg 박스 → SAM Tracker 정제 조합을
  실제로 코드화해서 성능 재확인" 항목에 반영(완료 체크 + 실측 결과 추가)
