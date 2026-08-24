"""fashion_clip 상품 임베딩 시각화용 데이터 export — 발표 자료 준비(1단계).

이미 계산돼 pgvector(`product_garment_embedding`)에 저장된 임베딩을 읽어서, 2단계
(`validation/REC/product-embedding-similarity-check/*.ipynb`)가 matplotlib/scikit-learn으로
그림만 그리면 되게 필요한 데이터를 로컬 파일로 떨궈 둔다:
  - 쿼리 상품(카테고리별 최다 표본에서 자동 선정) + top-K 이웃 + 두 쪽 상품 이미지
  - 산점도(§2)용 임베딩 표본 + 카테고리 라벨

torch가 필요 없다(임베딩 계산이 아니라 조회만 한다) — `requirements.txt`만 있으면 되므로
`backfill_garment_embeddings.py`와 달리 `ai` 컨테이너 안에서 그대로 돌아간다:

    docker exec vintib-ai python scripts/export_similar_product_samples.py

로컬(호스트)에서 돌리려면 `--be-base-url http://localhost:8080`(기본값) 그대로 두고,
`AI/.env`의 `VECTOR_DB_*`가 호스트에서 접속 가능한 값(기본 포트 5433)인지 확인할 것.

설계 문서 없음 — 발표 자료용 1회성 유틸리티다(`docs/plans/AI/` 대상 아님. 새 도메인 로직이
아니라 기존 `embedding_store`/BE 공개 API를 읽기만 하는 조회 스크립트).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_AI_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _AI_ROOT)  # `app.*` — cwd가 AI/든 repo root든 상관없이 늘 잡히게 직접 넣는다.

import httpx  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.db import get_vector_engine  # noqa: E402
from app.recommend.personalize import embedding_store  # noqa: E402
from app.recommend.personalize.embedding_store import ProductGarmentEmbedding  # noqa: E402


def fetch_all_embeddings() -> list[dict]:
    """`product_garment_embedding` 전체를 (product_id, embedding, category)로 가져온다.

    `embedding_store.py`에는 상품 1건 조회(`fetch_garment_embedding`)/top-k 검색
    (`find_similar`)뿐 전체 조회가 없어 여기서 직접 쿼리한다 — 운영 DAO 모듈은 건드리지
    않는다(이 스크립트 전용 1회성 쿼리).
    """
    with Session(get_vector_engine()) as session:
        rows = session.execute(
            select(
                ProductGarmentEmbedding.product_id,
                ProductGarmentEmbedding.embedding,
                ProductGarmentEmbedding.category,
            ).order_by(ProductGarmentEmbedding.product_id)
        ).all()
    return [
        {"product_id": r.product_id, "embedding": list(r.embedding), "category": r.category}
        for r in rows
    ]


def fetch_first_image(client: httpx.Client, be_base_url: str, product_id: int) -> bytes | None:
    """상품 상세에서 첫 이미지 URL을 찾아 내려받는다. 실패는 전부 `None`(경고만 찍는다)."""
    try:
        resp = client.get(f"{be_base_url}/api/products/{product_id}")
        resp.raise_for_status()
        images = resp.json()["data"].get("images", [])
        if not images:
            return None
        img_resp = client.get(images[0]["url"])
        img_resp.raise_for_status()
        return img_resp.content
    except Exception as exc:  # noqa: BLE001 — 이미지 1건 실패로 전체를 막지 않는다
        print(f"  [경고] product_id={product_id} 이미지 조회 실패: {type(exc).__name__}: {exc}")
        return None


def save_image(raw: bytes, path: Path) -> bool:
    """원본 포맷(webp 등)과 무관하게 RGB JPEG로 통일해 저장한다(2단계 노트북 로딩 단순화)."""
    try:
        Image.open(io.BytesIO(raw)).convert("RGB").save(path, "JPEG", quality=90)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  [경고] 이미지 저장 실패({path.name}): {type(exc).__name__}: {exc}")
        return False


def pick_query_products(rows: list[dict], num_queries: int) -> list[dict]:
    """카테고리별로 표본이 가장 많은 카테고리에서 하나씩 쿼리 상품을 고른다.

    category가 `None`인 행은 쿼리 후보에서 제외한다 — 쿼리는 "서로 다른 카테고리"를
    보여주는 게 목적이라 카테고리를 모르는 상품은 적합하지 않다. 표본이 가장 많은
    카테고리를 우선하는 이유는 top-K 이웃이 실제로 존재할 가능성이 높아서다. 무작위 대신
    `product_id`가 가장 작은 상품을 골라 재현 가능하게 한다.
    """
    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["category"] is not None:
            by_category[row["category"]].append(row)

    ranked_categories = sorted(by_category, key=lambda c: len(by_category[c]), reverse=True)
    queries = []
    for category in ranked_categories[:num_queries]:
        candidates = sorted(by_category[category], key=lambda r: r["product_id"])
        queries.append(candidates[0])
    return queries


def build_scatter_sample(
    rows: list[dict], max_points: int, must_include_ids: set[int]
) -> list[dict]:
    """산점도(§2)용 표본을 카테고리 비율을 최대한 유지하며 뽑는다.

    `must_include_ids`(쿼리 상품들)는 표본 상한과 무관하게 항상 포함한다 — 산점도에
    별표(★)로 강조할 점이 표본에서 빠지면 안 되기 때문이다.
    """
    if len(rows) <= max_points:
        return rows

    by_category: dict[str | None, list[dict]] = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)

    ratio = max_points / len(rows)
    sampled_ids: set[int] = set()
    sampled: list[dict] = []
    for group in by_category.values():
        take = max(1, round(len(group) * ratio))
        for row in group[:take]:
            if row["product_id"] not in sampled_ids:
                sampled.append(row)
                sampled_ids.add(row["product_id"])

    by_id = {row["product_id"]: row for row in rows}
    for pid in must_include_ids:
        if pid not in sampled_ids and pid in by_id:
            sampled.append(by_id[pid])
            sampled_ids.add(pid)

    return sampled[:max_points] if len(sampled) > max_points else sampled


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--be-base-url", default="http://localhost:8080")
    parser.add_argument("--num-queries", type=int, default=3)
    parser.add_argument(
        "--query-product-ids",
        default=None,
        help="쉼표로 구분한 product_id 목록. 주면 자동 선택(카테고리별 최다 표본) 대신 이걸 쓴다.",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--max-scatter-points",
        type=int,
        default=1500,
        help="산점도(§2)용 전체 임베딩 표본 상한 — 너무 많으면 t-SNE가 느려진다",
    )
    parser.add_argument(
        "--out-dir",
        default=os.path.join(
            _AI_ROOT, "validation", "REC", "product-embedding-similarity-check", "data"
        ),
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    print("[1/4] pgvector에서 전체 임베딩 조회 중...")
    rows = fetch_all_embeddings()
    print(f"  총 {len(rows)}건")
    if not rows:
        raise SystemExit(
            "임베딩이 하나도 없습니다 — scripts/backfill_garment_embeddings.py를 먼저 실행하세요."
        )

    category_counts: dict[str | None, int] = defaultdict(int)
    for row in rows:
        category_counts[row["category"]] += 1
    print("  카테고리별 건수 (None=미분류. 과거엔 BE categoryId와 AI GarmentCategory 6종이")
    print("  섞여 저장된 적이 있어(app/recommend/personalize/embedding_store.py 주석 참고),")
    print("  값 형태가 일관되지 않을 수 있다 — 아래 목록을 보고 이상하면 해석에 반영할 것):")
    for category, count in sorted(category_counts.items(), key=lambda kv: -kv[1]):
        print(f"    {category!r:<20} {count:>5}건")

    print("\n[2/4] 쿼리 상품 선정 중...")
    by_id_full = {row["product_id"]: row for row in rows}
    if args.query_product_ids:
        wanted_ids = [int(x) for x in args.query_product_ids.split(",")]
        queries = [by_id_full[pid] for pid in wanted_ids if pid in by_id_full]
        missing = set(wanted_ids) - set(by_id_full)
        if missing:
            print(f"  [경고] 임베딩이 없어 건너뛴 product_id: {sorted(missing)}")
    else:
        queries = pick_query_products(rows, args.num_queries)
    for q in queries:
        print(f"  쿼리: product_id={q['product_id']} category={q['category']!r}")
    if not queries:
        raise SystemExit(
            "쿼리로 쓸 상품을 하나도 못 골랐습니다 — --query-product-ids로 직접 지정하세요."
        )

    print(f"\n[3/4] 쿼리별 top-{args.top_k} 이웃 조회 + 이미지 다운로드 중...")
    query_sets = []
    needed_image_ids: set[int] = set()
    for q in queries:
        matches = embedding_store.find_similar(q["product_id"], args.top_k)
        neighbors = [
            {
                "product_id": m.product_id,
                "score": m.score,
                "category": by_id_full.get(m.product_id, {}).get("category"),
            }
            for m in matches
        ]
        query_sets.append(
            {
                "query_product_id": q["product_id"],
                "query_category": q["category"],
                "neighbors": neighbors,
            }
        )
        needed_image_ids.add(q["product_id"])
        needed_image_ids.update(n["product_id"] for n in neighbors)

    print(f"  이미지 {len(needed_image_ids)}장 다운로드 중 (BE: {args.be_base_url})...")
    image_ok: dict[int, bool] = {}
    with httpx.Client(timeout=10.0) as client:
        for pid in sorted(needed_image_ids):
            raw = fetch_first_image(client, args.be_base_url, pid)
            image_ok[pid] = raw is not None and save_image(raw, images_dir / f"{pid}.jpg")

    for qs in query_sets:
        qs["query_image_ok"] = image_ok.get(qs["query_product_id"], False)
        for n in qs["neighbors"]:
            n["image_ok"] = image_ok.get(n["product_id"], False)

    (out_dir / "query_sets.json").write_text(
        json.dumps(query_sets, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  저장: {out_dir / 'query_sets.json'}")

    print(f"\n[4/4] 산점도용 임베딩 표본 저장 중 (상한 {args.max_scatter_points}장)...")
    query_ids = {q["product_id"] for q in queries}
    sampled = build_scatter_sample(rows, args.max_scatter_points, must_include_ids=query_ids)

    embeddings = np.array([r["embedding"] for r in sampled], dtype=np.float32)
    categories = np.array(
        [r["category"] if r["category"] is not None else "미분류" for r in sampled]
    )
    product_ids = np.array([r["product_id"] for r in sampled])
    np.savez(
        out_dir / "embeddings_sample.npz",
        embeddings=embeddings,
        categories=categories,
        product_ids=product_ids,
    )
    print(f"  저장: {out_dir / 'embeddings_sample.npz'} ({len(sampled)}건, 원본 {len(rows)}건 중)")
    print(f"\n완료 -> {out_dir.resolve()}")


if __name__ == "__main__":
    main()
