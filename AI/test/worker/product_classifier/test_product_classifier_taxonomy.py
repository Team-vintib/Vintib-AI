"""product_classifier taxonomy ID 매핑 검증.

사용자 확정 예시(2026-08-01 채팅)로 검산한다: JACKET = MEN 22 / WOMEN 52 / UNISEX 82,
SUNGLASSES = MEN 51 / WOMEN 81 / UNISEX 111. 이 값들이 어긋나면 seed 삽입 순서 전제
(`taxonomy.py` 상단 docstring 참고)가 깨진 것이다."""

from product_classifier.taxonomy import (
    ALL_SUBCATEGORIES,
    CATEGORY_ID_MAP,
    Gender,
    MajorCategory,
    Subcategory,
    category_id,
    category_path,
    major_of,
)


def test_total_subcategory_count_is_30():
    assert len(ALL_SUBCATEGORIES) == 30
    assert len(set(ALL_SUBCATEGORIES)) == 30  # 중복 없음


def test_category_id_map_covers_all_gender_subcategory_pairs():
    assert len(CATEGORY_ID_MAP) == len(Gender) * len(ALL_SUBCATEGORIES)


def test_jacket_ids_match_user_confirmed_values():
    assert category_id(Gender.men, Subcategory.jacket) == 22
    assert category_id(Gender.women, Subcategory.jacket) == 52
    assert category_id(Gender.unisex, Subcategory.jacket) == 82


def test_sunglasses_ids_match_user_confirmed_values():
    assert category_id(Gender.men, Subcategory.sunglasses) == 51
    assert category_id(Gender.women, Subcategory.sunglasses) == 81
    assert category_id(Gender.unisex, Subcategory.sunglasses) == 111


def test_major_of_resolves_correctly():
    assert major_of(Subcategory.denim) == MajorCategory.bottom
    assert major_of(Subcategory.sunglasses) == MajorCategory.accessory


def test_category_path_has_major_then_subcategory_label():
    path = category_path(Subcategory.cardigan)
    assert path == ["아우터", "가디건"]
