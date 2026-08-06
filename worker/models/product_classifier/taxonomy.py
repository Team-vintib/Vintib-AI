"""3-depth 상품 카테고리 taxonomy: 성별(depth1) x 대분류(depth2) x 소분류(depth3).

`AI/validation/CLASS/product-info-check/taxonomy.py`(검증 스파이크)를 프로덕션으로 승격한
버전이다 — 값은 항상 그쪽과 같게 유지하고, `garment_measurement/contracts.py`·
`sam3/contracts.py` 관례에 맞춰 문자열 튜플 대신 `str, Enum`으로 바꾼 것만 다르다.

**2026-08-03: BE가 확정한 실제 시드로 전면 갱신했다**(`BE/docs/db/category-taxonomy.md`,
원본 `BE/src/main/resources/db/seed.sql`). 이전 버전은 시드가 커밋되기 전이라 ID를 역산
공식으로 추정했는데, 이제 실제 표가 있으므로 추정을 버렸다. 바뀐 것:

- 소분류 30 -> **35종**, 대분류 6 -> **7종**(`dress_jumpsuit`, 여성·공용에만 존재)
- 개명: `T_SHIRT`->`TSHIRT`, `HOODIE_ZIP_UP`->`HOOD_ZIPUP`, `SHORTS`->`SHORT_PANTS`,
  `LOAFER`->`DRESS_SHOES`, `SANDALS`->`SANDALS_SLIPPERS`
- 삭제: `VEST` / 추가: `PADDED_JACKET`, `SLEEVELESS`, `JOGGER_PANTS`, `COTTON_PANTS`,
  `DRESS`, `JUMPSUIT`
- **ID 공식 폐기**: 남성엔 원피스/점프슈트가 없어 성별별 소분류 개수가 다르다
  (남 33 / 여 35 / 공용 35). 균등 블록을 가정한 옛 공식은 못 쓴다.

**이 모듈은 성별 축을 분류하지 않는다.** BE 문서의 "사용 방법"은 AI가 성별도 판별하라고
적고 있지만, 2026-08-03에 사용자가 기존 결정(성별은 등록 폼에서 사용자가 직접 선택)을
유지하기로 재확인했다 — 평면 촬영 의류는 원리적으로 성별 판별이 안 되는 경우가 많고
(그래서 UNISEX가 있다), 정답셋에 성별 라벨이 없어 검증 자체가 불가능하다. 분류기는
`Subcategory`까지만 예측하고, ID 조합은 폼에서 받은 성별과 합쳐 이 모듈이 계산한다.

설계: `.claude/plans/ai/CH012-~2.MD`
"""

from __future__ import annotations

from enum import Enum

TAXONOMY_VERSION = "v2-be-seed-2026-08-03"


class Gender(str, Enum):
    """depth 1 — 이 모듈은 분류하지 않는다(사용자가 폼에서 직접 선택). ID 조합용으로만 쓴다."""

    men = "MEN"
    women = "WOMEN"
    unisex = "UNISEX"


class MajorCategory(str, Enum):
    """depth 2(대분류) — ID 계산에 순서가 그대로 쓰이므로 임의로 재배열하지 않는다."""

    outer = "OUTER"
    top = "TOP"
    bottom = "BOTTOM"
    shoes = "SHOES"
    bag = "BAG"
    accessory = "ACCESSORY"
    dress_jumpsuit = "DRESS_JUMPSUIT"


class Subcategory(str, Enum):
    """depth 3(소분류) — 대분류별 순서 고정. 총 35종."""

    # OUTER
    jacket = "JACKET"
    coat = "COAT"
    cardigan = "CARDIGAN"
    padded_jacket = "PADDED_JACKET"
    hood_zipup = "HOOD_ZIPUP"
    # TOP
    tshirt = "TSHIRT"
    shirt = "SHIRT"
    knit = "KNIT"
    hoodie = "HOODIE"
    sweatshirt = "SWEATSHIRT"
    sleeveless = "SLEEVELESS"
    # BOTTOM
    denim = "DENIM"
    slacks = "SLACKS"
    cargo_pants = "CARGO_PANTS"
    skirt = "SKIRT"
    short_pants = "SHORT_PANTS"
    jogger_pants = "JOGGER_PANTS"
    cotton_pants = "COTTON_PANTS"
    # SHOES
    sneakers = "SNEAKERS"
    boots = "BOOTS"
    dress_shoes = "DRESS_SHOES"
    sandals_slippers = "SANDALS_SLIPPERS"
    # BAG
    backpack = "BACKPACK"
    shoulder_bag = "SHOULDER_BAG"
    tote_bag = "TOTE_BAG"
    cross_bag = "CROSS_BAG"
    pouch = "POUCH"
    # ACCESSORY
    hat = "HAT"
    belt = "BELT"
    scarf = "SCARF"
    jewelry = "JEWELRY"
    watch = "WATCH"
    sunglasses = "SUNGLASSES"
    # DRESS_JUMPSUIT (여성·공용 전용)
    dress = "DRESS"
    jumpsuit = "JUMPSUIT"


