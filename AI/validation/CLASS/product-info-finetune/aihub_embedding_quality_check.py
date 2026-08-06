"""zero-shot fashion-clip vs 카테고리 파인튜닝(last-N=4) 백본 — 임베딩 품질(유사상품
추천 관점) 비교.

**분류 정확도와는 다른 질문이다.** last-N=4는 이미 분류 정확도로 검증됐다(test 0.8424,
CH014). 여기서 보는 건 "유사 상품 추천"에 쓸 임베딩으로는 어느 쪽이 나은가다 — 분류
파인튜닝은 카테고리 결정 경계를 cross-entropy로 학습하므로, 같은 카테고리 안의 미세한
시각적 다양성을 눌러버릴 위험이 있다(neural collapse류 현상). 그러면 분류엔 좋아도
"같은 재킷 중에 뭐가 더 닮았나"를 구분하는 용도로는 오히려 나빠질 수 있다.

측정 지표(둘 다 순수 함수, `--vectors`/`--categories`만 있으면 torch 없이도 계산 가능):

1. `intra_inter_gap()` — 카테고리 내부 평균 코사인 유사도 vs 카테고리 간 평균 코사인
   유사도의 차이. 내부 유사도가 1에 가깝게 뭉쳐 있으면(=간격이 벌어져도 내부 값 자체가
   너무 높으면) 카테고리 안의 다양성이 눌린 것 — 추천용으로는 나쁜 신호다.
2. `knn_category_purity()` — top-k 최근접 이웃 중 같은 카테고리 비율(참고용, 분류
   신호와의 정합성만 확인 — 이 값이 높다고 추천 품질이 좋다는 뜻은 아니다).

`aihub_seed_pricing_corpus.py`의 `collect_rows()`(샘플링)/`embed_one()`(masked variant
임베딩)를 그대로 재사용한다 — 코퍼스가 실제로 쓸 전처리와 동일 조건으로 비교해야
의미가 있어서다.

사용법:
    python aihub_embedding_quality_check.py \\
        --label-root /path/to/aihub/extracted/clothes \\
        --image-root /path/to/aihub/extracted/images \\
        --checkpoint-path artifacts_finetune/vit_last4_category_masked_lr1e-05/checkpoint.pt \\
        --samples-per-category 30
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import aihub_embed
import aihub_seed_pricing_corpus as seed

DEFAULT_SAMPLES_PER_CATEGORY = 30
DEFAULT_TOP_K = 5


def intra_inter_gap(vectors: Any, categories: list[str]) -> dict[str, float]:
    """카테고리 내부/카테고리 간 평균 코사인 유사도와 그 차이(gap).

    `vectors`는 이미 L2 정규화돼 있다고 가정한다(내적 = 코사인 유사도). gap이 작을수록
    카테고리 내부와 카테고리 간 구분이 흐릿하다는 뜻이고, intra_mean 자체가 1에 가까우면
    gap이 커도 내부가 뭉개진 것 — 두 값을 같이 봐야 한다.
    """
    import numpy as np

    sims = vectors @ vectors.T
    n = len(categories)
    labels = list(categories)
    same = [[labels[i] == labels[j] for j in range(n)] for i in range(n)]
    same_arr = np.array(same, dtype=bool)
    np.fill_diagonal(same_arr, False)
    not_self = ~np.eye(n, dtype=bool)

    intra_vals = sims[same_arr]
    inter_vals = sims[(~same_arr) & not_self]
    intra_mean = float(intra_vals.mean()) if intra_vals.size else float("nan")
    inter_mean = float(inter_vals.mean()) if inter_vals.size else float("nan")
    return {"intra_mean": intra_mean, "inter_mean": inter_mean, "gap": intra_mean - inter_mean}


def knn_category_purity(vectors: Any, categories: list[str], *, top_k: int) -> float:
    """각 항목의 top-k(자기 자신 제외) 최근접 이웃 중 같은 카테고리 비율의 평균(참고용)."""
    import numpy as np

    sims = vectors @ vectors.T
    n = len(categories)
    sims = sims.copy()
    np.fill_diagonal(sims, -np.inf)
    purities = []
    for i in range(n):
        neighbor_idx = np.argsort(-sims[i])[:top_k]
        same = sum(1 for j in neighbor_idx if categories[j] == categories[i])
        purities.append(same / top_k)
    return float(np.mean(purities)) if purities else float("nan")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="zero-shot vs last-N=4 파인튜닝 백본의 임베딩 품질(유사상품 추천 관점) 비교"
    )
    parser.add_argument("--label-root", required=True, help="라벨링데이터 JSON 루트")
    parser.add_argument("--image-root", required=True, help="원천데이터 이미지 루트")
    parser.add_argument("--checkpoint-path", required=True)
    parser.add_argument("--model-id", default=seed.DEFAULT_MODEL_ID)
    parser.add_argument("--unfreeze-layers", type=int, default=seed.DEFAULT_UNFREEZE_LAYERS)
    parser.add_argument("--samples-per-category", type=int, default=DEFAULT_SAMPLES_PER_CATEGORY)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)

    from pathlib import Path

    label_root = Path(args.label_root)
    image_root = Path(args.image_root)
    checkpoint_path = Path(args.checkpoint_path)

    print("AI-Hub 라벨 스캔 중...", flush=True)
    rows = seed.collect_rows(
        label_root, image_root, max_per_category=args.samples_per_category, limit=None
    )
    if not rows:
        print(
            "샘플로 쓸 이미지를 찾지 못했다 — --label-root/--image-root를 확인할 것",
            file=sys.stderr,
        )
        return 1
    categories = [row.category for row in rows]
    print(f"{len(rows):,}장 샘플 (카테고리 {len(set(categories))}종)", flush=True)

    import numpy as np
    from transformers import AutoProcessor

    def _embed_all(model: Any, processor: Any) -> Any:
        vectors = np.zeros((len(rows), model.config.projection_dim), dtype="float32")
        for index, row in enumerate(rows):
            vectors[index] = seed.embed_one(model, processor, row, args.device)
            if (index + 1) % 50 == 0:
                print(f"  ... {index + 1:,}/{len(rows):,}", file=sys.stderr, flush=True)
        return vectors

    print("\n[zero-shot 원본 백본]", flush=True)
    zero_shot_model, zero_shot_processor = aihub_embed.load_model(args.model_id, args.device)
    zero_shot_vectors = _embed_all(zero_shot_model, zero_shot_processor)

    print("\n[last-N=4 파인튜닝 백본]", flush=True)
    finetuned_model = seed.load_backbone(
        args.model_id, args.unfreeze_layers, checkpoint_path, args.device
    )
    finetuned_processor = AutoProcessor.from_pretrained(args.model_id, use_fast=True)
    finetuned_vectors = _embed_all(finetuned_model, finetuned_processor)

    print("\n--- 결과 ---")
    for label, vectors in (
        ("zero-shot", zero_shot_vectors),
        ("last-N=4 파인튜닝", finetuned_vectors),
    ):
        gap = intra_inter_gap(vectors, categories)
        purity = knn_category_purity(vectors, categories, top_k=args.top_k)
        print(
            f"{label:16s} intra={gap['intra_mean']:.4f} inter={gap['inter_mean']:.4f} "
            f"gap={gap['gap']:.4f}  top-{args.top_k} 카테고리 순도={purity:.4f}"
        )
    print(
        "\n(참고) intra_mean이 1에 가까울수록 카테고리 내부가 뭉개진 것 — 파인튜닝이 "
        "zero-shot보다 intra_mean은 높은데 gap은 안 벌어지면, 분류 성능은 올라도 "
        "추천용 세부 구분력은 떨어졌다는 신호다."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
