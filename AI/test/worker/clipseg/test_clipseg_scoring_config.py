"""점수·등급 상수의 정합성 검증.

**이 값들은 근거 없는 임의값이다**(라벨링된 검증셋이 없다). 그래서 여기서는 절대값을 고정하지
않고 **순서와 구조만** 고정한다 — 가중치를 실측으로 갈아끼울 때 테스트가 발목을 잡지 않으면서도,
"SUSPECTED가 DETECTED보다 더 깎인다" 같은 뒤집힌 설정은 잡히게 하는 게 목적이다.
"""

import registry
from contracts import ConditionGrade, FindingStatus, Severity


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
    # 오탐이 가격을 깎지 않게 하는 완충이다.
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
    # C는 "그 외"라서 하한을 갖지 않는다 — 하한이 붙으면 어떤 점수도 등급을 못 받는 구간이 생긴다.
    grades = [grade for _, grade in registry.GRADE_THRESHOLDS]
    assert ConditionGrade.c not in grades
    assert len(grades) == len(set(ConditionGrade)) - 1
    assert len(set(grades)) == len(grades)


def test_grade_thresholds_are_ordered_like_the_grades():
    # 점수 하한이 높은 쪽이 더 좋은 등급이어야 한다(S > A > B).
    grades = [grade for _, grade in registry.GRADE_THRESHOLDS]
    assert grades == [ConditionGrade.s, ConditionGrade.a, ConditionGrade.b]


def test_statement_exemption_switch_is_a_boolean_flag():
    # 소명 면제 규칙을 코드에 흩뿌리지 않고 한 곳에서 끌 수 있게 둔 스위치다.
    assert isinstance(registry.EXEMPT_MINOR_SUSPECTED_FROM_STATEMENT, bool)