# depth2 -> depth3 순서 고정(ID 계산이 이 순서에 의존한다).
SUBCATEGORIES: dict[MajorCategory, tuple[Subcategory, ...]] = {
    MajorCategory.outer: (
        Subcategory.jacket,
        Subcategory.coat,
        Subcategory.cardigan,
        Subcategory.padded_jacket,
        Subcategory.hood_zipup,
    ),
    MajorCategory.top: (
        Subcategory.tshirt,
        Subcategory.shirt,
        Subcategory.knit,
        Subcategory.hoodie,
        Subcategory.sweatshirt,
        Subcategory.sleeveless,
    ),
    MajorCategory.bottom: (
        Subcategory.denim,
        Subcategory.slacks,
        Subcategory.cargo_pants,
        Subcategory.skirt,
        Subcategory.short_pants,
        Subcategory.jogger_pants,
        Subcategory.cotton_pants,
    ),
    MajorCategory.shoes: (
        Subcategory.sneakers,
        Subcategory.boots,
        Subcategory.dress_shoes,
        Subcategory.sandals_slippers,
    ),
    MajorCategory.bag: (
        Subcategory.backpack,
        Subcategory.shoulder_bag,
        Subcategory.tote_bag,
        Subcategory.cross_bag,
        Subcategory.pouch,
    ),
    MajorCategory.accessory: (
        Subcategory.hat,
        Subcategory.belt,
        Subcategory.scarf,
        Subcategory.jewelry,
        Subcategory.watch,
        Subcategory.sunglasses,
    ),
    MajorCategory.dress_jumpsuit: (Subcategory.dress, Subcategory.jumpsuit),
}

# 성별별로 **존재하는** 대분류. 남성엔 원피스/점프슈트가 없다 — 순서가 곧 ID 순서다.
_COMMON_MAJORS: tuple[MajorCategory, ...] = (
    MajorCategory.outer,
    MajorCategory.top,
    MajorCategory.bottom,
    MajorCategory.shoes,
    MajorCategory.bag,
    MajorCategory.accessory,
)
MAJORS_BY_GENDER: dict[Gender, tuple[MajorCategory, ...]] = {
    Gender.men: _COMMON_MAJORS,
    Gender.women: _COMMON_MAJORS + (MajorCategory.dress_jumpsuit,),
    Gender.unisex: _COMMON_MAJORS + (MajorCategory.dress_jumpsuit,),
}

ALL_SUBCATEGORIES: tuple[Subcategory, ...] = tuple(
    code for major in MajorCategory for code in SUBCATEGORIES[major]
)
assert len(ALL_SUBCATEGORIES) == 35, len(ALL_SUBCATEGORIES)

_SUBCATEGORY_TO_MAJOR: dict[Subcategory, MajorCategory] = {
    code: major for major in MajorCategory for code in SUBCATEGORIES[major]
}


def major_of(subcategory: Subcategory) -> MajorCategory:
    """소분류가 속한 대분류를 반환한다."""
    return _SUBCATEGORY_TO_MAJOR[subcategory]


# API 응답의 "path" 필드(예: ["상의", "니트"])에 쓰는 한글 표시 라벨. BE 시드의 `name`과 동일.
KR_MAJOR_LABELS: dict[MajorCategory, str] = {
    MajorCategory.outer: "아우터",
    MajorCategory.top: "상의",
    MajorCategory.bottom: "하의",
    MajorCategory.shoes: "신발",
    MajorCategory.bag: "가방",
    MajorCategory.accessory: "액세서리",
    MajorCategory.dress_jumpsuit: "원피스 및 점프슈트",
}

KR_SUBCATEGORY_LABELS: dict[Subcategory, str] = {
    Subcategory.jacket: "자켓",
    Subcategory.coat: "코트",
    Subcategory.cardigan: "가디건",
    Subcategory.padded_jacket: "패딩",
    Subcategory.hood_zipup: "후드집업",
    Subcategory.tshirt: "티셔츠",
    Subcategory.shirt: "셔츠",
    Subcategory.knit: "니트",
    Subcategory.hoodie: "후드티",
    Subcategory.sweatshirt: "맨투맨",
    Subcategory.sleeveless: "민소매",
    Subcategory.denim: "데님",
    Subcategory.slacks: "슬랙스",
    Subcategory.cargo_pants: "카고팬츠",
    Subcategory.skirt: "스커트",
    Subcategory.short_pants: "숏팬츠",
    Subcategory.jogger_pants: "트레이닝/조거",
    Subcategory.cotton_pants: "코튼팬츠",
    Subcategory.sneakers: "스니커즈",
    Subcategory.boots: "부츠",
    Subcategory.dress_shoes: "구두",
    Subcategory.sandals_slippers: "샌들/슬리퍼",
    Subcategory.backpack: "백팩",
    Subcategory.shoulder_bag: "숄더백",
    Subcategory.tote_bag: "토트백",
    Subcategory.cross_bag: "크로스백",
    Subcategory.pouch: "파우치",
    Subcategory.hat: "모자",
    Subcategory.belt: "벨트",
    Subcategory.scarf: "스카프",
    Subcategory.jewelry: "주얼리",
    Subcategory.watch: "시계",
    Subcategory.sunglasses: "선글라스",
    Subcategory.dress: "원피스",
    Subcategory.jumpsuit: "점프슈트",
}

