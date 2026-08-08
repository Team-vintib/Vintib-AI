"""동일 상품 텍스트 매칭 코퍼스(product_corpus_item)를 채우는 실행 도구(CH030).

`app/pricing/product_corpus.py::refresh_category()`는 이미 만들어져 있지만 자동으로
실행되지 않는다 — 이 스크립트가 BE 카테고리(기본: 전체 소분류 24~126, `docs/
category-taxonomy.md` 참고)를 순회하며 채운다.

**torch/ML 의존성이 없다** — `backfill_garment_embeddings.py`(임베딩 백필, GPU 필요)와
달리 httpx + SQLAlchemy만 쓴다. `ai` 컨테이너 안에서 그대로 실행 가능하다.

**전제조건**: BE 공개 API(`GET /api/products`, `GET /api/brands`)와 AI 자체 vector-db
(`vector_db_*` 설정)에 둘 다 닿아야 한다 — 로컬 노트북에서 돌리려면 두 곳 다 터널링해야
하므로, 보통은 배포된 서버에서 직접 실행하는 게 더 간단하다:

    docker compose exec ai python scripts/refresh_product_corpus.py

로컬에서 돌리려면 `AI/.env`에 `be_base_url`/`vector_db_*`를 서버 값으로 맞춰야 한다.

사용법:
    python scripts/refresh_product_corpus.py                    # 전체 소분류(24~126)
    python scripts/refresh_product_corpus.py --category-ids 24 29 62
    python scripts/refresh_product_corpus.py --dry-run           # 브랜드 별칭 사전만 확인

설계: docs/plans/AI/CH030-pricing-text-match.md
"""

from __future__ import annotations

import argparse
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_AI_ROOT = os.path.dirname(_SCRIPT_DIR)
# `app.*` — cwd가 AI/든 repo root든 상관없이 늘 잡히게 직접 넣는다(backfill_garment_embeddings.py와 동일).
sys.path.insert(0, _AI_ROOT)

from app.pricing import product_corpus  # noqa: E402

# BE 카테고리 taxonomy v2의 소분류(depth=3) id 범위(24~126, docs/category-taxonomy.md).
# `product.category_id`는 항상 이 범위의 값이다.
_ALL_SUBCATEGORY_IDS = tuple(range(24, 127))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--category-ids",
        type=int,
        nargs="*",
        default=None,
        help="갱신할 categoryId 목록. 생략하면 전체 소분류(24~126)를 순회한다",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="브랜드 별칭 사전만 로드해 확인하고 코퍼스는 갱신하지 않는다",
    )
    args = parser.parse_args()

    product_corpus.init_schema()

    alias_map = product_corpus.get_brand_alias_map()
    print(f"[refresh] 브랜드 별칭 {len(alias_map)}개 로드")
    if not alias_map:
        print("[refresh] 경고: 브랜드 별칭이 0개다 — GET /api/brands 연결을 확인할 것")
    if args.dry_run:
        print("[refresh] --dry-run: 코퍼스를 갱신하지 않았다.")
        return

    category_ids = args.category_ids or _ALL_SUBCATEGORY_IDS
    total = 0
    for category_id in category_ids:
        count = product_corpus.refresh_category(category_id)
        total += count
        print(f"[refresh] categoryId={category_id}: {count}건 갱신")
    print(f"[refresh] 완료 — 총 {total}건")


if __name__ == "__main__":
    main()
