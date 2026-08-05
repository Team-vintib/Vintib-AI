"""파인튜닝된 backbone이 **미커버 클래스**(zero-shot 전용)에서도 여전히 잘하는지,
원본(동결) backbone과 우리 정답셋으로 나란히 비교한다.

last-N/LoRA 파인튜닝은 AI-Hub가 덮는 11~14종 라벨로만 학습됐다 — 나머지 21~24종
(신발·가방 등)은 학습 신호가 전혀 없다. 브리핑(`CLASSIFIER_FINETUNE_BRIEF.md` §3)이
원래 전체 파인튜닝을 금지한 이유가 정확히 이거다: 백본을 흔들면 이 미커버 클래스들의
zero-shot 표현이 망가질 수 있다. 실제로 색상 순차학습이 카테고리를 zero-shot 이하로
깎아먹는 걸 이미 확인했다(`aihub_finetune_probe.py` 결과, 2026-08-05) — 그러니 카테고리
학습도 미커버 클래스를 깎아먹었을 가능성을 확인해야 한다.

AI-Hub에는 미커버 클래스 이미지가 아예 없어서, 우리 정답셋
(`product-info-check/data/ground_truth.json` + `inputs/`)에서 **체크포인트가 모르는
클래스**(`classes` 필드에 없는 것)만 골라, 원본 backbone과 파인튜닝된 backbone 각각으로
zero-shot 정확도를 재서 비교한다. 텍스트 인코더는 두 backbone에서 항상 동일하다
(last-N/LoRA 둘 다 텍스트 타워를 아예 안 건드림) — 그래서 텍스트 임베딩은 한 번만 뽑는다.

사용법:
    python aihub_ground_truth_zero_shot_check.py \\
        --ground-truth-dir ../product-info-check \\
        --checkpoint artifacts_finetune/vit_last4_category_masked_lr1e-05/checkpoint.pt \\
        --method last-n --unfreeze-layers 4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import aihub_dataset
import aihub_embed
import aihub_evaluate
import aihub_finetune_probe
import aihub_preprocess

METHODS = ("last-n", "lora")


def load_ground_truth_rows(ground_truth_dir: Path) -> list[dict]:
    """`aihub_evaluate.evaluate_ground_truth()`와 같은 규칙 — synthetic 이미지는 제외."""
    truth_path = ground_truth_dir / "data" / "ground_truth.json"
    if not truth_path.exists():
        raise FileNotFoundError(f"정답셋이 없다: {truth_path}")
    rows = json.loads(truth_path.read_text(encoding="utf-8"))
    return [row for row in rows if not row.get("synthetic")]


def resolve_ground_truth_image(ground_truth_dir: Path, image_file: str) -> Path | None:
    """`inputs/` 또는 공유 폴더(`QUAL/sam3-condition-check/sample_images`)에서 찾는다."""
    inputs_dir = ground_truth_dir / "inputs"
    shared_dir = ground_truth_dir.parents[1] / "QUAL" / "sam3-condition-check" / "sample_images"
    for candidate_dir in (inputs_dir, shared_dir):
        candidate = candidate_dir / image_file
        if candidate.exists():
            return candidate
    return None


def encode_ground_truth_images(
    model: Any, processor: Any, image_paths: list[Path], device: str
) -> Any:
    """정답셋 이미지를 원본 그대로(마스크 없음) 인코딩한다 — `evaluate_ground_truth()`와
    같은 전처리라 두 backbone의 결과를 그 리포트와도 직접 비교할 수 있다."""
    import numpy as np
    from PIL import Image

    vectors = []
    for path in image_paths:
        with Image.open(path) as image:
            prepared = aihub_preprocess.render_variant(image, None, "raw")
        inputs = processor(images=[prepared], return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        features = model.get_image_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)
        vectors.append(features.detach().cpu().float().numpy()[0])
    return np.stack(vectors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="파인튜닝된 backbone이 미커버 클래스 zero-shot도 유지하는지 원본과 비교"
    )
    parser.add_argument(
        "--ground-truth-dir", type=Path, required=True, help="product-info-check 폴더"
    )
    parser.add_argument("--checkpoint", type=Path, required=True, help="비교할 파인튜닝 체크포인트")
    parser.add_argument("--method", required=True, choices=METHODS)
    parser.add_argument("--model-id", default=aihub_embed.FASHION_CLIP_MODEL_ID)
    parser.add_argument(
        "--unfreeze-layers", type=int, default=2, help="--method last-n 전용, 체크포인트와 맞출 것"
    )
    parser.add_argument("--r", type=int, default=8, help="--method lora 전용")
    parser.add_argument("--alpha", type=int, default=16, help="--method lora 전용")
    parser.add_argument("--dropout", type=float, default=0.05, help="--method lora 전용")
    parser.add_argument("--target-modules", nargs="*", default=["q_proj", "v_proj"])
    parser.add_argument("--device", default=None)
    args = parser.parse_args(argv)

    import torch

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")

    rows = load_ground_truth_rows(args.ground_truth_dir)
    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    covered = set(checkpoint.get("classes", []))
    uncovered = set(aihub_dataset.ALL_SUBCATEGORIES) - covered

    usable, images = [], []
    for row in rows:
        if row.get("subcategory") not in uncovered:
            continue
        path = resolve_ground_truth_image(args.ground_truth_dir, row["image_file"])
        if path is None:
            continue
        usable.append(row)
        images.append(path)

    if not usable:
        print(
            f"정답셋에서 미커버 클래스({len(uncovered)}종) 이미지를 못 찾았다 — "
            "업로드된 이미지들의 subcategory를 확인할 것",
            file=sys.stderr,
        )
        return 1

    print(f"미커버 클래스 {len(uncovered)}종 중 정답셋에서 찾은 이미지: {len(usable)}장")
    print(f"대상 클래스: {sorted({row['subcategory'] for row in usable})}")

    original_model, processor = aihub_embed.load_model(args.model_id, device)
    original_embeddings = encode_ground_truth_images(original_model, processor, images, device)

    adapted_model = aihub_finetune_probe.load_frozen_backbone(
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
    adapted_embeddings = encode_ground_truth_images(adapted_model, processor, images, device)

    category_codes = list(aihub_dataset.ALL_SUBCATEGORIES)
    category_texts = aihub_evaluate.encode_texts(
        [aihub_dataset.CATEGORY_PROMPT(code) for code in category_codes],
        original_model,
        processor,
        device,
    )

    truth = [row["subcategory"] for row in usable]
    original_labels = aihub_evaluate.zero_shot_labels_for_embeddings(
        original_embeddings, category_texts, category_codes
    )
    adapted_labels = aihub_evaluate.zero_shot_labels_for_embeddings(
        adapted_embeddings, category_texts, category_codes
    )

    original_correct = sum(a == b for a, b in zip(original_labels, truth))
    adapted_correct = sum(a == b for a, b in zip(adapted_labels, truth))
    total = len(truth)

    print(f"\n원본 백본(동결)  : {original_correct}/{total} = {original_correct / total:.4f}")
    print(f"파인튜닝된 백본  : {adapted_correct}/{total} = {adapted_correct / total:.4f}")

    changed = [
        (row["image_file"], truth_label, o, a)
        for row, truth_label, o, a in zip(usable, truth, original_labels, adapted_labels)
        if o != a
    ]
    if changed:
        print("\n원본 대비 예측이 달라진 이미지:")
        for image_file, truth_label, o, a in changed:
            if o == truth_label and a != truth_label:
                marker = "🔴"  # 파인튜닝 때문에 새로 틀림 - 망각의 직접 증거
            elif a == truth_label and o != truth_label:
                marker = "🟢"  # 파인튜닝이 오히려 고침
            else:
                marker = "  "
            print(f"  {marker} {image_file} (정답={truth_label}): 원본={o} → 파인튜닝={a}")
    else:
        print("\n원본과 예측이 완전히 동일 — 미커버 클래스 회귀 없음 ✅")

    return 0


if __name__ == "__main__":
    sys.exit(main())
