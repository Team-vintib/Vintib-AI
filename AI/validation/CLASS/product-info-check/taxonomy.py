"""3-depth 상품 카테고리 taxonomy: 성별(depth1) x 대분류(depth2) x 소분류(depth3).

**근거는 BE가 확정한 실제 시드 데이터다**(`BE/docs/db/category-taxonomy.md`, 원본은
`BE/src/main/resources/db/seed.sql`). 2026-08-03에 그 문서 기준으로 전면 갱신했다 —
이전 버전은 시드가 커밋되기 전이라 ID를 역산 공식으로 추정하고 있었는데, 이제 실제 표가
있으므로 **추정을 버리고 표를 그대로 상수화한다**(사용자 확정).

## 이전 버전(소분류 30종)에서 바뀐 것

- 소분류 30 -> **35종**, 대분류 6 -> **7종**(`DRESS_JUMPSUIT` 추가, 여성·공용에만 존재)
- 개명: `T_SHIRT`->`TSHIRT`, `HOODIE_ZIP_UP`->`HOOD_ZIPUP`, `SHORTS`->`SHORT_PANTS`,
  `LOAFER`->`DRESS_SHOES`, `SANDALS`->`SANDALS_SLIPPERS`
- 삭제: `VEST`(아우터) — 시드에 없다
- 추가: `PADDED_JACKET`, `SLEEVELESS`, `JOGGER_PANTS`, `COTTON_PANTS`, `DRESS`, `JUMPSUIT`
- **ID 공식 폐기**: 예전엔 `base + gender_idx * 30 + sub_idx`로 균등 블록을 가정했는데,
  남성엔 원피스/점프슈트가 없어 성별별 소분류 개수가 다르다(남 33 / 여 35 / 공용 35).
  아래 `_build_*_id_map()`이 "성별 순 -> 대분류 순 -> 소분류 순" 삽입 순서를 그대로
  재현하고, 문서에 적힌 실제 값으로 assert해 검산한다.

## 성별 축은 이 스파이크의 분류 대상이 아니다

`BE/docs/db/category-taxonomy.md`의 "사용 방법"은 AI가 성별도 판별하라고 적고 있지만,
**성별은 사용자가 등록 폼에서 직접 고르는 것으로 유지한다**(2026-08-01 확정을 2026-08-03에
재확인). 근거: (a) 평면 촬영된 티셔츠·데님은 원리적으로 남/여 구분이 안 되는 경우가 많다
(그래서 UNISEX가 존재한다), (b) 정답셋에 성별 라벨이 0건이라 검증할 방법 자체가 없다.
FE/BE 요청은 `.claude/requests/` 참고.

그래서 파이프라인은 이렇게 된다:

    분류기 -> subcategory_code (35-way)          <- 이 모듈이 검증하는 부분
          -> major_of(subcategory_code)          <- 대분류 코드로 역산(실측 1.00)
          -> major_category_id(gender, major)    <- 폼에서 받은 성별과 조합해 depth2 id
"""

from __future__ import annotations

TAXONOMY_VERSION = "v2-be-seed-2026-08-03"

# depth 1. ID는 1~3(삽입 순서 그대로).
GENDER_CODES: tuple[str, ...] = ("MEN", "WOMEN", "UNISEX")

# depth 2(대분류) 코드 — 성별과 무관한 코드 집합. 실제 행은 성별마다 따로 있다(id 4~23).
MAJOR_CATEGORIES: tuple[str, ...] = (
    "OUTER",
    "TOP",
    "BOTTOM",
    "SHOES",
    "BAG",
    "ACCESSORY",
    "DRESS_JUMPSUIT",
)

# 성별별로 존재하는 대분류. **남성엔 원피스/점프슈트가 없다** — 순서가 곧 ID 순서다.
MAJORS_BY_GENDER: dict[str, tuple[str, ...]] = {
    "MEN": ("OUTER", "TOP", "BOTTOM", "SHOES", "BAG", "ACCESSORY"),
    "WOMEN": ("OUTER", "TOP", "BOTTOM", "SHOES", "BAG", "ACCESSORY", "DRESS_JUMPSUIT"),
    "UNISEX": ("OUTER", "TOP", "BOTTOM", "SHOES", "BAG", "ACCESSORY", "DRESS_JUMPSUIT"),
}

