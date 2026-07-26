"""라이브 댓글 관리 정확도 평가용 라벨링 데이터셋 (S15P11A108-196).

세 세트로 나눠 둔다. **Set A와 Set B의 지표는 합치지 않는다** — 합치면 Set A의 존재 이유
(기존 수치와의 대조 가능성)가 깨진다.

- **Set A — 호환셋(210건)**: `test/model_selection/classifier_benchmark.ipynb` §2의 생성 로직을
  그대로 포팅한 것. 같은 샘플이어야 그 노트북에 기록된 모델 수치(`kor_unsmile` 악성 recall
  58.3%, `kcelectra_base_hate` 98.8%)와 규칙 기반 결과를 같은 표에 놓을 수 있다.
  `test/`를 프로덕션에서 import하지 않는 규약(`AI/CLAUDE.md`)에 따라 여기서 재선언한다.
- **Set B — 확장셋(수제)**: Set A에 없는 축. ① 사전 어휘를 품었지만 정상인 문장(오탐 유발),
  ② 어휘로는 안 잡히는 문맥형 악성, ③ Set A가 다루지 않는 우회 변형(모음 늘이기·구두점 삽입·
  부분 로마자화).
- **Set C — 반복질문셋**: paraphrase 그룹 + 기대 근거 문서 id. 지식베이스 밖 그룹은
  `expected_doc_id=None`으로 두어 "침묵해야 하는 케이스"를 표현한다.

설계: .claude/plans/ai/004-live-comment-moderation-evaluation.md
"""

from __future__ import annotations

from dataclasses import dataclass

NORMAL = "정상"
ABUSIVE = "악성"


@dataclass(frozen=True)
class ModerationCase:
    """비매너 판정 평가 케이스 한 건."""

    comment: str
    expected: str  # NORMAL | ABUSIVE
    variant: str  # 원문 / 초성체 / 띄어쓰기 / 웃음패딩 / 모음늘이기 / 구두점 / 로마자 / 함정정상 / 문맥형


@dataclass(frozen=True)
class FaqCase:
    """반복질문 평가 케이스. expected_doc_id가 None이면 지식베이스 밖(침묵해야 함)."""

    question: str
    group: str  # 같은 group = 같은 질문의 다른 표현
    expected_doc_id: str | None


# ---------------------------------------------------------------------------
# 우회 변형 생성기
# ---------------------------------------------------------------------------

