"""다른 태스크로 적응된 backbone을 얼린 채, sklearn 선형 프로브로 다른 태스크 성능을
빠르게 잰다.

`aihub_finetune_vit.py`/`aihub_finetune_lora.py`의 `--freeze-backbone` 진단 모드는 이
질문("이 backbone이 다른 태스크에서도 여전히 쓸만한가")에 답하려고 torch SGD로 헤드를
학습시키는데, 이건 사실 **볼록(convex) 선형 분류 문제**라 sklearn(LBFGS)이 훨씬 빠르고
확실하게 수렴한다 — 2026-08-05 실측: SGD로 30epoch을 돌려도 loss가 계속 떨어지며 수렴을
못 했다(색상-웜스타트 backbone → 카테고리, test 0.55 근처에서 여전히 상승 중).

기존 파이프라인(`aihub_finetune_vit.py`/`aihub_finetune_lora.py`)을 고치는 대신 이 파일을
따로 둔다 — 회귀 위험 없이 결과만 빠르게 확인하기 위해서다. STEP4(`aihub_train_head.py`)와
정확히 같은 방식(feature 한 번 추출 → sklearn 학습·평가)을 쓴다.

사용법 — last-N 백본 진단:
    python aihub_finetune_probe.py --pixel-cache-dir .../artifacts --task category \\
        --variant masked --method last-n --unfreeze-layers 4 \\
        --checkpoint .../vit_last4_color_masked_lr1e-05_warm/checkpoint.pt

사용법 — LoRA 백본 진단:
    python aihub_finetune_probe.py --pixel-cache-dir .../artifacts --task category \\
        --variant masked --method lora --r 16 --alpha 32 \\
        --checkpoint .../lora_r16_a32_d0.05_qv_color_masked_lr0.0001_warm/checkpoint.pt

`--unfreeze-layers`(last-N) 또는 `--r`/`--alpha`/`--target-modules`(LoRA)는 **체크포인트를
만들 때 쓴 것과 같은 값**을 줘야 한다 — 아키텍처가 안 맞으면 state_dict 키가 어긋나
겹치는 파라미터만 조용히 로드된다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import aihub_finetune_vit as vit
import aihub_train_head

METHODS = ("last-n", "lora")


def load_frozen_backbone(
    method: str,
    checkpoint_path: Path,
    device: str,
    *,
    model_id: str,
    unfreeze_layers: int,
    r: int,
    alpha: int,
    dropout: float,
    target_modules: tuple[str, ...],
) -> Any:
    """checkpoint의 backbone_state_dict를 불러와 완전히 얼린 모델을 돌려준다."""
    import torch

    if method == "last-n":
        model = vit.load_model(model_id, unfreeze_layers, device)
    else:
        import aihub_finetune_lora as lora

        model = lora.load_model(model_id, r, alpha, dropout, target_modules, device)

    checkpoint = torch.load(checkpoint_path, map_location=device)
    compatible_state = vit.drop_incompatible_keys(checkpoint["backbone_state_dict"], model)
    model.load_state_dict(compatible_state, strict=False)
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    model.eval()
    return model


def extract_embeddings(model: Any, pixels: Any, batch_size: int, device: str) -> Any:
    """pixel_values 캐시에서 L2 정규화 임베딩을 한 번만 뽑는다(그래디언트 없음)."""
    import numpy as np
    import torch

    vectors = []
    with torch.no_grad():
        for start in range(0, len(pixels), batch_size):
            batch = torch.from_numpy(pixels[start : start + batch_size]).to(
                device=device, dtype=torch.float32
            )
            features = model.get_image_features(pixel_values=batch)
            features = features / features.norm(dim=-1, keepdim=True)
            vectors.append(features.cpu().float().numpy())
    if not vectors:
        return np.zeros((0, 0), dtype="float32")
    return np.concatenate(vectors, axis=0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="다른 태스크로 적응된 backbone을 얼린 채, sklearn 선형 프로브로 다른 "
        "태스크 성능을 빠르게 잰다(torch SGD 진단 모드보다 훨씬 빠르고 확실히 수렴)"
    )
    parser.add_argument("--pixel-cache-dir", type=Path, required=True)
    parser.add_argument("--task", required=True, choices=aihub_train_head.TASKS)
    parser.add_argument("--variant", default="masked", choices=("raw", "masked"))
    parser.add_argument(
        "--checkpoint", type=Path, required=True, help="진단할 backbone의 checkpoint.pt"
    )
    parser.add_argument("--method", required=True, choices=METHODS)
    parser.add_argument("--model-id", default=vit.DEFAULT_MODEL_ID)
    parser.add_argument(
        "--unfreeze-layers",
        type=int,
        default=vit.DEFAULT_UNFREEZE_LAYERS,
        help="--method last-n 전용. 체크포인트 학습 때와 같은 값을 줄 것",
    )
    parser.add_argument("--r", type=int, default=8, help="--method lora 전용")
    parser.add_argument("--alpha", type=int, default=16, help="--method lora 전용")
    parser.add_argument("--dropout", type=float, default=0.05, help="--method lora 전용")
    parser.add_argument(
        "--target-modules", nargs="*", default=["q_proj", "v_proj"], help="--method lora 전용"
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device", default=None)
    parser.add_argument("--class-weight", default="balanced", choices=("balanced", "none"))
    args = parser.parse_args(argv)

    import torch

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")

    model = load_frozen_backbone(
        args.method,
        args.checkpoint,
        device,
        model_id=args.model_id,
        unfreeze_layers=args.unfreeze_layers,
        r=args.r,
        alpha=args.alpha,
        dropout=args.dropout,
        target_modules=tuple(args.target_modules),
    )

    class_weight = None if args.class_weight == "none" else "balanced"

    embeddings_by_split = {}
    rows_by_split = {}
    for split in ("train", "val", "test"):
        pixels, rows = vit.load_pixel_split(args.pixel_cache_dir, split, args.variant)
        embeddings_by_split[split] = extract_embeddings(model, pixels, args.batch_size, device)
        rows_by_split[split] = rows
        print(f"{split}: {embeddings_by_split[split].shape[0]:,}건 임베딩 추출 완료")

    x_train, y_train, _ = aihub_train_head.build_task_dataset(
        embeddings_by_split["train"], rows_by_split["train"], args.task
    )
    if len(y_train) == 0:
        print(f"학습 표본이 0개다(task={args.task})", file=sys.stderr)
        return 1

    print(f"task={args.task} train={len(y_train):,} classes={len(set(y_train))}")
    sklearn_model = aihub_train_head.train(x_train, y_train, class_weight=class_weight)

    for split in ("train", "val", "test"):
        x, y, _ = aihub_train_head.build_task_dataset(
            embeddings_by_split[split], rows_by_split[split], args.task
        )
        if not y:
            print(f"({split}: 대상 표본 0건)")
            continue
        result = aihub_train_head.evaluate(sklearn_model, x, y)
        print(f"[{split}] n={result['n']:,} accuracy={result['accuracy']:.4f}")

    print(
        "\n(참고) 이 결과는 --checkpoint의 backbone을 완전히 얼린 채 sklearn 헤드만 새로 "
        "학습시킨 것이다 — 원래 그 태스크 전용으로 파인튜닝했을 때 결과와 비교해서 "
        "backbone이 이 태스크를 얼마나 유지하고 있는지 판단하면 된다."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
