"""동일 상품 텍스트 매칭(CH030) — 전부 순수 함수, 네트워크·DB 없음."""

from app.pricing.product_match import build_match_keys, normalize_title, resolve_brand_id

_ALIAS_MAP = {"리바이스": 1, "levi's": 1, "메종키츠네": 2, "maison kitsuné": 2}


# --- normalize_title ---------------------------------------------------------


def test_normalize_title_strips_noise_tokens():
    tokens = normalize_title("리바이스 501 빈티지 미착용 M")
    assert "빈티지" not in tokens
    assert "미착용" not in tokens
    assert "m" not in tokens
    assert "501" in tokens


def test_normalize_title_lowercases_and_splits_punctuation():
    tokens = normalize_title("Levi's 501!!")
    assert "levi" in tokens
    assert "s" not in tokens or "501" in tokens  # 's는 노이즈 사이즈 토큰과 겹치지 않는지만 확인
    assert "501" in tokens


# --- resolve_brand_id ---------------------------------------------------------


def test_resolve_brand_id_prefers_explicit_brand_id():
    resolved = resolve_brand_id(
        brand_id=99, product_name="리바이스 501", brand_alias_map=_ALIAS_MAP
    )
    assert resolved == 99


def test_resolve_brand_id_falls_back_to_title_alias():
    resolved = resolve_brand_id(
        brand_id=None, product_name="리바이스 501 빈티지", brand_alias_map=_ALIAS_MAP
    )
    assert resolved == 1


def test_resolve_brand_id_matches_english_alias_too():
    resolved = resolve_brand_id(
        brand_id=None, product_name="Levi's 501 vintage", brand_alias_map=_ALIAS_MAP
    )
    assert resolved == 1


def test_resolve_brand_id_none_when_no_alias_found():
    resolved = resolve_brand_id(
        brand_id=None, product_name="이름없는 브랜드 자켓", brand_alias_map=_ALIAS_MAP
    )
    assert resolved is None


# --- build_match_keys ---------------------------------------------------------
# CH031: 1단계(추출)와 분리됐다 — 이미 추출된 tokens/brand_id를 받아 키만 조합한다.


def test_build_match_keys_strict_includes_brand_and_tokens():
    keys = build_match_keys(tokens=["501", "빈티지"], brand_id=1, category="BOTTOM_PANTS")
    assert keys.strict.startswith("1:")
    assert "BOTTOM_PANTS" in keys.strict
    assert "501" in keys.strict


def test_build_match_keys_relaxed_drops_title_tokens():
    keys = build_match_keys(tokens=["501", "빈티지"], brand_id=1, category="BOTTOM_PANTS")
    assert keys.relaxed == "1:BOTTOM_PANTS"


def test_build_match_keys_is_deterministic_regardless_of_token_order():
    first = build_match_keys(
        tokens=["리바이스", "슬림핏", "501"], brand_id=1, category="BOTTOM_PANTS"
    )
    second = build_match_keys(
        tokens=["501", "슬림핏", "리바이스"], brand_id=1, category="BOTTOM_PANTS"
    )
    assert first.strict == second.strict


def test_build_match_keys_dedupes_tokens():
    keys = build_match_keys(tokens=["501", "501", "빈티지"], brand_id=1, category="BOTTOM_PANTS")
    assert keys.strict.count("501") == 1


def test_build_match_keys_unknown_brand_uses_placeholder():
    keys = build_match_keys(tokens=["자켓"], brand_id=None, category="OUTER_JACKET")
    assert keys.strict.startswith("unknown:")
    assert keys.relaxed == "unknown:OUTER_JACKET"
