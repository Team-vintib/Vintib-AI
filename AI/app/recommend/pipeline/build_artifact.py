"""브랜드(또는 상점) 유사도 그래프 아티팩트 오프라인 빌드 CLI.

사용 예:
    python -m app.recommend.pipeline.build_artifact \
        --data app/recommend/data --entity brand --out app/recommend/artifacts

data 디렉터리 구성:
    data/brands.yaml            # 엔티티 목록 (brands.example.yaml 스키마 참고)
    data/images/<id>/*.jpg      # 엔티티별 상품 이미지

무거운 의존성(numpy/torch/sentence-transformers/umap/pyyaml)은 requirements-pipeline.txt 참고.
설계: .claude/plans/ai/001-brand-similarity-graph.md
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from app.recommend.artifact import write_artifact
from app.recommend.pipeline.aggregate import aggregate_by_group
from app.recommend.pipeline.embed import DEFAULT_CLIP_MODEL, embed_images
from app.recommend.pipeline.layout import project_2d
from app.recommend.pipeline.similarity import knn_edges, top_neighbors

KNN_K = 8
NEIGHBORS_N = 50
SIZE_MIN = 8.0
SIZE_MAX = 30.0


def _load_entities(data_dir: Path) -> list[dict]:
    import yaml

    with (data_dir / "brands.yaml").open(encoding="utf-8") as f:
        entities = yaml.safe_load(f)
    if not entities:
        raise ValueError("brands.yaml 이 비어 있습니다.")
    return entities


def _resolve_images(data_dir: Path, entity: dict) -> list[Path]:
    patterns = entity.get("images") or [f"images/{entity['id']}/*"]
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(sorted(data_dir.glob(pattern)))
    return [p for p in paths if p.is_file()]


def _node_sizes(counts: list[int]) -> list[float]:
    lo, hi = min(counts), max(counts)
    if hi == lo:
        return [(SIZE_MIN + SIZE_MAX) / 2 for _ in counts]
    return [SIZE_MIN + (SIZE_MAX - SIZE_MIN) * (c - lo) / (hi - lo) for c in counts]


def build(data_dir: Path, out_dir: Path, entity: str, model_name: str, seed: int) -> Path:
    entities = _load_entities(data_dir)
    image_paths: list[Path] = []
    group_ids: list[str] = []
    meta_by_id: dict[str, dict] = {}
    for item in entities:
        item_id = item["id"]
        paths = _resolve_images(data_dir, item)
        if not paths:
            raise ValueError(f"'{item_id}' 의 이미지를 찾지 못했습니다.")
        image_paths.extend(paths)
        group_ids.extend([item_id] * len(paths))
        thumbnail = item.get("thumbnail")
        if thumbnail is None:
            thumbnail = str(paths[0].relative_to(data_dir)).replace("\\", "/")
        meta_by_id[item_id] = {"name": item.get("name", item_id), "thumbnail": thumbnail}

    item_vectors = embed_images(image_paths, model_name)
    ids, vectors, counts = aggregate_by_group(item_vectors, group_ids)
    coords = project_2d(vectors, seed=seed)
    sizes = _node_sizes(counts)

    nodes = [
        {
            "id": item_id,
            "name": meta_by_id[item_id]["name"],
            "x": round(float(coords[i, 0]), 4),
            "y": round(float(coords[i, 1]), 4),
            "size": round(float(sizes[i]), 2),
            "thumbnail": meta_by_id[item_id]["thumbnail"],
        }
        for i, item_id in enumerate(ids)
    ]
    edges = knn_edges(vectors, ids, k=KNN_K)
    neighbors = top_neighbors(vectors, ids, n=NEIGHBORS_N)
    meta = {
        "entity_type": entity,
        "embedding_model": model_name,
        "dim": int(vectors.shape[1]),
        "count": len(ids),
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    entity_dir = out_dir / entity
    write_artifact(entity_dir, meta, nodes, edges, neighbors)
    return entity_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="브랜드 유사도 그래프 아티팩트 빌드")
    parser.add_argument("--data", type=Path, default=Path("app/recommend/data"))
    parser.add_argument("--out", type=Path, default=Path("app/recommend/artifacts"))
    parser.add_argument("--entity", default="brand")
    parser.add_argument("--model", default=DEFAULT_CLIP_MODEL)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    entity_dir = build(args.data, args.out, args.entity, args.model, args.seed)
    print(f"아티팩트 생성 완료: {entity_dir}")


if __name__ == "__main__":
    main()
