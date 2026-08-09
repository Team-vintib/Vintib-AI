"""악성 분류기 — 사전 매칭 + 우회패턴 정규화 + 백엔드 스왑.

전부 순수 로직이라 CI에서 그대로 실행된다(무거운 의존성 없음).
"""

import pytest

from app.chat import registry
from app.chat.classifier import (
    HuggingFaceClassifier,
    HybridClassifier,
    RuleBasedClassifier,
    build_classifier,
    jamo_runs,
    normalize,
)

# --- 정규화 ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("병 신 같은 방송", "병신같은방송"),  # 공백 삽입
        ("시발!!!", "시발"),  # 문장부호
        ("MiChin", "michin"),  # 소문자화
        ("이거 M 사이즈", "이거m사이즈"),  # 영문/한글 혼용 유지
    ],
)
def test_normalize_strips_noise(raw, expected):
    assert normalize(raw) == expected


def test_jamo_runs_only_collects_standalone_jamo():
    # 일반 음절은 초성으로 환원하지 않는다 — "소백산"→"ㅅㅂㅅ" 같은 오탐을 막기 위함.
    assert jamo_runs("소백산 다녀왔어요") == ""
    assert jamo_runs("ㅅㅂ 이게 뭐야") == "ㅅㅂ"
    assert jamo_runs("웃기네ㅋㅋㅋㅋ") == "ㅋ"  # 반복은 접힌다


# --- 규칙 기반 판정 -------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "저런 걸 옷이라고 파네 진짜 미친놈인가",  # 직접 욕설
        "여자가 무슨 명품을 입고 방송을 하냐 꼴값이네",  # 혐오/인신공격
        "병 신 같은 방송이네",  # 우회: 공백 삽입
        "개새끼야ㅋㅋㅋㅋㅋ",  # 우회: 웃음 접미사 패딩
        "ㅅㅂ 이게 무슨 가격이야",  # 우회: 초성체(띄어 쓴 자모)
        "ㅄ 이게 무슨 가격이야",  # 우회: 초성체(합쳐진 겹자모 코드포인트, U+3144)
    ],
)
def test_abusive_comments_exceed_threshold(text):
    assert RuleBasedClassifier().score(text).score >= registry.ABUSE_THRESHOLD


@pytest.mark.parametrize(
    "text",
    [
        "이 옷 진짜 예쁘네요 판매자님 감사합니다",
        "소백산 갔다 왔는데 이 자켓 잘 어울리겠네요",  # 초성 환원했다면 ㅅㅂ 오탐이 났을 문장
        "이거 M 사이즈 있나요?",
        "배송은 얼마나 걸리나요?",
        "웃기네ㅋㅋㅋㅋㅋㅋ",
    ],
)
def test_clean_comments_score_zero(text):
    result = RuleBasedClassifier().score(text)
    assert result.score == 0.0
    assert result.label == "clean"


@pytest.mark.parametrize(
    "text",
    [
        "fuck this seller",
        "what the FUCK is this price",  # 대문자 -- normalize()가 소문자화
        "this is bullshit",  # 부분 문자열: "shit"
        "you're such a bitch",
        "asshole seller never responds",
        "stop being a fucking asshole",
    ],
)
def test_english_abuse_terms_exceed_threshold(text):
    assert RuleBasedClassifier().score(text).score >= registry.ABUSE_THRESHOLD


@pytest.mark.parametrize(
    "text",
    [
        "this shirt looks great",  # "shit"의 상위 문자열이 아님(s-h-i-r-t) -- 오탐 방지 확인
        "do you have a discount code",  # "cunt"와 글자 순서가 다름(c-o-u-n-t) -- 오탐 방지 확인
        "thanks for the fast shipping",
    ],
)
def test_english_clean_sentences_stay_clean(text):
    result = RuleBasedClassifier().score(text)
    assert result.score == 0.0
    assert result.label == "clean"


def test_result_label_names_the_matched_rule():
    assert RuleBasedClassifier().score("진짜 미친놈인가").label == "미친놈"


# --- 백엔드 스왑 ----------------------------------------------------------


def test_default_backend_is_hybrid_of_rule_and_kcelectra():
    # CH030: recall이 너무 낮은 rule_based 단독 대신 KcELECTRA-base-hate가 기본이다.
    # 하이브리드(뒤 테스트 참고): 모델 단독은 사전에 있는 뻔한 욕설도 놓치는 게
    # 실측으로 확인돼, rule_based와 OR로 묶는다.
    classifier = build_classifier()
    assert isinstance(classifier, HybridClassifier)
    assert isinstance(classifier._model, HuggingFaceClassifier)


def test_rule_based_still_available_as_fallback():
    # 원복은 registry.ACTIVE_CLASSIFIER를 "rule_based"로 되돌리는 것만으로 가능해야 한다.
    assert isinstance(build_classifier("rule_based"), RuleBasedClassifier)


def test_model_backed_key_builds_hybrid_without_loading():
    # 어댑터 생성 시점에는 transformers를 건드리지 않는다(지연 import) — CI에서도 안전하다.
    classifier = build_classifier("kcelectra_base_hate")
    assert isinstance(classifier, HybridClassifier)
    assert isinstance(classifier._rule, RuleBasedClassifier)
    assert isinstance(classifier._model, HuggingFaceClassifier)