# depth 3(소분류) — 대분류별 순서 고정(ID 순서와 동일). 총 35종.
SUBCATEGORIES: dict[str, tuple[str, ...]] = {
    "OUTER": ("JACKET", "COAT", "CARDIGAN", "PADDED_JACKET", "HOOD_ZIPUP"),
    "TOP": ("TSHIRT", "SHIRT", "KNIT", "HOODIE", "SWEATSHIRT", "SLEEVELESS"),
    "BOTTOM": (
        "DENIM",
        "SLACKS",
        "CARGO_PANTS",
        "SKIRT",
        "SHORT_PANTS",
        "JOGGER_PANTS",
        "COTTON_PANTS",
    ),
    "SHOES": ("SNEAKERS", "BOOTS", "DRESS_SHOES", "SANDALS_SLIPPERS"),
    "BAG": ("BACKPACK", "SHOULDER_BAG", "TOTE_BAG", "CROSS_BAG", "POUCH"),
    "ACCESSORY": ("HAT", "BELT", "SCARF", "JEWELRY", "WATCH", "SUNGLASSES"),
    "DRESS_JUMPSUIT": ("DRESS", "JUMPSUIT"),
}

# 소분류 35-way 분류의 고정 라벨 순서 — 대분류 나열 순 -> 대분류 내부 나열 순.
ALL_SUBCATEGORIES: tuple[str, ...] = tuple(
    code for major in MAJOR_CATEGORIES for code in SUBCATEGORIES[major]
)
assert len(ALL_SUBCATEGORIES) == 35, len(ALL_SUBCATEGORIES)

_SUBCATEGORY_TO_MAJOR: dict[str, str] = {
    code: major for major in MAJOR_CATEGORIES for code in SUBCATEGORIES[major]
}


def major_of(subcategory_code: str) -> str:
    """소분류 코드가 속한 대분류 코드를 반환한다. 모르는 코드면 KeyError."""
    return _SUBCATEGORY_TO_MAJOR[subcategory_code]


# 혼동쌍 — V2a 혼동행렬에서 실제로 섞이는지 확인하는 대상.
# `(TSHIRT, SHIRT)`는 실측으로 발견해 추가했다(`REPORT.md` §10) — 원래 목록엔 없었는데
# CLIP 오답 5건 중 3건이 이 쌍이었다. 하의 3종 신설(JOGGER/COTTON)로 생긴 쌍도 넣었다.
CONFUSION_PAIRS: tuple[tuple[str, str], ...] = (
    ("JACKET", "COAT"),
    ("JACKET", "PADDED_JACKET"),
    ("CARDIGAN", "HOOD_ZIPUP"),
    ("HOODIE", "HOOD_ZIPUP"),
    ("KNIT", "SWEATSHIRT"),
    ("TSHIRT", "SWEATSHIRT"),
    ("TSHIRT", "SHIRT"),
    ("SLACKS", "CARGO_PANTS"),
    ("SLACKS", "COTTON_PANTS"),
    ("CARGO_PANTS", "JOGGER_PANTS"),
    ("SKIRT", "DRESS"),
    ("SHOULDER_BAG", "CROSS_BAG"),
    ("SHOULDER_BAG", "TOTE_BAG"),
    ("CROSS_BAG", "TOTE_BAG"),
)

# 경계 규정 — 사람마다 갈리는 판정을 코드 옆에 적어 둔다. 정답셋 라벨링·프롬프트·학습셋
# 수집이 전부 같은 기준을 쓰게 하려는 것이다(적어두지 않으면 라벨러마다 달라진다).
BOUNDARY_RULES: dict[str, str] = {
    "TSHIRT": (
        "폴로 셔츠(카라 + 목 부근 2~4개 단추, 그 아래는 막힘)는 SHIRT가 아니라 TSHIRT다. "
        "단추가 목 아래부터 밑단까지 쭉 이어질 때만 SHIRT."
    ),
    "SHIRT": "단추가 목~밑단까지 이어지는 셔츠. 폴로는 TSHIRT로 보낸다.",
    "COTTON_PANTS": "면 치노 계열. 정장 원단의 주름 잡힌 바지는 SLACKS.",
    "DRESS": "상하의가 한 벌로 이어진 원피스. 치마만 따로면 SKIRT.",
}

