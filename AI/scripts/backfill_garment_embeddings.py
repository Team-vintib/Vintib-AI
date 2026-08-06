"""기존(시드) 상품의 의류 임베딩을 벡터DB에 채우는 1회성 백필 도구.

**품질검수 큐(`POST /quality/inspections`)를 거치지 않는다.** 백필은 하자 탐지·점수·
오버레이가 전혀 필요 없는데, 그 큐에 태우면 BE+Redis+AI 게이트웨이+GPU 워커가 전부 떠
있어야 한다 — 불필요한 의존이다. 대신 이 스크립트가 직접 우리 모델을 호출한다: SAM3로
옷을 탐지·크롭하고(`worker/models/sam3/segmenter.py`), zero-shot CLIP으로 임베딩한 뒤
(`worker/models/sam3/garment_embedding.py`), pgvector에 저장한다
(`app/recommend/personalize/embedding_store.py`) — 신규 등록 상품의 품질검수 파이프라인이
쓰는 것과 정확히 같은 함수를 그대로 재사용한다.

**카테고리는 BE의 categoryId를 그대로 쓴다.** `worker/models/product_classifier/
taxonomy.py`의 `CATEGORY_ID_MAP`을 거꾸로 조회한다 — 이 taxonomy는 분류 파인튜닝이 이미
BE 시드(`BE/docs/db/category-taxonomy.md`) 기준으로 정확히 맞춰 놓은 것이라 새 매핑을
만들 필요가 없다. 품질검수의 `GarmentCategory`(상의/아우터/하의 6종)와는 다른 개념이다 —
그건 SAM3 하자-탐지 프롬프트 선택용이고, 여기 저장하는 category는 추천 필터용 메타데이터일
뿐이라 taxonomy.py의 35종(가방·신발·액세서리·원피스 포함)을 그대로 쓴다. 사진에 실제
"옷"이 없으면(가방/신발 등) SAM3 탐지가 자연히 크롭을 못 만들어(`garment_crop=None`)
스킵된다 — 카테고리로 미리 걸러내지 않는다.

**전제조건**: BE가 뜬 상태여야 하고(상품 목록/상세 조회), 이 스크립트를 실행하는 환경에
torch/transformers/SAM3 의존성이 있어야 한다(품질검수 워커와 같은 요건).

사용법 (`app.*`/`sam3.*` import 때문에 어디서 실행하든 무관하게 sys.path를 스크립트가
직접 잡는다):
    python AI/scripts/backfill_garment_embeddings.py --dry-run   # 대상 목록만 확인
    python AI/scripts/backfill_garment_embeddings.py             # 실제 실행

설계: `.claude/plans/serialized-nibbling-mango.md`
"""

from __future__ import annotations

import argparse
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_AI_ROOT = os.path.dirname(_SCRIPT_DIR)
_REPO_ROOT = os.path.dirname(_AI_ROOT)
# `app.*` — cwd가 AI/든 repo root든 상관없이 늘 잡히게 직접 넣는다.
sys.path.insert(0, _AI_ROOT)
# `sam3.*`/`product_classifier.*` — quality_check_worker_example.py와 같은 이유로 부모
# 디렉터리(worker/models/)를 넣는다(여러 워커 패키지가 flat하게 sys.path에 들어가면
# sys.modules 캐시가 충돌한다 — AI/test/conftest.py 참고).
sys.path.insert(0, os.path.join(_REPO_ROOT, "worker", "models"))

import httpx  # noqa: E402

from app.recommend.personalize import embedding_store  # noqa: E402
from app.recommend.personalize.catalog import VISIBLE_SALE_STATUS  # noqa: E402
from product_classifier.taxonomy import CATEGORY_ID_MAP  # noqa: E402
from sam3.contracts import BaseColor, GarmentCategory  # noqa: E402
from sam3.garment_embedding import (  # noqa: E402
    EMBEDDING_MODEL_ID,
    GarmentEmbeddingNotReady,
    embed_garment,
)
from sam3.prompts import select_prompt_set  # noqa: E402
from sam3.segmenter import ImageFetchFailed, InspectionTarget, build_segmenter  # noqa: E402

# BE categoryId -> taxonomy.py Subcategory 값. CATEGORY_ID_MAP 키는 (Gender, Subcategory)라
# 성별이 다르면 같은 subcategory도 id가 다르지만(예: tshirt 여성 62 / 공용 97), 이 역방향
# 조회는 "이 id가 어떤 subcategory인지"만 알면 되므로 성별은 버린다.
_ID_TO_SUBCATEGORY_VALUE: dict[int, str] = {
    product_id: subcategory.value for (_gender, subcategory), product_id in CATEGORY_ID_MAP.items()
}

# 세그멘테이션에 필요한 형식상의 값 — `Sam3PcsSegmenter._detect_garment()`가 카테고리
# 무관 프롬프트로 옷을 찾아 실제 크롭 결과에는 영향이 없다(하자-탐지 프롬프트 선택에만
# 쓰이는데, 백필은 하자 탐지를 안 한다).
_DUMMY_PROMPT_SET = select_prompt_set(GarmentCategory.top_shirt, BaseColor.light)


