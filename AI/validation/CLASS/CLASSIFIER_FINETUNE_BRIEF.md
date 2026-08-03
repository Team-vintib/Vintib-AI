# 상품 분류 헤드 학습 브리핑 (AI-Hub 의류 통합 데이터)

작성 2026-08-03. 이 문서를 읽는 에이전트가 **그대로 수행할 작업 지시서**다.
설계 근거는 `.claude/plans/ai/CH014-class-finetune.md`, 실측 근거는
`AI/validation/CLASS/product-info-check/REPORT.md`.

---

## 0. ⚠️ 이 작업이 무엇이고, 무엇이 아닌가

**하는 일**: 상품 사진 1장에서 **카테고리(소분류 35종)와 색상(13종+MIXED)** 을 맞히는
정확도를 올린다. 판매자가 상품 등록할 때 폼을 자동 채우는 기능이다.

**하지 않는 일 — 아래와 혼동하지 마라. 실제로 혼동 사고가 있었다.**

| 착각하기 쉬운 것 | 실제 |
| --- | --- |
| 추천용 임베딩 모델 학습 | **전혀 다른 작업.** `validation/REC/recommendation-embedding-finetune/`은 상품 추천용이다. **이 폴더를 건드리지 마라.** |
| 검색/유사도 임베딩 파인튜닝 | 아니다. 우리는 **분류 헤드**를 학습한다 |
| 백본(CLIP) 전체 파인튜닝 | **명시적으로 금지.** 이유는 §3 |
| 가상 시착 / 하자 탐지 모델 | 다른 도메인이다 |

**한 줄 요약**: `fashion_clip` 백본은 **동결**하고, 그 위에 **선형 분류 헤드**만 학습한다.

---

## 1. 먼저 읽을 문서 (이 순서로)

1. `AI/CLAUDE.md` — 하드 룰(GMS 금지), CI 절차, 테스트 배치 함정
2. `.claude/plans/ai/CH014-class-finetune.md` — **이 작업의 설계 계획. 가장 중요**
3. `AI/validation/CLASS/product-info-check/REPORT.md` §18~§20 — 실측 근거
4. `AI/validation/CLASS/product-info-check/taxonomy.py` / `color.py` — 라벨 정본
5. Notion "실험실 > [DATA] 의류 통합 데이터 — 어노테이션 포맷" (LAB-76) — 데이터 포맷 명세
   - ⚠️ **LAB-76 §2의 매핑표는 낡았다.** taxonomy v1(30종) 기준으로 쓰였다. 아래 §5의 v2 표를 쓴다.

---

## 2. 지금 무엇이 실패하고 있는가 (실측, N=19)

`fashion_clip` zero-shot 기준선:

| 지표 | 값 |
| --- | --- |
| 소분류 35종 top-1 | 0.7895 |
| 소분류 top-3 | **1.0000** |
| 대분류 역산 | 1.0000 |
| 색상 | 0.8947 |
| CPU p50 지연 | 123ms |

**오답 4건이 전부다:**

| 이미지 | 정답 | 예측 | 유형 |
| --- | --- | --- | --- |
| `small_pro.jpg` | TSHIRT | SHIRT | **폴로 셔츠** |
| `black_stain.png` | TSHIRT | SHIRT | **폴로 셔츠** |
| `logo_test.jpg` | TSHIRT | SHIRT | 긴팔 크루넥 티, 뒷면 촬영 |
| `greyp.png` | COTTON_PANTS | CARGO_PANTS | 하의 세부 |

색상 오답 2건은 **둘 다 검은 상의**(BLACK→GRAY, BLACK→NAVY).

**두 가지 사실이 접근 방식을 결정한다:**

1. **top-3이 1.00이다** → 임베딩은 이미 클래스를 분리하고 있고, 틀리는 건 top-1 결정 경계뿐이다.
   백본을 흔들 이유가 없다. **선형 헤드가 정확히 이 간극을 메운다.**
2. **후보 모델 4종(범용 CLIP / FashionCLIP / Marqo 2종)이 전부 같은 사진에서 같은 방식으로
   틀렸다** → 체크포인트 교체로는 더 못 움직인다. 지도 신호가 필요하다.

---

## 3. 접근 방식 — 동결 백본 + 헤드 (전체 파인튜닝 금지)

