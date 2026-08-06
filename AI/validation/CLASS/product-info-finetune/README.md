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
| `aihub_cache_pixels.py` | STEP 3.5(선택) | ✗ | ViT 파인튜닝용 입력 텐서(`pixel_values`) 캐싱. 모델 미로드라 GPU 불필요 |
| `aihub_finetune_vit.py` | STEP 3.6(선택, 실험) | **✓** | 비전 인코더 마지막 N개 블록 파인튜닝 — 선형 프로브 대비 비교 |
| `aihub_finetune_lora.py` | STEP 3.7(선택, 실험) | **✓** | 비전 인코더 LoRA 파인튜닝 — last-N 언프리즈 대비 비교 |
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

게이트 2 색상 표는 다색 콤마 조합("Black,White" 등)까지 세면 수백 줄이 나온다 — 기본으로
상위 20개만 찍고 나머지는 합계 한 줄로 접는다. 전체가 필요하면 `--color-top 0`.

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
        --label-root           /path/to/aihub/008.의류_통합_데이터 \
        --accessory-label-root /path/to/aihub/009.패션_액세서리_착용_데이터 \
        --image-root /path/to/aihub \
        --out-dir    .../artifacts \
        --split "$split" --variant "$variant" --batch-size 64
  done
done
```

`masked`와 `raw`를 **둘 다** 뽑는 게 브리핑 §3(A)의 요구사항이다 — 그 차이가 곧 "배경 제거의
가치"다. 이미 있는 산출물은 건너뛴다(`--overwrite`로 강제). 액세서리 착용컷이 도메인에
안 맞으면 `--shot-type product`로 제품 단독컷만 쓸 수 있다.

⚠️ **`--accessory-label-root`를 빼먹지 말 것.** `sample.jsonl`이 의류·액세서리를 섞고
있고 `label_path`는 소스마다 다른 루트 기준 상대경로다. `masked` variant에서 이 인자가
없으면 액세서리 행은 의류 라벨 폴더에서 폴리곤을 찾으려다 실패해 **마스크 없이(원본
그대로) 처리된다** — 에러 없이 조용히 품질이 떨어지는 경로라 실수하기 쉽다(2026-08-04
실측으로 발견). `raw` variant는 폴리곤이 필요 없어 무관하다.

산출물 3종(행 순서 일치): `<split>_<variant>.npy` · `.jsonl` · `.meta.json`.
`.meta.json`의 `failures.missing_image`가 크면 `--image-root`가 틀린 것이다.

## STEP 3.5 — (선택) ViT 파인튜닝용 입력 텐서 캐싱

선형 헤드만 쓸 거면 건너뛴다. **ViT 백본 마지막 N개 블록을 언프리즈해 파인튜닝**을
비교 실험할 때만 필요하다 — 같은 이미지를 epoch마다 다시 디코드·크롭하는 비용을
없애려고, 모델에 넣기 직전의 `pixel_values` 텐서를 한 번만 만들어 캐시해 둔다.

```bash
python validation/CLASS/product-info-finetune/aihub_cache_pixels.py \
    --index      .../artifacts/sample.jsonl \
    --label-root           /path/to/aihub/008.의류_통합_데이터 \
    --accessory-label-root /path/to/aihub/009.패션_액세서리_착용_데이터 \
    --image-root /path/to/aihub \
    --out-dir    .../artifacts \
    --split train --variant masked --batch-size 64
```

`aihub_embed.py`와 달리 **모델 가중치를 안 실어서 GPU가 필요 없다**(이미지 프로세서만
쓴다) — `pixel_values`에서 멈추고 `model.get_image_features()`까지 가지 않는다. 언프리즈
경계(마지막 몇 개 블록인지, LoRA인지)가 바뀌어도 이 캐시는 그대로 재사용된다 — 모델
구조가 아니라 입력 단계에서 멈추기 때문이다. 기본 dtype은 `float16`(저장 공간 절반).

산출물은 `aihub_embed.py`와 같은 폴더에 둬도 된다 — 파일명에 `_pixels` 접미사가 붙어
임베딩 `.npy`와 안 겹친다: `<split>_<variant>[_<source>]_pixels.{npy,jsonl,meta.json}`.

⚠️ 이 캐시는 **선형 헤드 산출물(`head_*.joblib`, 임베딩 `.npy`)과 완전히 별개**다 — 지우거나
덮어써도 이미 검증된 선형 프로브 베이스라인에는 영향이 없다.

## STEP 3.6 — (선택, 실험) ViT 파인튜닝 비교

선형 헤드(STEP 4)가 **1순위 결과물**이고 이건 그 대비 비교 실험이다. 브리핑 §3의 전체
파인튜닝 금지를 어기지 않는다 — 텍스트 타워는 통째로 동결하고, 비전 인코더도 마지막
N개 블록만 언프리즈해 흔들리는 범위를 최소화한다.

```bash
tmux new -s aihub-finetune
python validation/CLASS/product-info-finetune/aihub_finetune_vit.py \
    --pixel-cache-dir .../artifacts \
    --task category --variant masked \
    --unfreeze-layers 2 --epochs 10 --batch-size 32
