"""내부 호가 편향 완화 필터(CH016 §3.3, CH030) — 전부 순수 함수, 네트워크·DB 없음."""

from datetime import UTC, datetime

from app.pricing.hedge import (
    InternalCandidate,
    apply_hedge_filters,
    filter_by_sale_status,
    filter_sane_price,
    filter_stale_listings,
)

_NOW = datetime(2026, 8, 6, tzinfo=UTC)


def _candidate(**overrides) -> InternalCandidate:
    base = {
        "product_id": 1,
        "title": "상품",
        "price": 50_000,
        "sale_type": "DIRECT_SALE",
        "sale_status": "ON_SALE",
        "created_at": "2026-08-01T00:00:00",
    }
    base.update(overrides)
    return InternalCandidate(**base)


# --- 판매상태 필터 (CH030) -----------------------------------------------------


def test_keeps_asking_and_sold_both():
    """호가(ON_SALE)·완료거래(SOLD) 둘 다 남긴다 — 사용자 결정 4번."""
    candidates = [
        _candidate(sale_status="ON_SALE"),
        _candidate(sale_status="SOLD", sale_type="DIRECT_SALE"),
        _candidate(sale_status="SOLD", sale_type="AUCTION"),
    ]
    kept, notes = filter_by_sale_status(candidates)

    assert len(kept) == 3
    assert notes == []


def test_drops_auction_in_progress_and_unknown_status():
    """확정 가격이 없는 진행 중 경매·상태 불명 매물은 뺀다."""
    candidates = [
        _candidate(sale_status="AUCTION_IN_PROGRESS"),
        _candidate(sale_status=None),
    ]
    kept, notes = filter_by_sale_status(candidates)

    assert kept == []
    assert notes


def test_no_notes_when_nothing_dropped():
    candidates = [_candidate(sale_status="ON_SALE")]
    kept, notes = filter_by_sale_status(candidates)

    assert len(kept) == 1
    assert notes == []


# --- price_kind 태그 (CH030) ---------------------------------------------------


def test_price_kind_tags_asking():
    assert _candidate(sale_status="ON_SALE").price_kind == "ASKING"


def test_price_kind_tags_sold_direct():
    candidate = _candidate(sale_status="SOLD", sale_type="DIRECT_SALE")
    assert candidate.price_kind == "SOLD_DIRECT"


def test_price_kind_tags_sold_auction():
    candidate = _candidate(sale_status="SOLD", sale_type="AUCTION")
    assert candidate.price_kind == "SOLD_AUCTION"


def test_price_kind_none_for_unresolvable_state():
    candidate = _candidate(sale_status="AUCTION_IN_PROGRESS")
    assert candidate.price_kind is None


# --- 최신성 필터 --------------------------------------------------------------


def test_drops_stale_listings():
    fresh = _candidate(product_id=1, created_at="2026-08-01T00:00:00")
    stale = _candidate(product_id=2, created_at="2025-01-01T00:00:00")

    kept, notes = filter_stale_listings([fresh, stale], now=_NOW, max_age_days=180)

    assert [c.product_id for c in kept] == [1]
    assert notes


def test_keeps_listing_with_unparseable_date():
    """판단 근거가 없다고 표본을 줄이지 않는다."""
    candidate = _candidate(created_at="이상한 값")
    kept, notes = filter_stale_listings([candidate], now=_NOW)

    assert kept == [candidate]
    assert notes == []


def test_keeps_listing_with_missing_date():
    candidate = _candidate(created_at=None)
    kept, notes = filter_stale_listings([candidate], now=_NOW)

    assert kept == [candidate]


# --- 가격 절대 방어 -----------------------------------------------------------


def test_drops_prices_outside_sane_bounds():
    too_cheap = _candidate(product_id=1, price=500)
    sane = _candidate(product_id=2, price=50_000)
    too_expensive = _candidate(product_id=3, price=200_000_000)

    kept, notes = filter_sane_price([too_cheap, sane, too_expensive])

    assert [c.product_id for c in kept] == [2]
    assert notes


def test_drops_missing_price():
    candidate = _candidate(price=None)
    kept, notes = filter_sane_price([candidate])

    assert kept == []
    assert notes


# --- 조합 ---------------------------------------------------------------------


def test_apply_hedge_filters_chains_all_three():
    bad_status = _candidate(product_id=1, sale_status="AUCTION_IN_PROGRESS")
    stale = _candidate(product_id=2, created_at="2020-01-01T00:00:00")
    insane_price = _candidate(product_id=3, price=100)
    good = _candidate(product_id=4)

    kept, notes = apply_hedge_filters([bad_status, stale, insane_price, good], now=_NOW)

    assert [c.product_id for c in kept] == [4]
    assert len(notes) == 3  # 세 필터 각각 최소 1건씩 걸렀다
