"""슬롯 C — comps + 상태로 가격대를 산출한다.

**규칙 baseline이 대조군이다.** LAB-15가 "LLM은 정밀한 정량적 추론에 약하다"고 적어 뒀으므로,
LLM 가격 산정기를 붙이더라도 `중앙값 × 상태계수`를 이기는지 먼저 증명해야 한다(CH002 V4).
그래서 baseline을 먼저 만들고 `llm`은 키만 선언해 둔다.

전부 순수 함수다 — 네트워크도 Redis도 모른다. CI에서 그대로 검증된다.

⚠️ 여기 쓰이는 계수·경계는 전부 `registry.py`의 **근거 없는 임의값**이다. 실판매가 정답셋으로
캘리브레이션하기 전에는 이 값들로 나온 가격의 정확도를 주장할 수 없다.

설계: .claude/plans/ai/CH003-pricing-service-prototype.md
"""

from __future__ import annotations

import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.pricing import registry
from app.pricing.schemas import (
    CompItem,
    CompsStats,
    ConditionGrade,
    ConfidenceLevel,
    PriceRange,
    ReasonCode,
)

__all__ = [
    "Pricer",
    "PricingOutcome",
    "RuleBaselinePricer",
    "build_pricer",
    "condition_coefficient",
]

# 신뢰도 가중치. 표본 수를 가장 무겁게 본다 — 매물 1건으로 낸 가격은 분산이 낮아도 못 믿는다.
_W_SAMPLE = 0.5
_W_USED = 0.2
_W_DISPERSION = 0.3


@dataclass(frozen=True)
class PricingOutcome:
    """가격 산정 결과. 스키마 조립은 service가 한다."""

    priced: bool
    reason_code: ReasonCode
    coefficient: float
    confidence: float
    confidence_level: ConfidenceLevel
    price_range: PriceRange | None = None
    comps_stats: CompsStats | None = None
    comps_used: list[CompItem] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _round_to(value: float, unit: int) -> int:
    if unit <= 1:
        return int(round(value))
    return int(round(value / unit) * unit)


def _percentile(sorted_prices: list[int], fraction: float) -> int:
    """선형 보간 없는 최근접 순위 백분위. n=1에서도 안전하다."""
    if not sorted_prices:
        return 0
    index = int(round(fraction * (len(sorted_prices) - 1)))
    return sorted_prices[index]


def condition_coefficient(score: float, grade: ConditionGrade) -> float:
    """상태 점수를 중앙값에 곱할 계수로 바꾼다.

    **`score/100`을 쓰면 안 된다.** comps 자체가 상태 불명의 중고라 중앙값은 이미 "평균적
    중고"의 가격이다. 그대로 곱하면 70점짜리 평범한 물건이 30% 할인돼 버린다. 기준점에서
    얼마나 벗어났는지로 보정한다.

    점수가 범위를 벗어나면 등급 테이블로 폴백한다.
    """
    if not 0.0 <= score <= 100.0:
        return registry.GRADE_COEFFICIENTS[grade]
    raw = 1.0 + (score - registry.REFERENCE_CONDITION_SCORE) * registry.CONDITION_SENSITIVITY
    return round(_clamp(raw, registry.CONDITION_COEF_MIN, registry.CONDITION_COEF_MAX), 4)


class Pricer(ABC):
    """가격 산정기 인터페이스."""

    key: str

    @abstractmethod
    def price(
        self,
        comps: list[CompItem],
        *,
        condition_score: float,
        condition_grade: ConditionGrade,
        retail_price: int | None = None,
    ) -> PricingOutcome:
        raise NotImplementedError


