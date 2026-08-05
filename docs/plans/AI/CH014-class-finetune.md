# CH014 — 상품 분류(카테고리+색상) 지도학습 헤드

## 배경/목표

`fashion_model_compare.ipynb` 실측(2026-08-03, N=17)에서 후보 4종이 **전부 같은 top1
0.7059**로 동률이 나왔고, **오답 5건이 4개 모델에서 거의 동일**했다. 체크포인트를 더 바꿔도
안 움직인다는 뜻이므로, 남은 축은 **지도 신호**다. AI-Hub "의류 통합 데이터"(550,634건,
Notion LAB-76)로 **백본은 얼리고 헤드만 얹는다.**

## 1. 실측 진단 — 어디가 약한가

### 1-1. 카테고리: 오답 5건 = 2가지 유형뿐

| 이미지 | 정답 | 4개 모델 예측 | 유형 |
|---|---|---|---|
| `small_pro.jpg` | TSHIRT | SHIRT (4/4 동일) | **폴로** — 흰 피케 폴로 |
| `black_stain.png` | TSHIRT | SHIRT (4/4 동일) | **폴로** — 네이비 폴로 |
| `logo_test.jpg` | TSHIRT | SHIRT (4/4 동일) | 긴팔 크루넥 티, **뒷면 촬영** |
| `greyp.png` | SLACKS | CARGO_PANTS (4/4) | **정답셋 라벨 의심** |
| `navy_cotton.png` | SLACKS | COTTON/CARGO/JOGGER (갈림) | **정답셋 라벨 의심** |

대분류별: OUTER 4/4(1.00) · BOTTOM 4/6(0.67) · TOP 4/7(0.57). 촬영유형별 차이는 없다
(flat 0.69 / hanging 0.75, n=4라 무의미).

**top-3이 1.00인 게 핵심 신호다.** 게다가 범용 `clip_vit_b32`는 BOTTOM top3가 0.67로
**SLACKS를 top-3에도 못 올리는데**, 패션 체크포인트 3종은 전부 1.00이다 — 패션 파인튜닝이
**표현은 개선했고 결정 경계만 못 고쳤다**는 증거다. 정확히 linear probe가 메우는 간극이다.

**하의 2건은 정답셋 라벨이 낡았을 가능성이 높다.** 두 이미지를 육안 확인했다:
`greyp.png`는 주름 없는 차콜 면 와이드 팬츠, `navy_cotton.png`는 네이비 면 치노(파일명부터
"cotton")다. 둘 다 **`COTTON_PANTS`가 없던 taxonomy v1 시절에 SLACKS로 라벨링**됐고, v2에서
그 코드가 생겼다. 재라벨링하면 `navy_cotton.png`는 fashion_clip·marqo_siglip이 이미 맞히고
있어 **0.7059 → 0.7647**이 된다. → 사용자 승인 필요(§3).

### 1-2. 색상: fashion_clip 0.8824, 남은 실패는 BLACK 하나뿐

| 모델 | color | +wb | p50(CPU) |
|---|---|---|---|
| clip_vit_b32 | 0.4706 | 0.5882 | 125ms |
| **fashion_clip** | **0.8824** | 0.8235 | **123ms** |
| marqo_fashion_clip | 0.7647 | 0.7647 | 653ms |
| marqo_fashion_siglip | 0.7647 | 0.6471 | 1012ms |

fashion_clip 혼동행렬: **BLACK 0/2**(→GRAY 1, →NAVY 1)가 유일한 실패. WHITE 3/3 · GRAY 1/1 ·
GREEN 1/1 · **BLUE 6/6 · NAVY 4/4**.

- **BLUE↔NAVY가 완전히 해결됐다.** 팔레트 축소(SKYBLUE→BLUE) + 패션 체크포인트 조합의 성과다.
  §17에서 최대 오답원이던 축이 10/10이 됐다.
- 남은 건 **어두운 무채색(BLACK↔GRAY↔NAVY)** 뿐이고, 둘 다 TOP이다. 검은 원단의 노출 편차라
  광학적 문제에 가깝다 — 550k의 다양한 조명이 직접 도움 되는 지점.
