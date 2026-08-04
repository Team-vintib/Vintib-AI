# 상품 분류 헤드 학습 (AI-Hub 의류 통합 데이터)

`fashion_clip` 백본을 **동결**한 채 그 위에 선형 분류 헤드만 학습해서, 상품 사진의
**카테고리(소분류 35종)** 와 **색상(13종+MIXED)** 정확도를 올리는 스파이크.

- 지시서: [`../CLASSIFIER_FINETUNE_BRIEF.md`](../CLASSIFIER_FINETUNE_BRIEF.md)
- 설계: `.claude/plans/ai/CH014-class-finetune.md`
- 실측 근거: [`../product-info-check/REPORT.md`](../product-info-check/REPORT.md) §18~§20
- 라벨 정본: `../product-info-check/taxonomy.py` · `color.py` (**수정 금지**)
- 데이터 포맷: Notion LAB-76

> 추천용 임베딩 학습(`validation/REC/recommendation-embedding-finetune/`)과는 **전혀 다른
> 작업**이다. 백본 전체 파인튜닝도 금지다(브리핑 §3).

## 실행 위치 — 코드는 로컬, 무거운 실행은 원격

AI-Hub 데이터는 로컬에 없고 **원격 GPU 서버에만** 있다(브리핑 §3-1). 그래서:

- 모든 무거운 단계는 `argparse`를 받는 `.py`다. **노트북에 넣지 않는다** — 원격 Jupyter
  커널은 연결이 끊기면 죽는다. `tmux` 안에서 스크립트로 돌린다.
- 경로는 전부 `--root` / `--out-dir`로 받는다. 하드코딩된 절대경로가 없다.
- 중간 산출물은 파일(`.jsonl` / `.npy` / `.joblib`)로 떨어뜨려 세션이 끊겨도 이어갈 수 있다.
- 산출물은 `artifacts/`에 쌓이고 `AI/.gitignore`에 이미 등록돼 있다.

## 지금 실행할 것 — STEP 1. scan (착수 게이트)

**이미지는 아직 안 받아도 된다. 라벨 JSON만 있으면 된다.**

```bash
tmux new -s aihub-scan

cd /path/to/repo/AI                     # ← 리포 경로로 바꿀 것
pip install -r requirements-dev.txt     # scan은 표준 라이브러리만 쓴다(ruff/pytest용으로 설치)

python validation/CLASS/product-info-finetune/aihub_dataset.py scan \
    --root /path/to/aihub/008.의류_통합_데이터 \
    --out  validation/CLASS/product-info-finetune/artifacts/scan.txt
```

| 인자 | 채울 값 |
| --- | --- |
| `--root` | 라벨 JSON이 들어 있는 디렉터리. **하위 전체를 재귀 탐색**하므로 데이터셋 루트를 그대로 줘도 된다(`원천데이터`의 jpg는 무시한다) |
| `--out` | 리포트를 파일로도 남긴다. 생략하면 표준출력만 |
| `--limit N` | 먼저 감을 잡고 싶으면 `--limit 5000`으로 빠르게 한 번 |

550,634개를 다 읽으므로 디스크 속도에 따라 수 분~수십 분이 걸린다. 50,000개마다 진행
상황을 stderr로 찍는다.

### scan 출력에서 내가(사용자가) 판정해야 하는 것 2개

이 두 개는 **이 작업의 전제**라 통과하지 못하면 설계를 다시 해야 한다(브리핑 §4).

1. **게이트 1 — `metadata.model.type`의 front/back이 상품컷인가 착용샷인가.**
   scan이 값마다 이미지 경로를 5개씩 찍는다. **그 파일을 직접 열어 보고** "옷만 찍은
   상품컷"인지 "사람이 입은 사진"인지 알려줄 것. 우리 서비스 입력은 flat 15 / hanging 4 /
   worn 0이라, 전부 착용샷이면 도메인 갭이 커서 학습해도 안 오를 수 있다.
2. **게이트 2 — `clothes.color`에 Navy가 실재하는가.** LAB-76이 자기모순이다(§3-1은
   Navy 있는 14종, §4-7은 없는 13종). scan이 `>>> Navy 실측 건수:`로 찍는다.