def test_hybrid_defers_to_rule_based_when_it_matches():
    # rule_based가 걸리면 모델을 아예 안 부른다(느린 모델 호출 생략) -- 모델 대신 더미를
    # 넣어서, 호출됐다면 바로 터지게 해서 "안 불렸다"를 검증한다.
    class ExplodingModel:
        def score(self, text: str):  # pragma: no cover - 호출되면 안 됨
            raise AssertionError("rule_based가 이미 걸렸는데 모델까지 호출됨")

    classifier = HybridClassifier(RuleBasedClassifier(), ExplodingModel())
    result = classifier.score("병신같은 방송이네")
    assert result.score >= registry.ABUSE_THRESHOLD


def test_hybrid_falls_back_to_model_when_rule_based_misses():
    class StubModel:
        def score(self, text: str):
            from app.chat.classifier import AbuseResult

            return AbuseResult(score=0.9, label="hate")

    classifier = HybridClassifier(RuleBasedClassifier(), StubModel())
    # 사전/초성체 어디에도 안 걸리는 문장이어야 모델로 넘어간다.
    result = classifier.score("저 사람은 옷 고르는 안목이 부족한 편이다")
    assert result.score == 0.9
    assert result.label == "hate"


def test_unknown_backend_fails_fast():
    with pytest.raises(ValueError, match="등록되지 않은 분류기"):
        build_classifier("does_not_exist")


@pytest.mark.parametrize("text", ["ㅇ", "ㅋㅋ", "넵"])
def test_hybrid_skips_model_for_short_clean_text(text):
    # 실측: KcELECTRA가 "ㅇ"/"ㅋㅋ"/"넵" 같은 흔한 짧은 반응을 전부 ABUSIVE로 오탐했다.
    # 사전/초성체에 안 걸리는 짧은 입력은 모델을 아예 안 태우고 clean으로 본다 --
    # 호출되면 바로 터지는 더미로 "모델이 안 불렸다"를 검증한다.
    class ExplodingModel:
        def score(self, text: str):  # pragma: no cover - 호출되면 안 됨
            raise AssertionError("짧은 입력인데 모델까지 호출됨")

    classifier = HybridClassifier(RuleBasedClassifier(), ExplodingModel())
    result = classifier.score(text)
    assert result.score == 0.0
    assert result.label == "clean"


def test_hybrid_still_catches_short_dictionary_abuse():
    # 길이 게이트는 모델 호출만 건너뛴다 -- 짧아도 사전/초성체에 걸리면 그대로 차단된다.
    classifier = HybridClassifier(RuleBasedClassifier(), None)
    result = classifier.score("ㅂㅅ")
    assert result.score >= registry.ABUSE_THRESHOLD


class _ExplodingModel:
    """호출되면 바로 터지는 더미 -- "모델이 안 불렸다"를 검증하는 용도."""

    def score(self, text: str):  # pragma: no cover - 호출되면 안 됨
        raise AssertionError("화이트리스트에 걸려야 하는데 모델까지 호출됨")


@pytest.mark.parametrize("text", ["ㅋㅋㅋㅋㅋ", "ㅋㅋㅋㅋㅋㅋㅋ", "ㅎㅎㅎㅎㅎㅎ"])
def test_hybrid_collapses_repeats_before_length_gate(text):
    # 실측: "ㅋㅋㅋㅋㅋ"(반복 접기 전 정규화 길이 5)는 길이 게이트를 피해 모델까지 가서
    # 0.8645로 오탐했다. 반복 문자를 접은 길이로 게이트를 걸어야 한다 -- 실제 내용은
    # "ㅋ" 하나뿐이니까.
    classifier = HybridClassifier(RuleBasedClassifier(), _ExplodingModel())
    result = classifier.score(text)
    assert result.score == 0.0
    assert result.label == "clean"


@pytest.mark.parametrize(
    "text",
    [
        "이거 M 사이즈 있나요",
        "이 색상도 있나요",
        "그만 좀 하세요",
        "도배 하지 마세요",
        "광고 그만하세요",
        "조용히 좀 해주세요",
    ],
)
def test_hybrid_whitelists_safe_questions_and_moderation_requests(text):
    # 실측: KcELECTRA가 정중한 질문/관리요청 문장까지 공격적으로 오인식했다(0.50~0.81).
    # 같은 모델에서 진짜 은근한 모욕과 점수가 겹쳐서 임계값 조정으론 못 고치므로, 안전하다고
    # 확인된 패턴 자체를 화이트리스트로 모델 호출 전에 우회시킨다.
    classifier = HybridClassifier(RuleBasedClassifier(), _ExplodingModel())
    result = classifier.score(text)
    assert result.score == 0.0
    assert result.label == "clean"


def test_hybrid_whitelist_does_not_swallow_informal_indirect_insult():
    # 화이트리스트는 정중한 "-나요/-까요" 질문형만 잡는다 -- 반말 의문형("~하냐")이나
    # 서술형은 안 걸려서 사전에 없는 은근한 모욕은 여전히 모델로 넘어가야 한다.
    class StubModel:
        def score(self, text: str):
            from app.chat.classifier import AbuseResult

            return AbuseResult(score=0.9, label="offensive")

    classifier = HybridClassifier(RuleBasedClassifier(), StubModel())
    result = classifier.score("여자가 무슨 명품을 입고 방송을 하냐")
    assert result.score == 0.9
