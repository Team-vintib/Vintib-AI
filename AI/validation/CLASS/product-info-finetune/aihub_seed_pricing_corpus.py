"""내부 CLIP 유사도 코퍼스(CH020) 시딩 — AI-Hub 학습 이미지 + 가상 가격.

`app/pricing/internal_clip` comps 백엔드가 읽는 `internal_clip_vectors.npy` +
`internal_clip_meta.json` 쌍을 만든다. **이번 라운드의 코퍼스는 전부 합성 데이터다** —
실제 (이미지, 가격) 쌍 데이터가 아직 어디에도 없어서(BE 상품 시드 60건 중 brand_id 있는
건 8건뿐, 이미지가 MinIO에 실제로 있는지도 미확인 — CH020 §0), 분류기 파인튜닝에 이미
쓴 AI-Hub 이미지 + 카테고리별 임의 기준가로 메커니즘부터 검증한다. 가격 숫자 자체는
검증 전까지 무의미하다 — `data_source="synthetic_aihub"`로 항상 표시해 실데이터와 절대
안 섞이게 한다.

`aihub_finetune_vit.py`(체크포인트 로딩) + `aihub_embed.py`(이미지 경로 해석)를 그대로
재사용한다 — `app/pricing/clip_embed.py`와 로직은 같지만 import는 하지 않는다
(validation은 원격 GPU 서버에서 단독 스크립트로 실행되고, 프로덕션 쪽도 `validation/`을
import하지 않는 기존 규약과 대칭을 맞춘 것 — 두 곳 다 같은 판단 로직을 각자 복사해 둔다).

사용법:
    python aihub_seed_pricing_corpus.py \\
        --image-root /path/to/aihub/data \\
        --checkpoint-path artifacts_finetune/vit_last4_category_masked_lr1e-05/checkpoint.pt \\
        --out-dir ../../../app/pricing/data \\
        --max-per-category 200
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import aihub_dataset
import aihub_embed
import aihub_finetune_vit as base
import aihub_preprocess

DEFAULT_MODEL_ID = base.DEFAULT_MODEL_ID
DEFAULT_UNFREEZE_LAYERS = 4
DEFAULT_MAX_PER_CATEGORY = 200

# `app/pricing/internal_corpus.py`의 VECTORS_FILENAME/META_FILENAME과 같은 이름이어야
# 한다 — 서로 import하지 않으니 이름이 어긋나지 않게 여기 다시 적어둔다.
VECTORS_FILENAME = "internal_clip_vectors.npy"
META_FILENAME = "internal_clip_meta.json"

# 카테고리별 임의 기준가(원) — MockCompsSource와 같은 성격의 결정적 가짜값, 실측 아님.
_CATEGORY_BASE_PRICE_KRW: dict[str, int] = {
    "COAT": 150_000,
    "JACKET": 120_000,
    "CARDIGAN": 60_000,
    "KNIT": 50_000,
    "SHIRT": 40_000,
    "TSHIRT": 25_000,
    "SKIRT": 45_000,
    "SLACKS": 55_000,
    "DENIM": 58_000,
    "SHORT_PANTS": 35_000,
    "JOGGER_PANTS": 45_000,
    "COTTON_PANTS": 50_000,
    "CARGO_PANTS": 52_000,
    "DRESS": 70_000,
    "JUMPSUIT": 80_000,
    "HOODIE": 55_000,
    "SLEEVELESS": 30_000,
}
_DEFAULT_BASE_PRICE_KRW = 50_000


def synthetic_price(category: str, image_path: str) -> int:
    """카테고리 기준가 × sha256 결정론적 비율(0.70~1.30). `hash()`가 아니다 — 파이썬
    문자열 해시는 프로세스마다 시드가 달라 재실행 시 값이 바뀐다(`MockCompsSource`와
    같은 이유로 sha256을 쓴다)."""
    digest = hashlib.sha256(f"{category}:{image_path}".encode("utf-8")).digest()
    ratio = 0.70 + (int.from_bytes(digest[:2], "big") % 601) / 1000
    base_price = _CATEGORY_BASE_PRICE_KRW.get(category, _DEFAULT_BASE_PRICE_KRW)
    return round(base_price * ratio / 1000) * 1000


def build_meta_row(category: str, image_path: str) -> dict[str, Any]:
    """벡터 한 행에 대응하는 메타 dict. `internal_corpus.CorpusItem`과 같은 필드."""
    return {
        "aihub_category": category,
        "synthetic_price": synthetic_price(category, image_path),
        "data_source": "synthetic_aihub",
    }


def collect_rows(
    image_root: Path, *, max_per_category: int, limit: int | None
) -> list[tuple[Path, str]]:
    """AI-Hub 라벨을 순회해 (실제 이미지 경로, 카테고리) 쌍을 카테고리당 상한까지 모은다.

    매핑이 없는(`subcategory is None`) 라벨과 실제 이미지 파일을 못 찾은 행은 건너뛴다.
    """
    counts: dict[str, int] = {}
    rows: list[tuple[Path, str]] = []
    for raw_label in aihub_dataset.load_labels(image_root, limit=limit):
        record, _reason = aihub_dataset.to_record(raw_label)
        category = record.subcategory
        if category is None:
            continue
        if counts.get(category, 0) >= max_per_category:
            continue
        image_path = aihub_embed.resolve_image_path(
            {"image_path": record.image_path, "label_path": record.label_path}, image_root
        )
        if image_path is None or not image_path.exists():
            continue
        rows.append((image_path, category))
        counts[category] = counts.get(category, 0) + 1
    return rows


def load_backbone(model_id: str, unfreeze_layers: int, checkpoint_path: Path, device: str) -> Any:
    """파인튜닝된 체크포인트를 얹은 backbone. `aihub_finetune_vit.py`의 `--init-checkpoint`
    로딩 경로와 같은 판단(shape 불일치 키 필터링)을 쓴다."""
    import torch

    model = base.load_model(model_id, unfreeze_layers, device)
    checkpoint = torch.load(checkpoint_path, map_location=device)
    compatible = base.drop_incompatible_keys(checkpoint["backbone_state_dict"], model)
    model.load_state_dict(compatible, strict=False)
    model.eval()
    return model


def embed_one(model: Any, processor: Any, image_path: Path, device: str) -> list[float]:
    """이미지 1장 → L2 정규화 임베딩. 폴리곤 정보가 없어 "raw" variant로 전처리한다
    (`aihub_ground_truth_zero_shot_check.py`와 같은 방식)."""
    import torch
    from PIL import Image

    with Image.open(image_path) as image:
        prepared = aihub_preprocess.render_variant(image, None, "raw")
    inputs = processor(images=[prepared], return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(pixel_values=inputs["pixel_values"].to(device))
        features = features / features.norm(dim=-1, keepdim=True)
    return features[0].cpu().tolist()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="내부 CLIP 유사도 코퍼스 시딩(CH020) — AI-Hub 이미지 + 가상 가격(합성 데이터)"
    )
    parser.add_argument("--image-root", type=Path, required=True, help="AI-Hub 데이터 루트")
    parser.add_argument("--checkpoint-path", type=Path, required=True)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--unfreeze-layers", type=int, default=DEFAULT_UNFREEZE_LAYERS)
    parser.add_argument("--out-dir", type=Path, required=True, help="보통 app/pricing/data/")
    parser.add_argument("--max-per-category", type=int, default=DEFAULT_MAX_PER_CATEGORY)
    parser.add_argument(
        "--limit", type=int, default=None, help="AI-Hub 라벨 스캔 상한(스모크 테스트용)"
    )
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)

    print("AI-Hub 라벨 스캔 중...", flush=True)
    rows = collect_rows(args.image_root, max_per_category=args.max_per_category, limit=args.limit)
    if not rows:
        print("코퍼스로 쓸 이미지를 찾지 못했다 — --image-root를 확인할 것", file=sys.stderr)
        return 1
    categories = sorted({category for _, category in rows})
    print(f"{len(rows):,}장 수집 완료 (카테고리 {len(categories)}종: {', '.join(categories)})")

    import numpy as np
    from transformers import AutoProcessor

    model = load_backbone(args.model_id, args.unfreeze_layers, args.checkpoint_path, args.device)
    processor = AutoProcessor.from_pretrained(args.model_id, use_fast=True)

    vectors = np.zeros((len(rows), model.config.projection_dim), dtype="float32")
    meta: list[dict[str, Any]] = []
    for index, (image_path, category) in enumerate(rows):
        vectors[index] = embed_one(model, processor, image_path, args.device)
        meta.append(build_meta_row(category, str(image_path)))
        if (index + 1) % 50 == 0:
            print(f"  ... {index + 1:,}/{len(rows):,}", file=sys.stderr, flush=True)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    np.save(args.out_dir / VECTORS_FILENAME, vectors)
    (args.out_dir / META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"저장 완료: {args.out_dir} ({len(rows):,}건, data_source=synthetic_aihub)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