같이 나오는 것: `clothes.type` 13종 실제 건수(pants/skirt 분해 포함), `pants_length`
히스토그램(**SHORT_PANTS 임계를 여기서 정한다**), `topneck_color_design` 분포(polo 건수 =
폴로 헤드 학습량), `sleeve_length_type` 분포, 그룹 키 크기 분포, 경로 샘플.

**scan 출력을 그대로 붙여넣어 줄 것.** 그 숫자를 보고 다음 단계로 간다.

## STEP 2. index (게이트 통과 후)

라벨 인덱스 + 그룹 단위 분할 + 층화 샘플링. 여기까지도 이미지가 필요 없다 — 이 단계의
결과로 **어떤 이미지를 받을지**가 정해진다(전체 약 40GB → 5만 장 약 3.5GB).

```bash
python validation/CLASS/product-info-finetune/aihub_dataset.py index \
    --root /path/to/aihub/008.의류_통합_데이터 \
    --out-dir validation/CLASS/product-info-finetune/artifacts \
    --short-pants-max-cm <scan 히스토그램으로 정한 값>
```

`--short-pants-max-cm`을 주지 않으면 `04bottom_01pants`는 통째로 제외된다(= SHORT_PANTS
파생 안 함). **scan 히스토그램을 보기 전에는 이 값을 넣지 않는다.**

산출물:

- `artifacts/index.jsonl` — 매핑된 전 레코드 + `split`
- `artifacts/sample.jsonl` — 층화 샘플(train은 카테고리 3,000/색상 2,000 상한, val·test는
  커버 클래스당 100장). **이 목록의 이미지만 받으면 된다.**

## STEP 3~5. 아직 구현 안 함 (게이트 판정 후 작성)

브리핑 §12의 순서대로 게이트를 먼저 통과시킨 뒤 만든다. 게이트가 깨지면 이 단계들의
설계 자체가 바뀌기 때문에 미리 쓰지 않았다.

| 파일 | 역할 |
| --- | --- |
| `aihub_preprocess.py` | Polygon → 마스크 → bbox 크롭 + 배경 흰색 치환 |
| `aihub_embed.py` | fashion_clip(동결) 이미지 임베딩 → `artifacts/*.npy` (GPU, 1회) |
| `aihub_train_head.py` | (A) 색상 14-way 로지스틱 회귀 · (B) 폴로 이진 헤드 → `.joblib` |
| `aihub_evaluate.py` | AI-Hub 홀드아웃 + 우리 정답셋 19장 동시 평가 |

## 설계 메모 — 코드를 읽기 전에 알아 둘 것

- **모듈명은 전부 `aihub_` 접두어다.** pytest 기본 import 모드가 테스트 파일이 있는 폴더를
  `sys.path`에 통째로 올리기 때문에, `dataset.py` 같은 흔한 이름을 쓰면
  `REC/recommendation-embedding-finetune/dataset.py`를 가려 CI 수집이 깨진다(2026-08-03 실제 사고).
- 같은 이유로 `aihub_dataset.py`는 `taxonomy.py`/`color.py`를 **`sys.path` 조작 없이**
  `importlib`으로 파일 경로에서 직접 로드한다(`_pic_*`라는 유일한 모듈명).
- **파싱 함정 3개**(LAB-76)를 `parse_label()`이 전부 흡수한다: 점 포함 평탄 키,
  문자열 `"null"`, 실제 키 이름(`annotation_point`). `metadata.pants.*`가 별도 블록이
  아니라 `metadata.clothes` 안에 들어 있는 것도 처리한다.
- **그룹 누수 방지**: 파일명의 첫 숫자 그룹(`01_sou_000834_...` → `000834`)이 같은 이미지는
  같은 의류의 front/back/wear다. split은 **그룹 단위**로 먼저 나눈다(브리핑 §8).
- 재현성 상수(`SEED` `TRAIN/VAL/TEST_RATIO` 캡)는 파일 상단에 노출돼 있고 학습·평가가
  같은 값을 공유한다.

## 로컬에서 돌리는 것 (에이전트 담당)

```bash
cd AI
ruff check .
black --check .
pytest -q
```

`test_class_finetune_dataset.py`는 무거운 의존성이 없어 CI에서 그대로 돈다 — 파싱 함정,
매핑 우선순위, 그룹 분할 누수를 픽스처로 고정한다.