```

STEP 3.5의 `pixel_values` 캐시가 미리 있어야 한다. 첫 실행은 `--unfreeze-layers 2`(비전
인코더 마지막 2블록)로 시작한다 — 4, 6 등으로 늘려가며 선형 프로브 대비 개선폭이 흔들림
위험보다 큰지 확인한 뒤, 그래도 부족하면 LoRA로 넘어간다(다음 실험, 아직 미착수).

산출물은 `artifacts_finetune/<run_name>/`(선형 헤드·임베딩과 완전히 분리된 폴더)에
`checkpoint.pt`(언프리즈된 파라미터만 — 사전학습 그대로인 나머지는 저장 안 함) +
`meta.json`(epoch별 val accuracy 이력, best epoch, test accuracy)로 쌓인다. `--unfreeze-layers`나
`--lr-backbone`을 바꿔 다시 돌리면 폴더 이름이 달라져 이전 run이 안 지워진다.

⚠️ 이 스크립트가 학습하는 헤드는 `nn.Linear` + 언프리즈된 백본 조합이라 **STEP 4의 sklearn
헤드와 구조가 다르다** — `aihub_evaluate.py`로는 못 읽는다. 비교는 이 스크립트가 찍는
test accuracy 숫자를 STEP 5 리포트의 헤드/zero-shot 숫자와 나란히 놓고 보는 식이다.

### 다른 태스크 체크포인트에서 이어서 학습(웜스타트, 선택)

기본은 매번 원본 `fashion_clip`에서 새로 시작한다(카테고리 run과 색상 run은 독립). 다른
태스크의 체크포인트에서 이어받고 싶으면(예: 카테고리로 파인튜닝한 backbone에서 색상을
이어서 학습) `--init-checkpoint`에 그 `checkpoint.pt` 경로를 준다:

```bash
python validation/CLASS/product-info-finetune/aihub_finetune_vit.py \
    --pixel-cache-dir .../artifacts \
    --task color --variant masked \
    --unfreeze-layers 4 --epochs 5 --batch-size 32 \
    --init-checkpoint .../artifacts_finetune/vit_last4_category_masked_lr1e-05/checkpoint.pt
```

헤드(`nn.Linear`)는 절대 안 가져온다(태스크마다 클래스 수가 달라 shape가 안 맞는다) —
백본(언프리즈된 파라미터)만 이어받고 헤드는 새로 초기화한다. `--unfreeze-layers`가 체크포인트
학습 때와 다르면 경고만 찍고 겹치는 파라미터만 로드한다. run 폴더 이름에 `_warm`이 붙어
독립학습 run과 안 겹친다 — 둘 다 남겨서 `aihub_finetune_summary.py --best-per-group
method,task`로 어느 쪽이 더 나은지 비교하는 걸 권장한다(하나가 다른 하나를 대체하지 않는다).

### 이 백본이 원래 태스크도 여전히 잘하는지 진단(`--freeze-backbone`)

배포될 기능은 사진 한 장에 카테고리·색상을 **동시에** 내야 한다 — 그러니 색상으로 이어서
학습한 backbone이 카테고리도 여전히 잘하는지(혹은 그 반대) 확인이 필요하다. `--init-checkpoint`
와 `--freeze-backbone`을 같이 주면, 그 backbone을 **더 학습시키지 않고** 새 헤드만 학습해
순수하게 "이 backbone이 다른 태스크에 얼마나 쓸만한가"를 잰다:

```bash
python validation/CLASS/product-info-finetune/aihub_finetune_vit.py \
    --pixel-cache-dir .../artifacts \
    --task category --variant masked \
    --unfreeze-layers 4 --epochs 5 --batch-size 32 \
    --init-checkpoint .../artifacts_finetune/vit_last4_color_masked_lr1e-05_warm/checkpoint.pt \
    --freeze-backbone