**왜 전체 파인튜닝을 금지하는가**: AI-Hub 데이터는 우리 소분류 35종 중 **11종만** 덮는다.
나머지 24종(신발 4 · 가방 5 · 액세서리 6 포함 15종은 데이터가 **0장**)은 zero-shot에 의존한다.
백본을 바꾸면 **그쪽이 먼저 무너진다.** 실제로 신발·가방은 zero-shot이 이미 잘 맞힌다
(`apc.png` CROSS_BAG 정답, `loaf.png` DRESS_SHOES score 0.995).

### 2단계 구조 — 임베딩을 캐시한다

```
[1단계 · GPU 1회] 이미지 → fashion_clip(동결) → 임베딩 .npy 캐시
[2단계 · CPU 초단위] 임베딩 + 라벨 → 선형 헤드 → .joblib
```

GPU는 1단계에만 필요하다. 2단계는 재학습이 초 단위라 하이퍼파라미터 탐색이 사실상 공짜다.

### 학습할 헤드 2개 (우선순위 순)

**(A) 색상 14-way 로지스틱 회귀** — 가장 확실하다. 색상은 **라벨 커버리지 100%**라
정석대로 된다(카테고리와 달리 빈 클래스가 없다).
- **입력 변형 2개를 반드시 비교하라**: ① 원본 이미지 ② Polygon 마스크 bbox 크롭 + 배경 흰색 치환.
  그 차이가 곧 "배경 제거의 가치"다. 과거 색상 실패의 원인이 배경 오염이었다(REPORT §V3:
  콘크리트 바닥이 1등 클러스터로 잡힘).

**(B) 폴로 이진 판별기** — 35-way를 **건드리지 않는다.** zero-shot이 top-2로
`{TSHIRT, SHIRT}`를 뽑았을 때만 발동하는 이진 헤드다.
- 학습 데이터를 라벨로 정확히 뽑을 수 있다:
  `02top_02t-shirt` + `topneck_color_design`에 `polo` 포함 → TSHIRT 양성
  `02top_04shirt` + `topneck_color_design == "shirts collar"` → SHIRT 양성
- 나머지 33종 동작을 전혀 안 건드리므로 **회귀 위험이 없다.** 이게 이 설계의 핵심 장점이다.

**(C) 전면 하이브리드 프로토타입** — (A)(B)가 끝난 뒤 선택. 커버 11종은 이미지 프로토타입,
미커버 24종은 텍스트 프로토타입. ⚠️ CLIP의 이미지/텍스트 임베딩은 서로 다른 영역에 뭉쳐
있어(modality gap) 그냥 섞으면 **이미지 프로토타입을 가진 11종이 부당하게 이긴다.**
모달리티별 평균 차감 후 재정규화하고, **미커버 클래스 정확도가 떨어지지 않는지 반드시 확인**하라.

### 못 고치는 것 (시도하지 마라)

하의 세부 5종(DENIM / SLACKS / CARGO_PANTS / JOGGER_PANTS / COTTON_PANTS)은 AI-Hub의
`04bottom_01pants`에 **소재·디테일 정보가 없어 원리적으로 불가능**하다.
`pants_silhouette`(skinny/wide/loose)는 실루엣이지 종류가 아니다. 이건 별도로
번개장터 크롤(`validation/CLASS/crawl-collector/`, `sites/bunjang.yaml` 검증 완료)로 모아야 한다.

---

## 4. 반드시 먼저 할 것 — scan (게이트 2개)

**코드를 다 쓰기 전에, 라벨 JSON만 훑어 아래 2개를 확인하라.** 둘 다 이 작업의 전제를
흔들 수 있다. 이미지는 안 받아도 되고 JSON만 있으면 된다.

| # | 확인 | 방법 | 왜 중요한가 |
| --- | --- | --- | --- |
| 1 | `metadata.model.type`의 **front / back이 "옷만 찍은 상품컷"인지 "모델이 입은 사진"인지** | 각 값에서 5장씩 실제로 이미지를 열어 확인 | 우리 서비스 입력은 **flat 15 / hanging 4 / worn 0**이다. 전부 착용샷이면 도메인 갭이 커서 학습해도 안 오를 수 있다 |
| 2 | `metadata.clothes.color`에 **Navy가 실재하는가** | distinct 값 카운트 | LAB-76이 자기모순이다(§3-1은 Navy 있는 14종, §4-7은 없는 13종). 우리 팔레트엔 Navy가 있고 정답셋 4/19가 NAVY다. 없으면 Navy만 지도 신호가 빈다 |

