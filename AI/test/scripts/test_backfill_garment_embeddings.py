"""백필 스크립트(`scripts/backfill_garment_embeddings.py`) 테스트.

BE 네트워크 호출은 `httpx.MockTransport`로 흉내낸다. `backfill_one()`은 실제 SAM3/CLIP
없이도 검증할 수 있다 — 세그멘터를 가짜로 주고 `embed_garment()`/`save_garment_embedding()`
만 monkeypatch하면 제어 흐름(여러 이미지 중 첫 성공만 씀, 못 찾으면 스킵 등)을 그대로 볼 수
있다. 실제 모델 정확도는 로컬 GPU 환경에서 수동 검증한다.
"""

import httpx

from scripts import backfill_garment_embeddings as backfill
from scripts.backfill_garment_embeddings import (
    backfill_one,
    eligible_products,
    fetch_all_products,
    fetch_product_detail,
    subcategory_value,
)


class TestSubcategoryValue:
    def test_maps_known_id_to_subcategory(self):
        # taxonomy.CATEGORY_ID_MAP[(Gender.men, Subcategory.jacket)] == 24 (taxonomy.py 검산값)
        assert subcategory_value(24) == "JACKET"

    def test_bag_and_dress_ids_also_map(self):
        # 가방/원피스도 taxonomy.py엔 있다 — 품질검수 GarmentCategory(6종)와 달리 스킵 대상이 아니다.
        # taxonomy 검산값: (women, jumpsuit) == 91.
        assert subcategory_value(91) == "JUMPSUIT"

    def test_none_id_returns_none(self):
        assert subcategory_value(None) is None

    def test_unknown_id_returns_none(self):
        assert subcategory_value(999999) is None


class TestEligibleProducts:
    def test_keeps_visible_statuses_only(self):
        products = [
            {"id": 1, "saleStatus": "ON_SALE"},
            {"id": 2, "saleStatus": "SOLD"},
            {"id": 3, "saleStatus": "AUCTION_SCHEDULED"},
            {"id": 4, "saleStatus": "DRAFT"},
        ]
        assert [p["id"] for p in eligible_products(products)] == [1, 3]


def _paged_response(content, page, has_next):
    return httpx.Response(
        200,
        json={
            "success": True,
            "data": {
                "content": content,
                "page": page,
                "size": 100,
                "totalElements": 0,
                "totalPages": 0,
                "hasNext": has_next,
            },
        },
    )


def test_fetch_all_products_paginates_until_no_next():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        calls.append(page)
        if page == 0:
            return _paged_response([{"id": 1}], page=0, has_next=True)
        return _paged_response([{"id": 2}], page=1, has_next=False)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    products = fetch_all_products(client, "http://be", page_size=1)
    assert [p["id"] for p in products] == [1, 2]
    assert calls == [0, 1]


def test_fetch_product_detail_unwraps_data_envelope():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/products/42"
        return httpx.Response(
            200, json={"success": True, "data": {"id": 42, "categoryName": "니트"}}
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    detail = fetch_product_detail(client, "http://be", 42)
    assert detail == {"id": 42, "categoryName": "니트"}


class _FakeResult:
    def __init__(self, garment_crop):
        self.garment_crop = garment_crop


class _FakeSegmenter:
    """image_index -> crop(또는 None/예외)을 미리 정해 둔 스텁."""

    def __init__(self, crops_by_index: dict[int, object]):
        self._crops_by_index = crops_by_index
        self.segmented_indices: list[int] = []

    def segment(self, target, image_index):
        self.segmented_indices.append(image_index)
        crop = self._crops_by_index.get(image_index, None)
        if crop is backfill.ImageFetchFailed:
            raise backfill.ImageFetchFailed(f"이미지 {image_index} 실패")
        return _FakeResult(crop)


class TestBackfillOne:
    def test_saves_embedding_using_first_successful_crop(self, monkeypatch):
        segmenter = _FakeSegmenter({0: None, 1: "crop-1"})
        monkeypatch.setattr(backfill, "embed_garment", lambda crop: [0.1, 0.2])
        saved = []
        monkeypatch.setattr(
            backfill.embedding_store,
            "save_garment_embedding",
            lambda **kwargs: saved.append(kwargs),
        )

        ok = backfill_one(segmenter, 1, ["https://x/0.jpg", "https://x/1.jpg"], category_id=24)

        assert ok is True
        assert segmenter.segmented_indices == [0, 1]  # 0번은 크롭 없어 1번까지 진행
        assert saved == [
            {
                "product_id": 1,
                "embedding": [0.1, 0.2],
                "model_id": backfill.EMBEDDING_MODEL_ID,
                "category": "JACKET",
            }
        ]

    def test_returns_false_when_no_image_has_a_garment(self, monkeypatch):
        segmenter = _FakeSegmenter({0: None, 1: None})
        saved = []
        monkeypatch.setattr(
            backfill.embedding_store,
            "save_garment_embedding",
            lambda **kwargs: saved.append(kwargs),
        )

        ok = backfill_one(segmenter, 1, ["https://x/0.jpg", "https://x/1.jpg"], category_id=24)

        assert ok is False
        assert saved == []

    def test_image_fetch_failure_tries_next_image(self, monkeypatch):
        segmenter = _FakeSegmenter({0: backfill.ImageFetchFailed, 1: "crop-1"})
        monkeypatch.setattr(backfill, "embed_garment", lambda crop: [0.3])
        saved = []
        monkeypatch.setattr(
            backfill.embedding_store,
            "save_garment_embedding",
            lambda **kwargs: saved.append(kwargs),
        )

        ok = backfill_one(segmenter, 1, ["https://x/0.jpg", "https://x/1.jpg"], category_id=None)

        assert ok is True
        assert saved[0]["category"] is None

    def test_embedding_not_ready_returns_false_without_saving(self, monkeypatch):
        segmenter = _FakeSegmenter({0: "crop-0"})

        def _explode(crop):
            raise backfill.GarmentEmbeddingNotReady("torch 없음")

        monkeypatch.setattr(backfill, "embed_garment", _explode)
        saved = []
        monkeypatch.setattr(
            backfill.embedding_store,
            "save_garment_embedding",
            lambda **kwargs: saved.append(kwargs),
        )

        ok = backfill_one(segmenter, 1, ["https://x/0.jpg"], category_id=24)

        assert ok is False
        assert saved == []
