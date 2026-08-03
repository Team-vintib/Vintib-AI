"""크롤러가 쓰는 라벨 정의 — CH012 스파이크 정의의 **미러**.

정본은 `AI/validation/CLASS/product-info-check/`의 `taxonomy.py`(카테고리)와 `color.py`
(팔레트)다. 다만 그 파일들은 다른 브랜치(`origin/feat/211-product-info-model`)에만 있어서
이 브랜치에서 import할 수 없다 — 브리핑(`VLM_DATA_COLLECTION_BRIEF.md` §6)이 "그대로 가져가도
된다"고 허용한 범위 안에서, **크롤러가 실제로 쓰는 부분만** 복사해 둔다.

두 브랜치가 합쳐지면 이 파일은 지우고 `product-info-check` 쪽을 import하는 게 맞다. 그때까지는
아래 값을 바꿀 때 정본도 같이 고칠 것 — 특히 `TAXONOMY_VERSION`이 다르면 수집한 JSONL이 어느
taxonomy 기준인지 추적이 안 된다.

이 파일은 표준 라이브러리만 쓴다(CI에서 그대로 import된다).
"""

from __future__ import annotations

# 정본(taxonomy.py)과 같은 값이어야 한다. 수집 산출물 JSONL 각 행에 기록된다.
TAXONOMY_VERSION = "v1-chat-confirmed-2026-08-01"

# depth 2(대분류) — 순서 고정.
MAJOR_CATEGORIES: tuple[str, ...] = ("OUTER", "TOP", "BOTTOM", "SHOES", "BAG", "ACCESSORY")

# depth 3(소분류) — 대분류별 순서 고정. 총 30종. 모델이 예측하는 유일한 축이다.
SUBCATEGORIES: dict[str, tuple[str, ...]] = {
    "OUTER": ("JACKET", "COAT", "CARDIGAN", "VEST", "HOODIE_ZIP_UP"),
    "TOP": ("T_SHIRT", "SHIRT", "KNIT", "HOODIE", "SWEATSHIRT"),
    "BOTTOM": ("DENIM", "SLACKS", "CARGO_PANTS", "SKIRT", "SHORTS"),
    "SHOES": ("SNEAKERS", "BOOTS", "LOAFER", "SANDALS"),
    "BAG": ("BACKPACK", "SHOULDER_BAG", "TOTE_BAG", "CROSS_BAG", "POUCH"),
    "ACCESSORY": ("HAT", "BELT", "SCARF", "JEWELRY", "WATCH", "SUNGLASSES"),
}

ALL_SUBCATEGORIES: tuple[str, ...] = tuple(
    code for major in MAJOR_CATEGORIES for code in SUBCATEGORIES[major]
)

_SUBCATEGORY_TO_MAJOR: dict[str, str] = {
    code: major for major in MAJOR_CATEGORIES for code in SUBCATEGORIES[major]
}


def major_of(subcategory_code: str) -> str:
    """소분류 코드가 속한 대분류 코드. 모르는 코드면 KeyError."""
    return _SUBCATEGORY_TO_MAJOR[subcategory_code]


def is_valid_subcategory(code: str) -> bool:
    return code in _SUBCATEGORY_TO_MAJOR


# 브리핑 §4.3 — 수집 데이터에 의도적으로 다수 포함해야 하는 혼동쌍. 커버리지 리포트가
# 이 쌍들의 수집 건수를 따로 보여준다.
CONFUSION_PAIRS: tuple[tuple[str, str], ...] = (
    ("JACKET", "COAT"),
    ("CARDIGAN", "HOODIE_ZIP_UP"),
    ("HOODIE", "HOODIE_ZIP_UP"),
    ("KNIT", "SWEATSHIRT"),
    ("T_SHIRT", "SWEATSHIRT"),
    ("SLACKS", "CARGO_PANTS"),
    ("SHOULDER_BAG", "CROSS_BAG"),
    ("SHOULDER_BAG", "TOTE_BAG"),
    ("CROSS_BAG", "TOTE_BAG"),
)

# 색상 팔레트 코드 — color.py의 PALETTE 키 집합과 같아야 한다(hex는 크롤러가 안 쓴다).
# **잠정값**: BE/FE 확정 전이라 바뀔 수 있다(브리핑 §1).
# 13종 + MIXED로 사용자 확정(2026-08-03). 근거·은퇴 코드 매핑은
# `../product-info-check/color.py`의 PALETTE 주석 참고 — 값은 항상 그쪽과 일치시킨다.
PALETTE_CODES: tuple[str, ...] = (
    "BLACK",
    "WHITE",
    "GRAY",
    "RED",
    "ORANGE",
    "PINK",
    "YELLOW",
    "BROWN",
    "GREEN",
    "BLUE",
    "PURPLE",
    "BEIGE",
    "NAVY",
)

MIXED_LABEL = "MIXED"

# 브리핑 §4.1 — 촬영유형. 크롤링만으로는 판별할 수 없어서 사이트 스펙의 기본값 선언이나
# 사후 라벨링으로 채운다.
SHOT_TYPES: tuple[str, ...] = ("worn", "flat", "hanging")