추가로 scan이 출력해야 하는 것:
- `clothes.type` 13종의 실제 건수 (특히 `04bottom_01pants` / `04bottom_02skirt` 분해 —
  LAB-76 표에는 bottom 123,500 합계만 있다)
- `pants_length` 분포 히스토그램 → **SHORT_PANTS 파생 임계값을 여기서 정한다**
- `topneck_color_design` 값 분포 (특히 `polo` 건수 — (B) 헤드의 학습량이 결정된다)
- `sleeve_length_type` 분포 (SLEEVELESS 파생량)
- **그룹 키 크기 분포** (§7 참고)

**데이터 받는 순서 요령**: 이미지 전체는 약 40GB(550,634 × ~70KB)인데 우리는 **5만 장이면
충분**하다. ① 라벨 JSON만 먼저 받아 ② 인덱스를 만들고 층화 샘플링으로 파일 목록을 확정한 뒤
③ 그 목록의 이미지만 받는다 → 약 3.5GB. 게이트 확인도 ①만으로 끝난다.

---

## 5. 라벨 매핑 (taxonomy v2 기준 — LAB-76 §2 대신 이걸 쓴다)

정본은 `product-info-check/taxonomy.py`(소분류 35종)와 `color.py`(13종+MIXED)다.
**이 두 파일을 수정하지 마라** — 2026-08-03에 BE 확정 시드 기준으로 갱신을 마쳤다.

### 카테고리 — 직접 매핑 9종

| AI-Hub `clothes.type` | 우리 코드 |
| --- | --- |
| `01outer_01coat` | `COAT` |
| `01outer_02jacket` | `JACKET` |
| `01outer_04cardigan` | `CARDIGAN` |
| `02top_02t-shirt` | `TSHIRT` |
| `02top_03sweater` | `KNIT` |
| `02top_04shirt` | `SHIRT` |
| `04bottom_02skirt` | `SKIRT` |
| `03-1onepiece(dress)` | `DRESS` |
| `03-2onepiece(jumpsuite)` | `JUMPSUIT` |

### 제외 (우리 코드에 대응이 없거나 미결정) — 학습에서 빼라

| AI-Hub | 이유 |
| --- | --- |
| `02top_05vest` | taxonomy v2에 `VEST`가 **없다**(BE 시드에 없음) |
| `01outer_03jumper` | `JACKET` 흡수 여부 미결정 |
| `02top_01blouse` | `SHIRT` 흡수 여부 미결정 |
| `04bottom_01pants` | 하위 5종 구분 불가(§3 참고). 단 아래 `SHORT_PANTS` 파생에만 사용 |

### 파생 규칙 — 우선순위 순으로 적용 (앞의 규칙이 이긴다)

1. `02top_*` + `topneck_color_design == "hood"` → **`HOODIE`**
2. `02top_*` + `sleeve_length_type == "sleeveless"` → **`SLEEVELESS`**
3. `04bottom_01pants` + `pants_length` < 임계 → **`SHORT_PANTS`** (임계는 scan 히스토그램으로 결정)
4. 그 외는 위 직접 매핑표

**폴로 플래그(카테고리 라벨이 아니라 (B) 헤드 전용)**: `topneck_color_design`에 `polo`가
포함되면 폴로다. 카테고리 라벨은 그대로 `TSHIRT`로 두고, 별도 boolean 컬럼으로 들고 간다.

→ 합계 **9 직접 + 2~3 파생 = 11~12종 / 35종**. 나머지는 zero-shot 유지.

### 색상 — 그대로 매핑 (대소문자·공백 정규화 후)

`Black→BLACK` `White→WHITE` `Gray→GRAY` `Red→RED` `Orange→ORANGE` `Pink→PINK`
`Yellow→YELLOW` `Brown→BROWN` `Green→GREEN` `Blue→BLUE` `Purple→PURPLE` `Beige→BEIGE`
`Navy→NAVY`(게이트 2 확인 후) `Mixed→MIXED`

---

## 6. 쓸 컬럼만 — 100개 넘는 필드 중 10개

### 필수 7

| 필드 | 용도 |
| --- | --- |
| `dataset.image_path` | 이미지 로드 |
| `dataset.width` / `.height` | **Polygon 좌표 정규화에 필수** |
| `annotation[].annotation_point` | 세그멘테이션 마스크 → 배경 제거 크롭 |
| `metadata.clothes.type` | 카테고리 정답 라벨 |
| `metadata.clothes.color` | 색상 정답 라벨 |
| `metadata.model.type` | 촬영유형(front/back/wear) — 층화 평가·도메인 갭 측정 |