assert set(KR_SUBCATEGORY_LABELS) == set(ALL_SUBCATEGORIES)
assert set(KR_MAJOR_LABELS) == set(MajorCategory)


def category_path(subcategory: Subcategory) -> list[str]:
    """API 응답 `path` 필드용 — [대분류 한글, 소분류 한글]."""
    major = major_of(subcategory)
    return [KR_MAJOR_LABELS[major], KR_SUBCATEGORY_LABELS[subcategory]]


# --------------------------------------------------------------------------
# ID 매핑 — BE 시드 삽입 순서(성별 -> 대분류 -> 소분류)를 그대로 재현한다.
# 아래 assert가 `BE/docs/db/category-taxonomy.md` 표의 실제 값으로 검산한다.
# --------------------------------------------------------------------------
_MAJOR_ID_BASE = 4  # depth2: 4~23 (성별 3개 다음)
_SUBCATEGORY_ID_BASE = 24  # depth3: 24~126 (대분류 20개 다음)

GENDER_ID_MAP: dict[Gender, int] = {gender: i + 1 for i, gender in enumerate(Gender)}


def _build_major_id_map() -> dict[tuple[Gender, MajorCategory], int]:
    mapping: dict[tuple[Gender, MajorCategory], int] = {}
    next_id = _MAJOR_ID_BASE
    for gender in Gender:
        for major in MAJORS_BY_GENDER[gender]:
            mapping[(gender, major)] = next_id
            next_id += 1
    return mapping


def _build_category_id_map() -> dict[tuple[Gender, Subcategory], int]:
    mapping: dict[tuple[Gender, Subcategory], int] = {}
    next_id = _SUBCATEGORY_ID_BASE
    for gender in Gender:
        for major in MAJORS_BY_GENDER[gender]:
            for subcat in SUBCATEGORIES[major]:
                mapping[(gender, subcat)] = next_id
                next_id += 1
    return mapping


MAJOR_CATEGORY_ID_MAP: dict[tuple[Gender, MajorCategory], int] = _build_major_id_map()
CATEGORY_ID_MAP: dict[tuple[Gender, Subcategory], int] = _build_category_id_map()

# 문서 표의 실제 값으로 검산 — 시드 순서가 바뀌면 import 시점에 즉시 터진다.
assert MAJOR_CATEGORY_ID_MAP[(Gender.men, MajorCategory.outer)] == 4
assert MAJOR_CATEGORY_ID_MAP[(Gender.women, MajorCategory.dress_jumpsuit)] == 16
assert MAJOR_CATEGORY_ID_MAP[(Gender.unisex, MajorCategory.dress_jumpsuit)] == 23
assert len(MAJOR_CATEGORY_ID_MAP) == 20
assert CATEGORY_ID_MAP[(Gender.men, Subcategory.jacket)] == 24
assert CATEGORY_ID_MAP[(Gender.men, Subcategory.sunglasses)] == 56
assert CATEGORY_ID_MAP[(Gender.women, Subcategory.tshirt)] == 62
assert CATEGORY_ID_MAP[(Gender.women, Subcategory.jumpsuit)] == 91
assert CATEGORY_ID_MAP[(Gender.unisex, Subcategory.tshirt)] == 97
assert CATEGORY_ID_MAP[(Gender.unisex, Subcategory.jumpsuit)] == 126
assert len(CATEGORY_ID_MAP) == 103
assert (Gender.men, Subcategory.dress) not in CATEGORY_ID_MAP  # 남성엔 원피스가 없다


def major_category_id(gender: Gender, major: MajorCategory) -> int:
    """(성별, 대분류) -> depth2 categoryId. **AI가 BE에 돌려주는 값**.

    성별은 분류기가 아니라 등록 폼에서 온다 — 모듈 docstring 참고.
    남성 + DRESS_JUMPSUIT처럼 존재하지 않는 조합이면 KeyError.
    """
    return MAJOR_CATEGORY_ID_MAP[(gender, major)]


def category_id(gender: Gender, subcategory: Subcategory) -> int:
    """(성별, 소분류) -> depth3 categoryId(최종 `product.category_id`).

    분류기는 이 함수를 호출하지 않는다 — 소분류는 사용자가 FE 드롭다운에서 고른다.
    """
    return CATEGORY_ID_MAP[(gender, subcategory)]
