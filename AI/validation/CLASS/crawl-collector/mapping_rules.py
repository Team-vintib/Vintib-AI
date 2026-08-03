"""원본 쇼핑몰 카테고리 텍스트 → 우리 소분류 코드 매핑 규칙 레지스트리.

브리핑 §5가 "매핑 방법 자체를 설계하는 게 이번 작업의 핵심"이라고 지정한 부분의 절반이다
(나머지 절반은 `mapping.py`의 점수화/신뢰도 판정).

**왜 YAML이 아니라 파이썬인가**: 규칙은 CI에서 테스트되는 로직에 가깝다. `validation/`의
`model_registry.py` 관례(중앙 레지스트리 dict + 상수)를 그대로 따르고, PyYAML은 CI에 설치되지
않아 규칙을 데이터 파일로 빼면 테스트가 CI에서 스킵된다. **사이트마다 다른 정확 매핑
테이블**(`"아우터 > 자켓 > 블루종" -> JACKET`)은 그 반대로 사이트 스펙 YAML에 둔다 — 그쪽은
사이트가 늘 때마다 바뀌는 데이터고, 이 파일은 사이트와 무관한 한국어 의류 용어 사전이다.

## 매칭 규칙 세 가지

1. **가장 긴 키워드가 이긴다.** `"후드집업"`은 `HOODIE`의 `"후드"`(2자)와 `HOOD_ZIPUP`의
   `"후드집업"`(4자)에 동시에 걸리는데, 길이 점수로 후자가 이긴다. 규칙 나열 순서에
   의존하지 않는다 — 순서 의존은 규칙이 늘수록 조용히 깨진다.
2. **배제어(`exclude`)가 있으면 그 규칙은 아예 후보에서 빠진다.** `"데님자켓"`이 `DENIM`으로
   가지 않게 하는 장치.
3. **`ambiguous=True`인 규칙이 이기면 무조건 사람 검수 대상**(`needs_review`)이 된다.
   브리핑 §5.4의 "정장 자켓이 OUTER인지 격식 상의인지" 같은, 사진을 봐야 정해지는 항목들.

우리 taxonomy에 없는 카테고리(원피스·안경·양말 등)는 **일부러 규칙을 만들지 않는다.** 비슷한
코드에 욱여넣지 말고 `unmapped`으로 남겨 taxonomy 확장 논의 근거로 쓰라는 게 브리핑 §5.5다.
"""

from __future__ import annotations

from dataclasses import dataclass

from labels import is_valid_subcategory


@dataclass(frozen=True)
class MappingRule:
    """소분류 코드 하나에 대응하는 키워드 묶음."""

    code: str
    keywords: tuple[str, ...]
    # 이 단어가 텍스트에 있으면 규칙 자체를 후보에서 제외한다(오탐 차단).
    exclude: tuple[str, ...] = ()
    # True면 이 규칙이 이겨도 자동 확정하지 않고 사람 검수로 넘긴다.
    ambiguous: bool = False
    note: str = ""


def _rule(
    code: str,
    *keywords: str,
    exclude: tuple[str, ...] = (),
    ambiguous: bool = False,
    note: str = "",
) -> MappingRule:
    return MappingRule(
        code=code, keywords=keywords, exclude=exclude, ambiguous=ambiguous, note=note
    )


