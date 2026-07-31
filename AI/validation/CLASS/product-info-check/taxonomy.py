"""3-depth 상품 카테고리 taxonomy: 성별(depth1) x 대분류(depth2) x 소분류(depth3).

BE가 채팅으로 확정한 내용(2026-08-01)을 근거로 한다. `.claude/plans/ai/CH012-product-info-classify.md`는
저장소 어디에도 없다(git log/전체 브랜치/stash까지 확인함, 존재하지 않음) — 그래서 이 스파이크는
그 채팅 확정 내용을 설계 근거로 삼는다.

**이 스파이크는 성별 축을 분류 대상으로 다루지 않는다.** 사용자 결정(2026-08-01 채팅):
성별은 등록 폼에서 사용자가 직접 고른다. 최종 `categoryId = f(gender_code, subcategory_code)`
조합 방식은 문서화 차원에서 `category_id()`로 남겨 두지만, 이 스파이크의 분류기(classify.py)는
`subcategory_code`까지만 예측한다.

**ID를 하드코딩하지 않는다.** 아래 ID는 "seed 데이터가 성별 → 대분류 → 소분류 순으로
auto-increment 삽입된다"는 전제로 역산한 값이다(사용자 확정, 2026-08-01). 실제 seed.sql은
이 저장소에 아직 커밋돼 있지 않다(BE/docs/db, BE/src 전체 확인함 — 없음). BE가 seed 순서를
바꾸거나 소분류를 추가하면 아래 상수만 그대로 대조해서 고치면 된다 — 모델은 ID를 직접
출력하지 않고 항상 (gender_code, subcategory_code) 쌍을 출력하고, ID 변환은 최종 소비처
(BE/폼 통합, 이 스파이크 밖)에서 한 번만 한다.
"""

from __future__ import annotations

TAXONOMY_VERSION = "v1-chat-confirmed-2026-08-01"

# depth 1 — 이 스파이크는 분류하지 않는다(사용자가 폼에서 직접 선택). ID 조합용으로만 남겨 둠.
GENDER_CODES: tuple[str, ...] = ("MEN", "WOMEN", "UNISEX")

# depth 2(대분류) — ID 계산에 순서가 그대로 쓰이므로 임의로 재배열하지 않는다.
MAJOR_CATEGORIES: tuple[str, ...] = ("OUTER", "TOP", "BOTTOM", "SHOES", "BAG", "ACCESSORY")

# depth 3(소분류/중분류) — 대분류별 순서 고정. 총 30종.
SUBCATEGORIES: dict[str, tuple[str, ...]] = {
    "OUTER": ("JACKET", "COAT", "CARDIGAN", "VEST", "HOODIE_ZIP_UP"),
    "TOP": ("T_SHIRT", "SHIRT", "KNIT", "HOODIE", "SWEATSHIRT"),
    "BOTTOM": ("DENIM", "SLACKS", "CARGO_PANTS", "SKIRT", "SHORTS"),
    "SHOES": ("SNEAKERS", "BOOTS", "LOAFER", "SANDALS"),
    "BAG": ("BACKPACK", "SHOULDER_BAG", "TOTE_BAG", "CROSS_BAG", "POUCH"),
    "ACCESSORY": ("HAT", "BELT", "SCARF", "JEWELRY", "WATCH", "SUNGLASSES"),
}

# 소분류 30-way 분류(V2a)의 고정 라벨 순서 — 대분류 나열 순 -> 대분류 내부 나열 순.
ALL_SUBCATEGORIES: tuple[str, ...] = tuple(
    code for major in MAJOR_CATEGORIES for code in SUBCATEGORIES[major]
)

_SUBCATEGORY_TO_MAJOR: dict[str, str] = {
    code: major for major in MAJOR_CATEGORIES for code in SUBCATEGORIES[major]
}


def major_of(subcategory_code: str) -> str:
    """소분류 코드가 속한 대분류 코드를 반환한다. 모르는 코드면 KeyError."""
    return _SUBCATEGORY_TO_MAJOR[subcategory_code]


# 사용자가 지정한 혼동쌍(V0 정답셋에 의도적으로 섞고, V2a 혼동행렬에서 실제로 섞이는지 확인).
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

