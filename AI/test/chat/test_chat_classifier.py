"""악성 분류기 — 사전 매칭 + 우회패턴 정규화 + 백엔드 스왑.

전부 순수 로직이라 CI에서 그대로 실행된다(무거운 의존성 없음).
"""

import pytest

from app.chat import registry
from app.chat.classifier import (
    HuggingFaceClassifier,
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


def test_result_label_names_the_matched_rule():
    assert RuleBasedClassifier().score("진짜 미친놈인가").label == "미친놈"


# --- 백엔드 스왑 ----------------------------------------------------------


def test_default_backend_is_kcelectra():
    # CH030: recall이 너무 낮은 rule_based 대신 KcELECTRA-base-hate가 기본이다.
    assert isinstance(build_classifier(), HuggingFaceClassifier)


def test_rule_based_still_available_as_fallback():
    # 원복은 registry.ACTIVE_CLASSIFIER를 "rule_based"로 되돌리는 것만으로 가능해야 한다.
    assert isinstance(build_classifier("rule_based"), RuleBasedClassifier)


def test_model_backed_key_builds_hf_adapter_without_loading():
    # 어댑터 생성 시점에는 transformers를 건드리지 않는다(지연 import) — CI에서도 안전하다.
    assert isinstance(build_classifier("kcelectra_base_hate"), HuggingFaceClassifier)


def test_unknown_backend_fails_fast():
    with pytest.raises(ValueError, match="등록되지 않은 분류기"):
        build_classifier("does_not_exist")
