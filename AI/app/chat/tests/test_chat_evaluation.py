"""정확도 평가 하네스 검증 + CI 회귀 게이트 (S15P11A108-196).

두 종류의 테스트가 섞여 있다.

1. **하네스 자체 검증** — 지표 계산(혼동행렬·P/R/F1·백분위)과 평가셋 생성이 맞는지.
2. **회귀 게이트** — 실측치를 하한으로 고정해 품질이 나빠지면 CI가 잡게 한다.
   결함 수정은 이번 스코프가 아니므로(196은 테스트 티켓) 게이트는 **품질 강제가 아니라 회귀
   방지**다. 하한은 실측치보다 약간 낮게 잡았다.

오탐/미탐은 값이 아니라 **집합**으로 고정한다. `<=` 부분집합이라 분류기를 개선하면 집합이
줄어들어 그대로 통과하고, 악화되면 새 항목이 생겨 실패한다.

평가 대상이 stdlib + numpy만 쓰므로 이 파일은 CI에서 스킵 없이 실행된다.
"""

import pytest

from app.chat import registry
from app.chat.classifier import AbuseClassifier, AbuseResult, RuleBasedClassifier
from app.chat.eval_dataset import (
    ABUSIVE,
    NORMAL,
    ModerationCase,
    build_set_a,
    build_set_b,
    build_set_c,
    label_distribution,
    to_chosung,
    to_spaced,
    with_dot_separator,
    with_latin_lookalike,
    with_laugh_suffix,
    with_vowel_stretch,
)
from app.chat.evaluation import evaluate_faq, evaluate_moderation
from app.chat.faq import build_retriever

# --- 우회 변형 생성기 -----------------------------------------------------


@pytest.mark.parametrize(
    ("generator", "given", "expected"),
    [
        (to_chosung, "미친놈아", "ㅁㅊㄴㅇ"),
        (to_chosung, "병 신", "ㅂ ㅅ"),  # 한글이 아닌 문자는 그대로
        (to_spaced, "병신같은게", "병 신 같 은 게"),
        (with_laugh_suffix, "한심하네", "한심하네ㅋㅋㅋㅋㅋㅋ"),
        (with_vowel_stretch, "시발", "시이이발"),  # 첫 음절 모음(ㅣ) -> '이' 2회
        (with_vowel_stretch, "개새끼", "개애애새끼"),
        (with_dot_separator, "개새끼", "개.새.끼"),
        (with_latin_lookalike, "시발", "si발"),  # 첫 매칭 음절만 로마자화
    ],
)
def test_evasion_generators(generator, given, expected):
    assert generator(given) == expected


def test_generators_pass_through_when_nothing_applies():
    # 한글 음절이 없으면 원문 그대로 — 호출부가 중복 케이스를 만들지 않도록.
    assert with_vowel_stretch("abc") == "abc"
    assert with_latin_lookalike("abc") == "abc"


# --- 평가셋 구성 ----------------------------------------------------------


def test_set_a_reproduces_the_benchmark_sample_set():
    """기존 벤치마크와 대조 가능해야 하므로 규모·분포가 원본과 같아야 한다."""
    cases = build_set_a()
    assert len(cases) == 210
    assert label_distribution(cases) == {NORMAL: 126, ABUSIVE: 84}


def test_set_a_covers_the_three_original_evasion_variants():
    variants = {c.variant for c in build_set_a() if c.expected == ABUSIVE}
    assert variants == {"원문", "웃음패딩", "초성체", "띄어쓰기"}


def test_set_b_adds_axes_that_set_a_lacks():
    cases = build_set_b()
    variants = {c.variant for c in cases}
    # Set A에 없는 축: 함정정상(오탐 유발), 문맥형 악성, 추가 우회 변형.
    assert {"함정정상", "문맥형", "모음늘이기", "구두점", "로마자"} <= variants
    assert label_distribution(cases) == {NORMAL: 13, ABUSIVE: 18}


def test_set_c_pairs_every_in_kb_group_with_a_faq_doc():
    cases = build_set_c()
    in_kb = [c for c in cases if c.expected_doc_id is not None]
    out_of_kb = [c for c in cases if c.expected_doc_id is None]
    assert len(in_kb) == 18
    assert len(out_of_kb) == 8
    # 그룹마다 근거 문서가 하나로 일관돼야 한다.
    by_group: dict[str, set[str]] = {}
    for case in in_kb:
        by_group.setdefault(case.group, set()).add(case.expected_doc_id)
    assert all(len(docs) == 1 for docs in by_group.values())


# --- 지표 계산 ------------------------------------------------------------