def subcategory_value(category_id: int | None) -> str | None:
    """BE categoryId -> taxonomy.py Subcategory 문자열. 모르는 id면 None(그래도 임베딩은
    시도한다 — category는 부가 메타데이터일 뿐 저장 여부를 결정하지 않는다)."""
    if category_id is None:
        return None
    return _ID_TO_SUBCATEGORY_VALUE.get(category_id)


def fetch_all_products(client: httpx.Client, be_base_url: str, page_size: int = 100) -> list[dict]:
    """`GET /api/products`를 끝까지 페이지네이션해 전체 상품(list 응답)을 모은다."""
    products: list[dict] = []
    page = 0
    while True:
        resp = client.get(f"{be_base_url}/api/products", params={"page": page, "size": page_size})
        resp.raise_for_status()
        body = resp.json()["data"]
        products.extend(body["content"])
        if not body["hasNext"]:
            break
        page += 1
    return products


def fetch_product_detail(client: httpx.Client, be_base_url: str, product_id: int) -> dict:
    resp = client.get(f"{be_base_url}/api/products/{product_id}")
    resp.raise_for_status()
    return resp.json()["data"]


def eligible_products(products: list[dict]) -> list[dict]:
    """`personalize/catalog.py`와 같은 가시성 기준만 적용한다 — 카테고리로 미리 거르지
    않는다(SAM3 탐지 자체가 옷이 없는 사진을 자연히 걸러낸다)."""
    return [p for p in products if p["saleStatus"] in VISIBLE_SALE_STATUS]


def backfill_one(
    segmenter, product_id: int, image_urls: list[str], category_id: int | None
) -> bool:
    """한 상품을 실제로 처리한다 — SAM3 탐지+크롭 -> zero-shot CLIP 임베딩 -> pgvector 저장.

    torch/SAM3가 필요해 유닛 테스트 대상이 아니다(`embed_garment()`/`segmenter.segment()`와
    같은 성격 — 로컬 GPU 환경에서 수동 검증한다). 여러 이미지 중 옷을 찾은 첫 장만 쓴다
    (`_embed_first_garment()`와 같은 이유 — 상품당 벡터는 1개면 충분하다).
    """
    target = InspectionTarget(
        product_id=product_id, image_urls=tuple(image_urls), prompt_set=_DUMMY_PROMPT_SET
    )
    garment_crop = None
    for i in range(len(image_urls)):
        try:
            result = segmenter.segment(target, i)
        except ImageFetchFailed as exc:
            print(f"[backfill] product_id={product_id} 이미지 {i} 로드 실패: {exc}")
            continue
        if result.garment_crop is not None:
            garment_crop = result.garment_crop
            break

    if garment_crop is None:
        return False

    try:
        vector = embed_garment(garment_crop)
    except GarmentEmbeddingNotReady as exc:
        print(f"[backfill] product_id={product_id} 임베딩 준비 안 됨: {exc}")
        return False

    embedding_store.save_garment_embedding(
        product_id=product_id,
        embedding=vector,
        model_id=EMBEDDING_MODEL_ID,
        category=subcategory_value(category_id),
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--be-base-url", default="http://localhost:8080")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument(
        "--backend", default="sam3_pcs", help="worker/models/sam3/registry.py의 세그멘터 키"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="대상 목록만 출력하고 임베딩/저장은 하지 않는다"
    )
    args = parser.parse_args()

    with httpx.Client(timeout=10.0) as client:
        print(f"[backfill] {args.be_base_url}에서 상품 목록 조회 중...")
        products = eligible_products(fetch_all_products(client, args.be_base_url, args.page_size))
        print(f"  대상 {len(products)}개 상품(비공개/판매완료 제외)")

        if args.dry_run:
            for product in products:
                print(f"  product_id={product['id']}")
            print("[backfill] --dry-run: 임베딩을 계산하지 않았다.")
            return

        print(f"[backfill] 세그멘터 로딩 중... (backend={args.backend})")
        embedding_store.init_schema()
        segmenter = build_segmenter(args.backend)

        succeeded, skipped = 0, 0
        for product in products:
            product_id = product["id"]
            try:
                detail = fetch_product_detail(client, args.be_base_url, product_id)
            except httpx.HTTPError as exc:
                print(f"[backfill] product_id={product_id} 상세 조회 실패: {exc}")
                skipped += 1
                continue

            image_urls = [img["url"] for img in detail.get("images", [])]
            if not image_urls:
                print(f"[backfill] product_id={product_id} 등록된 이미지 없음, 스킵")
                skipped += 1
                continue

            if backfill_one(segmenter, product_id, image_urls, detail.get("categoryId")):
                succeeded += 1
                print(f"[backfill] product_id={product_id} 임베딩 저장 완료")
            else:
                skipped += 1
                print(f"[backfill] product_id={product_id} 옷을 찾지 못해 스킵")

        print(f"[backfill] 완료 — 저장 {succeeded}건, 스킵 {skipped}건")


if __name__ == "__main__":
    main()
