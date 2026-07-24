"""bge-m3를 상품 카탈로그 도메인(프록시 라벨)에 맞게 파인튜닝하는 실행 스크립트.

Throwaway/spike code for AI/test/ — NOT production code. `Jira S15P11A108-292`의 결과물
3·4번("파인튜닝 스크립트 작성", "학습 실행 및 체크포인트 저장")을 담당한다.

베이스 모델을 bge-m3로만 한정한 이유
------------------------------------
`kanana-nano-embedding`은 `trust_remote_code` 커스텀 클래스(Kanana2Vec, 참고:
`AI/test/model_selection/loaders.load_kanana_embedding`)라 forward/pooling을 직접 감싸는
커스텀 학습 루프가 필요하다. `bge-m3`는 `FlagEmbedding` 라이브러리가 공식 대조학습
파인튜닝 엔트리포인트(query/pos/neg JSONL 입력)를 제공해 커스텀 루프를 새로 짤 필요가
없다 — 이번 스코프는 bge-m3만 다루고 kanana-nano-embedding은 후속 과제로 남긴다.

`AI/test/garment-mask-finetune-check/finetune_segmentation.py`와 다르게 여기서는 순수
torch 루프를 직접 짜지 않는다 — 그쪽은 "torchvision classifier head 교체"라는 표준 학습
API가 없는 태스크였지만, 텍스트 임베딩 대조학습은 성숙한 라이브러리 지원이 있는 태스크라
검증된 코드를 재사용하는 쪽이 리스크가 낮다.

인자 확인 완료 (2026-07-24)
----------------------------
`FlagEmbedding.finetune.embedder.encoder_only.m3` 모듈과 `--model_name_or_path`/
`--train_data`/`--output_dir`/`--temperature`/`--train_group_size` 등 아래 커맨드의
인자명은 로컬에 설치된 FlagEmbedding 패키지 소스(`FlagEmbedding/abc/finetune/embedder/
AbsArguments.py`, `finetune/embedder/encoder_only/m3/arguments.py`)를 직접 읽어 확인했다
— `train_data`는 `nargs="+"`라 여러 경로도 받지만 파일 하나만 넘겨도 된다. `output_dir`/
`learning_rate`/`num_train_epochs`/`per_device_train_batch_size`/`save_steps`는 HF
`TrainingArguments`를 그대로 상속해서 쓰는 표준 인자다. 다만 이 확인은 로컬에 설치된
특정 버전 기준이므로, 실제 학습 환경의 FlagEmbedding 버전이 다르면
`python -m FlagEmbedding.finetune.embedder.encoder_only.m3 --help`로 재확인할 것.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model_selection"))
from model_registry import EMBEDDING_MODELS  # noqa: E402 — sys.path 조정 이후 import

BASE_MODEL_ID = EMBEDDING_MODELS["bge-m3"]

_ROOT = Path(__file__).parent
CHECKPOINT_DIR = _ROOT / "checkpoints" / "bge-m3-catalog-ft"

# 하이퍼파라미터 — Jira -292 description에 지침 없음(담당자 재량 확인됨). 재현 가능하도록
# 상수로 노출한다. FlagEmbedding BGE-M3 파인튜닝 공식 예제의 기본값을 참고한 값이며,
# 실제 학습 시 데이터 규모에 맞게 조정 필요.
LEARNING_RATE = 1e-5
NUM_EPOCHS = 3
BATCH_SIZE = 8
TEMPERATURE = 0.02
SAVE_STEPS = 500
# dataset.py의 NUM_EXPLICIT_NEGATIVES(4)+positive 1개 = 5. FlagEmbedding 기본값(8)을 쓰면
# neg가 4개뿐이라 부족분을 중복 샘플링으로 채운다(AbsDataset.__getitem__ 확인됨) — 데이터와
# 정확히 맞춰 불필요한 negative 중복을 없앤다.
TRAIN_GROUP_SIZE = ds.NUM_EXPLICIT_NEGATIVES + 1


def prepare_data() -> None:
    """`dataset.py`로 train/val JSONL을 (재)생성한다. 이미 있으면 덮어쓴다."""
    catalog_items = ds.load_catalog()
    train_items, val_items = ds.split_items(catalog_items)
    ds.write_jsonl(ds.build_pairs(train_items), ds.TRAIN_JSONL)
    ds.write_jsonl(ds.build_pairs(val_items), ds.VAL_JSONL)


def _build_finetune_command() -> list[str]:
    """FlagEmbedding CLI 호출 커맨드 조립. 리스크: 모듈 상단 docstring 참고."""
    return [
        sys.executable,
        "-m",
        "FlagEmbedding.finetune.embedder.encoder_only.m3",
        "--model_name_or_path",
        BASE_MODEL_ID,
        "--train_data",
        str(ds.TRAIN_JSONL),
        "--output_dir",
        str(CHECKPOINT_DIR),
        "--learning_rate",
        str(LEARNING_RATE),
        "--num_train_epochs",
        str(NUM_EPOCHS),
        "--per_device_train_batch_size",
        str(BATCH_SIZE),
        "--temperature",
        str(TEMPERATURE),
        "--save_steps",
        str(SAVE_STEPS),
        "--train_group_size",
        str(TRAIN_GROUP_SIZE),
    ]


def run_finetune() -> None:
    """FlagEmbedding 파인튜닝 서브프로세스를 실행하고 체크포인트를 `CHECKPOINT_DIR`에 남긴다.

    체크포인트는 `.gitignore`의 `AI/test/**/checkpoints/` 규칙으로 커밋 대상에서 제외된다.
    """
    if not ds.TRAIN_JSONL.exists():
        raise FileNotFoundError(
            f"{ds.TRAIN_JSONL}가 없습니다 — 먼저 prepare_data() 또는 `python dataset.py`를 실행하세요."
        )
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = _build_finetune_command()
    print(f"[finetune_embedding] 실행: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    prepare_data()
    run_finetune()
