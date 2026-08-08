"""comps 수집 — 파싱·쿼리 조립·mock 결정성 검증.

**네트워크에 절대 닿지 않는다.** LLM 백엔드도 키가 없을 때 fetch 전에 끊기는 것만 확인한다
(`AI/CLAUDE.md` 하드 룰: GMS 호출은 사람이 직접 실행한다).
"""

import pytest

from app.pricing.comps import (
    CompsUnavailable,
    InternalClipCompsSource,
    InternalCompsSource,
    InternalTextCompsSource,
    LlmWebSearchCompsSource,
    MockCompsSource,
    _extract_json_array,
    _extract_json_array_lenient,
    _rows_to_items,
    _salvage_json_objects,
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


# --- 부분 복구(CH017 B2 — 응답이 잘려 배열이 안 닫힌 경우) --------------------------


def test_salvage_recovers_completed_objects_before_truncation():
    """마지막 객체가 잘려도 그 앞의 완결된 객체들은 살린다."""
    text = '[{"title": "a", "price": 1000}, {"title": "b", "price": 2000}, {"title": "c", "pr'
    assert _salvage_json_objects(text) == [
        {"title": "a", "price": 1000},
        {"title": "b", "price": 2000},
    ]


def test_salvage_returns_empty_when_nothing_completed():
    assert _salvage_json_objects('[{"title": "잘림 시작') == []


def test_lenient_prefers_strict_parse_when_array_is_well_formed():
    """배열이 완결돼 있으면 부분 복구를 타지 않는다 — truncated=False."""
    rows, truncated = _extract_json_array_lenient('[{"title": "a", "price": 1000}]')
    assert rows == [{"title": "a", "price": 1000}]
    assert truncated is False


def test_lenient_falls_back_to_salvage_when_array_is_truncated():
    text = '[{"title": "a", "price": 1000}, {"title": "b", "pr'
    rows, truncated = _extract_json_array_lenient(text)
    assert rows == [{"title": "a", "price": 1000}]
    assert truncated is True


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


# --- internal_clip 백엔드 (CH020, torch/실제 코퍼스 미접촉 — monkeypatch로 격리) --------


def test_internal_clip_without_image_url_reports_no_image():
    result = InternalClipCompsSource().fetch("아무 쿼리")
    assert result.items == []
    assert result.reason == ReasonCode.no_image_provided


def test_internal_clip_promotes_embed_failure_to_comps_unavailable(monkeypatch):
    from app.pricing import clip_embed

    def _explode(*args, **kwargs):
        raise clip_embed.ClipEmbedNotReady("체크포인트 없음")

    monkeypatch.setattr(clip_embed, "embed_image_from_url", _explode)

    with pytest.raises(CompsUnavailable, match="체크포인트 없음"):
        InternalClipCompsSource().fetch("아무 쿼리", image_url="https://example.com/a.jpg")


def test_internal_clip_promotes_missing_corpus_to_comps_unavailable(monkeypatch):
    from app.pricing import clip_embed, internal_corpus

    monkeypatch.setattr(clip_embed, "embed_image_from_url", lambda *a, **k: [0.1, 0.2])

    def _explode(*args, **kwargs):
        raise internal_corpus.CorpusNotReady("코퍼스 없음")

    monkeypatch.setattr(internal_corpus, "get_corpus", _explode)

    with pytest.raises(CompsUnavailable, match="코퍼스 없음"):
        InternalClipCompsSource().fetch("아무 쿼리", image_url="https://example.com/a.jpg")


def test_internal_clip_reports_insufficient_comps_when_no_matches(monkeypatch):
    from app.pricing import clip_embed, internal_corpus

    monkeypatch.setattr(clip_embed, "embed_image_from_url", lambda *a, **k: [0.1, 0.2])
    monkeypatch.setattr(internal_corpus, "get_corpus", lambda *a, **k: object())
    monkeypatch.setattr(internal_corpus, "query_similar", lambda *a, **k: [])

    result = InternalClipCompsSource().fetch("아무 쿼리", image_url="https://example.com/a.jpg")

    assert result.items == []
    assert result.reason == ReasonCode.insufficient_comps


def test_internal_clip_converts_matches_to_comp_items(monkeypatch):
    from app.pricing import clip_embed, internal_corpus

    monkeypatch.setattr(clip_embed, "embed_image_from_url", lambda *a, **k: [0.1, 0.2])
    monkeypatch.setattr(internal_corpus, "get_corpus", lambda *a, **k: object())
    match_item = internal_corpus.CorpusItem(
        aihub_category="JACKET", synthetic_price=120_000, data_source="synthetic_aihub"
    )
    monkeypatch.setattr(internal_corpus, "query_similar", lambda *a, **k: [(match_item, 0.9)])

    result = InternalClipCompsSource().fetch("아무 쿼리", image_url="https://example.com/a.jpg")

    assert result.reason is None
    assert len(result.items) == 1
    assert result.items[0].price == 120_000
    assert result.items[0].source == "internal_clip"
    assert result.items[0].is_used is None
    assert result.notes  # 합성 데이터라는 경고가 있어야 한다


# --- internal 백엔드 (CH024, 실데이터 — pgvector/BE API 전부 monkeypatch로 격리) ----------


def test_internal_without_product_id_reports_no_image():
    result = InternalCompsSource().fetch("아무 쿼리")
    assert result.items == []
    assert result.reason == ReasonCode.no_image_provided


def test_internal_reports_no_image_when_embedding_missing(monkeypatch):
    from app.recommend.personalize import embedding_store

    monkeypatch.setattr(embedding_store, "fetch_garment_embedding", lambda product_id: None)

    result = InternalCompsSource().fetch("q", product_id=1042)

    assert result.items == []
    assert result.reason == ReasonCode.no_image_provided


def test_internal_reports_insufficient_when_no_matches(monkeypatch):
    from app.recommend.personalize import embedding_store

    monkeypatch.setattr(embedding_store, "fetch_garment_embedding", lambda product_id: object())
    monkeypatch.setattr(embedding_store, "find_similar", lambda *a, **k: [])

    result = InternalCompsSource().fetch("q", product_id=1042)

    assert result.items == []
    assert result.reason == ReasonCode.insufficient_comps


def _fake_match(product_id: int):
    from app.recommend.personalize.embedding_store import SimilarGarmentMatch

    return SimilarGarmentMatch(product_id=product_id, score=0.9)


def _fake_be_product(product_id: int, **overrides):
    from app.shared.be_client import BeProduct

    base = {
        "product_id": product_id,
        "title": f"상품{product_id}",
        "brand": "테스트브랜드",
        "category_id": 97,
        "condition_grade": "A",
        "sale_type": "DIRECT_SALE",
        "sale_status": "ON_SALE",
        "price": 50_000,
        "created_at": "2026-08-01T00:00:00",
    }
    base.update(overrides)
    return BeProduct(**base)


def test_internal_converts_matches_using_be_data(monkeypatch):
    from app.recommend.personalize import embedding_store
    from app.shared import be_client

    monkeypatch.setattr(embedding_store, "fetch_garment_embedding", lambda product_id: object())
    monkeypatch.setattr(embedding_store, "find_similar", lambda *a, **k: [_fake_match(2)])
    monkeypatch.setattr(be_client, "fetch_product", lambda product_id, **k: _fake_be_product(2))

    result = InternalCompsSource().fetch("q", product_id=1042)

    assert result.reason is None
    assert len(result.items) == 1
    assert result.items[0].price == 50_000
    assert result.items[0].source == "internal"
    assert result.items[0].is_used is True


def test_internal_excludes_candidates_be_cannot_fetch(monkeypatch):
    """BE 조회 실패(다운·삭제된 상품 등)한 후보는 조용히 빠진다."""
    from app.recommend.personalize import embedding_store
    from app.shared import be_client

    monkeypatch.setattr(embedding_store, "fetch_garment_embedding", lambda product_id: object())
    monkeypatch.setattr(
        embedding_store, "find_similar", lambda *a, **k: [_fake_match(2), _fake_match(3)]
    )
    monkeypatch.setattr(
        be_client,
        "fetch_product",
        lambda product_id, **k: _fake_be_product(3) if product_id == 3 else None,
    )

    result = InternalCompsSource().fetch("q", product_id=1042)

    assert len(result.items) == 1


def test_internal_reports_insufficient_when_all_candidates_fail_hedge(monkeypatch):
    """확정 가격이 없는 진행 중 경매만 후보로 잡히면(CH030 `filter_by_sale_status`) 정제 후
    0건이 된다. 호가(ON_SALE)·완료거래(SOLD)는 CH030부터 sale_type과 무관하게 통과한다 —
    ON_SALE인 AUCTION 매물이 걸러지던 CH024 시절 동작과는 다르다."""
    from app.recommend.personalize import embedding_store
    from app.shared import be_client

    monkeypatch.setattr(embedding_store, "fetch_garment_embedding", lambda product_id: object())
    monkeypatch.setattr(embedding_store, "find_similar", lambda *a, **k: [_fake_match(2)])
    monkeypatch.setattr(
        be_client,
        "fetch_product",
        lambda product_id, **k: _fake_be_product(2, sale_status="AUCTION_IN_PROGRESS"),
    )

    result = InternalCompsSource().fetch("q", product_id=1042)

    assert result.items == []
    assert result.reason == ReasonCode.insufficient_comps
    assert result.notes


def test_internal_keeps_completed_auction_sale(monkeypatch):
    """완료된 경매 낙찰(SOLD+AUCTION)도 CH030부터는 포함된다(사용자 결정 4번)."""
    from app.recommend.personalize import embedding_store
    from app.shared import be_client

    monkeypatch.setattr(embedding_store, "fetch_garment_embedding", lambda product_id: object())
    monkeypatch.setattr(embedding_store, "find_similar", lambda *a, **k: [_fake_match(2)])
    monkeypatch.setattr(
        be_client,
        "fetch_product",
        lambda product_id, **k: _fake_be_product(2, sale_type="AUCTION", sale_status="SOLD"),
    )

    result = InternalCompsSource().fetch("q", product_id=1042)

    assert len(result.items) == 1


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


def test_parse_captures_finish_reason():
    """CH017 진단 필드 — BE 계약이 아니라 서비스 내부 로깅용이다."""
    response = {
        "candidates": [
            {
                "finishReason": "STOP",
                "groundingMetadata": {"webSearchQueries": ["q"]},
                "content": {"parts": [{"text": '[{"title": "a", "price": 1000}]'}]},
            }
        ]
    }
    result = LlmWebSearchCompsSource()._parse(response)
    assert result.finish_reason == "STOP"
    assert result.truncated is False


def test_parse_salvages_items_when_response_is_truncated():
    """회귀 방지(CH017 B2) — 예전엔 배열이 안 닫히면 검색·과금이 됐어도 0건으로 버렸다."""
    truncated_text = '[{"title": "a", "price": 1000}, {"title": "b", "pr'
    response = {
        "candidates": [
            {
                "finishReason": "MAX_TOKENS",
                "groundingMetadata": {"webSearchQueries": ["q"]},
                "content": {"parts": [{"text": truncated_text}]},
            }
        ]
    }
    result = LlmWebSearchCompsSource()._parse(response)
    assert result.items[0].price == 1000
    assert result.truncated is True
    assert result.finish_reason == "MAX_TOKENS"
    assert result.notes  # 잘렸다는 사실을 밝힌다


# --- internal_text 백엔드 (CH030, 텍스트 매칭) ---------------------------------


def _fake_corpus_candidate(product_id: int, **overrides):
    from app.pricing.product_corpus import CorpusCandidate

    base = {
        "product_id": product_id,
        "title": f"상품{product_id}",
        "price": 45_000,
        "sale_type": "DIRECT_SALE",
        "sale_status": "ON_SALE",
        "created_at": "2026-08-01T00:00:00",
    }
    base.update(overrides)
    return CorpusCandidate(**base)


def test_internal_text_without_product_id_reports_no_image():
    result = InternalTextCompsSource().fetch("아무 쿼리")
    assert result.reason == ReasonCode.no_image_provided


def test_internal_text_reports_insufficient_when_be_product_missing(monkeypatch):
    from app.shared import be_client

    monkeypatch.setattr(be_client, "fetch_product", lambda product_id, **k: None)

    result = InternalTextCompsSource().fetch("q", product_id=1042)

    assert result.items == []
    assert result.reason == ReasonCode.insufficient_comps


def test_internal_text_uses_strict_key_first(monkeypatch):
    from app.pricing import product_corpus
    from app.shared import be_client

    monkeypatch.setattr(be_client, "fetch_product", lambda product_id, **k: _fake_be_product(1042))
    monkeypatch.setattr(product_corpus, "get_brand_alias_map", lambda: {})
    seen_keys = []

    def _fake_find(match_key, *, exclude_product_id, limit):
        seen_keys.append(match_key)
        return [_fake_corpus_candidate(2), _fake_corpus_candidate(3), _fake_corpus_candidate(4)]

    monkeypatch.setattr(product_corpus, "find_by_match_key", _fake_find)

    result = InternalTextCompsSource().fetch("q", product_id=1042)

    assert len(seen_keys) == 1  # 1차 키만으로 min_comps_for_pricing(3)를 채웠다 — 2차 조회 없음
    assert len(result.items) == 3
    assert result.product_match_key == seen_keys[0]


def test_internal_text_falls_back_to_relaxed_key_when_strict_insufficient(monkeypatch):
    from app.pricing import product_corpus
    from app.shared import be_client

    monkeypatch.setattr(be_client, "fetch_product", lambda product_id, **k: _fake_be_product(1042))
    monkeypatch.setattr(product_corpus, "get_brand_alias_map", lambda: {})
    calls = []

    def _fake_find(match_key, *, exclude_product_id, limit):
        calls.append(match_key)
        if len(calls) == 1:
            return [_fake_corpus_candidate(2)]  # min_comps_for_pricing(3) 미달
        return [_fake_corpus_candidate(2), _fake_corpus_candidate(3), _fake_corpus_candidate(4)]

    monkeypatch.setattr(product_corpus, "find_by_match_key", _fake_find)

    result = InternalTextCompsSource().fetch("q", product_id=1042)

    assert len(calls) == 2  # 1차 부족 → 2차(완화)로 재조회
    assert len(result.items) == 3
    assert result.product_match_key == calls[0]  # 응답 키는 항상 1차(엄격)


def test_internal_text_reports_insufficient_when_no_candidates(monkeypatch):
    from app.pricing import product_corpus
    from app.shared import be_client

    monkeypatch.setattr(be_client, "fetch_product", lambda product_id, **k: _fake_be_product(1042))
    monkeypatch.setattr(product_corpus, "get_brand_alias_map", lambda: {})
    monkeypatch.setattr(product_corpus, "find_by_match_key", lambda *a, **k: [])

    result = InternalTextCompsSource().fetch("q", product_id=1042)

    assert result.items == []
    assert result.reason == ReasonCode.insufficient_comps
    assert result.product_match_key  # 빈 결과여도 키는 돌려준다 — BE가 match_key를 저장해야 하므로


def test_internal_text_converts_candidates_with_price_kind(monkeypatch):
    from app.pricing import product_corpus
    from app.shared import be_client

    monkeypatch.setattr(be_client, "fetch_product", lambda product_id, **k: _fake_be_product(1042))
    monkeypatch.setattr(product_corpus, "get_brand_alias_map", lambda: {})
    monkeypatch.setattr(
        product_corpus,
        "find_by_match_key",
        lambda *a, **k: [
            _fake_corpus_candidate(2, sale_status="ON_SALE"),
            _fake_corpus_candidate(3, sale_status="SOLD", sale_type="DIRECT_SALE"),
            _fake_corpus_candidate(4, sale_status="SOLD", sale_type="AUCTION"),
        ],
    )

    result = InternalTextCompsSource().fetch("q", product_id=1042)

    price_kinds = {item.price_kind for item in result.items}
    assert price_kinds == {"ASKING", "SOLD_DIRECT", "SOLD_AUCTION"}
    assert all(item.source == "internal_text" for item in result.items)


def test_internal_text_excludes_candidates_failing_hedge(monkeypatch):
    from app.pricing import product_corpus
    from app.shared import be_client

    monkeypatch.setattr(be_client, "fetch_product", lambda product_id, **k: _fake_be_product(1042))
    monkeypatch.setattr(product_corpus, "get_brand_alias_map", lambda: {})
    monkeypatch.setattr(
        product_corpus,
        "find_by_match_key",
        lambda *a, **k: [_fake_corpus_candidate(2, sale_status="AUCTION_IN_PROGRESS")],
    )

    result = InternalTextCompsSource().fetch("q", product_id=1042)

    assert result.items == []
    assert result.reason == ReasonCode.insufficient_comps