# 키워드는 `mapping.normalize()`를 거친 형태(소문자·공백/구분자 제거)로 적는다.
# 예: "zip-up"이 아니라 "zipup", "카고 팬츠"가 아니라 "카고팬츠".
RULES: tuple[MappingRule, ...] = (
    # ---------------- OUTER ----------------
    _rule(
        "JACKET",
        "자켓",
        "재킷",
        "점퍼",
        "잠바",
        "블루종",
        "블레이저",
        "바람막이",
        "윈드브레이커",
        "무스탕",
        "라이더",
        "야상",
        "아노락",
        "항공점퍼",
        "ma1",
        "jacket",
        "blazer",
        "blouson",
        exclude=("정장자켓", "수트자켓"),
        note="정장/수트 자켓은 아래 ambiguous 규칙이 따로 잡는다.",
    ),
    _rule(
        "JACKET",
        "정장자켓",
        "수트자켓",
        "플리스",
        "후리스",
        ambiguous=True,
        note="브리핑 §5.4 예시. 플리스는 점퍼형(JACKET)과 롱코트형(COAT) 둘 다 흔해 "
        "사진을 봐야 정해진다. 패딩은 taxonomy v2에서 PADDED_JACKET이 생겨 빠졌다.",
    ),
    _rule(
        "COAT",
        "코트",
        "트렌치",
        "더플",
        "체스터필드",
        "coat",
        "trench",
        note="트렌치/더플은 그 자체로 코트 형태가 확정된다. 롱패딩은 taxonomy v2부터 "
        "PADDED_JACKET이 받는다(충전재 아우터는 기장과 무관하게 그쪽).",
    ),
    _rule("CARDIGAN", "가디건", "카디건", "cardigan"),
    # VEST(베스트/조끼) 규칙은 2026-08-03 taxonomy v2에서 **삭제**했다 — BE 시드에 해당
    # 소분류가 없다. 모듈 docstring 정책대로 비슷한 코드에 욱여넣지 않고 `unmapped`으로
    # 남긴다(taxonomy 확장 논의 근거). 그래서 KNIT/JACKET의 "니트베스트"·"패딩조끼"
    # 배제어도 그대로 둔다 — 그쪽으로 새는 것보다 unmapped이 낫다.
    _rule(
        "PADDED_JACKET",
        "패딩",
        "롱패딩",
        "숏패딩",
        "패딩점퍼",
        "다운점퍼",
        "덕다운",
        "padding",
        "puffer",
        "downjacket",
        exclude=("패딩조끼", "패딩베스트"),
        note="taxonomy v2 신설. 예전엔 패딩이 JACKET(ambiguous)/COAT로 갈렸는데 이제 "
        "전용 코드가 있다 — 길이 무관하게 충전재 아우터는 전부 여기로.",
    ),
    _rule(
        "HOOD_ZIPUP",
        "후드집업",
        "후디집업",
        "집업후드",
        "집업",
        "지퍼후드",
        "zipup",
        "ziphood",
        note="'집업'만 있어도 지퍼 아우터로 본다 — 길이 점수상 HOODIE의 '후드'를 이긴다.",
    ),
    # ---------------- TOP ----------------
    _rule(
        "TSHIRT",
        "티셔츠",
        "반팔티",
        "긴팔티",
        "반소매티",
        "무지티",
        "tshirt",
        "tee",
        exclude=("맨투맨",),
    ),
    _rule(
        "SHIRT",
        "셔츠",
        "남방",
        "블라우스",
        "shirt",
        "blouse",
        exclude=("티셔츠", "맨투맨", "스웨트셔츠", "스웻셔츠"),
        note="'티셔츠'는 '셔츠'를 포함하므로 배제어로도 한 번 더 막는다(길이 점수만으로도 "
        "이기지만, 규칙이 늘어나도 안 깨지게).",
    ),
    _rule(
        "KNIT",
        "니트",
        "스웨터",
        "울집업",
        "knit",
        "sweater",
        exclude=("니트베스트", "니트조끼", "니트가디건", "니트카디건"),
        note="니트 베스트/가디건은 아이템 형태가 우선이라 VEST/CARDIGAN으로 보낸다.",
    ),
    _rule(
        "HOODIE",
        "후드",
        "후디",
        "hoodie",
        "hood",
        exclude=("집업", "지퍼", "zipup", "후드집업"),
    ),
    _rule(
        "SWEATSHIRT",
        "맨투맨",
        "스웨트셔츠",
        "스웻셔츠",
        "트레이닝상의",
        "sweatshirt",
        "crewneck",
    ),
    _rule(
        "SLEEVELESS",
        "민소매",
        "나시",
        "슬리브리스",
        "탱크탑",
        "캡소매",
        "sleeveless",
        "tanktop",
        note="taxonomy v2 신설.",
    ),
    # ---------------- BOTTOM ----------------
    _rule(
        "DENIM",
        "데님",
        "청바지",
        "진팬츠",
        "denim",
        "jeans",
        exclude=(
            "자켓",
            "재킷",
            "셔츠",
            "스커트",
            "치마",
            "원피스",
            "점퍼",
            "반바지",
            "숏팬츠",
            "쇼츠",
        ),
        note="데님은 소재어라 상의/스커트/반바지에도 붙는다 — 아이템어가 같이 있으면 양보한다.",
    ),
    _rule(
        "SLACKS",
        "슬랙스",
        "정장바지",
        "드레스팬츠",
        "정장팬츠",
        "slacks",
        "trousers",
    ),
    _rule("CARGO_PANTS", "카고", "cargo", exclude=("카고반바지", "카고숏팬츠")),
    _rule(
        "SKIRT",
        "스커트",
        "치마",
        "skirt",
        exclude=("치마바지",),
    ),
    _rule(
        "SHORT_PANTS",
        "반바지",
        "숏팬츠",
        "쇼트팬츠",
        "쇼츠",
        "하프팬츠",
        "버뮤다",
        "카고반바지",
        "카고숏팬츠",
        "shorts",
    ),
    _rule(
        "JOGGER_PANTS",
        "조거",
        "조거팬츠",
        "트레이닝팬츠",
        "트레이닝바지",
        "스웨트팬츠",
        "츄리닝",
        "jogger",
        "sweatpants",
        "trackpants",
        note="taxonomy v2 신설. SWEATSHIRT의 '트레이닝상의'와 문자열이 달라 충돌하지 않는다.",
    ),
    _rule(
        "COTTON_PANTS",
        "코튼팬츠",
        "면바지",
        "치노",
        "치노팬츠",
        "chino",
        "cottonpants",
        note="taxonomy v2 신설. 정장 원단의 주름 잡힌 바지는 SLACKS 쪽이다.",
    ),
    _rule(
        "SLACKS",
        "팬츠",
        "바지",
        "pants",
        exclude=(
            "반바지",
            "청바지",
            "카고",
            "슬랙스",
            "숏팬츠",
            "쇼츠",
            "하프팬츠",
            "데님",
            "진팬츠",
            "정장바지",
            "드레스팬츠",
            "치마바지",
            "조거",
            "트레이닝",
            "스웨트팬츠",
            "코튼팬츠",
            "면바지",
            "치노",
            "멜빵바지",
        ),
        ambiguous=True,
        note="아이템어 없이 '팬츠/바지'만 있는 카테고리. 하의 7종 중 무엇이든 될 수 있어 "
        "사진 검수로 넘긴다(가장 흔한 SLACKS를 제안값으로만 둔다).",
    ),
    # ---------------- DRESS_JUMPSUIT (taxonomy v2 신설 대분류) ----------------
    _rule(
        "DRESS",
        "원피스",
        "드레스",
        "onepiece",
        "dress",
        exclude=("드레스팬츠", "드레스슈즈"),
        note="taxonomy v2 신설. '드레스팬츠'(SLACKS)·'드레스슈즈'(DRESS_SHOES)와 겹쳐 "
        "배제어가 필수다.",
    ),
    _rule(
        "JUMPSUIT",
        "점프슈트",
        "오버올",
        "멜빵바지",
        "살로페트",
        "jumpsuit",
        "overall",
        "dungarees",
        note="taxonomy v2 신설.",
    ),
    # ---------------- SHOES ----------------
    _rule("SNEAKERS", "스니커즈", "운동화", "sneaker", "trainers"),
    _rule("BOOTS", "부츠", "워커", "첼시부츠", "boots", "bootie"),
    _rule(
        "DRESS_SHOES",
        "로퍼",
        "구두",
        "더비슈즈",
        "옥스포드슈즈",
        "드레스슈즈",
        "loafer",
        "dressshoes",
        note="taxonomy v2에서 LOAFER -> DRESS_SHOES로 개명 — 구두 전반을 받는 코드가 됐다.",
    ),
    _rule("SANDALS_SLIPPERS", "샌들", "슬리퍼", "쪼리", "뮬", "sandal", "slipper", "flipflop"),
    # ---------------- BAG ----------------
    _rule("BACKPACK", "백팩", "배낭", "책가방", "backpack", "rucksack"),
    _rule("SHOULDER_BAG", "숄더백", "숄더", "shoulderbag", "hobo"),
    _rule("TOTE_BAG", "토트백", "토트", "에코백", "쇼퍼백", "totebag", "tote"),
    _rule("CROSS_BAG", "크로스백", "크로스바디", "메신저백", "crossbody", "crossbag", "messenger"),
    _rule("POUCH", "파우치", "클러치", "pouch", "clutch"),
    # ---------------- ACCESSORY ----------------
    _rule("HAT", "모자", "볼캡", "비니", "버킷햇", "베레모", "캡모자", "hat", "cap", "beanie"),
    _rule("BELT", "벨트", "belt", exclude=("벨트백",)),
    _rule("SCARF", "스카프", "머플러", "목도리", "scarf", "muffler"),
    _rule(
        "JEWELRY",
        "주얼리",
        "쥬얼리",
        "반지",
        "목걸이",
        "귀걸이",
        "팔찌",
        "발찌",
        "jewelry",
        "jewellery",
        "necklace",
        "bracelet",
        "earring",
    ),
    _rule("WATCH", "시계", "워치", "watch"),
    _rule("SUNGLASSES", "선글라스", "썬글라스", "sunglass", "sunglasses"),
)