- **화이트밸런스는 이제 해롭다**(0.88→0.82). 범용 체크포인트의 편향을 상쇄하던 보정이라,
  체크포인트가 패션을 알게 되자 노이즈가 됐다.
- **보조색상은 전 모델 0.00**(§2-3 참고).

### 1-3. 결론 — 모델 선택

**`fashion_clip`(patrickjohncyh/fashion-clip)을 백본으로 고정한다.** 카테고리 동률,
색상 최고(0.882), **지연 최저(123ms — marqo 대비 5~8배 빠름)**. marqo 2종은 ViT-B/16이라
비용만 크고 얻는 게 없다.

## 2. 코드 점검 결과 (선행 수정 필요)

| # | 문제 | 근거 | 조치 |
|---|---|---|---|
| 1 | `EmbeddingZeroShotClassifier.TEMPERATURE = 100.0` 하드코딩 | fashion_clip **ece 0.312**, 권장 임계값 0.999로 과신. marqo_fashion_clip은 ece 0.227인데 커버리지 13/17로 더 나음 | 모델의 `logit_scale`을 쓰거나 홀드아웃 temperature scaling. **랭킹엔 영향 없고 임계값 자동채움에만 영향** |
| 2 | SigLIP에 softmax 적용 | `classify.py` docstring이 이미 예고한 단순화. SigLIP 정식은 sigmoid(logit_scale+bias) | marqo_siglip을 안 쓰기로 했으므로 **보류**(문서화만) |
| 3 | 보조색상 전 모델 0.00 | `SECONDARY_MIN_SCORE = 0.15`인데 temp=100 softmax라 1등이 0.99+를 먹어 2등이 절대 못 넘음 | #1과 같은 뿌리. 확률 임계 대신 **순위+마진** 기준으로 바꾼다 |
| 4 | `_wb` 변형이 패션 체크포인트에서 유해 | 실측 0.88→0.82, 0.76→0.65 | 기본 조합에서 제외(코드는 유지, baseline 전용으로 주석) |
| 5 | 지연이 CPU 전용 측정 | 5~8배 차이가 의사결정에 영향 | `device` 옵션 추가 |
| 6 | 정답셋 N=17 / 35종 중 6종만 등장 | **4개 모델 전부 0.7059 동률** | 이게 진짜 병목 — §4-3 평가셋 확장 |

## 3. 사용자가 제공해야 하는 것

| # | 항목 | 왜 필요한가 | 없으면 |
|---|---|---|---|
| 1 | **AI-Hub 데이터 실물** — 다운로드 완료 경로, 폴더 구조, 총 용량 | 전처리 코드가 경로 규약에 의존 | 착수 불가 |
| 2 | **`model.type`의 front/back이 상품컷인가 착용샷인가** (샘플 20장 육안) | 우리 입력은 flat 14 / hanging 4 / **worn 0**. 전부 착용샷이면 도메인 갭이 크다 | 학습해도 안 오를 수 있음 |
| 3 | **`metadata.clothes.color`에 Navy가 실재하는가** | LAB-76 §3-1(14종, Navy 있음)과 §4-7(13종, Navy 없음)이 **모순**. 우리 팔레트엔 Navy가 있고 정답셋 4/17이 NAVY | Navy만 지도 신호 없음 → 별도 라벨링 |
| 4 | **GPU 서버** — VRAM, CUDA 버전, 디스크 여유, 접속 방법 | 임베딩 추출 배치 크기 결정 | 로컬 RTX 4070(8GB)으로 대체 가능하나 느림 |
| 5 | **라벨 정정 승인 2건** — `greyp.png`·`navy_cotton.png` → `COTTON_PANTS` | §1-1. 지표가 0.7059→0.7647로 바뀐다 | 잘못된 기준선으로 학습 효과를 오판 |
| 6 | **라이선스** — 상업적 이용 / 모델 배포 가능 여부 | 실서비스 반영 가부 | PoC까지만 |

## 4. 구현 설계

