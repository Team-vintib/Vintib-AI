"""상품 텍스트 임베딩 오프라인 캐시 빌드 (개인화 추천 T1/T2용, 오프라인 전용).

전체 상품 카탈로그의 텍스트(title/brand)를 kanana-nano 임베딩으로 인코딩해 서빙이 읽을
캐시(item_vectors.npy + item_meta.json)를 만든다. 유저 개인화는 들어가지 않는다 — 유저별
취향 벡터는 요청 시점에 서빙(personalize/service.py)이 이 아이템 벡터로부터 집계한다.

무거운 의존성(torch/transformers)은 함수 내부에서 지연 import 한다 — 서비스 런타임/CI가 이
모듈을 import 해도 로드되지 않도록. 의존성은 requirements-pipeline.txt(CI 미설치) 참고.

실데이터 전환 시: 이 스크립트로 생성한 item_vectors.npy/item_meta.json 을 personalize/catalog.py
의 로더가 읽도록 교체하면, 목업 벡터 생성 경로가 실 임베딩으로 바뀐다.

사용 예:
    python -m app.recommend.pipeline.embed_catalog \
        --catalog app/recommend/personalize/data/mock_catalog.json \
        --out app/recommend/personalize/artifacts

설계: .claude/plans/ai/002-personalized-recommendation-mvp.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# model_registry.ACTIVE_EMBEDDING(kanana-nano-embedding)과 동일. test/(스파이크)는 프로덕션에서
# import 하지 않으므로 모델 id는 문자열로 고정한다(embed.py 의 DEFAULT_CLIP_MODEL 과 동일 패턴).
DEFAULT_EMBEDDING_MODEL = "kakaocorp/kanana-nano-2.1b-embedding"

VECTORS_FILE = "item_vectors.npy"
META_FILE = "item_meta.json"

# item_meta.json 에 남길 카드/랭킹용 필드.
_META_FIELDS = (
    "product_id",
    "title",
    "thumbnail",
    "price",
    "brand",
    "brand_id",
    "category_id",
    "sale_type",
    "sale_status",
    "view_count",
)


def _product_text(row: dict) -> str:
    """임베딩 입력 텍스트. 의미 신호가 있는 title/brand 를 이어 붙인다."""
    parts = [row.get("title"), row.get("brand")]
    return " ".join(p for p in parts if p)


def embed_texts(
    texts: list[str],
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    max_length: int = 512,
):
    """텍스트 목록을 L2 정규화된 kanana 임베딩 (M, D) numpy 배열로 변환한다.

    kanana-nano-embedding 은 커스텀 모델 코드(Kanana2Vec)를 실어 trust_remote_code=True 가
    필요하다(test/model_selection/loaders.load_kanana_embedding 과 동일). doc instruction 은
    recommendation.ipynb/recommendation_benchmark.py 와 동일하게 빈 문자열을 쓴다.
    """
    import numpy as np
    from transformers import AutoModel

    model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
    embeddings = np.asarray(model.encode(texts, instruction="", max_length=max_length))
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return (embeddings / norms).astype(np.float32)


def build_catalog_embeddings(
    catalog_path: Path,
    out_dir: Path,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> None:
    """카탈로그 JSON을 읽어 item_vectors.npy + item_meta.json 캐시를 생성한다."""
    import numpy as np

    rows = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not rows:
        raise ValueError(f"카탈로그가 비어 있습니다: {catalog_path}")

    texts = [_product_text(row) for row in rows]
    vectors = embed_texts(texts, model_name=model_name)
    meta = [{field: row.get(field) for field in _META_FIELDS} for row in rows]

    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / VECTORS_FILE, vectors)
    (out_dir / META_FILE).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[embed_catalog] {len(rows)}개 상품 임베딩 저장 → {out_dir}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="상품 텍스트 임베딩 캐시 빌드(오프라인).")
    parser.add_argument("--catalog", type=Path, required=True, help="카탈로그 JSON 경로")
    parser.add_argument("--out", type=Path, required=True, help="캐시 출력 디렉터리")
    parser.add_argument("--model", type=str, default=DEFAULT_EMBEDDING_MODEL, help="임베딩 모델 id")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    build_catalog_embeddings(args.catalog, args.out, model_name=args.model)
