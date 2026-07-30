"""SAM3 레지스트리의 점수·등급 상수 정합성 검증.

`worker/models/clipseg/registry.py`용 테스트(`test_clipseg_scoring_config.py`)와 같은 목적·같은
값이어야 한다(점수 산식은 findings의 출처가 아니라 정책 문제) — **이 값들은 근거 없는
임의값**이라 절대값은 고정하지 않고 순서·구조만 고정한다.
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


def test_scoring_constants_match_clipseg_registry():
    """두 백엔드가 같은 하자에 다른 점수를 매기면 판매자·구매자 신뢰가 깨진다."""
    import registry as clipseg_registry

    assert registry.SEVERITY_FACTORS == clipseg_registry.SEVERITY_FACTORS
    assert registry.STATUS_FACTORS == clipseg_registry.STATUS_FACTORS
    assert registry.SEVERITY_BOUNDS == clipseg_registry.SEVERITY_BOUNDS
    assert registry.GRADE_THRESHOLDS == clipseg_registry.GRADE_THRESHOLDS
    assert (
        registry.EXEMPT_MINOR_SUSPECTED_FROM_STATEMENT
        == clipseg_registry.EXEMPT_MINOR_SUSPECTED_FROM_STATEMENT
    )
