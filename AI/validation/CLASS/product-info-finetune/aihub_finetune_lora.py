"""ViT 비전 인코더 LoRA 파인튜닝 — last-N 언프리즈(`aihub_finetune_vit.py`) 다음 비교 실험.

last-N 언프리즈는 마지막 몇 개 블록을 **통째로** 학습해 그 블록들의 파라미터 전부가
바뀐다. LoRA는 반대 방향이다 — **모든 비전 인코더 레이어**의 attention 사영(기본
`q_proj`·`v_proj`)에 저랭크 어댑터(A·B, rank `r`)만 얹고 원본 가중치는 그대로 둔 채
어댑터만 학습한다. 레이어 전체를 훨씬 얕게, 하지만 끝까지 건드린다는 점에서 last-N과
정반대 트레이드오프다 — 브리핑 §3의 미커버 24종 회귀 위험을 last-N보다 더 줄이면서도
표현 적응력을 얻을 수 있는지가 이 실험의 관심사다.

텍스트 타워는 last-N과 동일하게 **전혀 안 건드린다**. `post_layernorm`·`visual_projection`도
last-N과 동일하게 **직접** 학습한다(LoRA로 안 쪼갠다 — 작은 선형층 하나뿐이라 저랭크
분해할 이유가 없다. last-N 쪽과 같은 판단이다).

학습 루프·평가·pixel 캐시 로딩은 `aihub_finetune_vit.py`의 것을 **그대로 재사용**한다 —
그 함수들은 `model.parameters()`의 `requires_grad`만 보고 옵티마이저를 구성하므로
LoRA 어댑터 파라미터로도 동일하게 동작한다(`peft.get_peft_model()`이 원본 가중치는
자동으로 얼리고 어댑터만 `requires_grad=True`로 남긴다 — 새로 짤 이유가 없다).

⚠️ `CLIPModel` 전체가 아니라 `model.vision_model`**만** `get_peft_model()`에 넘긴다.
`target_modules=["q_proj","v_proj"]`는 이름 끝이 일치하는 서브모듈을 전부 찾는데,
`CLIPModel` 전체를 넘기면 텍스트 타워의 같은 이름 모듈(`text_model.encoder.layers.*.
self_attn.q_proj`)까지 걸려 텍스트 인코더가 조용히 파인튜닝될 위험이 있다. `vision_model`만
넘기면 애초에 `text_model`이 범위 밖이라 이 위험이 구조적으로 없다.

산출물은 `run_name()`이 `lora_`로 시작해 `aihub_finetune_vit.py`(`vit_last`)와 이름공간이
안 겹치고, 노트북의 `method_of()` 분류도 그대로 잡는다.

의존성: `peft`(신규, `validation/requirements-test.txt`에 추가함 — 서버에 없으면
`pip install peft`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import aihub_finetune_vit as base
import aihub_train_head

DEFAULT_MODEL_ID = base.DEFAULT_MODEL_ID
DEFAULT_R = 8
DEFAULT_ALPHA = 16
DEFAULT_DROPOUT = 0.05
DEFAULT_TARGET_MODULES = ("q_proj", "v_proj")
DEFAULT_EPOCHS = 10
DEFAULT_BATCH_SIZE = 32
DEFAULT_LR_ADAPTER = 1e-4
DEFAULT_LR_HEAD = 1e-3


def run_name(
    task: str,
    variant: str,
    r: int,
    lr_adapter: float,
    *,
    alpha: int = DEFAULT_ALPHA,
    dropout: float = DEFAULT_DROPOUT,
    target_modules: tuple[str, ...] = DEFAULT_TARGET_MODULES,
    warm_start: bool = False,
    frozen_backbone: bool = False,
) -> str:
    """`lora_`로 시작 — 노트북의 `method_of()`가 이 접두어로 LoRA를 분류한다.

    `alpha`/`dropout`/`target_modules`도 이름에 반영한다 — `r`·`lr_adapter`만 반영하던
    이전 버전은 이 셋만 바꿔 스윕하면 폴더명이 겹쳐 이전 run을 덮어썼다.

    `warm_start=True`면 `_warm` 접미사를 붙인다 — `aihub_finetune_vit.run_name()`과 같은
    이유(다른 태스크 체크포인트에서 이어받은 run을 독립학습 run과 구분).

    `frozen_backbone=True`면 `_probe` 접미사를 붙인다 — `--freeze-backbone`으로 어댑터를
    더 학습시키지 않고 헤드만 학습한 진단 run이다.
    """
    modules_tag = "".join(sorted(m.split("_")[0] for m in target_modules))
    suffix = ("_warm" if warm_start else "") + ("_probe" if frozen_backbone else "")
    return (
        f"lora_r{r}_a{alpha}_d{dropout:g}_{modules_tag}_{task}_{variant}_lr{lr_adapter:g}{suffix}"
    )


def load_model(
    model_id: str,
    r: int,
    alpha: int,
    dropout: float,
    target_modules: tuple[str, ...],
    device: str,
) -> Any:
    """fashion_clip을 싣고 **비전 인코더에만** LoRA를 건다. 텍스트 타워는 통째로 동결."""
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModel

    model = AutoModel.from_pretrained(model_id)
    model.to(device)
    for parameter in model.parameters():
        parameter.requires_grad_(False)

    lora_config = LoraConfig(
        r=r,
        lora_alpha=alpha,
        lora_dropout=dropout,
        target_modules=list(target_modules),
        bias="none",
    )
    # 모듈 문서 상단 경고 참고 — CLIPModel 전체가 아니라 vision_model만 넘긴다.
    model.vision_model = get_peft_model(model.vision_model, lora_config)

    for parameter in model.vision_model.post_layernorm.parameters():
        parameter.requires_grad_(True)
    for parameter in model.visual_projection.parameters():
        parameter.requires_grad_(True)

    return model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ViT 비전 인코더 LoRA 파인튜닝 — last-N 언프리즈 대비 비교 실험"
    )
    parser.add_argument("--pixel-cache-dir", type=Path, required=True)
    parser.add_argument("--task", default="category", choices=aihub_train_head.TASKS)
    parser.add_argument("--variant", default="masked", choices=("raw", "masked"))
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--r", type=int, default=DEFAULT_R, help="LoRA rank")
    parser.add_argument("--alpha", type=int, default=DEFAULT_ALPHA, help="LoRA alpha(스케일)")
    parser.add_argument("--dropout", type=float, default=DEFAULT_DROPOUT)
    parser.add_argument(
        "--target-modules",
        nargs="*",
        default=list(DEFAULT_TARGET_MODULES),
        help="LoRA를 걸 서브모듈 이름(vision_model 안에서만 매칭됨 — 위 docstring 경고 참고)",
    )
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--lr-adapter", type=float, default=DEFAULT_LR_ADAPTER)
    parser.add_argument("--lr-head", type=float, default=DEFAULT_LR_HEAD)
    parser.add_argument("--device", default=None, help="기본값: cuda가 있으면 cuda")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="기본값: <pixel-cache-dir>/../artifacts_finetune (last-N과 같은 폴더, run_name으로 구분)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="같은 이름의 기존 run 폴더를 덮어쓴다. 기본은 버전을 올려 저장한다(_v2, _v3, …)",
    )
    parser.add_argument(
        "--init-checkpoint",
        type=Path,
        default=None,
        help="다른 태스크에서 저장한 checkpoint.pt 경로. 주면 그 backbone(헤드 제외)에서 "
        "이어서 학습한다 — 예: 카테고리로 파인튜닝한 체크포인트에서 이어받아 색상을 학습",
    )
    parser.add_argument(
        "--freeze-backbone",
        action="store_true",
        help="--init-checkpoint로 불러온 backbone(LoRA 어댑터 포함)을 더 학습시키지 않고 "
        "완전히 얼린 채 헤드만 학습한다 — '이 backbone이 다른 태스크에서도 여전히 쓸만한가'를 "
        "재는 진단용",
    )
    args = parser.parse_args(argv)

    import torch

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    # aihub_finetune_vit.py와 같은 이유 — 헤드 초기화·셔플 순서를 고정해야 같은 인자로
    # 다시 돌렸을 때 재현이 된다(2026-08-05 실측: 시드 없이 재실행하니 결과가 바뀌었다).
    torch.manual_seed(base.SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(base.SEED)

    x_train_pixels, train_rows = base.load_pixel_split(args.pixel_cache_dir, "train", args.variant)
    x_val_pixels, val_rows = base.load_pixel_split(args.pixel_cache_dir, "val", args.variant)
    x_test_pixels, test_rows = base.load_pixel_split(args.pixel_cache_dir, "test", args.variant)

    x_train, y_train_labels, _ = aihub_train_head.build_task_dataset(
        x_train_pixels, train_rows, args.task
    )
    x_val, y_val_labels, _ = aihub_train_head.build_task_dataset(x_val_pixels, val_rows, args.task)
    x_test, y_test_labels, _ = aihub_train_head.build_task_dataset(
        x_test_pixels, test_rows, args.task
    )

    if len(y_train_labels) == 0:
        print(f"학습 표본이 0개다(task={args.task}) — pixel 캐시/필터를 확인할 것", file=sys.stderr)
        return 1

    y_train, classes = base.encode_labels(y_train_labels)
    label_index = {label: i for i, label in enumerate(classes)}

    x_val, y_val, dropped_val = base.filter_known_classes(x_val, y_val_labels, label_index)
    x_test, y_test, dropped_test = base.filter_known_classes(x_test, y_test_labels, label_index)
    if dropped_val or dropped_test:
        print(
            f"⚠ train에 없는 클래스라 평가에서 제외: val {dropped_val}건, test {dropped_test}건",
            file=sys.stderr,
        )

    print(
        f"task={args.task} variant={args.variant} lora_r={args.r} alpha={args.alpha} "
        f"train={len(y_train):,} val={len(y_val):,} test={len(y_test):,} classes={len(classes)}"
    )

    model = load_model(
        args.model_id, args.r, args.alpha, args.dropout, tuple(args.target_modules), device
    )

    if args.init_checkpoint is not None:
        checkpoint = torch.load(args.init_checkpoint, map_location=device)
        source_r = checkpoint.get("lora_r")
        source_modules = checkpoint.get("target_modules")
        if source_r != args.r or source_modules != list(args.target_modules):
            print(
                f"⚠ --init-checkpoint의 LoRA 설정(r={source_r}, target_modules={source_modules})이 "
                f"지금 설정(r={args.r}, target_modules={list(args.target_modules)})과 다르다 — "
                "겹치는 파라미터만 로드되고 나머지는 새로 초기화된 채로 남는다",
                file=sys.stderr,
            )
        compatible_state = base.drop_incompatible_keys(checkpoint["backbone_state_dict"], model)
        model.load_state_dict(compatible_state, strict=False)
        print(f"backbone 웜스타트: {args.init_checkpoint} (task={checkpoint.get('task')})")

    if args.freeze_backbone:
        for parameter in model.parameters():
            parameter.requires_grad_(False)
        print("backbone 동결(진단 모드) — 헤드만 학습한다")

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"학습 대상 파라미터: {trainable:,} / {total:,} ({trainable / total:.2%})")

    feature_dim = model.config.projection_dim
    head = torch.nn.Linear(feature_dim, len(classes)).to(device)

    result = base.train_finetune(
        model,
        head,
        x_train,
        y_train,
        x_val,
        y_val,
        epochs=args.epochs,
        lr_backbone=args.lr_adapter,
        lr_head=args.lr_head,
        batch_size=args.batch_size,
        device=device,
    )

    best_state = result["best_state"]
    model.load_state_dict(best_state["backbone"], strict=False)
    head.load_state_dict(best_state["head"])
    test_result = base.evaluate_finetune(model, head, x_test, y_test, args.batch_size, device)
    print(
        f"best epoch={best_state['epoch']}  val_accuracy={result['best_val_accuracy']:.4f}  "
        f"test_accuracy={test_result['accuracy']:.4f}"
    )

    name = run_name(
        args.task,
        args.variant,
        args.r,
        args.lr_adapter,
        alpha=args.alpha,
        dropout=args.dropout,
        target_modules=tuple(args.target_modules),
        warm_start=args.init_checkpoint is not None,
        frozen_backbone=args.freeze_backbone,
    )
    out_dir = args.out_dir or (args.pixel_cache_dir.parent / "artifacts_finetune")
    run_dir = out_dir / name
    if not args.overwrite:
        run_dir = base.next_versioned_dir(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "model_id": args.model_id,
            "task": args.task,
            "variant": args.variant,
            "lora_r": args.r,
            "lora_alpha": args.alpha,
            "target_modules": list(args.target_modules),
            "classes": classes,
            "backbone_state_dict": best_state["backbone"],
            "head_state_dict": best_state["head"],
        },
        run_dir / "checkpoint.pt",
    )
    meta = {
        "model_id": args.model_id,
        "task": args.task,
        "variant": args.variant,
        "lora_r": args.r,
        "lora_alpha": args.alpha,
        "lora_dropout": args.dropout,
        "target_modules": list(args.target_modules),
        "epochs": args.epochs,
        "lr_adapter": args.lr_adapter,
        "lr_head": args.lr_head,
        "batch_size": args.batch_size,
        "init_checkpoint": str(args.init_checkpoint) if args.init_checkpoint else None,
        "frozen_backbone": args.freeze_backbone,
        "classes": classes,
        "history": result["history"],
        "best_epoch": best_state["epoch"],
        "best_val_accuracy": result["best_val_accuracy"],
        "test_accuracy": test_result["accuracy"],
        "trainable_params": trainable,
        "total_params": total,
        "dropped_val_rows": dropped_val,
        "dropped_test_rows": dropped_test,
    }
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"저장: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
