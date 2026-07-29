"""규칙 baseline 가격 산정기 — 순수 로직 검증.

여기서 고정하는 건 **산출 방식의 성질**이지 특정 숫자가 아니다. 계수·경계는 아직 근거 없는
임의값이라(registry 주석 참고) 값 자체를 박아 두면 캘리브레이션할 때마다 테스트가 깨진다.
대신 단조성·상한·반올림처럼 값을 바꿔도 유지돼야 하는 불변식을 검사한다.
"""

from app.pricing import registry
from app.pricing.pricer import RuleBaselinePricer, build_pricer, condition_coefficient
from app.pricing.schemas import CompItem, ConditionGrade, ConfidenceLevel, ReasonCode


def _comp(price: int, *, is_used: bool | None = True) -> CompItem:
    return CompItem(title="t", price=price, source="mock", is_used=is_used)


def _pricer(min_comps: int = 1) -> RuleBaselinePricer:
    return RuleBaselinePricer(min_comps=min_comps)


def _price(comps, score=70.0, grade=ConditionGrade.b, retail=None):
    return _pricer().price(comps, condition_score=score, condition_grade=grade, retail_price=retail)


def test_mid_is_median_times_coefficient_at_reference_score():
    """기준 점수(70)에서는 계수가 1이라 중앙값이 그대로 나온다."""
    outcome = _price([_comp(10_000), _comp(20_000), _comp(30_000)], score=70.0)

    assert outcome.priced
    assert outcome.coefficient == 1.0
    assert outcome.comps_stats.median == 20_000
    assert outcome.price_range.mid == 20_000


def test_condition_score_moves_the_price_monotonically():
    """상태가 좋을수록 비싸야 한다 — 계수 방향이 뒤집히면 여기서 잡힌다."""
    comps = [_comp(10_000), _comp(20_000), _comp(30_000)]
    low = _price(comps, score=40.0).price_range.mid
    mid = _price(comps, score=70.0).price_range.mid
    high = _price(comps, score=95.0).price_range.mid

    assert low < mid < high


def test_condition_coefficient_is_clamped():
    """극단값이 들어와도 계수가 registry 한계를 넘지 않는다."""
    assert condition_coefficient(0.0, ConditionGrade.c) == registry.CONDITION_COEF_MIN
    assert condition_coefficient(100.0, ConditionGrade.s) <= registry.CONDITION_COEF_MAX


def test_out_of_range_score_falls_back_to_grade_table():
    """점수가 범위를 벗어나면 등급으로 계수를 정한다."""
    assert (
        condition_coefficient(-1.0, ConditionGrade.a)
        == registry.GRADE_COEFFICIENTS[ConditionGrade.a]
    )


def test_extreme_outlier_is_trimmed_away():
    """표본 5건 이상이면 최고·최저를 잘라낸다 — LLM comps는 이상치 하나가 중앙값을 흔든다."""
    comps = [_comp(p) for p in (10_000, 19_000, 20_000, 21_000, 900_000)]
    outcome = _price(comps)

    assert outcome.comps_stats.count == 3  # 5건 중 양끝 제거
    assert outcome.comps_stats.median == 20_000


def test_price_is_rounded_to_registry_unit():
    outcome = _price([_comp(10_123), _comp(20_456), _comp(30_789)])

    assert outcome.price_range.mid % registry.PRICE_ROUNDING_UNIT == 0
    assert outcome.price_range.min % registry.PRICE_ROUNDING_UNIT == 0
    assert outcome.price_range.max % registry.PRICE_ROUNDING_UNIT == 0


def test_range_width_never_exceeds_the_cap():
    """폭 상한이 없으면 '적중률 100%'를 만들 수 있어 지표가 무의미해진다(CH002 §V4)."""
    outcome = _price([_comp(10_000)])  # 표본 1건 → 신뢰도 최저 → 폭 최대
    span = outcome.price_range.max - outcome.price_range.min
    ratio = span / outcome.price_range.mid

    assert ratio <= registry.MAX_RANGE_WIDTH * 2 + 0.01


def test_low_sample_widens_the_range():
    """표본이 적으면 범위가 넓어야 한다."""
    narrow = _price([_comp(p) for p in (19_000, 20_000, 21_000, 20_500, 19_500)]).price_range
    wide = _price([_comp(20_000)]).price_range

    assert (wide.max - wide.min) / wide.mid > (narrow.max - narrow.min) / narrow.mid


def test_no_comps_is_not_priced_but_not_an_error():
    """근거가 없으면 가격을 내지 않는다. 그래도 예외가 아니라 결과다."""
    outcome = _price([])

    assert outcome.priced is False
    assert outcome.reason_code is ReasonCode.insufficient_comps
    assert outcome.price_range is None
    assert outcome.confidence_level is ConfidenceLevel.low


def test_min_comps_threshold_is_respected():
    """백엔드별 최소 표본 미만이면 가격을 내지 않는다."""
    pricer = RuleBaselinePricer(min_comps=3)
    outcome = pricer.price(
        [_comp(10_000), _comp(20_000)],
        condition_score=70.0,
        condition_grade=ConditionGrade.b,
    )

    assert outcome.priced is False


def test_confirmed_new_items_are_excluded():
    """신품으로 확인된 매물은 중고 시세를 오염시키므로 뺀다. 판별 불가(None)는 남긴다."""
    comps = [_comp(10_000), _comp(900_000, is_used=False), _comp(12_000, is_used=None)]
    outcome = _price(comps)

    assert outcome.comps_stats.count == 2
    assert all(c.is_used is not False for c in outcome.comps_used)


def test_retail_price_only_adds_a_rationale_line():
    """정가는 앵커가 아니라 근거 문장일 뿐이다 — 가격 자체는 바뀌지 않는다."""
    comps = [_comp(10_000), _comp(20_000), _comp(30_000)]
    without = _price(comps)
    with_retail = _price(comps, retail=100_000)

    assert with_retail.price_range.mid == without.price_range.mid
    assert len(with_retail.rationale) > len(without.rationale)


def test_llm_pricer_is_declared_but_not_implemented():
    """레지스트리에 키만 있고 구현이 없다는 걸 명시적으로 고정한다."""
    try:
        build_pricer("llm", min_comps=1)
    except NotImplementedError as exc:
        assert "CH002" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("llm pricer가 구현된 것처럼 통과했다")