# 자동 확정(mapped) 최소 신뢰도. 이 아래는 needs_review로 떨어진다.
CONFIDENCE_AUTO_THRESHOLD = 0.70

# ambiguous 규칙이 이겼을 때 부여하는 신뢰도 상한.
AMBIGUOUS_CONFIDENCE_CAP = 0.50

# 1·2위 코드가 동점일 때의 신뢰도 상한 — 반드시 자동 확정 임계값 아래여야 한다.
TIE_CONFIDENCE_CAP = 0.45

# 카테고리가 좁혀 준 후보 안에서 상품명이 하나를 지목했을 때의 신뢰도 상한.
# 카테고리 단독 매핑(최대 0.95)보다는 낮게 두되, 자동 확정 임계값(0.70)은 넘게 한다 —
# 후보가 이미 2~3개로 제한돼 있어 열린 상품명 매칭(PRODUCT_NAME_PENALTY)보다 훨씬 안전하다.
NAME_RESOLVE_CONFIDENCE_CAP = 0.85

# 카테고리 텍스트가 아니라 상품명에서 매칭됐을 때 곱하는 감쇠 계수 — 상품명은
# "블랙 오버핏 데님 자켓 (린넨 셔츠 증정)"처럼 노이즈가 많아 카테고리보다 덜 믿는다.
PRODUCT_NAME_PENALTY = 0.75


def rules_for(code: str) -> tuple[MappingRule, ...]:
    """특정 소분류 코드에 걸린 규칙들(테스트/디버깅용)."""
    return tuple(rule for rule in RULES if rule.code == code)


def _validate() -> None:
    """규칙에 taxonomy에 없는 코드를 적는 실수를 import 시점에 잡는다."""
    bad = sorted({rule.code for rule in RULES if not is_valid_subcategory(rule.code)})
    if bad:
        raise ValueError(f"RULES에 taxonomy에 없는 소분류 코드가 있다: {bad}")
    for rule in RULES:
        if not rule.keywords:
            raise ValueError(f"키워드가 빈 규칙: {rule.code}")


_validate()