### 파생용 3

`metadata.pants.pants_length` · `metadata.clothes.topneck_color_design` ·
`metadata.clothes.sleeve_length_type`

### 절대 쓰지 말 것

- **케어라벨**(`washing_method` `bleach` `ironing` `drycleaning` …) — 이미지에서 추론 불가
- **착용자 신상·신체치수**(`model.job` `model.age` `body_height` `weight` `chest_size_*` …) —
  상품 속성이 아니다. `job`은 40여 종인데 학습에 넣으면 편향만 심어진다
- **의류 실측**(`metadata.top.*` `skirt.*` `dress.*` …) — 분류엔 불필요.
  **예외: `pants.pants_length`만 SHORT_PANTS 파생에 쓴다**
- `metadata.model.gender` — **착용자(사람)의 성별이지 옷의 성별이 아니다.** 게다가 UNISEX가
  없어 우리 3-way와 라벨 공간이 다르다. **성별은 AI가 판별하지 않는 것으로 확정됐다**
  (`.claude/requests/be/005-category-gender-stays-in-form.md`). 쓰지 마라

---

## 7. 파싱 함정 3개 (LAB-76에 기록된 실제 함정)

1. **최상위 키가 점 포함 평탄 키다.** `metadata.model` / `metadata.clothes`처럼 생겼지만
   중첩 객체가 **아니다**. `js["metadata"]["clothes"]`는 실패한다.
   `js["metadata.clothes"]["metadata.clothes.type"]`가 맞다.
2. **빈 값이 `None`이 아니라 문자열 `"null"`이다.** 숫자 필드도 문자열이다(`"56"`, `"66.0"`).
   캐스팅 전에 반드시 `"null"` 체크.
3. **명세 표기와 실제 JSON 키가 다르다.** 명세는 `annotation.type`인데 실제 키는
   `annotation_type`, `annotation_point`다. **코드는 실제 키 기준으로 써라.**
   또 `dataset.category`는 스펙상 0=OCR/1=객체인식인데 **실제 값이 8**이다 — 신뢰하지 마라.

---

## 8. train / val / test 분할 — 그룹 누수를 반드시 막아라

**비율**: train 0.8 / val 0.1 / test 0.1 (AI-Hub 자체 관례와 동일). 시드는 파일 상단 상수로 노출.

**⚠️ 가장 중요한 규칙 — 같은 의류의 다른 촬영본이 split을 넘나들면 안 된다.**

파일명 `01_sou_000834_004168_wear_02top_04shirt_woman`에서 앞쪽 숫자(`000834`)가 같은
이미지들은 **같은 의류의 front / back / wear** 일 가능성이 높다. 이걸 train과 test에
흩어 놓으면 누수라 지표가 부풀려진다.

1. 파일명의 첫 숫자 그룹을 **그룹 키**로 뽑는다
2. **scan에서 그룹 크기 분포를 먼저 출력**해 실제로 2~3장씩 묶이는지 확인한다
   (전부 1이면 그룹 분할은 no-op이고, 그 사실 자체를 로그로 남긴다)
3. **그룹 단위로 분할**하고, 그 안에서 라벨 층화한다

이건 `AI/CLAUDE.md`의 기존 규율과 같은 취지다 — *"항목(row) 단위로 먼저 train/val을 나누고,
쌍은 그 이후 각 split 내부에서만 만든다. 순서를 반대로 하면 같은 아이템이 양쪽 split에
걸쳐 평가 지표가 부풀려진다."*

**층화 샘플링 규모**(550k 전부 쓰지 마라):
- 색상: 클래스당 2,000장 × 14 ≈ 28,000
- 카테고리: 커버 클래스당 3,000장 × 11 ≈ 33,000
- 합집합 중복 제거하면 5만 장 내외

---

## 9. 산출물 배치와 명명 규칙

```
AI/validation/CLASS/product-info-finetune/
  aihub_dataset.py       # 인덱싱 + 라벨 매핑 + 분할 + scan
  aihub_preprocess.py    # Polygon → 마스크 → bbox 크롭 + 배경 흰색
  aihub_embed.py         # 임베딩 추출 (GPU, 1회)
  aihub_train_head.py    # 색상 probe + 폴로 이진 헤드
  aihub_evaluate.py      # val/test + 우리 정답셋 19장 동시 평가
  README.md              # 실행 순서
  artifacts/             # .gitignore 추가 필요 — .npy / .joblib
```