### 4-0. 왜 파인튜닝이 아니라 헤드인가

- **top-3 = 1.00** → 표현은 이미 분리돼 있다. 백본을 흔들 이유가 없다.
- **커버리지 구멍**: AI-Hub는 35종 중 11종만 덮는다. 나머지 24종(신발·가방·액세서리 15종
  포함)은 zero-shot 의존인데, 백본을 바꾸면 **그쪽이 먼저 무너진다.**
- 헤드만이면 재학습이 초 단위라 하이퍼파라미터 탐색이 사실상 공짜다.

### 4-1. 2단계 구조 — 임베딩을 캐시한다

```
[1단계 · GPU 1회] 이미지 → fashion_clip(frozen) → 임베딩 .npy 캐시
[2단계 · CPU 초단위] 임베딩 + 라벨 → 헤드 학습 → .joblib
```

GPU는 **1단계에만** 필요하다. 2단계는 노트북 CPU로 몇 초다. 전처리 변형(원본 vs 마스크 크롭)을
비교할 때도 1단계만 두 번 돌리면 된다.

### 4-2. 세 갈래로 나눠 접근한다 (문제 성격이 다르다)

**(A) 색상 — 14-way linear probe. 커버리지 100%라 정석대로 된다.**
- 층화 샘플 색상당 2,000장 (Mixed 포함, Navy는 §3-3 확인 후)
- **입력 변형 2개를 반드시 비교**: 원본 vs Polygon 마스크 bbox 크롭 + 배경 흰색 치환.
  §V3 실패가 "콘크리트 바닥이 1등 클러스터"였으므로 이 델타가 곧 "배경 제거의 가치"다
- 수용 기준: 우리 정답셋 17장에서 **0.882 초과**. 0.90(VLM) 넘으면 색상에서 VLM 제거 검토

**(B) 카테고리 — 혼동쌍 이진 판별기부터. 가장 수술적이고 리스크가 0에 가깝다.**

실패가 딱 2쌍이므로 35-way를 건드리지 않는다. zero-shot이 top-2로 `{TSHIRT, SHIRT}`를
뽑았을 때만 발동하는 이진 헤드를 얹는다.

- 학습 데이터를 **라벨로 정확히 뽑을 수 있다**:
  `02top_02t-shirt` + `topneck_color_design == "polo"` → TSHIRT 양성
  `02top_04shirt` + `topneck_color_design == "shirts collar"` → SHIRT 양성
- 나머지 33종 동작을 **전혀 건드리지 않는다** → 회귀 위험 없음
- 수용 기준: 폴로 2건 회복, 나머지 15장 예측 불변

**(C) 카테고리 전면 — 하이브리드 프로토타입. (B) 이후 선택적.**
- 커버 11종은 **이미지 프로토타입**(클래스 평균 임베딩), 미커버 24종은 **텍스트 프로토타입**
- ⚠️ **모달리티 갭 보정 필수**: CLIP의 이미지/텍스트 임베딩은 서로 다른 영역에 뭉쳐 있어
  그냥 섞으면 이미지 프로토타입을 가진 11종이 부당하게 이긴다. 모달리티별 평균 차감 후
  재정규화하고, **미커버 클래스 정확도가 떨어지지 않는지 반드시 홀드아웃 확인**

**AI-Hub로 못 고치는 것**: 하의 세부(DENIM/SLACKS/CARGO/JOGGER/COTTON)는 pants 하위
소재·디테일 정보가 없어 원리적으로 불가능하다. 이건 **번개장터 크롤(`crawl-collector/`,
`sites/bunjang.yaml` 검증 완료)** 로 따로 모아야 한다. 도메인도 우리 서비스와 같다.

### 4-3. 평가셋 — 학습보다 이게 급하다

4개 모델이 전부 0.7059로 동률인 건 **정답셋이 모델을 구분하지 못한다**는 뜻이다(N=17,
35종 중 6종, `MIN_N_FOR_CONFIDENCE=30` 미달). AI-Hub 홀드아웃으로 클래스당 100장씩 뽑아
**커버 11종 × 100 = 1,100장 평가셋**을 먼저 만든다. 단 도메인이 다르므로(§3-2) **우리
정답셋 17장과 항상 함께 보고, 둘이 어긋나면 우리 것을 믿는다.**

