"""3-depth 상품 카테고리 taxonomy: 성별(depth1) x 대분류(depth2) x 소분류(depth3).

`AI/validation/CLASS/product-info-check/taxonomy.py`(검증 스파이크)를 프로덕션으로 승격한
버전이다 — ID 매핑 공식과 "ID 하드코딩 금지" 원칙은 그대로 가져오고, `garment_measurement/
contracts.py`·`sam3/contracts.py` 관례에 맞춰 문자열 튜플 대신 `str, Enum`으로 바꿨다.

**이 스파이크는 성별 축을 분류하지 않는다.** 사용자 결정(2026-08-01 채팅): 성별은 등록
폼에서 사용자가 직접 고른다. 분류기는 `Subcategory`까지만 예측하고, 최종
`categoryId = f(Gender, Subcategory)` 조합은 BE/폼 통합 단계(이 모듈 밖)에서 이뤄진다.

**ID를 하드코딩하지 않는다.** 아래 ID는 "seed 데이터가 성별 → 대분류 → 소분류 순으로
auto-increment 삽입된다"는 전제로 역산한 값이다(사용자 확정, 2026-08-01). 실제 seed.sql은
이 저장소에 아직 커밋돼 있지 않다(BE/docs/db, BE/src 전체 확인함 — 없음, 2026-08-02 재확인).
BE가 seed 순서를 바꾸거나 소분류를 추가하면 `MAJOR_CATEGORIES`/`SUBCATEGORIES`의 순서만
그대로 대조해서 고치면 된다 — 모델은 절대 ID를 직접 출력하지 않고 항상
(gender, subcategory) 쌍을 출력한다.

설계: `.claude/plans/ai/CH012-~2.MD`
"""

from __future__ import annotations

from enum import Enum

TAXONOMY_VERSION = "v1-chat-confirmed-2026-08-01"


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


class Subcategory(str, Enum):
    """depth 3(소분류) — 대분류별 순서 고정. 총 30종."""

    # OUTER
    jacket = "JACKET"
    coat = "COAT"
    cardigan = "CARDIGAN"
    vest = "VEST"
    hoodie_zip_up = "HOODIE_ZIP_UP"
    # TOP
    t_shirt = "T_SHIRT"
    shirt = "SHIRT"
    knit = "KNIT"
    hoodie = "HOODIE"
    sweatshirt = "SWEATSHIRT"
    # BOTTOM
    denim = "DENIM"
    slacks = "SLACKS"
    cargo_pants = "CARGO_PANTS"
    skirt = "SKIRT"
    shorts = "SHORTS"
    # SHOES
    sneakers = "SNEAKERS"
    boots = "BOOTS"
    loafer = "LOAFER"
    sandals = "SANDALS"
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


# depth2 -> depth3 순서 고정(ID 계산 공식이 이 순서에 의존한다).
SUBCATEGORIES: dict[MajorCategory, tuple[Subcategory, ...]] = {
    MajorCategory.outer: (
        Subcategory.jacket,
        Subcategory.coat,
        Subcategory.cardigan,
        Subcategory.vest,
        Subcategory.hoodie_zip_up,
    ),
    MajorCategory.top: (
        Subcategory.t_shirt,
        Subcategory.shirt,
        Subcategory.knit,
        Subcategory.hoodie,
        Subcategory.sweatshirt,
    ),
    MajorCategory.bottom: (
        Subcategory.denim,
        Subcategory.slacks,
        Subcategory.cargo_pants,
        Subcategory.skirt,
        Subcategory.shorts,
    ),
    MajorCategory.shoes: (
        Subcategory.sneakers,
        Subcategory.boots,
        Subcategory.loafer,
        Subcategory.sandals,
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
}

# 소분류 30-way 분류의 고정 라벨 순서 — 대분류 나열 순 -> 대분류 내부 나열 순.
ALL_SUBCATEGORIES: tuple[Subcategory, ...] = tuple(
    code for major in MajorCategory for code in SUBCATEGORIES[major]
)

_SUBCATEGORY_TO_MAJOR: dict[Subcategory, MajorCategory] = {
    code: major for major in MajorCategory for code in SUBCATEGORIES[major]
}


def major_of(subcategory: Subcategory) -> MajorCategory:
    """소분류가 속한 대분류를 반환한다."""
    return _SUBCATEGORY_TO_MAJOR[subcategory]


# API 응답의 "path" 필드(예: ["상의", "니트", "카디건"])에 쓰는 한글 표시 라벨.
KR_MAJOR_LABELS: dict[MajorCategory, str] = {
    MajorCategory.outer: "아우터",
    MajorCategory.top: "상의",
    MajorCategory.bottom: "하의",
    MajorCategory.shoes: "신발",
    MajorCategory.bag: "가방",
    MajorCategory.accessory: "액세서리",
}

KR_SUBCATEGORY_LABELS: dict[Subcategory, str] = {
    Subcategory.jacket: "자켓",
    Subcategory.coat: "코트",
    Subcategory.cardigan: "가디건",
    Subcategory.vest: "베스트",
    Subcategory.hoodie_zip_up: "후드 집업",
    Subcategory.t_shirt: "티셔츠",
    Subcategory.shirt: "셔츠",
    Subcategory.knit: "니트",
    Subcategory.hoodie: "후드티",
    Subcategory.sweatshirt: "맨투맨",
    Subcategory.denim: "청바지",
    Subcategory.slacks: "슬랙스",
    Subcategory.cargo_pants: "카고 팬츠",
    Subcategory.skirt: "치마",
    Subcategory.shorts: "반바지",
    Subcategory.sneakers: "스니커즈",
    Subcategory.boots: "부츠",
    Subcategory.loafer: "로퍼",
    Subcategory.sandals: "샌들",
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
}

assert set(KR_SUBCATEGORY_LABELS) == set(ALL_SUBCATEGORIES)
assert set(KR_MAJOR_LABELS) == set(MajorCategory)


def category_path(subcategory: Subcategory) -> list[str]:
    """API 응답 `path` 필드용 — [대분류 한글, 소분류 한글]."""
    major = major_of(subcategory)
    return [KR_MAJOR_LABELS[major], KR_SUBCATEGORY_LABELS[subcategory]]


def _build_category_id_map() -> dict[tuple[Gender, Subcategory], int]:
    """(gender, subcategory) -> categoryId.

    사용자 확정 예시로 검산: JACKET = MEN 22 / WOMEN 52 / UNISEX 82,
    SUNGLASSES = MEN 51 / WOMEN 81 / UNISEX 111 (아래 공식으로 둘 다 재현됨).
    """
    genders = tuple(Gender)
    block_size = len(ALL_SUBCATEGORIES)  # 30
    base_id = 22  # 성별/대분류 자체 행(3+6=9개)이 먼저 insert된다는 전제의 오프셋
    mapping: dict[tuple[Gender, Subcategory], int] = {}
    for gender_idx, gender in enumerate(genders):
        for sub_idx, subcat in enumerate(ALL_SUBCATEGORIES):
            mapping[(gender, subcat)] = base_id + gender_idx * block_size + sub_idx
    return mapping


CATEGORY_ID_MAP: dict[tuple[Gender, Subcategory], int] = _build_category_id_map()


def category_id(gender: Gender, subcategory: Subcategory) -> int:
    """최종 categoryId. 분류기는 이 함수를 호출하지 않는다(BE/폼 통합 단계 전용, 문서화 목적).

    성별은 사용자가 폼에서 고르므로, 실제 조합은 BE/폼 통합 단계(이 모듈 밖)에서 이뤄진다.
    """
    return CATEGORY_ID_MAP[(gender, subcategory)]