class _FixedClassifier(AbuseClassifier):
    """지정한 문장만 악성 점수를 주는 테스트 스텁."""

    def __init__(self, abusive: set[str]) -> None:  # noqa: ANN101 - 테스트 스텁
        self._abusive = abusive

    def score(self, text: str) -> AbuseResult:
        if text in self._abusive:
            return AbuseResult(score=1.0, label="stub")
        return AbuseResult(score=0.0, label="clean")


def _cases(*pairs: tuple[str, str]) -> list[ModerationCase]:
    return [ModerationCase(text, label, "원문") for text, label in pairs]


def test_confusion_matrix_counts_each_quadrant():
    cases = _cases(("a", ABUSIVE), ("b", ABUSIVE), ("c", NORMAL), ("d", NORMAL))
    result = evaluate_moderation(cases, _FixedClassifier({"a", "c"}), name="t")

    assert (result.true_positive, result.false_negative) == (1, 1)  # a 잡음, b 놓침
    assert (result.false_positive, result.true_negative) == (1, 1)  # c 오탐, d 통과
    assert result.total == 4
    assert result.accuracy == 0.5
    assert result.abuse_precision == 0.5
    assert result.abuse_recall == 0.5
    assert result.abuse_f1 == 0.5
    assert result.normal_recall == 0.5


def test_perfect_classifier_scores_one():
    cases = _cases(("a", ABUSIVE), ("b", NORMAL))
    result = evaluate_moderation(cases, _FixedClassifier({"a"}), name="t")
    assert result.accuracy == 1.0
    assert result.abuse_precision == result.abuse_recall == result.abuse_f1 == 1.0
    assert not result.false_positives and not result.false_negatives


def test_metrics_are_zero_not_error_on_empty_denominators():
    # 악성 샘플이 하나도 없으면 recall 분모가 0 — NaN이 아니라 0.0이어야 한다.
    result = evaluate_moderation(_cases(("a", NORMAL)), _FixedClassifier(set()), name="t")
    assert result.abuse_precision == 0.0
    assert result.abuse_recall == 0.0
    assert result.abuse_f1 == 0.0
    assert evaluate_moderation([], _FixedClassifier(set()), name="t").accuracy == 0.0


def test_misclassified_cases_carry_diagnosis():
    cases = [ModerationCase("놓친 문장", ABUSIVE, "초성체")]
    result = evaluate_moderation(cases, _FixedClassifier(set()), name="t")
    (missed,) = result.false_negatives
    assert missed.comment == "놓친 문장"
    assert missed.variant == "초성체"  # 미탐 원인 추적
    assert missed.predicted == NORMAL


def test_variant_recall_uses_all_abusive_cases_as_denominator():
    cases = [
        ModerationCase("x1", ABUSIVE, "초성체"),
        ModerationCase("x2", ABUSIVE, "초성체"),
        ModerationCase("y1", ABUSIVE, "원문"),
    ]
    result = evaluate_moderation(cases, _FixedClassifier({"x1"}), name="t")
    assert result.variant_recall() == {"초성체": (1, 2), "원문": (0, 1)}


def test_latency_percentiles_are_ordered():
    cases = _cases(*[(f"c{i}", NORMAL) for i in range(20)])
    stats = evaluate_moderation(cases, _FixedClassifier(set()), name="t").latency_stats()
    assert stats["p50"] <= stats["p95"] <= stats["p99"]


def test_clustering_metrics_trade_precision_for_recall():
    faq = evaluate_faq(build_set_c(), build_retriever())
    sweep = faq.threshold_sweep()
    # 임계치를 올리면 recall은 단조 감소한다(같은 쌍 집합에서 예측만 좁아지므로).
    recalls = [point["recall"] for point in sweep]
    assert recalls == sorted(recalls, reverse=True)


# --- 회귀 게이트: 비매너 판정 ---------------------------------------------

# 2026-07-26 실측(Set A 210건): accuracy 66.7% / 악성 P 100.0% R 16.7% / 오탐 0 / 미탐 70.
# 하한은 실측치보다 약간 낮게 — 부서지기 쉬운 게이트를 만들지 않는다.
SET_A_MIN_ACCURACY = 0.64
SET_A_MIN_ABUSE_PRECISION = 0.95
SET_A_MIN_ABUSE_RECALL = 0.15
SET_A_MAX_FALSE_NEGATIVES = 70  # 미탐이 이보다 늘면 회귀


@pytest.fixture(scope="module")
def set_a_result():
    return evaluate_moderation(build_set_a(), RuleBasedClassifier(), name="Set A")


@pytest.fixture(scope="module")
def set_b_result():
    return evaluate_moderation(build_set_b(), RuleBasedClassifier(), name="Set B")


@pytest.fixture(scope="module")
def faq_result():
    return evaluate_faq(build_set_c(), build_retriever())


