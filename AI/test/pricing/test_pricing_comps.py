"""comps 수집 — 파싱·쿼리 조립·mock 결정성 검증.

**네트워크에 절대 닿지 않는다.** LLM 백엔드도 키가 없을 때 fetch 전에 끊기는 것만 확인한다
(`AI/CLAUDE.md` 하드 룰: GMS 호출은 사람이 직접 실행한다).
"""

import pytest

from app.pricing.comps import (
    CompsUnavailable,
    LlmWebSearchCompsSource,
    MockCompsSource,
    _extract_json_array,
    _rows_to_items,
    build_comps_source,
    build_query,
)
from app.pricing.schemas import GarmentCategory, ReasonCode

# --- 쿼리 조립 --------------------------------------------------------------


def test_brand_is_prepended_when_missing_from_name():
    assert build_query("501 빅E 데님", brand="리바이스") == "리바이스 501 빅E 데님"


def test_brand_is_not_duplicated():
    """상품명에 이미 브랜드가 들어 있는 경우가 흔하다 — 중복 토큰은 검색을 흐린다."""
    assert build_query("리바이스 501", brand="리바이스") == "리바이스 501"


def test_category_term_is_appended_in_korean():
    """enum 값(BOTTOM_PANTS)을 그대로 넣으면 검색이 안 된다."""
    query = build_query("리바이스 501", category=GarmentCategory.bottom_pants)
    assert query.endswith("팬츠")


def test_query_works_without_brand_or_category():
    assert build_query("  빈티지 니트  ") == "빈티지 니트"


# --- mock 백엔드 ------------------------------------------------------------


def test_mock_is_deterministic_across_calls():
    """`hash()`가 아니라 sha256을 쓰는 이유 — 실행마다 값이 바뀌면 테스트가 무의미해진다."""
    first = MockCompsSource().fetch("리바이스 501")
    second = MockCompsSource().fetch("리바이스 501")

    assert [c.price for c in first.items] == [c.price for c in second.items]


def test_mock_differs_by_query():
    a = MockCompsSource().fetch("리바이스 501")
    b = MockCompsSource().fetch("나이키 후드")

    assert [c.price for c in a.items] != [c.price for c in b.items]


def test_mock_marks_itself_as_not_real():
    """목업 가격이 실시세로 오해되면 안 된다."""
    assert MockCompsSource().fetch("무엇이든").notes


def test_build_comps_source_rejects_unknown_key():
    with pytest.raises(ValueError, match="등록되지 않은"):
        build_comps_source("없는백엔드")


# --- JSON 파싱 --------------------------------------------------------------


def test_extracts_array_wrapped_in_prose():
    """모델이 '설명 문장 금지'를 어겨도 배열만 건져낸다."""
    text = '설명입니다.\n[{"title":"a","price":1000}]\n끝.'
    assert _extract_json_array(text) == [{"title": "a", "price": 1000}]


def test_broken_json_returns_empty():
    assert _extract_json_array('[{"title": "a", price:}]') == []


def test_no_array_returns_empty():
    assert _extract_json_array("검색 결과가 없습니다.") == []


def test_non_dict_rows_are_dropped():
    assert _extract_json_array('["문자열", {"price": 100}]') == [{"price": 100}]


# --- 행 → CompItem ----------------------------------------------------------


def test_comma_separated_price_string_is_parsed():
    items = _rows_to_items([{"title": "a", "price": "45,000원"}], "llm")
    assert items[0].price == 45_000


def test_rows_without_usable_price_are_dropped():
    rows = [
        {"title": "가격없음"},
        {"title": "영원", "price": 0},
        {"title": "음수", "price": -100},
        {"title": "문자만", "price": "가격문의"},
        {"title": "정상", "price": 30_000},
    ]
    items = _rows_to_items(rows, "llm")

    assert len(items) == 1
    assert items[0].price == 30_000


def test_non_boolean_is_used_becomes_none():
    """판별 불가를 False로 뭉개면 신품과 구별이 사라진다."""
    items = _rows_to_items([{"price": 100, "is_used": "yes"}], "llm")
    assert items[0].is_used is None


def test_boolean_is_used_is_preserved():
    items = _rows_to_items([{"price": 100, "is_used": False}], "llm")
    assert items[0].is_used is False


# --- LLM 백엔드 (네트워크 미접촉) ---------------------------------------------


def test_llm_source_fails_before_touching_network_without_key(monkeypatch):
    """키가 없으면 fetch 시점에 즉시 끊긴다.

    build 시점이 아니라 fetch 시점인 게 중요하다 — 서비스 조립은 `@lru_cache`라, build에서
    던지면 잘못 설정된 컨테이너가 모든 요청에 500을 뱉는다.
    """
    from app.core import config

    monkeypatch.setattr(config.settings, "gms_api_key", "")

    def _explode(*args, **kwargs):  # pragma: no cover — 불려선 안 된다
        raise AssertionError("키가 없는데 GMS를 호출했다")

    from app.pricing import gms

    monkeypatch.setattr(gms, "generate_content", _explode)

    with pytest.raises(CompsUnavailable, match="GMS_API_KEY"):
        LlmWebSearchCompsSource().fetch("리바이스 501")


# --- Gemini 응답 파싱 (네트워크 미접촉, dict를 직접 조립) ----------------------------


def test_parse_drops_response_without_candidates():
    result = LlmWebSearchCompsSource()._parse({})
    assert result.items == []
    assert result.reason == ReasonCode.no_search_performed


def test_parse_drops_response_without_grounding():
    """그라운딩(웹검색) 흔적이 없으면 검색 없이 지어낸 답일 수 있으므로 버린다."""
    response = {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}
    result = LlmWebSearchCompsSource()._parse(response)
    assert result.items == []
    assert result.reason == ReasonCode.no_search_performed


def test_parse_extracts_items_from_grounded_response():
    response = {
        "candidates": [
            {
                "groundingMetadata": {"webSearchQueries": ["리바이스 501"]},
                "content": {"parts": [{"text": '[{"title": "리바이스 501", "price": 45000}]'}]},
            }
        ]
    }
    result = LlmWebSearchCompsSource()._parse(response)
    assert result.reason is None
    assert result.items[0].price == 45_000
    assert result.items[0].source == "llm_web_search"


def test_parse_reports_parse_failed_when_grounded_but_unstructured():
    response = {
        "candidates": [
            {
                "groundingMetadata": {"groundingChunks": [{}]},
                "content": {"parts": [{"text": "검색은 했지만 표로 못 만들었습니다."}]},
            }
        ]
    }
    result = LlmWebSearchCompsSource()._parse(response)
    assert result.items == []
    assert result.reason == ReasonCode.parse_failed
