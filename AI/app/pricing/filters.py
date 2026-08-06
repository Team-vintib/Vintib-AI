"""comps 후처리 필터 — 순수 함수(CH017).

LLM이 준 매물을 무조건 신뢰하지 않고, 검색 후에 결정론적으로 걸러낸다('요즘 당근 AI 개발'의
"예외 처리는 프롬프트가 아니라 후처리 레이어" 인사이트). 프롬프트를 계속 다듬는 대신 이 파일이
그 역할을 한다.

**기본은 꺼져 있다**(`registry.ACTIVE_COMPS_FILTER = "none"`). comps 표본이 평균 1.7건뿐인
백엔드에서 필터가 표본을 0건으로 만들 위험이 실재하고, 켜는 게 정확도를 올리는지 내리는지
아직 실측하지 않았다.

설계: .claude/plans/ai/CH017-pricing-cheap-wins.md
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from app.pricing import registry
from app.pricing.schemas import CompItem

__all__ = ["FilterResult", "apply_comps_filters"]


@dataclass(frozen=True)
class FilterResult:
    """필터를 통과한 것과 걸러진 것 + 왜 걸러졌는지."""

    kept: list[CompItem]
    dropped: list[CompItem] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def apply_comps_filters(
    items: list[CompItem], *, brand: str | None = None, key: str | None = None
) -> FilterResult:
    """활성 필터(`registry.ACTIVE_COMPS_FILTER`)를 적용한다. `"none"`이면 전부 통과."""
    resolved = key or registry.ACTIVE_COMPS_FILTER
    if resolved == "none":
        return FilterResult(kept=items)
    if resolved == "keyword_mad":
        return _keyword_then_mad(items, brand=brand)
    raise ValueError(f"등록되지 않은 comps 필터입니다: {resolved!r}")


def _keyword_then_mad(items: list[CompItem], *, brand: str | None) -> FilterResult:
    kept, dropped, notes = filter_by_brand_keyword(items, brand=brand)
    kept, mad_dropped, mad_notes = filter_price_outliers_mad(kept)
    return FilterResult(kept=kept, dropped=[*dropped, *mad_dropped], notes=[*notes, *mad_notes])


def filter_by_brand_keyword(
    items: list[CompItem], *, brand: str | None
) -> tuple[list[CompItem], list[CompItem], list[str]]:
    """브랜드가 주어졌는데 매물 제목에 그 브랜드가 전혀 안 보이면 다른 상품일 가능성이 높다.

    브랜드가 없으면(요청에 브랜드가 안 실려 있으면) 아무것도 거르지 않는다 — 판단 근거가
    없는데 거르면 표본을 줄이기만 한다.
    """
    if not brand or not brand.strip():
        return items, [], []

    needle = brand.strip().lower()
    kept = [item for item in items if needle in item.title.lower()]
    dropped = [item for item in items if needle not in item.title.lower()]
    notes = [f"제목에 '{brand}'가 없는 매물 {len(dropped)}건을 제외했습니다."] if dropped else []
    return kept, dropped, notes


def filter_price_outliers_mad(
    items: list[CompItem],
) -> tuple[list[CompItem], list[CompItem], list[str]]:
    """가격의 MAD(median absolute deviation) 기준 이상치를 제외한다.

    표준편차 대신 MAD를 쓰는 이유: comps가 원래 이상치에 취약한데(단일 매물이 평균을 크게
    흔든다), 표준편차 자체가 그 이상치에 민감하다 — MAD는 이상치에 덜 흔들린다.

    표본이 4건 미만이면 아무것도 거르지 않는다 — 이 정도로 적으면 "이상치"와 "정상 분산"을
    구분할 근거가 없다.
    """
    if len(items) < 4:
        return items, [], []

    prices = [item.price for item in items]
    median = statistics.median(prices)
    deviations = [abs(p - median) for p in prices]
    mad = statistics.median(deviations)
    if mad == 0:
        return items, [], []

    threshold = registry.COMPS_FILTER_MAD_THRESHOLD
    kept: list[CompItem] = []
    dropped: list[CompItem] = []
    for item, deviation in zip(items, deviations, strict=True):
        # 0.6745는 MAD를 표준편차 스케일로 근사하는 표준 상수다(정규분포 가정).
        modified_z = 0.6745 * deviation / mad
        (kept if modified_z <= threshold else dropped).append(item)

    notes = [f"가격이 비정상적으로 튀는 매물 {len(dropped)}건을 제외했습니다."] if dropped else []
    return kept, dropped, notes