### ⚠️ 모듈 이름은 반드시 `aihub_` 접두어를 붙여라

pytest 기본(`prepend`) import 모드는 **테스트 파일이 있는 폴더를 통째로 `sys.path`에 올린다.**
그래서 **테스트 파일명뿐 아니라 형제 모듈 이름도** 다른 스파이크 폴더와 충돌하면 안 된다.
2026-08-03에 실제로 `product-info-check/dataset.py`가
`REC/recommendation-embedding-finetune/dataset.py`를 가려 **CI 수집이 깨졌다.**
`dataset.py` / `evaluate.py` / `embed.py` 같은 흔한 이름을 쓰면 같은 사고가 난다.

테스트 파일도 리포 전체에서 유일해야 한다 → `test_class_finetune_dataset.py` 같은 이름.

---

## 10. 하드 룰 (위반하면 안 되는 것)

1. **GMS API(`gms.ssafy.io`)를 경유하는 코드를 절대 실행하지 마라.** 팀 공용 유료 쿼터다.
   이 작업엔 GMS가 필요 없다 — 필요해 보이면 잘못 가고 있는 것이다. `AI/CLAUDE.md` 참고
2. **push 하지 마라.** 로컬 커밋까지만. push는 사용자가 직접 한다
3. 커밋 메시지는 `[S15P11A108-479] type: subject` 형식. **Co-Authored-By에 Claude를 넣지 마라**
4. **커밋 전 CI를 로컬에서 그대로 통과시켜라**:
   ```bash
   cd AI
   ruff check .
   black --check .
   pytest -q
   ```
   노트북(`.ipynb`)도 ruff 검사 대상이다
5. **무거운 import는 함수 내부 지연 import.** CI는 `requirements-dev.txt`만 설치한다 —
   torch/transformers를 모듈 최상단에서 import하면 CI가 깨진다. 무거운 의존성이 필요한
   테스트는 `pytest.importorskip`으로 가드
6. **`taxonomy.py` / `color.py`를 수정하지 마라.** BE 확정 시드 기준으로 갱신이 끝났다
7. **`worker/` 프로덕션 코드에 반영하지 마라.** §11 수용 기준을 통과한 뒤 별도 작업이다

---

## 11. 수용 기준

| 항목 | 현재 (N=19) | 목표 |
| --- | --- | --- |
| 색상 (우리 정답셋) | 0.8947 | **> 0.8947** (VLM 0.90 초과면 색상에서 VLM 제거 검토) |
| 폴로 2건 (`small_pro`, `black_stain`) | 0/2 | **2/2** |
| 나머지 17장 예측 | — | **불변** (회귀 가드 — 이게 깨지면 실패다) |
| CPU p50 지연 | 123ms | **≤ 200ms** (헤드는 행렬곱 1회라 사실상 0) |

**평가는 두 세트를 항상 같이 본다**: AI-Hub val/test **그리고** 우리 정답셋 19장.
**둘이 어긋나면 우리 정답셋을 믿어라** — 도메인이 다르다(AI-Hub는 착용샷 중심,
우리 입력은 flat/hanging).

우리 정답셋은 N=19로 작다(1장이 5.3%p). AI-Hub 홀드아웃으로 **커버 11종 × 100장 = 1,100장
평가셋**을 함께 만들어 추세를 보되, 최종 판단은 19장 쪽이다.

---

## 12. 작업 순서 요약

1. §1의 문서를 읽는다
2. `aihub_dataset.py`에 파싱 + 매핑 + scan을 구현한다 (픽스처로 단위 테스트, CI 통과)
3. **scan을 돌려 §4의 게이트 2개를 확인한다** → 결과를 사용자에게 보고하고 진행 여부를 받는다
4. 게이트 통과 후 `aihub_preprocess.py` → `aihub_embed.py`(GPU 1회, 두 변형) →
   `aihub_train_head.py` → `aihub_evaluate.py`
5. 수용 기준 대조 결과를 `product-info-check/REPORT.md`에 §21로 기록한다
6. 커밋(push 금지)

**막히거나 전제가 깨지면 진행하지 말고 사용자에게 보고하라.** 특히 게이트 2개는
"안 되면 이 작업 자체를 다시 설계해야 하는" 항목이다.
