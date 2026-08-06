"""`aihub_seed_pricing_corpus.py`의 순수 함수 테스트.

임베딩/체크포인트 로딩은 torch가 필요해 CI에서 못 돈다. 여기서 고정하는 건 그 앞뒤
순수 로직 — 가격 배정의 결정성과 카테고리 기준가 테이블의 유효성이다.
"""

from __future__ import annotations

import aihub_dataset
import aihub_seed_pricing_corpus as seed


def test_synthetic_price_is_deterministic_for_same_input():
    first = seed.synthetic_price("JACKET", "some/image.jpg")
    second = seed.synthetic_price("JACKET", "some/image.jpg")
    assert first == second


def test_synthetic_price_differs_by_image_path():
    """같은 카테고리라도 이미지가 다르면 가격이 갈려야 한다(전부 동일가면 검색 결과가
    가짜 티가 너무 난다)."""
    a = seed.synthetic_price("JACKET", "a.jpg")
    b = seed.synthetic_price("JACKET", "b.jpg")
    assert a != b


def test_synthetic_price_is_positive_for_unknown_category():
    """기준가 테이블에 없는 카테고리도 기본값으로 양수 가격을 낸다."""
    assert seed.synthetic_price("어떤미등록카테고리", "x.jpg") > 0


def test_category_base_price_keys_are_valid_taxonomy_labels():
    """오타로 존재하지 않는 카테고리에 기준가를 매겨두면 그 카테고리는 항상 기본값으로만
    가격이 매겨진다 — 조용히 새는 걸 막는다."""
    assert set(seed._CATEGORY_BASE_PRICE_KRW) <= set(aihub_dataset.ALL_SUBCATEGORIES)


def test_build_meta_row_shape():
    row = seed.build_meta_row("JACKET", "some/image.jpg")
    assert row["aihub_category"] == "JACKET"
    assert row["data_source"] == "synthetic_aihub"
    assert isinstance(row["synthetic_price"], int)
    assert row["synthetic_price"] > 0