```

이 test accuracy를 카테고리 전용으로 학습한 원래 결과와 비교하면, 색상 학습이 카테고리
성능을 얼마나 깎았는지(또는 안 깎았는지) 알 수 있다. run 폴더 이름엔 `_probe`가 붙는다.

## STEP 3.7 — (선택, 실험) LoRA 파인튜닝

STEP 3.6(last-N 언프리즈)의 대안이다. last-N은 마지막 몇 개 블록을 **통째로** 학습하고,
LoRA는 반대로 **모든 레이어**의 attention 사영에 저랭크 어댑터만 얹어 학습한다 — 건드리는
레이어 수는 많지만 레이어당 변화 폭은 훨씬 작다.

```bash
tmux new -s aihub-lora
pip install peft  # 서버에 아직 없으면
python validation/CLASS/product-info-finetune/aihub_finetune_lora.py \
    --pixel-cache-dir .../artifacts \
    --task category --variant masked \
    --r 8 --alpha 16 --epochs 10 --batch-size 32
```

`--r`(rank)이 핵심 손잡이다 — 크면 last-N에 가까워지고 작으면 원본 보존이 강해진다.
산출물은 STEP 3.6과 같은 `artifacts_finetune/`에 쌓이되 폴더 이름이 `lora_r{r}_...`로
시작해 `vit_last{N}_...`(STEP 3.6)와 안 겹친다.

STEP 3.6과 같은 이유로 `--init-checkpoint`도 지원한다(다른 태스크의 LoRA 체크포인트에서
이어서 학습). `--r`/`--target-modules`가 체크포인트 학습 때와 다르면 경고만 찍고 겹치는
어댑터 파라미터만 로드한다. `--freeze-backbone`도 동일하게 지원한다 — "이 어댑터가 다른
태스크에서도 여전히 쓸만한가" 진단은 STEP 3.6 쪽 설명을 그대로 참고.

## STEP 4 — 헤드 학습 (CPU, 수 초)

```bash
T=validation/CLASS/product-info-finetune/aihub_train_head.py
# 색상은 의류만 (아래 "소스 분리" 참고)
python $T --artifacts .../artifacts --task color --variant masked --source clothes --class-weight balanced
# 카테고리는 두 소스 다
python $T --artifacts .../artifacts --task category --variant masked --class-weight balanced
python $T --artifacts .../artifacts --task polo     --variant masked --class-weight balanced
```

### ⚠️ 소스 분리 — 색상 헤드에 액세서리를 넣지 마라

액세서리 색상 23종을 우리 팔레트로 접으면 **실버→GRAY · 골드→YELLOW · 로즈골드→PINK**가
된다. 그런데 `color.py`의 팔레트는 의류 색상으로 정의돼 있다(`GRAY: #9B9B9B`). 은목걸이를
회색 니트와 같은 클래스로 학습시키면 14-way 결정 경계가 금속 광택 쪽으로 끌려간다. JEWELRY는
목걸이+귀걸이 2:1로 접혀 표본이 두 배라 영향이 더 크다.

`--source`는 **행 필터**다(파일명 태그가 아니다) — 임베딩은 한 번만 뽑고 여기서 거른다.
헤드 파일명에 소스가 붙어(`head_color_masked_clothes.joblib`) 두 조건을 나란히 비교할 수 있다.
임베딩을 소스별로 따로 뽑았다면 그때만 `--embed-suffix`를 쓴다.

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

테스트 8종(`test_class_finetune_{dataset,accessory,preprocess,head,evaluate,cache_pixels,
finetune_vit,finetune_lora}.py`)은 무거운 의존성이 없어 CI에서 그대로 돈다 — 파싱 함정,
매핑 우선순위, 그룹 분할 누수, 폴리곤 좌표 처리, 태스크별 행 선택, zero-shot 채점 수학,
캐시 파일명 분리, 라벨 인코딩/미지 클래스 필터링, run_name 접두어(방법 분류/충돌 방지)를
고정한다. 각 스크립트의 무거운 본체(모델 로드·학습·추론)는 CI 밖(서버)에서만 검증한다.