# --------------------------------------------------------------------------
# 라벨 문구 — zero-shot은 라벨 문구에 민감하므로 템플릿마다 다른 함수를 노출한다.
# --------------------------------------------------------------------------
_KR_LABELS: dict[str, str] = {
    "JACKET": "자켓",
    "COAT": "코트",
    "CARDIGAN": "가디건",
    "PADDED_JACKET": "패딩",
    "HOOD_ZIPUP": "후드집업",
    "TSHIRT": "티셔츠",
    "SHIRT": "셔츠",
    "KNIT": "니트",
    "HOODIE": "후드티",
    "SWEATSHIRT": "맨투맨",
    "SLEEVELESS": "민소매",
    "DENIM": "데님",
    "SLACKS": "슬랙스",
    "CARGO_PANTS": "카고팬츠",
    "SKIRT": "스커트",
    "SHORT_PANTS": "숏팬츠",
    "JOGGER_PANTS": "트레이닝 조거팬츠",
    "COTTON_PANTS": "코튼팬츠",
    "SNEAKERS": "스니커즈",
    "BOOTS": "부츠",
    "DRESS_SHOES": "구두",
    "SANDALS_SLIPPERS": "샌들 슬리퍼",
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
    "DRESS": "원피스",
    "JUMPSUIT": "점프슈트",
}

