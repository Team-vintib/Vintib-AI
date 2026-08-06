"""product_classifier taxonomy ID 매핑 검증.

**BE가 확정한 실제 시드 표**(`BE/docs/db/category-taxonomy.md`)의 값으로 검산한다 —
2026-08-03 이전에는 시드가 커밋되기 전이라 역산 공식(JACKET = MEN 22 / WOMEN 52 /
UNISEX 82)으로 추정하고 있었는데, 실제 표가 나오면서 전부 바뀌었다(JACKET = 24/57/92).

여기서 고정하려는 건 **성별별 소분류 개수가 다른 비균등 블록을 제대로 재현하는가**다.
남성엔 원피스/점프슈트가 없어서(남 33 / 여 35 / 공용 35) 예전의 균등 블록 공식
(`base + gender_idx * 30 + sub_idx`)은 조용히 틀린 ID를 만든다.
"""

import pytest
from product_classifier.taxonomy import (
    ALL_SUBCATEGORIES,
    CATEGORY_ID_MAP,
    MAJOR_CATEGORY_ID_MAP,
    Gender,
    MajorCategory,
    Subcategory,
    category_id,
    category_path,
    major_category_id,
    major_of,
)


def test_total_subcategory_count_is_35():
    assert len(ALL_SUBCATEGORIES) == 35
    assert len(set(ALL_SUBCATEGORIES)) == 35  # 중복 없음


def test_id_maps_match_seed_row_counts():
    """시드 표 기준 depth2 20행 / depth3 103행."""
    assert len(MAJOR_CATEGORY_ID_MAP) == 20
    assert len(CATEGORY_ID_MAP) == 103


def test_men_have_no_dress_or_jumpsuit():
    """비균등 블록의 근원 — 이게 깨지면 뒤따르는 ID가 전부 밀린다."""
    assert (Gender.men, Subcategory.dress) not in CATEGORY_ID_MAP
    assert (Gender.men, Subcategory.jumpsuit) not in CATEGORY_ID_MAP
    assert (Gender.men, MajorCategory.dress_jumpsuit) not in MAJOR_CATEGORY_ID_MAP
    with pytest.raises(KeyError):
        category_id(Gender.men, Subcategory.dress)


@pytest.mark.parametrize(
    "gender,major,expected",
    [
        (Gender.men, MajorCategory.outer, 4),
        (Gender.men, MajorCategory.accessory, 9),
        (Gender.women, MajorCategory.outer, 10),
        (Gender.women, MajorCategory.dress_jumpsuit, 16),
        (Gender.unisex, MajorCategory.outer, 17),
        (Gender.unisex, MajorCategory.dress_jumpsuit, 23),
    ],
)
def test_major_ids_match_seed_table(gender, major, expected):
    assert major_category_id(gender, major) == expected


@pytest.mark.parametrize(
    "gender,subcategory,expected",
    [
        # 각 성별 블록의 첫 행과 마지막 행 — 경계가 맞으면 사이도 맞는다.
        (Gender.men, Subcategory.jacket, 24),
        (Gender.men, Subcategory.sunglasses, 56),
        (Gender.women, Subcategory.jacket, 57),
        (Gender.women, Subcategory.jumpsuit, 91),
        (Gender.unisex, Subcategory.jacket, 92),
        (Gender.unisex, Subcategory.jumpsuit, 126),
        # 문서 본문에 개별로 적힌 값들
        (Gender.men, Subcategory.tshirt, 29),
        (Gender.women, Subcategory.tshirt, 62),
        (Gender.unisex, Subcategory.tshirt, 97),
        (Gender.women, Subcategory.dress, 90),
        (Gender.unisex, Subcategory.dress, 125),
    ],
)
def test_subcategory_ids_match_seed_table(gender, subcategory, expected):
    assert category_id(gender, subcategory) == expected


def test_ids_are_contiguous_and_unique():
    """시드가 auto-increment로 삽입된다는 전제 — 구멍이나 중복이 있으면 전제가 깨진 것이다."""
    all_ids = sorted(MAJOR_CATEGORY_ID_MAP.values()) + sorted(CATEGORY_ID_MAP.values())
    assert all_ids == list(range(4, 127))


def test_major_of_resolves_correctly():
    assert major_of(Subcategory.denim) == MajorCategory.bottom
    assert major_of(Subcategory.sunglasses) == MajorCategory.accessory
    assert major_of(Subcategory.dress) == MajorCategory.dress_jumpsuit


def test_category_path_has_major_then_subcategory_label():
    path = category_path(Subcategory.cardigan)
    assert path == ["아우터", "가디건"]
    assert category_path(Subcategory.dress) == ["원피스 및 점프슈트", "원피스"]
