"""ViT 비전 인코더 마지막 N개 블록 파인튜닝 — 선형 프로브(`aihub_train_head.py`) 다음의
비교 실험이다.

브리핑(`CLASSIFIER_FINETUNE_BRIEF.md` §3)은 원래 **전체 백본 파인튜닝을 금지**했다 —
AI-Hub가 35종 중 11종만 덮어서, 백본을 흔들면 zero-shot에 의존하는 나머지 24종이 먼저
무너질 위험이 있어서다(카테고리·색상 헤드는 그래서 백본을 아예 로드하지도 않는 선형
프로브다). 이 스크립트는 그 원칙을 뒤집는 게 아니라, **이미 검증된 선형 프로브 베이스라인과
별도로** 흔들리는 범위를 최소화한 완화된 버전을 사용자 요청으로 추가 비교하는 것이다:

    [동결]      text_model / text_projection / logit_scale        — 전혀 안 건드린다
    [동결]      vision_model.encoder.layers[:-N]                  — 앞쪽 블록
    [언프리즈]  vision_model.encoder.layers[-N:]                  — 마지막 N개 블록
    [언프리즈]  vision_model.post_layernorm                       — 언프리즈 블록 바로 뒤
    [언프리즈]  visual_projection                                 — 공유 임베딩 공간 사영
    [신규 학습] 분류 헤드(`nn.Linear`)                              — 기존 sklearn 헤드와 별개

`aihub_cache_pixels.py`가 미리 만들어 둔 `pixel_values` 캐시를 그대로 쓴다 — 이미지 디코드·
마스크 크롭을 epoch마다 반복하지 않는다. 행 필터링(태스크별 라벨 선택)은
`aihub_train_head.build_task_dataset()`를 재사용한다 — 임베딩이든 pixel 텐서든 첫 축이
행이면 동작이 같다.

산출물은 기존 선형 헤드(`head_*.joblib`)·임베딩(`.npy`)과 **완전히 다른 폴더**
(기본 `artifacts_finetune/`)에 저장한다 — 이 실험을 몇 번을 돌려도 이미 검증된 베이스라인은
안 건드린다. run마다 폴더 이름이 달라(`run_name()`) 언프리즈 조건을 바꿔가며 나란히 쌓을
수 있다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import aihub_train_head

DEFAULT_MODEL_ID = "patrickjohncyh/fashion-clip"
DEFAULT_UNFREEZE_LAYERS = 2
DEFAULT_EPOCHS = 10
DEFAULT_BATCH_SIZE = 32
DEFAULT_LR_BACKBONE = 1e-5
DEFAULT_LR_HEAD = 1e-3
SEED = 42


def run_name(
    task: str,
    variant: str,
    unfreeze_layers: int,
    lr_backbone: float,
    *,
    warm_start: bool = False,
    frozen_backbone: bool = False,
) -> str:
    """run마다 다른 폴더 이름 — 하이퍼파라미터 조합이 다르면 이전 run과 안 겹친다.

    **같은 조합으로 다시 돌리면 이름이 같다** — `next_versioned_dir()`가 그 경우를
    처리한다(기본은 버전을 올려 저장, `--overwrite`로 강제 덮어쓰기).

    `warm_start=True`면 `_warm` 접미사를 붙인다 — `--init-checkpoint`로 다른 태스크의
    체크포인트에서 이어서 학습한 run은, 처음부터 학습한(독립학습) run과 같은 폴더에
    저장되면 안 된다(둘을 비교하는 게 목적이라 하나가 다른 하나를 덮어쓰면 안 됨).

    `frozen_backbone=True`면 `_probe` 접미사를 붙인다 — `--freeze-backbone`으로 백본을
    안 건드리고 헤드만 학습한 run이다("이 백본이 다른 태스크에서도 여전히 쓸만한가"를
    재는 진단 실행). 실제로 백본을 더 적응시킨 run과 구분해야 한다.

    `method_of()`는 접두어만 보므로 이 접미사들이 붙어도 방법 분류는 그대로 된다.
    """
    suffix = ("_warm" if warm_start else "") + ("_probe" if frozen_backbone else "")
    return f"vit_last{unfreeze_layers}_{task}_{variant}_lr{lr_backbone:g}{suffix}"


def next_versioned_dir(path: Path) -> Path:
    """`path`가 이미 있으면 안 겹치는 `_v2`, `_v3`, … 폴더명을 찾아 반환한다.

    `aihub_train_head.next_versioned_path()`와 같은 이유다 — torch 시드를 고정해도
    같은 명령을 재실행하면 결과가 미세하게 달라질 수 있는데(다른 라이브러리 버전,
    비결정적 CUDA 커널 등), 그때 이전 run의 체크포인트를 조용히 덮어쓰면 안 된다.
    """
    if not path.exists():
        return path
    version = 2
    while True:
        candidate = path.with_name(f"{path.name}_v{version}")
        if not candidate.exists():
            return candidate
        version += 1


def pixel_split_tag(split: str, variant: str) -> str:
    """`aihub_cache_pixels.pixel_tag(split, variant)`와 같은 규칙(소스 필터 없이 캐시했다고
    가정 — STEP 3.5 셀이 그렇게 돈다). 두 모듈이 따로 규칙을 들고 있으면 언젠가 어긋나므로
    여기서 문자열을 재조립하지 않고 이름만 맞춘다(테스트가 실제로 값을 맞대본다)."""
    tag = f"{split}_{variant}"
    return f"{tag}_pixels"


def encode_labels(labels: list[str]) -> tuple[list[int], list[str]]:
    """문자열 라벨 → (정수 인덱스 목록, 정렬된 클래스 목록). 클래스 목록이 곧 인덱스 규약이고
    체크포인트에 그대로 저장돼 추론 시 인덱스→라벨 복원에 쓰인다."""
    classes = sorted(set(labels))
    index = {label: i for i, label in enumerate(classes)}
    return [index[label] for label in labels], classes


def filter_known_classes(
    x: Any, labels: list[str], label_index: dict[str, int]
) -> tuple[Any, list[int], int]:
    """val/test에만 있고 train엔 없는 라벨은 헤드가 낼 수 없는 정답이라 평가에서 제외한다.

    조용히 버리면 정확도가 원인 모르게 낮아 보이므로, 몇 건을 버렸는지 같이 반환한다.
    """
    keep = [i for i, label in enumerate(labels) if label in label_index]
    y = [label_index[labels[i]] for i in keep]
    return x[keep], y, len(labels) - len(keep)


def load_pixel_split(cache_dir: Path, split: str, variant: str) -> tuple[Any, list[dict]]:
    """`aihub_cache_pixels.py` 산출물 한 쌍(.npy + .jsonl)을 읽는다. 행 순서가 일치한다."""
    import numpy as np

    tag = pixel_split_tag(split, variant)
    npy_path = cache_dir / f"{tag}.npy"
    jsonl_path = cache_dir / f"{tag}.jsonl"
    if not npy_path.exists():
        raise FileNotFoundError(
            f"pixel 캐시가 없다: {npy_path} — aihub_cache_pixels.py를 먼저 돌릴 것"
        )

    pixels = np.load(npy_path)
    rows = [
        json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line
    ]
    if len(rows) != len(pixels):
        raise ValueError(f"행 수 불일치: {npy_path}={len(pixels)} vs {jsonl_path}={len(rows)}")
    return pixels, rows


def load_model(model_id: str, unfreeze_layers: int, device: str) -> Any:
    """fashion_clip을 싣고, 텍스트 타워는 통째로 · 비전 타워는 마지막 N개 블록만 남기고 얼린다."""
    from transformers import AutoModel

    model = AutoModel.from_pretrained(model_id)
    model.to(device)
    for parameter in model.parameters():
        parameter.requires_grad_(False)

    if unfreeze_layers > 0:
        vision_layers = model.vision_model.encoder.layers
        for layer in vision_layers[-unfreeze_layers:]:
            for parameter in layer.parameters():
                parameter.requires_grad_(True)
        for parameter in model.vision_model.post_layernorm.parameters():
            parameter.requires_grad_(True)
        for parameter in model.visual_projection.parameters():
            parameter.requires_grad_(True)

    return model


def unfrozen_state_dict(model: Any) -> dict[str, Any]:
    """`requires_grad=True`인 파라미터만 CPU로 뽑는다 — 체크포인트를 작게 유지한다.

    복원할 때는 사전학습 가중치를 다시 로드한 뒤 이 dict를 `strict=False`로 얹는다 —
    나머지는 사전학습 그대로라 저장할 필요가 없다.
    """
    return {
        name: parameter.detach().cpu().clone()
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    }


def train_finetune(
    model: Any,
    head: Any,
    x_train: Any,
    y_train: list[int],
    x_val: Any,
    y_val: list[int],
    *,
    epochs: int,
    lr_backbone: float,
    lr_head: float,
    batch_size: int,
    device: str,
) -> dict:
    """미니배치 학습 루프. epoch마다 val accuracy를 재고 **최고 기록만** 체크포인트로 남긴다
    (마지막 epoch가 아니라 최고 시점 기준으로 test를 보기 위해서다 — 과적합 epoch를 그대로
    쓰면 test 숫자가 실제보다 나빠 보인다)."""
    import numpy as np
    import torch

    y_train_arr = np.asarray(y_train, dtype="int64")

    backbone_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(
        [
            {"params": backbone_params, "lr": lr_backbone},
            {"params": head.parameters(), "lr": lr_head},
        ]
    )
    loss_fn = torch.nn.CrossEntropyLoss()
    rng = np.random.default_rng(SEED)

    history: list[dict] = []
    best_val_accuracy = -1.0
    best_state: dict | None = None

    for epoch in range(1, epochs + 1):
        model.train()
        head.train()
        order = rng.permutation(len(y_train_arr))
        epoch_loss = 0.0
        for start in range(0, len(order), batch_size):
            batch_idx = order[start : start + batch_size]
            pixel_batch = torch.from_numpy(x_train[batch_idx]).to(
                device=device, dtype=torch.float32
            )
            label_batch = torch.from_numpy(y_train_arr[batch_idx]).to(device)

            features = model.get_image_features(pixel_values=pixel_batch)
            features = features / features.norm(dim=-1, keepdim=True)
            logits = head(features)
            loss = loss_fn(logits, label_batch)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.detach()) * len(batch_idx)

        train_loss = epoch_loss / len(y_train_arr)
        val_accuracy = evaluate_finetune(model, head, x_val, y_val, batch_size, device)["accuracy"]
        history.append({"epoch": epoch, "train_loss": train_loss, "val_accuracy": val_accuracy})
        print(
            f"  epoch {epoch}/{epochs}  loss={train_loss:.4f}  val_acc={val_accuracy:.4f}",
            flush=True,
        )

        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            best_state = {
                "epoch": epoch,
                "backbone": unfrozen_state_dict(model),
                "head": {k: v.detach().cpu().clone() for k, v in head.state_dict().items()},
            }

    return {"history": history, "best_val_accuracy": best_val_accuracy, "best_state": best_state}


def evaluate_finetune(
    model: Any, head: Any, x: Any, y: list[int], batch_size: int, device: str
) -> dict:
    """순차 배치로 정확도만 본다(학습이 아니므로 셔플이 필요 없다)."""
    import numpy as np
    import torch

    y_arr = np.asarray(y, dtype="int64")
    model.eval()
    head.eval()
    correct = 0
    with torch.no_grad():
        for start in range(0, len(y_arr), batch_size):
            end = start + batch_size
            pixel_batch = torch.from_numpy(x[start:end]).to(device=device, dtype=torch.float32)
            features = model.get_image_features(pixel_values=pixel_batch)
            features = features / features.norm(dim=-1, keepdim=True)
            logits = head(features)
            predicted = logits.argmax(dim=-1).cpu().numpy()
            correct += int((predicted == y_arr[start:end]).sum())
    return {"n": int(len(y_arr)), "accuracy": (correct / len(y_arr)) if len(y_arr) else 0.0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ViT 비전 인코더 마지막 N개 블록 파인튜닝 — 선형 프로브 대비 비교 실험"
    )
    parser.add_argument(
        "--pixel-cache-dir", type=Path, required=True, help="aihub_cache_pixels.py의 --out-dir"
    )
    parser.add_argument("--task", default="category", choices=aihub_train_head.TASKS)
    parser.add_argument("--variant", default="masked", choices=("raw", "masked"))
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--unfreeze-layers", type=int, default=DEFAULT_UNFREEZE_LAYERS)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--lr-backbone", type=float, default=DEFAULT_LR_BACKBONE)
    parser.add_argument("--lr-head", type=float, default=DEFAULT_LR_HEAD)
    parser.add_argument("--device", default=None, help="기본값: cuda가 있으면 cuda")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="기본값: <pixel-cache-dir>/../artifacts_finetune (선형 헤드 산출물과 분리)",
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
        help="--init-checkpoint로 불러온 backbone을 더 학습시키지 않고 완전히 얼린 채 "
        "헤드만 학습한다 — '이 backbone이 다른 태스크에서도 여전히 쓸만한가'를 재는 진단용 "
        "(예: 색상으로 이어서 학습한 backbone이 카테고리도 여전히 잘하는지 확인)",
    )
    args = parser.parse_args(argv)

    import torch

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    # 헤드(nn.Linear) 초기화·미니배치 셔플 순서를 고정한다 — 이게 없으면 같은 인자로
    # 다시 돌려도 매번 결과가 미세하게 달라져서(2026-08-05 실측: test 0.8435→0.8424),
    # "재현 안 되는 게 정상"인지 "뭔가 바뀐 건지" 구분이 안 된다.
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)

    x_train_pixels, train_rows = load_pixel_split(args.pixel_cache_dir, "train", args.variant)
    x_val_pixels, val_rows = load_pixel_split(args.pixel_cache_dir, "val", args.variant)
    x_test_pixels, test_rows = load_pixel_split(args.pixel_cache_dir, "test", args.variant)

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

    y_train, classes = encode_labels(y_train_labels)
    label_index = {label: i for i, label in enumerate(classes)}

    x_val, y_val, dropped_val = filter_known_classes(x_val, y_val_labels, label_index)
    x_test, y_test, dropped_test = filter_known_classes(x_test, y_test_labels, label_index)
    if dropped_val or dropped_test:
        print(
            f"⚠ train에 없는 클래스라 평가에서 제외: val {dropped_val}건, test {dropped_test}건",
            file=sys.stderr,
        )

    print(
        f"task={args.task} variant={args.variant} unfreeze_layers={args.unfreeze_layers} "
        f"train={len(y_train):,} val={len(y_val):,} test={len(y_test):,} classes={len(classes)}"
    )

    model = load_model(args.model_id, args.unfreeze_layers, device)

    if args.init_checkpoint is not None:
        checkpoint = torch.load(args.init_checkpoint, map_location=device)
        source_layers = checkpoint.get("unfreeze_layers")
        if source_layers != args.unfreeze_layers:
            print(
                f"⚠ --init-checkpoint의 unfreeze_layers({source_layers})가 "
                f"--unfreeze-layers({args.unfreeze_layers})와 다르다 — 겹치는 파라미터만 "
                "로드되고 나머지는 새로 초기화된 채로 남는다",
                file=sys.stderr,
            )
        model.load_state_dict(checkpoint["backbone_state_dict"], strict=False)
        print(f"backbone 웜스타트: {args.init_checkpoint} (task={checkpoint.get('task')})")

    if args.freeze_backbone:
        for parameter in model.parameters():
            parameter.requires_grad_(False)
        print("backbone 동결(진단 모드) — 헤드만 학습한다")

    feature_dim = model.config.projection_dim
    head = torch.nn.Linear(feature_dim, len(classes)).to(device)

    result = train_finetune(
        model,
        head,
        x_train,
        y_train,
        x_val,
        y_val,
        epochs=args.epochs,
        lr_backbone=args.lr_backbone,
        lr_head=args.lr_head,
        batch_size=args.batch_size,
        device=device,
    )

    # 최고 val 시점 가중치로 복원한 뒤 test를 본다 — 마지막 epoch가 아니라 최고 시점 기준.
    best_state = result["best_state"]
    model.load_state_dict(best_state["backbone"], strict=False)
    head.load_state_dict(best_state["head"])
    test_result = evaluate_finetune(model, head, x_test, y_test, args.batch_size, device)
    print(
        f"best epoch={best_state['epoch']}  val_accuracy={result['best_val_accuracy']:.4f}  "
        f"test_accuracy={test_result['accuracy']:.4f}"
    )

    name = run_name(
        args.task,
        args.variant,
        args.unfreeze_layers,
        args.lr_backbone,
        warm_start=args.init_checkpoint is not None,
        frozen_backbone=args.freeze_backbone,
    )
    out_dir = args.out_dir or (args.pixel_cache_dir.parent / "artifacts_finetune")
    run_dir = out_dir / name
    if not args.overwrite:
        run_dir = next_versioned_dir(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "model_id": args.model_id,
            "task": args.task,
            "variant": args.variant,
            "unfreeze_layers": args.unfreeze_layers,
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
        "unfreeze_layers": args.unfreeze_layers,
        "epochs": args.epochs,
        "lr_backbone": args.lr_backbone,
        "lr_head": args.lr_head,
        "batch_size": args.batch_size,
        "init_checkpoint": str(args.init_checkpoint) if args.init_checkpoint else None,
        "frozen_backbone": args.freeze_backbone,
        "classes": classes,
        "history": result["history"],
        "best_epoch": best_state["epoch"],
        "best_val_accuracy": result["best_val_accuracy"],
        "test_accuracy": test_result["accuracy"],
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
