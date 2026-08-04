# 상품 분류 헤드 학습 (AI-Hub 의류 통합 데이터 + 패션 액세서리 착용 데이터)

`fashion_clip` 백본을 **동결**한 채 그 위에 선형 분류 헤드만 학습해서, 상품 사진의
**카테고리(소분류 35종)** 와 **색상(13종+MIXED)** 정확도를 올리는 스파이크.

- 지시서: [`../CLASSIFIER_FINETUNE_BRIEF.md`](../CLASSIFIER_FINETUNE_BRIEF.md)
- 설계: `.claude/plans/ai/CH014-class-finetune.md`
- 실측 근거: [`../product-info-check/REPORT.md`](../product-info-check/REPORT.md) §18~§20
- 라벨 정본: `../product-info-check/taxonomy.py` · `color.py` (**수정 금지**)
- 데이터 포맷: Notion LAB-76(의류) · AI-Hub 데이터셋 상세 어노테이션 포맷(액세서리)

> 추천용 임베딩 학습(`validation/REC/recommendation-embedding-finetune/`)과는 **전혀 다른
> 작업**이다. 백본 전체 파인튜닝도 금지다(브리핑 §3).

## 데이터 소스 2개

| 소스 | dataSetSn | 덮는 우리 코드 | 비고 |
| --- | --- | --- | --- |
| 008. 의류 통합 데이터 | 71501 | COAT · JACKET · CARDIGAN · TSHIRT · KNIT · SHIRT · SKIRT · DRESS · JUMPSUIT + 파생 HOODIE · SLEEVELESS · SHORT_PANTS | 550,634건. 색상 라벨 커버리지 100% |
| 009. 패션 액세서리 착용 데이터 | 71441 | HAT · SUNGLASSES · JEWELRY | 카테고리·색상이 **별도 속성 JSON**에 있어 `accessory_id`로 조인해야 한다 |

여전히 안 덮이는 것: SHOES 4종 · BAG 5종 · BELT/SCARF/WATCH · 하의 세부 5종. **이들은 계속
zero-shot이 담당한다** — 그래서 백본을 동결한다(브리핑 §3).

### 확정된 매핑 판단 (2026-08-04)

- `02top_01blouse` → **`SHIRT`로 흡수**(사용자 확정). 29,719건이 SHIRT로 들어온다.
- `02top_05vest` → **제외 유지**(사용자 확정). taxonomy v2에 `VEST`가 없다.
- `안경테` → **제외**. 우리 taxonomy에 SUNGLASSES는 있어도 도수 안경은 없다.
- `목걸이`·`귀걸이` → 둘 다 `JEWELRY`(N:1). 그래서 JEWELRY만 표본이 2배로 들어온다 —
  `--accessory-cap`이 이걸 눌러 준다.
- 액세서리 색상 23종 → 13종+MIXED. 은퇴 코드는 `color.py`의 `RETIRED_COLOR_MAP`을 그대로
  따르고(실버→GRAY, 골드→YELLOW, 카키→GREEN, 와인→RED, 스카이블루→BLUE), 명세에만 있는
  3종은 이 스파이크가 판단했다: **민트→GREEN · 로즈골드→PINK · 투명/기타→제외**.

## 실행 환경 — 코드는 로컬, 무거운 실행은 원격 GPU

- 모든 무거운 단계는 `argparse`를 받는 `.py`다. 경로 하드코딩 없음, `Path.cwd()` 의존 없음.
- 노트북 `aihub_pipeline.ipynb`는 **얇은 드라이버**다 — 각 스크립트를 호출하고 결과 표를
  보여줄 뿐이다. 오래 걸리는 단계(scan, 임베딩)는 셀이 찍어 주는 `$ ...` 명령을 복사해
  **`tmux` 안에서** 돌리는 걸 권장한다(원격 커널은 끊기면 죽는다).
- 산출물은 `artifacts/`에 쌓이고 `AI/.gitignore`에 이미 등록돼 있다.

### 서버에 올려서 실행할 파일

| 파일 | 언제 | GPU | 역할 |
| --- | --- | --- | --- |
| `aihub_dataset.py` | STEP 1·2 | ✗ | 파싱 · 라벨 매핑 · 그룹 분할 · 층화 샘플링 · `scan` |
| `aihub_accessory.py` | (모듈) | ✗ | 액세서리 소스 파싱/매핑. `aihub_dataset.py`가 부른다 |
| `aihub_preprocess.py` | STEP 2.5 | ✗ | Polygon → 마스크 → bbox 크롭 + 배경 흰색. CLI는 미리보기용 |
| `aihub_embed.py` | STEP 3 | **✓** | fashion_clip(동결) 임베딩 → `.npy`. **여기만 GPU** |
| `aihub_train_head.py` | STEP 4 | ✗ | 색상/폴로/카테고리 헤드 학습 → `.joblib` (수 초) |
| `aihub_evaluate.py` | STEP 5 | △ | 홀드아웃 평가. 정답셋 평가를 켜면 모델 로드가 필요 |
| `aihub_pipeline.ipynb` | 전체 | — | 위 5개를 순서대로 호출하는 드라이버 |

