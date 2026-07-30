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

**[2026-07-30 확정 — 초안 수정]** 기존 `clipseg_qc_test.ipynb`에 섹션을 덧붙이는 대신
**별도 노트북 `clipseg-sam3tracker-hybrid-check/hybrid_qc_test.ipynb`로 분리**했다.
CLIPSeg 단독 검증과 하이브리드 실험이 한 파일에 섞이면 ⑴ 어느 쪽 결과인지 산출물 파일명으로만
구분되고 ⑵ CLIPSeg 단독을 재현하려면 매번 Tracker 셀까지 건너뛰어야 한다. `AI/CLAUDE.md`의
`<feature>-condition-check/` 디렉터리 관례에도 맞는다.

1단(탐지)에 CLIPSeg를 쓰는 근거는 그대로다: CLIPSeg의 224px 히트맵 기반 마스크가 SAM3 PCS의
1008px 마스크보다 구조적으로 거칠어서 정제로 얻을 이득이 이쪽이 더 크다(LAB-46 §3).

**분리에 따른 선행 작업** — `probs_to_instances()`(확률맵 → 인스턴스 변환)가
`clipseg_qc_test.ipynb` 안에만 있었다. 새 노트북도 같은 변환이 필요하므로 복사하는 대신
`qc_shared.py`로 이관하고 기존 노트북은 import하도록 고쳤다 — `qc_shared.py`의 존재 이유
("노트북마다 복사하면 한쪽만 고쳐져 조용히 어긋난다")가 그대로 적용되는 상황이다.

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

**[2026-07-30 실제 변경 내역]** (경로는 도메인 재구성 후 `validation/QUAL/` 기준)

| 파일 | 작업 |
| --- | --- |
| `AI/validation/QUAL/clipseg-sam3tracker-hybrid-check/hybrid_qc_test.ipynb` | **신규**(빌더: 세션 스크래치패드 `build_hybrid_nb.py`). 셀 29개 — CLIPSeg 탐지 → Tracker 로드/VRAM 실측 → 박스 변환·정제 → 지표(IoU·픽셀비·3분류)·시각화 → SAM3 단독 비교 → 저장 |
| `AI/validation/QUAL/qc_shared.py` | `probs_to_instances()` 이관(clipseg 노트북에서), `mask_iou()` 추가(정제 전/후 비교용), 모듈 docstring을 "노트북 세 개" 기준으로 갱신 |
| `AI/validation/QUAL/clipseg-condition-check/clipseg_qc_test.ipynb` | `probs_to_instances` 지역 정의 제거 → `qc_shared` import로 교체(+ 미사용이 된 `cv2`·`MIN_AREA_RATIO` import 정리, §2 마크다운에 이관 사실 명시) |
| `AI/.gitignore` | 새 `clipseg-sam3tracker-hybrid-check/outputs/` 산출물 경로 추가 |

`sam3_qc_test.ipynb`(§9 로딩·변환 패턴만 참고), `sam3_qc_test_seg_ver.ipynb`,
프로덕션(`worker/`)은 건드리지 않았다.

### 초안 대비 설계 보강 2가지

- **로드 순서** — CLIPSeg 탐지를 §1~§2에서 **전부 끝낸 뒤** §3에서 Tracker를 올린다. OOM 폴백으로
  CLIPSeg를 내려도 이미 계산된 인스턴스(마스크는 numpy=CPU)를 잃지 않는다.
  `sam3_qc_test.ipynb` §9는 PCS를 내리면 이후 셀이 깨지는 구조였는데 그 문제를 피했다.
- **정제 결과 3분류** — IoU와 픽셀비만 표로 내면 "타이트해진 것"과 "대상이 바뀐 것"이 섞인다.
  `TIGHTENED`(정제 이득) / `SIMILAR`(무의미) / `TARGET_CHANGED`(class-agnostic 함정)로 분류해
  비율을 집계한다. **분류 임계치 3개(`REFINE_IOU_MIN`/`REFINE_PX_RATIO_MAX`/`REFINE_TIGHTEN_MAX`)는
  근거 없는 초기값**이라 결과 JSON에 임계치를 함께 저장해 재해석 가능하게 했다.