# 한글 음절 -> 초성만 추출(초성체 우회 재현용). 유니코드 완성형 한글 공식:
# code = (초성index * 588) + (중성index * 28) + 종성index, 0xAC00('가')부터 시작.
_CHOSUNG_LIST = [
    "ㄱ",
    "ㄲ",
    "ㄴ",
    "ㄷ",
    "ㄸ",
    "ㄹ",
    "ㅁ",
    "ㅂ",
    "ㅃ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅉ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]
_HANGUL_BASE = 0xAC00
_HANGUL_LAST = 11171
_IEUNG_INDEX = 11  # 'ㅇ' — 홀로 쓰는 모음 음절(예: 'ㅣ' -> '이')을 만들 때의 초성


def to_chosung(text: str) -> str:
    """완성형 한글 음절을 초성만 남긴 문자열로 바꾼다(예: "미친놈아" -> "ㅁㅊㄴㅇ").

    한글 음절이 아닌 문자(공백 등)는 그대로 둔다. 실제 채팅에서 욕설 필터를
    피하려고 초성만 남기는 우회 패턴을 재현한다.
    """
    result = []
    for ch in text:
        code_point = ord(ch) - _HANGUL_BASE
        if 0 <= code_point <= _HANGUL_LAST:
            result.append(_CHOSUNG_LIST[code_point // 588])
        else:
            result.append(ch)
    return "".join(result)


def to_spaced(text: str) -> str:
    """음절 사이에 공백을 넣는다(예: "병신같은게" -> "병 신 같 은 게") — 띄어쓰기 우회 재현."""
    return " ".join(text)


def with_laugh_suffix(text: str, repeat: int = 6) -> str:
    """문장 끝에 자모("ㅋ")를 반복 추가한다 — 조롱성 웃음으로 욕설/비하를 감추는 패턴 재현."""
    return text + "ㅋ" * repeat


def with_vowel_stretch(text: str, repeat: int = 2) -> str:
    """첫 한글 음절의 모음을 늘린다(예: "시발" -> "시이이발") — 모음 늘이기 우회 재현.

    `classifier.py`의 정규화가 커버하지 못한다고 문서화한 패턴이라 미탐 측정용으로 넣는다.
    한글 음절이 없으면 원문을 그대로 돌려준다.
    """
    for i, ch in enumerate(text):
        code_point = ord(ch) - _HANGUL_BASE
        if 0 <= code_point <= _HANGUL_LAST:
            jungseong = (code_point % 588) // 28
            vowel_syllable = chr(_HANGUL_BASE + _IEUNG_INDEX * 588 + jungseong * 28)
            return text[: i + 1] + vowel_syllable * repeat + text[i + 1 :]
    return text


def with_dot_separator(text: str, separator: str = ".") -> str:
    """음절 사이에 구두점을 끼운다(예: "개새끼" -> "개.새.끼") — 구두점 삽입 우회 재현."""
    return separator.join(text)


# 부분 로마자화 우회용 음절 표. 욕설에 자주 쓰이는 음절만 최소로 담는다.
_LATIN_LOOKALIKE = {
    "시": "si",
    "씨": "ssi",
    "발": "bal",
    "병": "byung",
    "신": "sin",
    "개": "gae",
    "새": "sae",
    "끼": "ggi",
    "미": "mi",
    "친": "chin",
    "지": "ji",
    "랄": "ral",
}


def with_latin_lookalike(text: str) -> str:
    """첫 음절만 로마자로 바꾼다(예: "시발" -> "sibal"의 앞부분 = "si발") — 문자 치환 우회 재현.

    표에 없는 음절뿐이면 원문을 그대로 돌려준다(호출부에서 원문과 같으면 케이스를 만들지 않는다).
    """
    for i, ch in enumerate(text):
        if ch in _LATIN_LOOKALIKE:
            return text[:i] + _LATIN_LOOKALIKE[ch] + text[i + 1 :]
    return text


# ---------------------------------------------------------------------------
# Set A — 호환셋 (210건). classifier_benchmark.ipynb §2 재현.
# ---------------------------------------------------------------------------

# --- 정상 댓글 템플릿 21개 x 어미/이모지성 접미사 6개 = 126건 ---
_NORMAL_TEMPLATES = (
    "이 옷 진짜 예쁘네요 판매자님 감사합니다",
    "사이즈 잘 맞을까요",
    "색상 실물이 더 예쁘네요",
    "배송 빠르네요 감사합니다",
    "이전에 산 것도 좋았어요 재구매합니다",
    "핏이 너무 좋아요",
    "세탁 방법이 궁금해요",
    "방송 잘 보고 있습니다",
    "다음 방송 언제 하시나요",
    "포장 꼼꼼하게 잘 왔어요",
    "이 브랜드 처음 사보는데 기대되네요",
    "사진보다 실물이 더 좋아요",
    "이 가격에 이 퀄리티면 혜자에요",
    "구매하길 잘한 것 같아요",
    "판매자님 응대 친절하시네요",
    "품질 좋고 착용감도 편해요",
    "이 소재 계절에 잘 맞을 것 같아요",
    "라이브 진행 재밌게 잘 보고 있어요",
    "다른 색상도 예쁘네요",
    "필요했던 옷인데 마침 잘 샀어요",
    "구성품도 알차고 좋네요",
)
# 원본 그대로 유지한다. 첫 템플릿 + " 감사합니다" 접미사가 "…감사합니다 감사합니다"를 만드는
# 중복이 있지만, Set A의 목적은 기존 수치와의 대조이므로 원본 재현을 깨지 않는다.
_NORMAL_SUFFIXES = ("", "!", "~", " ㅎㅎ", " 감사합니다", " 진짜 최고예요")

# --- 악성(혐오/비방) 문장 템플릿 21개: 원문 + 웃음 접미사 버전 = 42건 ---
_ABUSIVE_SENTENCES = (
    "저런 걸 옷이라고 파네 진짜 미친놈인가",
    "여자가 무슨 명품을 입고 방송을 하냐 꼴값이네",
    "판매자 얼굴 보니까부터 실망이다",
    "그 가격에 그 퀄리티면 사기 아니냐",
    "목소리 진짜 짜증나게 하네",
    "누가 이런 걸 산다고 광고를 하냐 병신같은게",
    "얼굴만 믿고 방송하나 실력은 없네",
    "이 방송 진짜 노잼이다 꺼져라",
    "저 옷 입은 거 보니까 안목이 없네",
    "머리는 장식이냐 그것도 못 챙기고",
    "돈 받고 이렇게 파는 거 양심 있냐",
    "보고 있자니 한심하다 정말",
    "그 나이 먹고 저러고 사는 거 부끄럽지도 않냐",
    "재고 처리하려고 사기치는거 다 보인다",
    "누가 보면 대단한 브랜드인 줄 알겠네 우습다",
    "말하는 꼬라지 보니까 정떨어진다",
    "저러니 매출이 안 나오지 자업자득이다",
    "그 얼굴로 방송 나올 생각을 하다니 대단하다 진짜",
    "옷 고르는 눈이 그것밖에 안되나 답답하다",
    "누가 저런 말투로 방송을 하래 짜증나게",
    "실력도 없으면서 잘난 척은 다 하네",
)

# --- 짧은 비속어 어구 14개: 원문 + 초성체 + 띄어쓰기 우회 = 42건 ---
_SHORT_PROFANITY = (
    "미친놈아",
    "병신같은게",
    "재수없네",
    "정신나갔네",
    "한심하네",
    "역겹다",
    "구제불능이네",
    "무개념이네",
    "정신차려라",
    "생각이 없네",
    "부끄러운 줄 알아라",
    "낯짝이 두껍네",
    "싸구려 티 나네",
    "꼴보기 싫다",
)


def build_set_a() -> list[ModerationCase]:
    """호환셋 210건(정상 126 / 악성 84). 생성 순서까지 원본과 같다."""
    cases: list[ModerationCase] = []

    for template in _NORMAL_TEMPLATES:
        for suffix in _NORMAL_SUFFIXES:
            cases.append(ModerationCase(template + suffix, NORMAL, "원문"))

    for sentence in _ABUSIVE_SENTENCES:
        cases.append(ModerationCase(sentence, ABUSIVE, "원문"))
        cases.append(ModerationCase(with_laugh_suffix(sentence), ABUSIVE, "웃음패딩"))

    for phrase in _SHORT_PROFANITY:
        cases.append(ModerationCase(phrase, ABUSIVE, "원문"))
        cases.append(ModerationCase(to_chosung(phrase), ABUSIVE, "초성체"))
        cases.append(ModerationCase(to_spaced(phrase), ABUSIVE, "띄어쓰기"))

    return cases


# ---------------------------------------------------------------------------
# Set B — 확장셋 (수제). Set A에 없는 축만 채운다.
# ---------------------------------------------------------------------------

# ① 함정 정상 — 사전 표제어를 **부분 문자열로 품고 있지만** 전혀 악성이 아닌 문장.
#    `classifier.py`의 사전 매칭이 부분 문자열이라 여기서 오탐이 난다.
_TRAP_NORMAL = (
    "강아지 새끼 너무 귀여워요",  # 새끼
    "고양이 새끼 데려왔어요",  # 새끼
    "여기가 시발점이네요",  # 시발
    "등신대 사진 보고 왔어요",  # 등신
    "쓰레기 분리배출 하고 왔어요",  # 쓰레기
    "죽어라 일하고 이거 사려고요",  # 죽어라
    "닥쳐오는 겨울에 입을 옷 찾고 있어요",  # 닥쳐
    "꺼지지 않는 인기템이네요",  # 꺼지
)

# ② 정상인데 오탐 위험이 있다고 본 문장들 — 통과해야 정상이다(true negative 확인용).
_SAFE_NORMAL = (
    "이 옷 미친 예쁘다",  # 긍정 속어. 사전에 '미친' 단독은 없어야 한다
    "소백산 다녀왔어요",  # 초성 환원했다면 ㅅㅂ 오탐이 났을 문장
    "사부님 스타일 좋으세요",
    "웃기네ㅋㅋㅋㅋㅋㅋ",
    "이 브랜드 시그니처 라인인가요",
)

# ③ 문맥형 악성 — 욕설 어휘 없이 조롱·인신공격. 사전 방식으로는 구조적으로 못 잡는다.
_CONTEXTUAL_ABUSIVE = (
    "얼굴이 참 특이하시네요 ㅋㅋ",
    "이런 걸 파는 사람 수준 알만하다",
    "그 나이에 그런 옷을 왜 입으시는지",
    "돈이 없어서 이런 걸 파시는 건가요",
    "말투부터 신뢰가 안 가네요",
    "옷은 안 팔리고 시간만 버리시네요",
)

# ④ Set A가 다루지 않은 우회 변형의 원본 어구. 생성기 출력이 자연스러운 것만 골랐다.
_EVASION_SEEDS = ("시발", "개새끼", "미친놈")

# ⑤ 손으로 쓴 추가 우회 사례 — 생성기로 만들기 어려운 형태.
_MANUAL_EVASION = (
    ("ㅗㅗ 방송 접어라", "손가락"),
    ("졸라 짜증나네", "사전미포함"),
    ("s1발 진짜 뭐하냐", "문자치환"),
)


def build_set_b() -> list[ModerationCase]:
    """확장셋. 오탐/미탐 발굴이 목적이라 규모보다 축의 다양성을 우선한다."""
    cases: list[ModerationCase] = []

    cases.extend(ModerationCase(text, NORMAL, "함정정상") for text in _TRAP_NORMAL)
    cases.extend(ModerationCase(text, NORMAL, "원문") for text in _SAFE_NORMAL)
    cases.extend(ModerationCase(text, ABUSIVE, "문맥형") for text in _CONTEXTUAL_ABUSIVE)

    for seed in _EVASION_SEEDS:
        cases.append(ModerationCase(with_vowel_stretch(seed), ABUSIVE, "모음늘이기"))
        cases.append(ModerationCase(with_dot_separator(seed), ABUSIVE, "구두점"))
        romanized = with_latin_lookalike(seed)
        if romanized != seed:  # 표에 없는 음절뿐이면 원문과 같아져 중복이 된다
            cases.append(ModerationCase(romanized, ABUSIVE, "로마자"))

    cases.extend(ModerationCase(text, ABUSIVE, variant) for text, variant in _MANUAL_EVASION)
    return cases


# ---------------------------------------------------------------------------
# Set C — 반복질문셋. 근거 문서 id는 data/mock_faq.json과 맞춰져 있다.
# ---------------------------------------------------------------------------

_IN_KB_GROUPS: dict[str, tuple[str, tuple[str, ...]]] = {
    "사이즈": (
        "faq_size_01",
        ("이거 M 사이즈 있나요?", "M 사이즈도 있나요?", "혹시 M 사이즈 있나요??"),
    ),
    "재고": (
        "faq_stock_01",
        ("재고 아직 남아 있나요?", "재고 남아 있나요?", "아직 재고 남아 있나요?"),
    ),
    "가격": (
        "faq_price_01",
        ("가격이 얼마인가요?", "가격 얼마인가요?", "이거 가격이 얼마인가요?"),
    ),
    "배송": (
        "faq_ship_01",
        ("배송은 얼마나 걸리나요?", "배송 얼마나 걸리나요?", "배송은 얼마나 걸려요?"),
    ),
    "교환": (
        "faq_return_01",
        ("교환이나 반품 되나요?", "교환이나 반품 되요?", "교환 반품 되나요?"),
    ),
    "결제": (
        "faq_pay_01",
        ("결제는 어떻게 하나요?", "결제 어떻게 하나요?", "결제는 어떻게 해요?"),
    ),
}

# 지식베이스에 근거가 없는 그룹 — 반복질문으로 잡혀도 답변을 만들지 않아야 한다.
_OUT_OF_KB_GROUPS: dict[str, tuple[str, ...]] = {
    "매장위치": ("매장 위치가 어디인가요?", "매장 위치가 어디예요?"),
    "주차": ("주차 되나요?", "주차 가능한가요?"),
    "브랜드역사": ("이 브랜드 언제 생겼나요?", "브랜드 언제 생겼나요?"),
    "다음방송": ("다음 방송은 언제 하나요?", "다음 방송 언제 하나요?"),
}


def build_set_c() -> list[FaqCase]:
    """반복질문셋. 그룹 라벨이 클러스터링 정답, expected_doc_id가 근거 정답이다."""
    cases: list[FaqCase] = []
    for group, (doc_id, questions) in _IN_KB_GROUPS.items():
        cases.extend(FaqCase(q, group, doc_id) for q in questions)
    for group, questions in _OUT_OF_KB_GROUPS.items():
        cases.extend(FaqCase(q, group, None) for q in questions)
    return cases


def label_distribution(cases: list[ModerationCase]) -> dict[str, int]:
    """라벨별 건수. 세트 규모·균형을 리포트에 찍기 위한 것."""
    counts: dict[str, int] = {}
    for case in cases:
        counts[case.expected] = counts.get(case.expected, 0) + 1
    return counts