의존성: `pip install -r validation/requirements-test.txt` (torch/transformers/Pillow) +
`scikit-learn`·`joblib`(같은 파일에 이미 있다). STEP 1·2는 표준 라이브러리만으로 돈다.

## STEP 1 — scan (착수 게이트 2개)

**이미지 없이 라벨 JSON만 있으면 된다.**

```bash
tmux new -s aihub-scan
cd /path/to/repo/AI

python validation/CLASS/product-info-finetune/aihub_dataset.py scan \
    --root            /path/to/aihub/008.의류_통합_데이터 \
    --accessory-root  /path/to/aihub/009.패션_액세서리_착용_데이터 \
    --out             validation/CLASS/product-info-finetune/artifacts/scan.txt
```

먼저 감만 볼 거면 `--limit 5000`. 두 루트 중 하나만 줘도 된다.

### 사람이 판정해야 하는 것 2개 (브리핑 §4)

1. **게이트 1 — `metadata.model.type`의 front/back이 상품컷인가 착용샷인가.** scan이 값마다
   이미지 경로를 5개씩 찍는다. 그 파일을 직접 열어 볼 것. 우리 서비스 입력은
   flat 15 / hanging 4 / worn 0이라, 전부 착용샷이면 도메인 갭이 커서 학습해도 안 오를 수 있다.
2. **게이트 2 — `clothes.color`에 Navy가 실재하는가.** LAB-76이 자기모순이다(§3-1은 있고
   §4-7은 없다). scan이 `>>> Navy 실측 건수:`로 찍는다.

액세서리 쪽에서 추가로 볼 것: **조인이 성립하는지**(`조인 실패` 건수), **제품 단독컷 비율**
(우리 입력에 가까운 건 `product`다).

같이 나오는 것: `clothes.type` 13종 건수, `pants_length` 히스토그램(**SHORT_PANTS 임계를
여기서 정한다**), `topneck_color_design` 분포(polo 건수 = 폴로 헤드 학습량), 그룹 크기 분포,
경로 샘플.

## STEP 2 — index (인덱스 + 분할 + 층화 샘플)

여기서 **어떤 이미지를 받을지**가 정해진다. 이미지 전체는 수십 GB인데 5만 장이면 충분하다.

```bash
python validation/CLASS/product-info-finetune/aihub_dataset.py index \
    --root            /path/to/aihub/008.의류_통합_데이터 \
    --accessory-root  /path/to/aihub/009.패션_액세서리_착용_데이터 \
    --out-dir         validation/CLASS/product-info-finetune/artifacts \
    --category-cap    3000 \
    --accessory-cap   3000 \
    --color-cap       2000 \
    --eval-cap        100
```

### 데이터 활용 비중을 조절하는 손잡이 3개

| 손잡이 | 어디서 | 무엇을 바꾸나 |
| --- | --- | --- |
| `--category-cap` | index | 의류 소스의 **클래스당** 표본 상한 |
| `--accessory-cap` | index | 액세서리 소스의 클래스당 상한. 의류와 따로 건다 |
| `--class-weight balanced` | train_head | 남은 불균형을 손실 가중으로 보정 |

출력 맨 아래의 **"소스별 비중"** 표와 **"카테고리 분포(소스별)"** 표를 보고 다시 돌리면 된다.
카테고리 상한은 **엄수**된다 — 색상 쿼터를 채우려고 상한을 넘기지 않는다(옛 동작은
`--allow-cap-overflow`). `--short-pants-max-cm`은 **scan 히스토그램을 본 뒤에만** 준다.

산출물: `artifacts/index.jsonl`(전체) · `artifacts/sample.jsonl`(층화 샘플 — **이 목록의
이미지만 받으면 된다**).

## STEP 2.5 — 마스크 크롭 미리보기 (선택)

```bash
python validation/CLASS/product-info-finetune/aihub_preprocess.py \
    --index      .../artifacts/sample.jsonl \
    --label-root /path/to/aihub/008.의류_통합_데이터 \
    --image-root /path/to/aihub \
    --out-dir    .../artifacts/crop_preview --count 8
```

`__raw.jpg` / `__masked.jpg` 쌍을 나란히 열어 배경이 실제로 지워졌는지 확인한다.

## STEP 3 — 임베딩 추출 (**GPU, 여기만 무겁다**)