### 4-4. 전처리 파이프라인

1. **JSON 파싱** — 함정 3개(LAB-76): 최상위 키가 `metadata.clothes`처럼 **점 포함 평탄 키**
   (중첩 아님), 빈 값이 `None`이 아니라 **문자열 `"null"`**, 숫자도 문자열(`"66.0"`)
2. **라벨 매핑** — `clothes.type` 13종 → 우리 35종. v2 기준 갱신 필요(LAB-76 §2는 v1 기준이라
   낡음: VEST 삭제, DRESS·JUMPSUIT 신규 사용 가능). 파생: `SHORT_PANTS`(`pants_length` 임계),
   `SLEEVELESS`(`sleeve_length_type`), `HOODIE`(`topneck == "hood"`)
3. **마스크** — `annotation[].annotation_point`는 평탄 `[x1,y1,x2,y2,…]`. `dataset.width/height`로
   정규화 → 폴리곤 → 마스크 → bbox 크롭 + 배경 흰색
4. **split** — **행(아이템) 단위로 먼저 train/val을 나눈 뒤** 그 안에서 샘플링한다
   (`AI/CLAUDE.md` 관례: 순서를 반대로 하면 지표가 부풀려진다)
5. **임베딩 추출** — fashion_clip 이미지 인코더, L2 정규화 후 `.npy`

### 4-5. 산출물 배치

```
AI/validation/CLASS/product-info-finetune/     # 신규 스파이크 디렉터리
  dataset.py       # AI-Hub JSON 파싱 + 라벨 매핑 + split
  preprocess.py    # 마스크/크롭/배경치환
  embed.py         # GPU 1회 임베딩 추출 → artifacts/
  train_head.py    # 색상 probe + 혼동쌍 이진 헤드
  evaluate_head.py # 우리 정답셋 17장 + AI-Hub 홀드아웃 동시 평가
  artifacts/       # .gitignore — 임베딩·헤드 체크포인트
```

⚠️ `product-info-check/`에 **테스트 파일을 추가하지 않는다** — 그 폴더의 `dataset.py`가
`REC/recommendation-embedding-finetune/dataset.py`를 가려 CI가 깨진다(`AI/CLAUDE.md` 기록).
신규 폴더도 `dataset.py`를 두면 같은 충돌이 나므로 **테스트를 넣을 거면 파일명을
`aihub_dataset.py`처럼 유일하게** 짓는다.

### 4-6. GPU 서버 실행 순서

```bash
pip install -r AI/validation/requirements-test.txt   # torch/transformers/PIL
python embed.py --split train --variant masked       # 1단계, GPU
python embed.py --split train --variant raw          # 비교군
python train_head.py --task color --variant masked   # 2단계, CPU 수 초
python evaluate_head.py --task color
```

## 5. 수용 기준

| 항목 | 현재 | 목표 |
|---|---|---|
| 색상 (우리 정답셋 17장) | 0.882 | **> 0.882**, 가능하면 VLM 0.90 초과 |
| 카테고리 폴로 2건 | 0/2 | **2/2** |
| 카테고리 나머지 15장 | — | **예측 불변**(회귀 가드) |
| CPU p50 지연 | 123ms | **≤ 200ms**(헤드는 행렬곱 1회) |

## 6. 리스크

- **도메인 갭**(§3-2). front/back이 전부 착용샷이면 학습해도 flat 사진에서 안 오를 수 있다.
  → 착수 전 확인이 게이트다.
- **Navy 부재**(§3-3). 우리 팔레트 14종 중 하나에 지도 신호가 없을 수 있다.
- **N=17 과신**. 1장이 5.9%p다. AI-Hub 홀드아웃(§4-3)과 항상 같이 본다.
- **모달리티 갭**(§4-2 C). 보정 없이 하이브리드를 쓰면 커버 클래스만 유리해진다.
