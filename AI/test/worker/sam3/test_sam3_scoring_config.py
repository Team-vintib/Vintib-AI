"""SAM3 레지스트리의 점수·등급 상수 정합성 검증.

**이 값들은 근거 없는 임의값**이라(라벨링된 검증셋이 없다) 절대값은 고정하지 않고 순서·구조만
고정한다 — 가중치를 실측으로 갈아끼울 때 테스트가 발목을 잡지 않으면서도, "SUSPECTED가
DETECTED보다 더 깎인다" 같은 뒤집힌 설정은 잡히게 하는 게 목적이다.
"""

from sam3 import registry
from sam3.contracts import ConditionGrade, FindingStatus, Severity


def test_score_factors_cover_every_enum_value():
    assert set(registry.SEVERITY_FACTORS) == set(Severity)
    assert set(registry.STATUS_FACTORS) == set(FindingStatus)


def test_severity_factors_increase_with_severity():
    factors = registry.SEVERITY_FACTORS
    assert factors[Severity.minor] < factors[Severity.moderate] < factors[Severity.major]


def test_all_score_factors_are_positive():
    for factor in (*registry.SEVERITY_FACTORS.values(), *registry.STATUS_FACTORS.values()):
        assert factor > 0.0


def test_suspected_is_penalized_less_than_detected():
    assert registry.STATUS_FACTORS[FindingStatus.suspected] < (
        registry.STATUS_FACTORS[FindingStatus.detected]
    )


def test_severity_bounds_are_ascending():
    low, high = registry.SEVERITY_BOUNDS
    assert 0.0 < low < high


def test_grade_thresholds_are_descending():
    scores = [score for score, _ in registry.GRADE_THRESHOLDS]
    assert scores == sorted(scores, reverse=True)


def test_grade_thresholds_stay_inside_the_score_range():
    for score, _ in registry.GRADE_THRESHOLDS:
        assert 0.0 < score <= 100.0


def test_lowest_grade_has_no_lower_bound():
    grades = [grade for _, grade in registry.GRADE_THRESHOLDS]
    assert ConditionGrade.c not in grades
    assert len(grades) == len(set(ConditionGrade)) - 1
    assert len(set(grades)) == len(grades)


def test_grade_thresholds_are_ordered_like_the_grades():
    grades = [grade for _, grade in registry.GRADE_THRESHOLDS]
    assert grades == [ConditionGrade.s, ConditionGrade.a, ConditionGrade.b]


def test_statement_exemption_switch_is_a_boolean_flag():
    assert isinstance(registry.EXEMPT_MINOR_SUSPECTED_FROM_STATEMENT, bool)
