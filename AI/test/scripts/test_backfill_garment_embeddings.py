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
    category_value,
    eligible_products,
    fetch_all_products,
    fetch_product_detail,
    has_existing_embedding,
)


class TestCategoryValue:
    """CH024 Q4 — BE categoryId를 taxonomy로 변환하지 않고 그대로(문자열) 쓴다.

    실사용 경로(`app/gateway/router.py`)와 값 체계를 통일하기 위해서다 — 예전엔 이 스크립트만
    `product_classifier.taxonomy`로 역산한 Subcategory 문자열을 저장해, 실사용 경로가 저장하던
    품질검수 `GarmentCategory`와 같은 컬럼에 서로 다른 체계가 섞이는 버그가 있었다.
    """

    def test_returns_id_as_string(self):
        assert category_value(24) == "24"

    def test_none_id_returns_none(self):
        assert category_value(None) is None


class TestHasExistingEmbedding:
    """주기 실행 시 이미 임베딩 있는 상품을 재추론하지 않기 위한 판단(CH034 v2)."""

    def test_true_when_embedding_record_exists(self, monkeypatch):
        monkeypatch.setattr(
            backfill.embedding_store, "fetch_garment_embedding", lambda product_id: object()
        )
        assert has_existing_embedding(1) is True

    def test_false_when_no_embedding_record(self, monkeypatch):
        monkeypatch.setattr(
            backfill.embedding_store, "fetch_garment_embedding", lambda product_id: None
        )
        assert has_existing_embedding(1) is False


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
                "category": "24",
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