def test_set_a_metrics_do_not_regress(set_a_result):
    assert set_a_result.accuracy >= SET_A_MIN_ACCURACY
    assert set_a_result.abuse_precision >= SET_A_MIN_ABUSE_PRECISION
    assert set_a_result.abuse_recall >= SET_A_MIN_ABUSE_RECALL
    assert set_a_result.false_negative <= SET_A_MAX_FALSE_NEGATIVES


def test_set_a_produces_no_false_positives(set_a_result):
    # Set A의 정상 문장에는 사전 표제어가 없어 오탐이 0이어야 한다.
    assert set_a_result.false_positives == []


def test_moderation_latency_meets_design_target(set_a_result):
    # 설계 목표는 판정 경로 p95 300ms. 규칙 기반은 자릿수 여유가 크다.
    assert set_a_result.latency_stats()["p95"] < 300.0


# 알려진 오탐 — 전부 **사전 표제어를 부분 문자열로 품은 정상 문장**이다.
# 원인은 두 가지: ① 사전 어휘가 일반 명사와 겹침(새끼/쓰레기/등신) ② 부분 문자열 매칭이
# 다른 단어의 일부를 잡음(시발점/등신대/닥쳐오는/꺼지지). 수정은 별도 티켓.
KNOWN_FALSE_POSITIVES = frozenset(
    {
        "강아지 새끼 너무 귀여워요",
        "고양이 새끼 데려왔어요",
        "여기가 시발점이네요",
        "등신대 사진 보고 왔어요",
        "쓰레기 분리배출 하고 왔어요",
        "죽어라 일하고 이거 사려고요",
        "닥쳐오는 겨울에 입을 옷 찾고 있어요",
        "꺼지지 않는 인기템이네요",
    }
)

# 알려진 미탐 — 문맥형 6건은 어휘 사전으로는 **구조적으로** 못 잡는다(문맥 판단 필요).
# 나머지는 정규화가 커버하지 않는 우회 변형(모음 늘이기·로마자화·문자 치환)과 사전 미포함 어휘.
KNOWN_FALSE_NEGATIVES = frozenset(
    {
        "얼굴이 참 특이하시네요 ㅋㅋ",
        "이런 걸 파는 사람 수준 알만하다",
        "그 나이에 그런 옷을 왜 입으시는지",
        "돈이 없어서 이런 걸 파시는 건가요",
        "말투부터 신뢰가 안 가네요",
        "옷은 안 팔리고 시간만 버리시네요",
        "시이이발",
        "si발",
        "미이이친놈",
        "mi친놈",
        "ㅗㅗ 방송 접어라",
        "졸라 짜증나네",
        "s1발 진짜 뭐하냐",
    }
)


def test_no_new_false_positives(set_b_result):
    found = {case.comment for case in set_b_result.false_positives}
    assert found <= KNOWN_FALSE_POSITIVES, f"새 오탐: {found - KNOWN_FALSE_POSITIVES}"


def test_no_new_false_negatives(set_b_result):
    found = {case.comment for case in set_b_result.false_negatives}
    assert found <= KNOWN_FALSE_NEGATIVES, f"새 미탐: {found - KNOWN_FALSE_NEGATIVES}"


def test_punctuation_evasion_is_fully_caught(set_b_result):
    # 정규화가 실제로 값을 하는 축 — 구두점 삽입은 3/3 잡는다. 여기가 깨지면 정규화 회귀다.
    caught, total = set_b_result.variant_recall()["구두점"]
    assert caught == total


# --- 회귀 게이트: 반복질문 근거 -------------------------------------------

# 2026-07-26 실측(Set C 26건 / 325쌍): 클러스터링 P 87.5% R 95.5%,
# 근거 정확도 100%, 침묵 정확도 100%, 환각 0건.
MIN_CLUSTER_PRECISION = 0.80
MIN_CLUSTER_RECALL = 0.90
MIN_DOC_ACCURACY = 0.95


def test_clustering_does_not_regress(faq_result):
    metrics = faq_result.clustering_metrics(registry.embedder_config()["cluster_similarity"])
    assert metrics["precision"] >= MIN_CLUSTER_PRECISION
    assert metrics["recall"] >= MIN_CLUSTER_RECALL


def test_grounded_answers_cite_the_right_document(faq_result):
    assert faq_result.doc_accuracy >= MIN_DOC_ACCURACY
    assert faq_result.wrong_doc_cases == []


def test_never_answers_without_evidence(faq_result):
    """ "근거 있는 경우에만 응답"은 정책이라 회귀 여지를 두지 않는다 — 환각 0건 강제."""
    assert faq_result.hallucinated_cases == []
    assert faq_result.silence_accuracy == 1.0


def test_every_eval_question_reaches_the_faq_path(faq_result):
    # B-1 규칙 필터가 질문으로 못 잡으면 뒤 단계로 가지 못한다 — 평가셋 전체가 통과해야 한다.
    assert faq_result.question_detection_misses == []