class RuleBaselinePricer(Pricer):
    """중앙값 × 상태계수. 대조군이자 기본값."""

    key = "rule_baseline"

    def __init__(self, *, min_comps: int) -> None:
        self._min_comps = max(1, min_comps)

    def price(
        self,
        comps: list[CompItem],
        *,
        condition_score: float,
        condition_grade: ConditionGrade,
        retail_price: int | None = None,
    ) -> PricingOutcome:
        coefficient = condition_coefficient(condition_score, condition_grade)

        # 1) 신품으로 확인된 매물은 뺀다. 판별 불가(None)는 남긴다 — 중고 거래 검색 결과라
        #    대개 중고이고, None을 버리면 표본이 거의 남지 않는다.
        usable = [c for c in comps if c.price > 0 and c.is_used is not False]
        if len(usable) < self._min_comps:
            return PricingOutcome(
                priced=False,
                reason_code=ReasonCode.insufficient_comps,
                coefficient=coefficient,
                confidence=0.0,
                confidence_level=ConfidenceLevel.low,
                comps_used=usable,
                rationale=[
                    f"비교 가능한 중고 매물이 {len(usable)}건뿐이라 가격을 제안하지 않았습니다."
                ],
            )

        # 2) 표본이 충분하면 최고·최저 1건씩 잘라낸다. LLM이 가져온 매물은 단일 이상치가
        #    중앙값을 크게 흔든다.
        prices = sorted(c.price for c in usable)
        trimmed = prices[1:-1] if len(prices) >= 5 else prices

        median = int(statistics.median(trimmed))
        p25 = _percentile(trimmed, 0.25)
        p75 = _percentile(trimmed, 0.75)
        confirmed_used = sum(1 for c in usable if c.is_used is True)
        used_ratio = confirmed_used / len(usable)

        confidence = self._confidence(len(trimmed), used_ratio, median, p25, p75)
        mid = _round_to(median * coefficient, registry.PRICE_ROUNDING_UNIT)
        price_range = self._range(mid, confidence)

        return PricingOutcome(
            priced=True,
            reason_code=ReasonCode.priced,
            coefficient=coefficient,
            confidence=confidence,
            confidence_level=_confidence_level(confidence),
            price_range=price_range,
            comps_stats=CompsStats(
                count=len(trimmed),
                median=median,
                p25=p25,
                p75=p75,
                used_ratio=round(used_ratio, 3),
            ),
            comps_used=usable,
            rationale=self._rationale(
                len(trimmed),
                median,
                coefficient,
                condition_score,
                condition_grade,
                mid,
                retail_price,
            ),
        )

    def _confidence(self, count: int, used_ratio: float, median: int, p25: int, p75: int) -> float:
        sample = min(count / registry.CONFIDENCE_SATURATION_COMPS, 1.0)
        spread = (p75 - p25) / median if median > 0 else 1.0
        dispersion = _clamp(1.0 - spread, 0.0, 1.0)
        raw = _W_SAMPLE * sample + _W_USED * used_ratio + _W_DISPERSION * dispersion
        return round(_clamp(raw, 0.0, 1.0), 3)

    def _range(self, mid: int, confidence: float) -> PriceRange:
        """신뢰도가 낮을수록 넓힌다. 단 상한을 둔다 — 무한정 넓히면 적중률은 100%가 되지만
        아무 쓸모가 없다(CH002 §V4)."""
        width = registry.BASE_RANGE_WIDTH + (1.0 - confidence) * (
            registry.MAX_RANGE_WIDTH - registry.BASE_RANGE_WIDTH
        )
        unit = registry.PRICE_ROUNDING_UNIT
        return PriceRange(
            min=max(0, _round_to(mid * (1.0 - width), unit)),
            mid=mid,
            max=_round_to(mid * (1.0 + width), unit),
        )

    def _rationale(
        self,
        count: int,
        median: int,
        coefficient: float,
        score: float,
        grade: ConditionGrade,
        mid: int,
        retail_price: int | None,
    ) -> list[str]:
        lines = [
            f"비교 매물 {count}건의 중앙값은 {median:,}원입니다.",
            f"컨디션 {grade.value}({score:g}점)을 반영해 계수 {coefficient:.2f}를 적용했습니다.",
        ]
        if count < registry.CONFIDENCE_SATURATION_COMPS:
            lines.append("표본이 적어 제안 범위를 넓게 잡았습니다.")
        if retail_price and retail_price > 0:
            discount = (1 - mid / retail_price) * 100
            lines.append(f"신품 정가 {retail_price:,}원 대비 약 {discount:.0f}% 낮은 수준입니다.")
        return lines


def _confidence_level(confidence: float) -> ConfidenceLevel:
    bounds = registry.CONFIDENCE_LEVEL_BOUNDS
    if confidence >= bounds[ConfidenceLevel.high]:
        return ConfidenceLevel.high
    if confidence >= bounds[ConfidenceLevel.medium]:
        return ConfidenceLevel.medium
    return ConfidenceLevel.low


def build_pricer(key: str | None = None, *, min_comps: int) -> Pricer:
    """활성 가격 산정기를 만든다."""
    resolved = key or registry.ACTIVE_PRICER
    if resolved == "rule_baseline":
        return RuleBaselinePricer(min_comps=min_comps)
    if resolved == "llm":
        raise NotImplementedError(
            "LLM 가격 산정기는 아직 구현되지 않았습니다 — 규칙 baseline 대비 우위를 "
            "먼저 증명해야 합니다(CH002 V4)"
        )
    raise ValueError(f"등록되지 않은 pricer 백엔드입니다: {resolved!r}")