```bash
tmux new -s aihub-embed
for split in train val test; do
  for variant in masked raw; do
    python validation/CLASS/product-info-finetune/aihub_embed.py \
        --index      .../artifacts/sample.jsonl \
        --label-root /path/to/aihub/008.의류_통합_데이터 \
        --image-root /path/to/aihub \
        --out-dir    .../artifacts \
        --split "$split" --variant "$variant" --batch-size 64
  done
done
```

`masked`와 `raw`를 **둘 다** 뽑는 게 브리핑 §3(A)의 요구사항이다 — 그 차이가 곧 "배경 제거의
가치"다. 이미 있는 산출물은 건너뛴다(`--overwrite`로 강제). 액세서리 착용컷이 도메인에
안 맞으면 `--shot-type product`로 제품 단독컷만 쓸 수 있다.

산출물 3종(행 순서 일치): `<split>_<variant>.npy` · `.jsonl` · `.meta.json`.
`.meta.json`의 `failures.missing_image`가 크면 `--image-root`가 틀린 것이다.

## STEP 4 — 헤드 학습 (CPU, 수 초)

```bash
for task in color polo category; do
  python validation/CLASS/product-info-finetune/aihub_train_head.py \
      --artifacts .../artifacts --task "$task" --variant masked --class-weight balanced
done
```

- **color** — 14-way 로지스틱 회귀. 색상은 라벨 커버리지 100%라 가장 확실하다.
- **polo** — TSHIRT vs SHIRT 이진. 양성 = `02top_02t-shirt` + topneck에 `polo`,
  음성 = `02top_04shirt` + topneck == `shirts collar`. **35-way를 안 건드려서 회귀 위험 0.**
- **category** — 커버 클래스 N-way. 미커버 클래스는 계속 zero-shot이다.

## STEP 5 — 평가

```bash
python validation/CLASS/product-info-finetune/aihub_evaluate.py \
    --artifacts .../artifacts --variant masked --tasks color polo \
    --ground-truth-dir validation/CLASS/product-info-check \
    --out .../artifacts/eval_report.md
```

AI-Hub 홀드아웃과 우리 정답셋을 **항상 같이** 본다. 어긋나면 우리 정답셋을 믿는다(도메인이
다르다). 정답셋 평가는 브리핑 §11의 수용 기준 3개를 직접 찍는다 — 색상 정확도, 폴로 2건
회복, **나머지 예측 불변(회귀 가드)**. 정답셋 이미지(`product-info-check/inputs/`)는
gitignore라 서버에 따로 올려야 하고, 없으면 그 섹션만 건너뛴다.

카테고리 최종 예측은 **zero-shot top-1**이고, top-2가 `{TSHIRT, SHIRT}`일 때만 폴로 헤드가
뒤집는다. 나머지 33종 경로는 손대지 않는다.

## 설계 메모 — 코드를 읽기 전에

- **모듈명은 전부 `aihub_` 접두어다.** pytest 기본 import 모드가 테스트 파일이 있는 폴더를
  `sys.path`에 통째로 올리기 때문에, `dataset.py` 같은 흔한 이름을 쓰면
  `REC/recommendation-embedding-finetune/dataset.py`를 가려 CI 수집이 깨진다(2026-08-03 실제 사고).
- 같은 이유로 `aihub_dataset.py`는 `taxonomy.py`/`color.py`를 **`sys.path` 조작 없이**
  `importlib`으로 파일 경로에서 직접 로드한다(`_pic_*`라는 유일한 모듈명).
- **파싱 함정 3개**(LAB-76)를 `parse_label()`이 전부 흡수한다: 점 포함 평탄 키,
  문자열 `"null"`, 실제 키 이름(`annotation_point`). `metadata.pants.*`가 별도 블록이
  아니라 `metadata.clothes` 안에 들어 있는 것도 처리한다.
- **그룹 누수 방지**: 의류는 파일명의 첫 숫자 그룹(`01_sou_000834_...` → `000834`),
  액세서리는 `accessory_id`가 그룹 키다. split은 **그룹 단위**로 먼저 나눈다(브리핑 §8).
- ⚠️ **액세서리 파서는 AI-Hub 공개 명세만 보고 작성됐다** — 실물 샘플이 로컬에 없었다.
  그래서 래핑 구조에 의존하지 않고 키 이름으로 찾는다. `scan --accessory-root`의 출력이
  기대와 다르면 `aihub_accessory.py`를 먼저 고칠 것.

## 로컬에서 돌리는 것 (에이전트 담당)

```bash
cd AI
ruff check .
black --check .
pytest -q
```

테스트 3종(`test_class_finetune_{dataset,accessory,preprocess}.py`)은 무거운 의존성이 없어
CI에서 그대로 돈다 — 파싱 함정, 매핑 우선순위, 그룹 분할 누수, 폴리곤 좌표 처리를 고정한다.
