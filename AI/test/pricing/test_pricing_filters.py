"""comps 후처리 필터 — 순수 로직 검증(CH017 B3). 네트워크·DB 없음."""

import pytest

from app.pricing.filters import (
    apply_comps_filters,
    filter_by_brand_keyword,
    filter_price_outliers_mad,
)
from app.pricing.schemas import CompItem


def _comp(title: str, price: int) -> CompItem:
    return CompItem(title=title, price=price, source="llm_web_search")


# --- apply_comps_filters(기본 off) ------------------------------------------


def test_default_filter_passes_everything_through():
    """`registry.ACTIVE_COMPS_FILTER = "none"`이 기본이라 지금은 아무것도 안 걸러진다."""
    items = [_comp("리바이스 501", 30_000), _comp("나이키 후드", 900_000)]
    result = apply_comps_filters(items, brand="리바이스")

    assert result.kept == items
    assert result.dropped == []


def test_unknown_filter_key_raises():
    with pytest.raises(ValueError, match="등록되지 않은"):
        apply_comps_filters([], key="없는필터")


def test_keyword_mad_filter_can_be_selected_explicitly():
    items = [_comp("리바이스 501", 30_000), _comp("나이키 후드", 900_000)]
    result = apply_comps_filters(items, brand="리바이스", key="keyword_mad")

    assert [item.title for item in result.kept] == ["리바이스 501"]
    assert [item.title for item in result.dropped] == ["나이키 후드"]


# --- filter_by_brand_keyword -------------------------------------------------


def test_brand_filter_keeps_items_mentioning_the_brand():
    items = [_comp("리바이스 501 빅E", 30_000), _comp("나이키 후드 집업", 40_000)]
    kept, dropped, notes = filter_by_brand_keyword(items, brand="리바이스")

    assert [item.title for item in kept] == ["리바이스 501 빅E"]
    assert [item.title for item in dropped] == ["나이키 후드 집업"]
    assert notes


def test_brand_filter_is_case_insensitive():
    items = [_comp("LEVIS 501", 30_000)]
    kept, dropped, _ = filter_by_brand_keyword(items, brand="levis")

    assert kept == items
    assert dropped == []


def test_brand_filter_passes_through_when_brand_missing():
    """판단 근거(브랜드)가 없으면 거르지 않는다 — 표본만 줄어드는 걸 막는다."""
    items = [_comp("리바이스 501", 30_000)]
    kept, dropped, notes = filter_by_brand_keyword(items, brand=None)

    assert kept == items
    assert dropped == []
    assert notes == []


# --- filter_price_outliers_mad -----------------------------------------------


def test_mad_filter_drops_the_extreme_outlier():
    items = [_comp("a", 19_000), _comp("b", 20_000), _comp("c", 21_000), _comp("d", 5_000_000)]
    kept, dropped, notes = filter_price_outliers_mad(items)

    assert [item.price for item in kept] == [19_000, 20_000, 21_000]
    assert [item.price for item in dropped] == [5_000_000]
    assert notes


def test_mad_filter_skips_when_sample_too_small():
    """표본 4건 미만은 이상치를 판단할 근거가 없다."""
    items = [_comp("a", 10_000), _comp("b", 5_000_000)]
    kept, dropped, notes = filter_price_outliers_mad(items)

    assert kept == items
    assert dropped == []
    assert notes == []


def test_mad_filter_keeps_everything_when_all_prices_identical():
    """MAD가 0이면(전부 동일 가격) 0으로 나누기를 피하고 아무것도 거르지 않는다."""
    items = [_comp("a", 20_000) for _ in range(5)]
    kept, dropped, _ = filter_price_outliers_mad(items)

    assert kept == items
    assert dropped == []
