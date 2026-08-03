"""상품명/옵션 텍스트에서 색상 **후보**만 뽑는다 — 확정 라벨을 만들지 않는다.

사용자 결정(2026-08-01): 이번 수집기는 **카테고리만 자동 라벨링**하고 색상은 사람/후처리로
채운다. 상품명의 색상어는 오라벨 위험이 크기 때문이다:

- 쇼핑몰 상품명의 색상은 **대표 이미지의 색이 아니라 옵션 전체**를 나열하는 경우가 많다
  ("[3color] 오버핏 니트" / "블랙/아이보리/차콜").
- "차콜", "멜란지그레이", "인디고"처럼 팔레트 19종에 1:1로 안 떨어지는 표현이 흔하다.

그래서 이 모듈의 결과는 `CollectedItem.color_hints`에만 들어가고 `primary_color`는 `None`으로
남는다. 나중에 사람이 검수하거나 VLM으로 채울 때 **후보를 좁혀주는 용도**다.

표준 라이브러리만 쓴다.
"""

from __future__ import annotations

from labels import MULTI_LABEL, PALETTE_CODES
from mapping import normalize

# 팔레트 코드 -> 한국어/영어 표기 변형. 정규화(공백 제거·소문자)된 형태로 적는다.
_COLOR_TERMS: dict[str, tuple[str, ...]] = {
    "BLACK": ("블랙", "검정", "검은", "먹색", "black"),
    "WHITE": ("화이트", "흰색", "백색", "white"),
    "GRAY": ("그레이", "회색", "차콜", "챠콜", "멜란지", "gray", "grey", "charcoal"),
    "IVORY": ("아이보리", "오트밀", "크림", "ivory", "cream", "oatmeal"),
    "BEIGE": ("베이지", "샌드", "카멜", "beige", "sand", "camel"),
    "BROWN": ("브라운", "갈색", "초코", "모카", "brown", "choco", "mocha"),
    "KHAKI": ("카키", "올리브", "khaki", "olive"),
    "NAVY": ("네이비", "감청", "navy"),
    "BLUE": ("블루", "파랑", "파란", "인디고", "코발트", "blue", "indigo", "cobalt"),
    "SKYBLUE": ("스카이블루", "하늘색", "라이트블루", "skyblue", "lightblue"),
    "GREEN": ("그린", "초록", "민트", "green", "mint"),
    "YELLOW": ("옐로우", "옐로", "노랑", "노란", "머스타드", "yellow", "mustard"),
    "ORANGE": ("오렌지", "주황", "코랄", "orange", "coral"),
    "RED": ("레드", "빨강", "빨간", "red"),
    "PINK": ("핑크", "분홍", "로즈", "pink", "rose"),
    "PURPLE": ("퍼플", "보라", "라벤더", "바이올렛", "purple", "lavender", "violet"),
    "WINE": ("와인", "버건디", "마룬", "wine", "burgundy", "maroon"),
    "SILVER": ("실버", "은색", "silver"),
    "GOLD": ("골드", "금색", "gold"),
}

assert set(_COLOR_TERMS) == set(PALETTE_CODES), "색상어 사전이 팔레트 코드 집합과 어긋난다"

# 이 단어들이 있으면 단색 스냅이 오히려 틀린다 — MULTI 후보로 표시한다(브리핑 §1의 특수값).
_MULTI_TERMS: tuple[str, ...] = (
    "체크",
    "스트라이프",
    "패턴",
    "프린트",
    "플라워",
    "플로럴",
    "레오파드",
    "호피",
    "타이다이",
    "그라데이션",
    "배색",
    "멀티",
    "카모",
    "아가일",
    "check",
    "stripe",
    "pattern",
    "print",
    "floral",
    "leopard",
    "camo",
    "multi",
)

# "[3color]", "5컬러" 같은 옵션 표기 — 대표 이미지 색을 상품명에서 못 정한다는 신호.
_MULTI_OPTION_TERMS: tuple[str, ...] = ("color", "컬러", "colors")


def extract_color_hints(*texts: str) -> list[str]:
    """상품명·옵션 텍스트에서 팔레트 코드 후보를 등장 순서대로 뽑는다(중복 제거).

    패턴/프린트 단어가 있으면 `MULTI`도 후보에 넣는다. 아무것도 못 찾으면 빈 리스트.
    """
    joined = normalize(" ".join(t for t in texts if t))
    if not joined:
        return []

    found: list[tuple[int, str]] = []
    for code, terms in _COLOR_TERMS.items():
        positions = [joined.find(term) for term in terms]
        positions = [pos for pos in positions if pos >= 0]
        if positions:
            found.append((min(positions), code))

    hints = [code for _, code in sorted(found)]

    if any(term in joined for term in _MULTI_TERMS):
        hints.append(MULTI_LABEL)
    return list(dict.fromkeys(hints))


def is_color_ambiguous(hints: list[str], *texts: str) -> bool:
    """상품명만으로 주색상을 정할 수 없는 경우인지.

    후보가 2개 이상이거나(옵션 나열), "3COLOR"류 표기가 있으면 True. 검수 우선순위를
    매길 때 쓴다 — 후보가 정확히 1개면 사람이 훑고 넘기기 쉽다.
    """
    if len(hints) >= 2:
        return True
    joined = normalize(" ".join(t for t in texts if t))
    return any(term in joined for term in _MULTI_OPTION_TERMS)
