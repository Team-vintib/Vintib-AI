"""fashion_clip(**동결**) 이미지 임베딩 추출 — 파이프라인에서 GPU가 필요한 유일한 단계.

브리핑 §3의 2단계 구조 중 1단계다:

    [1단계 · GPU 1회] 이미지 → fashion_clip(frozen) → 임베딩 .npy 캐시   ← 이 파일
    [2단계 · CPU 초단위] 임베딩 + 라벨 → 선형 헤드 → .joblib

**백본은 학습하지 않는다.** `torch.no_grad()`로 추론만 하고 가중치를 건드리지 않는다
(브리핑 §3: 전체 파인튜닝 명시적 금지 — AI-Hub가 35종 중 11~14종만 덮어서, 백본을 흔들면
zero-shot에 의존하는 나머지 클래스가 먼저 무너진다).

산출물 3개가 **행 순서로 정렬**된다:
    <out>/<split>_<variant>.npy        float32 [N, D], L2 정규화 완료
    <out>/<split>_<variant>.jsonl      각 행의 레코드(라벨 포함)
    <out>/<split>_<variant>.meta.json  모델 id·차원·건수·실패 집계

tmux 안에서 돌릴 것 — 5만 장이면 GPU에서도 수십 분이다. `--overwrite` 없이 다시 돌리면
이미 있는 산출물은 건너뛴다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import aihub_preprocess

# `product-info-check/classify.py`의 레지스트리 키와 같은 이름을 쓴다 — 검증 스파이크에서
# 고른 체크포인트를 그대로 쓰고 있다는 걸 코드로 보이려는 것이다(CH014 §1-3에서
# fashion_clip으로 확정: 카테고리 동률·색상 최고 0.882·지연 최저 123ms).
FASHION_CLIP_MODEL_ID = "patrickjohncyh/fashion-clip"

DEFAULT_BATCH_SIZE = 64


def resolve_image_path(row: dict, image_root: Path) -> Path | None:
    """인덱스 한 줄 → 실제 이미지 파일 경로.

    AI-Hub JSON의 `image_path`는 `./008.의류 통합 데이터(3-1)/원천데이터/...`처럼 데이터셋
    루트 기준 상대경로다. 서버마다 어디에 풀었는지가 달라서 `--image-root`를 받아 이어
    붙이고, 실패하면 라벨 경로에서 유추하는 폴백을 차례로 시도한다.
    """
    candidates: list[Path] = []

    raw = row.get("image_path")
    if raw:
        cleaned = str(raw).replace("\\", "/").lstrip("./")
        candidates.append(image_root / cleaned)
        # 루트 이름(`008.의류 통합 데이터(3-1)`)까지 --image-root에 이미 포함된 경우
        parts = cleaned.split("/", 1)
        if len(parts) == 2:
            candidates.append(image_root / parts[1])

    # 폴백 — 라벨 경로의 `라벨링데이터`를 `원천데이터`로 바꾸고 확장자를 이미지로.
    label_path = row.get("label_path")
    if label_path:
        swapped = str(label_path).replace("라벨링데이터", "원천데이터")
        for suffix in (".jpg", ".png", ".jpeg"):
            candidates.append(image_root / Path(swapped).with_suffix(suffix))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


def load_index(
    path: Path, *, split: str | None, source: str | None, shot_type: str | None
) -> list[dict]:
    """인덱스 JSONL을 읽어 필터링한다."""
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if split and row.get("split") != split:
                continue
            if source and row.get("source") != source:
                continue
            if shot_type and row.get("shot_type") != shot_type:
                continue
            rows.append(row)
    return rows


def load_model(model_id: str, device: str) -> tuple[Any, Any]:
    """fashion_clip을 **추론 전용**으로 싣는다. 무거운 import는 여기 안에서만."""
    import torch
    from transformers import AutoModel, AutoProcessor

    model = AutoModel.from_pretrained(model_id)
    model.eval()
    model.to(device)
    for parameter in model.parameters():
        parameter.requires_grad_(False)  # 백본 동결을 코드로 못박는다
    # use_fast=True: torchvision 기반 빠른 프로세서. 체크포인트가 저장될 당시 설정에
    # use_fast가 없어 안 주면 transformers가 느린(PIL 기반) 프로세서로 폴백하며 경고를
    # 찍는다(v4.52부터는 fast가 기본값). 결과물(정규화된 리사이즈 텐서)은 사실상 동일하다.
    processor = AutoProcessor.from_pretrained(model_id, use_fast=True)
    torch.set_grad_enabled(False)
    return model, processor


def embed_rows(
    rows: list[dict],
    *,
    label_root: Path,
    image_root: Path,
    variant: str,
    model_id: str,
    device: str,
    batch_size: int,
    progress_every: int = 2000,
    accessory_label_root: Path | None = None,
) -> tuple[Any, list[dict], dict]:
    """`accessory_label_root`가 없으면 액세서리 행도 `label_root`(의류 라벨 폴더)로

    폴리곤을 찾으려다 실패한다 — `sample.jsonl`이 두 소스를 섞고 있고 `label_path`가
    소스마다 다른 루트 기준 상대경로이기 때문이다(2026-08-04 실측으로 확인). `raw`
    variant는 폴리곤이 필요 없어 이 문제와 무관하다.
    """
    """행 목록 → (임베딩 배열, 성공한 행 목록, 집계). 실패한 행은 조용히 빼고 센다."""
    import numpy as np
    from PIL import Image

    model, processor = load_model(model_id, device)

    vectors: list[Any] = []
    kept: list[dict] = []
    stats = {"missing_image": 0, "unreadable": 0, "no_polygon": 0, "normalized_polygon": 0}

    batch_images: list[Any] = []
    batch_rows: list[dict] = []

    def flush() -> None:
        if not batch_images:
            return
        inputs = processor(images=batch_images, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        features = model.get_image_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)  # L2 정규화
        vectors.append(features.cpu().float().numpy())
        kept.extend(batch_rows)
        batch_images.clear()
        batch_rows.clear()

    for index, row in enumerate(rows):
        if progress_every and index and index % progress_every == 0:
            print(f"  ... {index:,}/{len(rows):,}", file=sys.stderr, flush=True)

        image_path = resolve_image_path(row, image_root)
        if image_path is None or not image_path.exists():
            stats["missing_image"] += 1
            continue

        polygon = None
        if variant == "masked":
            row_label_root = label_root
            if row.get("source") == "accessory" and accessory_label_root is not None:
                row_label_root = accessory_label_root
            polygon = aihub_preprocess.load_polygon(
                row_label_root / row["label_path"], row.get("width"), row.get("height")
            )
            if polygon is None:
                stats["no_polygon"] += 1
            elif polygon.was_normalized:
                stats["normalized_polygon"] += 1

        try:
            with Image.open(image_path) as image:
                prepared = aihub_preprocess.render_variant(image, polygon, variant)
        except Exception:  # noqa: BLE001 — 깨진 파일 하나로 전체를 죽이지 않는다
            stats["unreadable"] += 1
            continue

        batch_images.append(prepared)
        batch_rows.append(row)
        if len(batch_images) >= batch_size:
            flush()
    flush()

    if not vectors:
        return np.zeros((0, 0), dtype="float32"), [], stats
    return np.concatenate(vectors, axis=0).astype("float32"), kept, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="fashion_clip(동결) 임베딩 추출 — GPU 1회")
    parser.add_argument("--index", type=Path, required=True, help="sample.jsonl 또는 index.jsonl")
    parser.add_argument("--label-root", type=Path, required=True, help="의류(clothes) 라벨 루트")
    parser.add_argument(
        "--accessory-label-root",
        type=Path,
        default=None,
        help="액세서리 라벨 루트. sample.jsonl이 두 소스를 섞으므로 masked variant에서 "
        "액세서리 행이 있으면 반드시 줘야 한다(안 주면 label_path가 안 맞아 폴리곤을 못 찾는다)",
    )
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--split", default="train", choices=("train", "val", "test", "all"))
    parser.add_argument("--variant", default="masked", choices=aihub_preprocess.VARIANTS)
    parser.add_argument("--source", default=None, choices=("clothes", "accessory"))
    parser.add_argument(
        "--shot-type",
        default=None,
        help="이 촬영유형만 쓴다(의류: front/back/wear, 액세서리: product/worn)",
    )
    parser.add_argument("--model-id", default=FASHION_CLIP_MODEL_ID)
    parser.add_argument("--device", default=None, help="기본값: cuda가 있으면 cuda")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    import numpy as np
    import torch

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{args.split}_{args.variant}"
    if args.source:
        tag += f"_{args.source}"
    npy_path = args.out_dir / f"{tag}.npy"
    if npy_path.exists() and not args.overwrite:
        print(f"이미 있다(건너뜀): {npy_path}  — 다시 만들려면 --overwrite")
        return 0

    rows = load_index(
        args.index,
        split=None if args.split == "all" else args.split,
        source=args.source,
        shot_type=args.shot_type,
    )
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        print("대상 행이 0개다 — --split/--source/--shot-type 필터를 확인할 것", file=sys.stderr)
        return 1

    has_accessory_rows = any(row.get("source") == "accessory" for row in rows)
    if args.variant == "masked" and has_accessory_rows and args.accessory_label_root is None:
        print(
            "⚠ masked variant인데 액세서리 행이 있고 --accessory-label-root가 없다 — "
            "그 행들은 의류 라벨 폴더에서 폴리곤을 찾으려다 실패해 마스크 없이(원본 그대로) 처리된다.",
            file=sys.stderr,
        )

    print(f"모델 {args.model_id} · device={device} · {len(rows):,}행 · variant={args.variant}")
    embeddings, kept, stats = embed_rows(
        rows,
        label_root=args.label_root,
        image_root=args.image_root,
        variant=args.variant,
        model_id=args.model_id,
        device=device,
        batch_size=args.batch_size,
        accessory_label_root=args.accessory_label_root,
    )

    np.save(npy_path, embeddings)
    with (args.out_dir / f"{tag}.jsonl").open("w", encoding="utf-8") as handle:
        for row in kept:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    meta = {
        "model_id": args.model_id,
        "variant": args.variant,
        "split": args.split,
        "source": args.source,
        "shot_type": args.shot_type,
        "rows_requested": len(rows),
        "rows_embedded": len(kept),
        "dim": int(embeddings.shape[1]) if embeddings.size else 0,
        "failures": stats,
    }
    (args.out_dir / f"{tag}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"저장: {npy_path}  shape={embeddings.shape}")
    print(f"실패 집계: {stats}")
    if stats["missing_image"] > len(rows) * 0.1:
        print("⚠ 이미지를 10% 넘게 못 찾았다 — --image-root가 틀렸을 가능성이 크다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
