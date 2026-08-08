"""동일 상품 매칭 1단계(속성 추출, CH031) — 네트워크에 절대 닿지 않는다.

`LlmAttributeExtractor`도 키가 없을 때/GMS 오류일 때 fetch 전에 끊기거나 폴백하는 것만
확인한다(`AI/CLAUDE.md` 하드 룰: GMS 호출은 사람이 직접 실행한다).
"""

import pytest

from app.pricing.attribute_extraction import (
    ExtractedAttributes,
    LlmAttributeExtractor,
    RegexAttributeExtractor,
    build_attribute_extractor,
)

_ALIAS_MAP = {"리바이스": 1, "levi's": 1}


# --- RegexAttributeExtractor --------------------------------------------------


def test_regex_extractor_prefers_explicit_brand_id():
    result = RegexAttributeExtractor().extract(
        product_name="리바이스 501", brand_id=99, brand_alias_map=_ALIAS_MAP
    )
    assert result.brand_id == 99


def test_regex_extractor_falls_back_to_title_alias():
    result = RegexAttributeExtractor().extract(
        product_name="리바이스 501 빈티지", brand_id=None, brand_alias_map=_ALIAS_MAP
    )
    assert result.brand_id == 1
    assert "501" in result.tokens
    assert "빈티지" not in result.tokens


def test_regex_extractor_returns_extracted_attributes():
    result = RegexAttributeExtractor().extract(
        product_name="아무 상품", brand_id=None, brand_alias_map={}
    )
    assert isinstance(result, ExtractedAttributes)
    assert result.brand_id is None


# --- LlmAttributeExtractor — 키 없음/오류 시 폴백 ------------------------------


def test_llm_extractor_falls_back_when_no_api_key(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "gms_api_key", "")

    result = LlmAttributeExtractor().extract(
        product_name="리바이스 501 빈티지", brand_id=None, brand_alias_map=_ALIAS_MAP
    )

    assert result.brand_id == 1
    assert "501" in result.tokens


def test_llm_extractor_falls_back_on_gms_error(monkeypatch):
    from app.core.config import settings
    from app.pricing import gms

    monkeypatch.setattr(settings, "gms_api_key", "fake-key")

    def _explode(**kwargs):
        raise gms.GmsError("네트워크 실패")

    monkeypatch.setattr(gms, "generate_content", _explode)

    result = LlmAttributeExtractor().extract(
        product_name="리바이스 501 빈티지", brand_id=None, brand_alias_map=_ALIAS_MAP
    )

    assert result.brand_id == 1
    assert "501" in result.tokens


def test_llm_extractor_calls_gms_without_search_tool(monkeypatch):
    """웹검색 그라운딩이 필요 없는 호출이라는 걸 확인한다."""
    from app.core.config import settings
    from app.pricing import gms

    monkeypatch.setattr(settings, "gms_api_key", "fake-key")
    captured = {}

    def _fake_generate_content(**kwargs):
        captured.update(kwargs)
        return {
            "candidates": [
                {"content": {"parts": [{"text": '{"brand": "리바이스", "keywords": ["501"]}'}]}}
            ]
        }

    monkeypatch.setattr(gms, "generate_content", _fake_generate_content)

    LlmAttributeExtractor().extract(
        product_name="리바이스 501 빈티지", brand_id=None, brand_alias_map=_ALIAS_MAP
    )

    assert captured["use_search"] is False


def test_llm_extractor_parses_brand_and_keywords(monkeypatch):
    from app.core.config import settings
    from app.pricing import gms

    monkeypatch.setattr(settings, "gms_api_key", "fake-key")
    monkeypatch.setattr(
        gms,
        "generate_content",
        lambda **k: {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": '{"brand": "리바이스", "keywords": ["501", "빅E"]}'}]
                    }
                }
            ]
        },
    )

    result = LlmAttributeExtractor().extract(
        product_name="리바이스 501 빅E 진청", brand_id=None, brand_alias_map=_ALIAS_MAP
    )

    assert result.brand_id == 1
    assert result.tokens == ["501", "빅e"]


def test_llm_extractor_falls_back_when_response_has_no_candidates(monkeypatch):
    from app.core.config import settings
    from app.pricing import gms

    monkeypatch.setattr(settings, "gms_api_key", "fake-key")
    monkeypatch.setattr(gms, "generate_content", lambda **k: {"candidates": []})

    result = LlmAttributeExtractor().extract(
        product_name="리바이스 501 빈티지", brand_id=None, brand_alias_map=_ALIAS_MAP
    )

    assert result.brand_id == 1  # regex 폴백
    assert "501" in result.tokens


def test_llm_extractor_falls_back_when_json_is_unparseable(monkeypatch):
    from app.core.config import settings
    from app.pricing import gms

    monkeypatch.setattr(settings, "gms_api_key", "fake-key")
    monkeypatch.setattr(
        gms,
        "generate_content",
        lambda **k: {"candidates": [{"content": {"parts": [{"text": "이건 JSON이 아니다"}]}}]},
    )

    result = LlmAttributeExtractor().extract(
        product_name="리바이스 501 빈티지", brand_id=None, brand_alias_map=_ALIAS_MAP
    )

    assert result.brand_id == 1  # regex 폴백


def test_llm_extractor_falls_back_when_keywords_are_empty(monkeypatch):
    from app.core.config import settings
    from app.pricing import gms

    monkeypatch.setattr(settings, "gms_api_key", "fake-key")
    monkeypatch.setattr(
        gms,
        "generate_content",
        lambda **k: {
            "candidates": [
                {"content": {"parts": [{"text": '{"brand": "리바이스", "keywords": []}'}]}}
            ]
        },
    )

    result = LlmAttributeExtractor().extract(
        product_name="리바이스 501 빈티지", brand_id=None, brand_alias_map=_ALIAS_MAP
    )

    assert result.brand_id == 1
    assert "501" in result.tokens  # regex 폴백 토큰


def test_llm_extractor_keeps_explicit_brand_id_over_llm_guess(monkeypatch):
    """요청에 brand_id가 이미 있으면 LLM이 다른 브랜드를 말해도 무시한다."""
    from app.core.config import settings
    from app.pricing import gms

    monkeypatch.setattr(settings, "gms_api_key", "fake-key")
    monkeypatch.setattr(
        gms,
        "generate_content",
        lambda **k: {
            "candidates": [
                {"content": {"parts": [{"text": '{"brand": "다른브랜드", "keywords": ["501"]}'}]}}
            ]
        },
    )

    result = LlmAttributeExtractor().extract(
        product_name="리바이스 501", brand_id=42, brand_alias_map=_ALIAS_MAP
    )

    assert result.brand_id == 42


# --- build_attribute_extractor ------------------------------------------------


def test_build_attribute_extractor_returns_regex_by_default():
    extractor = build_attribute_extractor("regex")
    assert isinstance(extractor, RegexAttributeExtractor)


def test_build_attribute_extractor_returns_llm():
    extractor = build_attribute_extractor("llm")
    assert isinstance(extractor, LlmAttributeExtractor)


def test_build_attribute_extractor_rejects_unknown_key():
    with pytest.raises(ValueError, match="등록되지 않은"):
        build_attribute_extractor("없는추출기")