## 검증 방법

```bash
cd AI
./.venv/Scripts/python.exe <스크래치패드>/build_hybrid_nb.py   # 노트북 재생성
./.venv/Scripts/python.exe -m ruff check .
./.venv/Scripts/python.exe -m black --check .
./.venv/Scripts/python.exe -m pytest -q
```

**정적 검증 결과(2026-07-30)**: ruff 통과 / black 통과 / pytest 720 passed·19 skipped.
노트북 코드 셀 13개 전부 `compile()` 파싱 확인, `qc_shared` 임포트 24개 전부 해석됨,
`mask_iou` 단위 성질(동일=1.0 / 비겹침=0.0 / 절반=0.5 / 대칭 / 빈마스크=0.0) 확인.

> ⚠️ **ruff는 `.ipynb`도 검사한다.** `AI/CLAUDE.md`는 "`validation/**/*.ipynb`는 lint/format
> 대상에서 제외"라고 적고 있으나, `pyproject.toml`의 `extend-exclude`에는 `AI_tryon/{tryondiffusion,
> CatVTON}`만 있고 노트북 제외 설정은 없다. 실제로 새 노트북에서 F541이 잡혔다. **black만** 제외되는
> 셈인데 그것도 설정이 아니라 `black[jupyter]` 미설치 때문이다("Skipping .ipynb files as Jupyter
> dependencies are not installed" — CI도 같은 상태). 노트북을 새로 만들면 ruff는 반드시 돌릴 것.

`probs_to_instances`는 `cv2`가 필요해 이 venv에서는 실행 검증이 안 된다(cv2는 `qual` 환경에만
있다). 그래서 `qc_shared`가 cv2 없이도 import되도록 함수 내부 지연 import를 유지했다.

실행은 `qual` conda 환경(RTX 4070 8GB)에서 사용자가 직접 한다 — SAM3 게이트 접근이 필요하고
이쪽 세션은 GPU/모델 접근이 없다. 확인 항목:

- CLIPSeg+Tracker 동시 적재 시 VRAM 실측값이 추정(1.85GB)과 맞는지 (§3, §7)
- 8장 중 정제로 마스크가 눈에 띄게 타이트해지는 사례가 있는지, 반대로 대상이 바뀐(class-agnostic
  함정) 사례가 있는지 → `TIGHTENED` / `TARGET_CHANGED` 비율 (§5)
- **§2 baseline 표가 `clipseg_qc_test.ipynb` §4와 같은 값인지** — 다르면 공유 로직이 어긋난
  것이므로 Tracker 결과를 해석하기 전에 원인부터 찾아야 한다
- 결과를 LAB-46 Notion 문서의 "다음 단계" 체크박스 중 "CLIPSeg 박스 → SAM Tracker 정제 조합을
  실제로 코드화해서 성능 재확인" 항목에 반영(완료 체크 + 실측 결과 추가)

## 이 스파이크가 끝나도 남는 것 (결론 과대해석 방지)

- **정량 정확도가 아니다.** 라벨링 정답셋이 없어 precision/recall을 못 낸다. `TIGHTENED`가 많다는
  건 "경계가 좁아졌다"까지고 "더 정확하다"의 증명이 아니다 — LAB-46 열린 질문 1번은 그대로 남는다.
- **SAM3 PCS 마스크와의 픽셀 단위 비교가 없다.** SAM3 노트북이 저장하는 JSON은
  `to_serializable()`이 mask를 버려 bbox/confidence/type만 남는다. 마스크 대조를 하려면 SAM3를
  다시 돌려 CLIPSeg·Tracker·PCS 세 모델을 동시에 올려야 해서 이번 스코프 밖이다.
- **탐지 성능은 CLIPSeg 그대로다.** Tracker는 탐지에 기여하지 않으므로 LAB-12가 지목한
  찢어짐·훼손 약점은 이 하이브리드로 개선되지 않는다. 그 약점은 별도 대응이 필요하다.