_EN_LABELS: dict[str, str] = {
    "JACKET": "jacket",
    "COAT": "coat",
    "CARDIGAN": "cardigan",
    "PADDED_JACKET": "padded puffer jacket",
    "HOOD_ZIPUP": "zip-up hoodie",
    "TSHIRT": "t-shirt",
    "SHIRT": "shirt",
    "KNIT": "knit sweater",
    "HOODIE": "hoodie",
    "SWEATSHIRT": "sweatshirt",
    "SLEEVELESS": "sleeveless top",
    "DENIM": "denim jeans",
    "SLACKS": "slacks",
    "CARGO_PANTS": "cargo pants",
    "SKIRT": "skirt",
    "SHORT_PANTS": "shorts",
    "JOGGER_PANTS": "jogger sweatpants",
    "COTTON_PANTS": "cotton chino pants",
    "SNEAKERS": "sneakers",
    "BOOTS": "boots",
    "DRESS_SHOES": "dress shoes",
    "SANDALS_SLIPPERS": "sandals",
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
    "DRESS": "dress",
    "JUMPSUIT": "jumpsuit",
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
    """템플릿 3: 중고 거래 맥락을 명시한 한글 템플릿."""
    return f"바닥에 펼쳐놓고 찍은 중고 {_KR_LABELS[code]} 사진"


# classify.py가 이 dict를 순회하며 템플릿별 정확도를 비교한다. 키 이름이 evaluate.py 리포트에
# 그대로 노출되므로 바꿀 때는 같이 맞춘다.
PROMPT_TEMPLATES: dict[str, "callable[[str], str]"] = {
    "kr_plain": _kr_plain,
    "en_clip_style": _en_clip_style,
    "kr_secondhand_flat": _kr_secondhand_flat,
}

# --------------------------------------------------------------------------
# 대분류(depth 2) 라벨/템플릿 — 2단계 분류의 1차 질의에 쓴다. 소분류용과 키 집합이 다르므로
# 별도로 둔다(같은 dict에 섞으면 우연히 겹치는 코드가 생겼을 때 조용히 잘못된 라벨을 반환).
# --------------------------------------------------------------------------
_KR_MAJOR_LABELS: dict[str, str] = {
    "OUTER": "아우터",
    "TOP": "상의",
    "BOTTOM": "하의",
    "SHOES": "신발",
    "BAG": "가방",
    "ACCESSORY": "액세서리",
    "DRESS_JUMPSUIT": "원피스 및 점프슈트",
}

_EN_MAJOR_LABELS: dict[str, str] = {
    "OUTER": "outerwear",
    "TOP": "top",
    "BOTTOM": "bottom",
    "SHOES": "shoes",
    "BAG": "bag",
    "ACCESSORY": "accessory",
    "DRESS_JUMPSUIT": "dress or jumpsuit",
}

assert set(_KR_MAJOR_LABELS) == set(MAJOR_CATEGORIES)
assert set(_EN_MAJOR_LABELS) == set(MAJOR_CATEGORIES)


def _kr_plain_major(code: str) -> str:
    return _KR_MAJOR_LABELS[code]


def _en_clip_style_major(code: str) -> str:
    return f"a photo of {_EN_MAJOR_LABELS[code]}"


def _kr_secondhand_flat_major(code: str) -> str:
    return f"바닥에 펼쳐놓고 찍은 중고 {_KR_MAJOR_LABELS[code]} 사진"


# PROMPT_TEMPLATES와 같은 키 집합 — 2단계 오케스트레이션이 같은 template_key로 대분류/
# 소분류 양쪽을 다 조회할 수 있게 한다.
MAJOR_PROMPT_TEMPLATES: dict[str, "callable[[str], str]"] = {
    "kr_plain": _kr_plain_major,
    "en_clip_style": _en_clip_style_major,
    "kr_secondhand_flat": _kr_secondhand_flat_major,
}
assert set(MAJOR_PROMPT_TEMPLATES) == set(PROMPT_TEMPLATES)


# --------------------------------------------------------------------------
# ID 매핑 — BE 시드 삽입 순서(성별 -> 대분류 -> 소분류)를 그대로 재현한다.
# 아래 assert가 `BE/docs/db/category-taxonomy.md` 표의 실제 값으로 검산한다.
# --------------------------------------------------------------------------
_GENDER_ID_BASE = 1  # depth1: 1~3
_MAJOR_ID_BASE = 4  # depth2: 4~23 (성별 3개 다음)
_SUBCATEGORY_ID_BASE = 24  # depth3: 24~126 (대분류 20개 다음)

GENDER_ID_MAP: dict[str, int] = {code: _GENDER_ID_BASE + i for i, code in enumerate(GENDER_CODES)}


def _build_major_id_map() -> dict[tuple[str, str], int]:
    mapping: dict[tuple[str, str], int] = {}
    next_id = _MAJOR_ID_BASE
    for gender in GENDER_CODES:
        for major in MAJORS_BY_GENDER[gender]:
            mapping[(gender, major)] = next_id
            next_id += 1
    return mapping


def _build_category_id_map() -> dict[tuple[str, str], int]:
    mapping: dict[tuple[str, str], int] = {}
    next_id = _SUBCATEGORY_ID_BASE
    for gender in GENDER_CODES:
        for major in MAJORS_BY_GENDER[gender]:
            for subcat in SUBCATEGORIES[major]:
                mapping[(gender, subcat)] = next_id
                next_id += 1
    return mapping


MAJOR_CATEGORY_ID_MAP: dict[tuple[str, str], int] = _build_major_id_map()
CATEGORY_ID_MAP: dict[tuple[str, str], int] = _build_category_id_map()

# 문서 표의 실제 값으로 검산 — 시드 순서가 바뀌면 여기서 즉시 터진다.
assert MAJOR_CATEGORY_ID_MAP[("MEN", "OUTER")] == 4
assert MAJOR_CATEGORY_ID_MAP[("WOMEN", "DRESS_JUMPSUIT")] == 16
assert MAJOR_CATEGORY_ID_MAP[("UNISEX", "DRESS_JUMPSUIT")] == 23
assert len(MAJOR_CATEGORY_ID_MAP) == 20
assert CATEGORY_ID_MAP[("MEN", "JACKET")] == 24
assert CATEGORY_ID_MAP[("MEN", "SUNGLASSES")] == 56
assert CATEGORY_ID_MAP[("WOMEN", "JACKET")] == 57
assert CATEGORY_ID_MAP[("WOMEN", "TSHIRT")] == 62
assert CATEGORY_ID_MAP[("WOMEN", "JUMPSUIT")] == 91
assert CATEGORY_ID_MAP[("UNISEX", "JACKET")] == 92
assert CATEGORY_ID_MAP[("UNISEX", "TSHIRT")] == 97
assert CATEGORY_ID_MAP[("UNISEX", "JUMPSUIT")] == 126
assert len(CATEGORY_ID_MAP) == 103
assert ("MEN", "DRESS") not in CATEGORY_ID_MAP  # 남성엔 원피스가 없다


def major_category_id(gender_code: str, major_code: str) -> int:
    """(성별, 대분류) -> depth2 categoryId. **AI가 BE에 돌려주는 값**(문서의 "사용 방법").

    성별은 분류기가 아니라 등록 폼에서 온다 — 모듈 docstring 참고.
    남성 + DRESS_JUMPSUIT처럼 존재하지 않는 조합이면 KeyError.
    """
    return MAJOR_CATEGORY_ID_MAP[(gender_code, major_code)]


def category_id(gender_code: str, subcategory_code: str) -> int:
    """(성별, 소분류) -> depth3 categoryId. 최종 `product.category_id`가 되는 값이다.

    분류기는 이 함수를 호출하지 않는다 — 소분류는 사용자가 FE 드롭다운에서 고른다.
    문서화/데모용이고, 학습셋 수집 시 코드->ID 대조에도 쓴다.
    """
    return CATEGORY_ID_MAP[(gender_code, subcategory_code)]