# --------------------------------------------------------------------------
# 라벨 문구 — V2a 프롬프트 템플릿 3종 비교용. zero-shot은 라벨 문구에 민감하므로
# 템플릿마다 다른 함수를 노출한다(classify.py가 PROMPT_TEMPLATES로 순회).
# --------------------------------------------------------------------------
_KR_LABELS: dict[str, str] = {
    "JACKET": "자켓",
    "COAT": "코트",
    "CARDIGAN": "가디건",
    "VEST": "베스트",
    "HOODIE_ZIP_UP": "후드 집업",
    "T_SHIRT": "티셔츠",
    "SHIRT": "셔츠",
    "KNIT": "니트",
    "HOODIE": "후드티",
    "SWEATSHIRT": "맨투맨",
    "DENIM": "청바지",
    "SLACKS": "슬랙스",
    "CARGO_PANTS": "카고 팬츠",
    "SKIRT": "치마",
    "SHORTS": "반바지",
    "SNEAKERS": "스니커즈",
    "BOOTS": "부츠",
    "LOAFER": "로퍼",
    "SANDALS": "샌들",
    "BACKPACK": "백팩",
    "SHOULDER_BAG": "숄더백",
    "TOTE_BAG": "토트백",
    "CROSS_BAG": "크로스백",
    "POUCH": "파우치",
    "HAT": "모자",
    "BELT": "벨트",
    "SCARF": "스카프",
    "JEWELRY": "주얼리",
    "WATCH": "시계",
    "SUNGLASSES": "선글라스",
}

_EN_LABELS: dict[str, str] = {
    "JACKET": "jacket",
    "COAT": "coat",
    "CARDIGAN": "cardigan",
    "VEST": "vest",
    "HOODIE_ZIP_UP": "zip-up hoodie",
    "T_SHIRT": "t-shirt",
    "SHIRT": "shirt",
    "KNIT": "knit sweater",
    "HOODIE": "hoodie",
    "SWEATSHIRT": "sweatshirt",
    "DENIM": "denim jeans",
    "SLACKS": "slacks",
    "CARGO_PANTS": "cargo pants",
    "SKIRT": "skirt",
    "SHORTS": "shorts",
    "SNEAKERS": "sneakers",
    "BOOTS": "boots",
    "LOAFER": "loafers",
    "SANDALS": "sandals",
    "BACKPACK": "backpack",
    "SHOULDER_BAG": "shoulder bag",
    "TOTE_BAG": "tote bag",
    "CROSS_BAG": "crossbody bag",
    "POUCH": "pouch",
    "HAT": "hat",
    "BELT": "belt",
    "SCARF": "scarf",
    "JEWELRY": "jewelry",
    "WATCH": "watch",
    "SUNGLASSES": "sunglasses",
}

assert set(_KR_LABELS) == set(ALL_SUBCATEGORIES)
assert set(_EN_LABELS) == set(ALL_SUBCATEGORIES)


def _kr_plain(code: str) -> str:
    """템플릿 1: 라벨 문구만(예: "니트"). 가장 단순한 zero-shot 프롬프트."""
    return _KR_LABELS[code]


def _en_clip_style(code: str) -> str:
    """템플릿 2: 표준 CLIP 영문 템플릿(예: "a photo of a knit sweater")."""
    return f"a photo of a {_EN_LABELS[code]}"


def _kr_secondhand_flat(code: str) -> str:
    """템플릿 3: 중고 거래 맥락을 명시한 한글 템플릿(예: "바닥에 펼쳐놓고 찍은 중고 니트 사진")."""
    return f"바닥에 펼쳐놓고 찍은 중고 {_KR_LABELS[code]} 사진"


# classify.py가 이 dict를 순회하며 템플릿별 정확도를 비교한다. 키 이름이 evaluate.py 리포트에
# 그대로 노출되므로 바꿀 때는 같이 맞춘다.
PROMPT_TEMPLATES: dict[str, "callable[[str], str]"] = {
    "kr_plain": _kr_plain,
    "en_clip_style": _en_clip_style,
    "kr_secondhand_flat": _kr_secondhand_flat,
}


def _build_category_id_map() -> dict[tuple[str, str], int]:
    """(gender_code, subcategory_code) -> categoryId.

    사용자 확정 예시로 검산: JACKET = MEN 22 / WOMEN 52 / UNISEX 82,
    SUNGLASSES = MEN 51 / WOMEN 81 / UNISEX 111 (아래 공식으로 둘 다 재현됨).
    """
    block_size = len(ALL_SUBCATEGORIES)  # 30
    base_id = 22  # 성별/대분류 자체 행(3+6=9개)이 먼저 insert된다는 전제의 오프셋
    mapping: dict[tuple[str, str], int] = {}
    for gender_idx, gender in enumerate(GENDER_CODES):
        for sub_idx, subcat in enumerate(ALL_SUBCATEGORIES):
            mapping[(gender, subcat)] = base_id + gender_idx * block_size + sub_idx
    return mapping


CATEGORY_ID_MAP: dict[tuple[str, str], int] = _build_category_id_map()


def category_id(gender_code: str, subcategory_code: str) -> int:
    """최종 categoryId. 이 스파이크의 분류기는 이 함수를 호출하지 않는다(문서화/데모 용도).

    성별은 사용자가 폼에서 고르므로, 실제 조합은 BE/폼 통합 단계(이 스파이크 밖)에서 이뤄진다.
    """
    return CATEGORY_ID_MAP[(gender_code, subcategory_code)]
