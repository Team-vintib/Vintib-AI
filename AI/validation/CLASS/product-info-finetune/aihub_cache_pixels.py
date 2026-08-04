"""ViT 파인튜닝 실험용 **입력 텐서** 캐싱 — `aihub_embed.py`의 STEP3와 형제 단계.

`aihub_embed.py`가 이미지를 fashion_clip에 태워 **임베딩**을 캐시하는 것과 달리, 이 파일은
그 직전에서 멈춘다:

    이미지 → (PIL 디코드 + 폴리곤 마스크 크롭) → CLIP 프로세서 → pixel_values 텐서  ← 여기서 캐시
                                                                  → (파인튜닝 학습 루프가 이어받음)

**왜 필요한가.** STEP3 실측으로 확인된 병목은 GPU 연산이 아니라 **PIL 이미지 디코드 +
마스크 크롭**이었다(대용량 원본 JPEG 압축 해제가 CPU 바운드). 선형 헤드 학습은 그 비용을
한 번만 내면 끝이지만, ViT 백본 파인튜닝은 같은 이미지를 **epoch마다 다시** 모델에
먹여야 한다 — 매 epoch 그 디코드·크롭을 반복하면 손해가 그대로 누적된다.

**왜 "중간 활성값"이 아니라 "입력 텐서"를 캐시하는가.** 언프리즈 경계 바로 앞의 중간
활성값(예: 인코더 레이어 k 직전 출력)을 캐시하면 더 빠르겠지만, 그 경계가 실험마다
바뀐다(마지막 N개 블록 언프리즈에서 N을 바꾸거나 LoRA로 전환하면 경계 자체가 사라진다)
— 그때마다 캐시를 다시 만들어야 해 재사용성이 낮다. 입력 텐서(`pixel_values`)는 모델
구조·언프리즈 전략과 완전히 무관해서, 어떤 파인튜닝 방법을 쓰든 그대로 재사용된다.

**백본은 여전히 안 태운다.** 이 파일은 `AutoProcessor`만 쓰고 `AutoModel`은 아예
로드하지 않는다 — 모델 forward가 없으니 GPU도 필요 없다(CPU에서도 충분히 빠르다).

산출물 3개(`aihub_embed.py`와 같은 패턴, `_pixels` 접미사로 구분해 같은 폴더에 둬도
임베딩 산출물과 안 겹친다):
    <out>/<split>_<variant>[_<source>]_pixels.npy        <dtype> [N, C, H, W]
    <out>/<split>_<variant>[_<source>]_pixels.jsonl      각 행의 레코드(라벨 포함)
    <out>/<split>_<variant>[_<source>]_pixels.meta.json  모델 id·shape·dtype·실패 집계

기본 dtype은 `float16`이다 — 정규화된 픽셀값(대략 [-2, 2] 범위)은 절반 정밀도로도
학습에 지장이 없고, 5만 장 단위에서는 저장 공간 차이가 크다(float32 대비 절반).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import aihub_embed  # 경로 해석·인덱스 로딩 규칙을 한 곳에만 두려고 재사용한다
import aihub_preprocess

DEFAULT_BATCH_SIZE = 64
DTYPE_CHOICES = ("float16", "float32")


def pixel_tag(split: str, variant: str, source: str | None = None) -> str:
    """`aihub_train_head.head_filename()`과 같은 목적 — 소스별 캐시가 서로 안 덮어쓴다."""
    tag = f"{split}_{variant}"
    if source:
        tag += f"_{source}"
    return f"{tag}_pixels"


def load_processor(model_id: str) -> Any:
    """CLIP 이미지 프로세서만 싣는다. 모델(가중치)은 로드하지 않는다 — GPU 불필요."""
    from transformers import AutoProcessor

    # use_fast=True — 이유는 aihub_embed.load_model()과 같다(느린 PIL 프로세서 폴백 경고 회피).
    return AutoProcessor.from_pretrained(model_id, use_fast=True)


def cache_pixel_rows(
    rows: list[dict],
    *,
    label_root: Path,
    image_root: Path,
    variant: str,
    model_id: str,
    batch_size: int,
    dtype: str = "float16",
    progress_every: int = 2000,
    accessory_label_root: Path | None = None,
) -> tuple[Any, list[dict], dict]:
    """행 목록 → (pixel_values 배열, 성공한 행 목록, 집계).

    `aihub_embed.embed_rows()`와 이미지 로딩·마스크 크롭 로직은 동일하다(그래서 실패 집계
    항목도 같다) — 다른 건 딱 하나, `model.get_image_features()`까지 가지 않고
    `processor(...).pixel_values`에서 멈춘다는 것.
    """
    import numpy as np
    import torch
    from PIL import Image

    processor = load_processor(model_id)
    torch_dtype = getattr(torch, dtype)

    vectors: list[Any] = []
    kept: list[dict] = []
    stats = {"missing_image": 0, "unreadable": 0, "no_polygon": 0, "normalized_polygon": 0}

    batch_images: list[Any] = []
    batch_rows: list[dict] = []

    def flush() -> None:
        if not batch_images:
            return
        inputs = processor(images=batch_images, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(torch_dtype)
        vectors.append(pixel_values.numpy())
        kept.extend(batch_rows)
        batch_images.clear()
        batch_rows.clear()

    for index, row in enumerate(rows):
        if progress_every and index and index % progress_every == 0:
            print(f"  ... {index:,}/{len(rows):,}", file=sys.stderr, flush=True)

        image_path = aihub_embed.resolve_image_path(row, image_root)
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
        return np.zeros((0, 0, 0, 0), dtype=dtype), [], stats
    return np.concatenate(vectors, axis=0), kept, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ViT 파인튜닝용 입력 텐서(pixel_values) 캐싱 — 모델은 안 태운다(GPU 불필요)"
    )
    parser.add_argument("--index", type=Path, required=True, help="sample.jsonl 또는 index.jsonl")
    parser.add_argument("--label-root", type=Path, required=True, help="의류(clothes) 라벨 루트")
    parser.add_argument(
        "--accessory-label-root",
        type=Path,
        default=None,
        help="액세서리 라벨 루트. sample.jsonl이 두 소스를 섞으므로 masked variant에서 "
        "액세서리 행이 있으면 반드시 줘야 한다(aihub_embed.py와 동일한 이유)",
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
    parser.add_argument("--model-id", default=aihub_embed.FASHION_CLIP_MODEL_ID)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--dtype", default="float16", choices=DTYPE_CHOICES)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    import numpy as np

    args.out_dir.mkdir(parents=True, exist_ok=True)
    tag = pixel_tag(args.split, args.variant, args.source)
    npy_path = args.out_dir / f"{tag}.npy"
    if npy_path.exists() and not args.overwrite:
        print(f"이미 있다(건너뜀): {npy_path}  — 다시 만들려면 --overwrite")
        return 0

    rows = aihub_embed.load_index(
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
            "그 행들은 마스크 없이(원본 그대로) 처리된다.",
            file=sys.stderr,
        )

    print(f"모델 {args.model_id} · pixel-only(모델 미로드) · {len(rows):,}행 · dtype={args.dtype}")
    pixels, kept, stats = cache_pixel_rows(
        rows,
        label_root=args.label_root,
        image_root=args.image_root,
        variant=args.variant,
        model_id=args.model_id,
        batch_size=args.batch_size,
        dtype=args.dtype,
        accessory_label_root=args.accessory_label_root,
    )

    np.save(npy_path, pixels)
    with (args.out_dir / f"{tag}.jsonl").open("w", encoding="utf-8") as handle:
        for row in kept:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    meta = {
        "model_id": args.model_id,
        "variant": args.variant,
        "split": args.split,
        "source": args.source,
        "shot_type": args.shot_type,
        "dtype": args.dtype,
        "shape": list(pixels.shape),
        "rows_requested": len(rows),
        "rows_cached": len(kept),
        "failures": stats,
    }
    (args.out_dir / f"{tag}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    size_mb = pixels.nbytes / (1024 * 1024)
    print(f"저장: {npy_path}  shape={pixels.shape}  dtype={args.dtype}  ({size_mb:,.0f} MB)")
    print(f"실패 집계: {stats}")
    if stats["missing_image"] > len(rows) * 0.1:
        print("⚠ 이미지를 10% 넘게 못 찾았다 — --image-root가 틀렸을 가능성이 크다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
