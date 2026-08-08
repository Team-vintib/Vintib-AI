"""동일 상품 매칭의 1단계(속성 추출) 스왑 지점 — 자유텍스트 → 브랜드+핵심 토큰(CH031).

당근마켓 사례 참고: LLM은 자유텍스트를 정규화된 속성으로 뽑아내는 1단계에만 쓰고, 그
다음(정확 키 집계·키워드 매칭)은 이미 CH030에 있다(`product_match.build_match_keys`).
이 모듈은 그 1단계의 두 구현체다 — `RegexAttributeExtractor`(기존 정규식/별칭 사전,
기본값)와 `LlmAttributeExtractor`(GMS).

⚠️ **`LlmAttributeExtractor`가 실제로 GMS를 호출한다.** `AI/CLAUDE.md` 하드 룰 대상 —
Claude는 이 경로를 실행하지 않는다(테스트 포함, monkeypatch로만 검증). 커밋 기본값은
항상 `regex`다(`registry.ACTIVE_ATTRIBUTE_EXTRACTOR`).

설계: docs/plans/AI/CH031-pricing-llm-attribute-extraction.md
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.pricing import registry
from app.pricing.product_match import normalize_title, resolve_brand_id

__all__ = [
    "AttributeExtractor",
    "ExtractedAttributes",
    "LlmAttributeExtractor",
    "RegexAttributeExtractor",
    "build_attribute_extractor",
]


@dataclass(frozen=True)
class ExtractedAttributes:
    """매칭 키를 만드는 데 쓸 최소 정보 — 정규화된 토큰(모델명 등) + 브랜드 id."""

    tokens: list[str]
    brand_id: int | None


class AttributeExtractor(ABC):
    """1단계(속성 추출) 인터페이스. `build_match_keys()`가 결과를 받아 2단계(정확 키
    집계)로 그대로 넘긴다 — 추출기가 바뀌어도 매칭 로직은 몰라도 된다."""

    key: str

    @abstractmethod
    def extract(
        self, *, product_name: str, brand_id: int | None, brand_alias_map: dict[str, int]
    ) -> ExtractedAttributes:
        raise NotImplementedError


class RegexAttributeExtractor(AttributeExtractor):
    """CH030의 기존 방식 — 정규식 토큰화 + 브랜드 별칭 부분일치.

    기본값이자 폴백 대상이다 — 네트워크가 없어 실패할 게 없다(`LlmAttributeExtractor`가
    실패하면 이 결과로 대체한다).
    """

    key = "regex"

    def extract(
        self, *, product_name: str, brand_id: int | None, brand_alias_map: dict[str, int]
    ) -> ExtractedAttributes:
        resolved_brand = resolve_brand_id(
            brand_id=brand_id, product_name=product_name, brand_alias_map=brand_alias_map
        )
        tokens = sorted(set(normalize_title(product_name)))
        return ExtractedAttributes(tokens=tokens, brand_id=resolved_brand)


class LlmAttributeExtractor(AttributeExtractor):
    """GMS(`gemini-3.5-flash`, `llm_web_search`와 같은 모델 재사용)로 자유텍스트에서
    브랜드+핵심 모델/식별 키워드를 뽑는다(CH031, 당근마켓 1단계).

    웹검색 그라운딩이 필요 없어(주어진 텍스트만 파싱) `gms.generate_content(use_search=
    False)`로 호출한다 — `comps.py`의 그라운딩 사후검사가 필요 없다.

    호출·파싱 실패는 예외가 아니라 `RegexAttributeExtractor`로 폴백한다 — 가격 산정
    자체가 LLM 장애로 막히면 안 된다(`comps.py`의 인프라-오류 vs 근거-부족 구분과 같은 원칙,
    다만 여기는 폴백이 있어 아예 실패 자체가 표면화되지 않는다).
    """

    key = "llm"

    def __init__(self, config: registry.AttributeExtractorConfig | None = None) -> None:
        self._config = config or registry.attribute_extractor_config(self.key)
        self._fallback = RegexAttributeExtractor()

    def extract(
        self, *, product_name: str, brand_id: int | None, brand_alias_map: dict[str, int]
    ) -> ExtractedAttributes:
        from app.core.config import settings
        from app.pricing import gms

        api_key = settings.gms_api_key.strip()
        if not api_key:
            return self._fallback.extract(
                product_name=product_name, brand_id=brand_id, brand_alias_map=brand_alias_map
            )

        try:
            response = gms.generate_content(
                api_key=api_key,
                model=self._config["model_id"] or "",
                prompt=_extraction_prompt(product_name),
                timeout=self._config["timeout_seconds"],
                max_output_tokens=self._config["max_output_tokens"],
                use_search=False,
            )
        except gms.GmsError:
            return self._fallback.extract(
                product_name=product_name, brand_id=brand_id, brand_alias_map=brand_alias_map
            )

        parsed = _parse_response(response)
        if parsed is None:
            return self._fallback.extract(
                product_name=product_name, brand_id=brand_id, brand_alias_map=brand_alias_map
            )

        resolved_brand = brand_id
        if resolved_brand is None and parsed.get("brand"):
            resolved_brand = resolve_brand_id(
                brand_id=None, product_name=str(parsed["brand"]), brand_alias_map=brand_alias_map
            )

        tokens = [str(t).strip().lower() for t in parsed.get("keywords", []) if str(t).strip()]
        if not tokens:
            return self._fallback.extract(
                product_name=product_name, brand_id=brand_id, brand_alias_map=brand_alias_map
            )
        return ExtractedAttributes(tokens=sorted(set(tokens)), brand_id=resolved_brand)


def _extraction_prompt(product_name: str) -> str:
    return (
        f"다음은 중고거래 상품명이다: '{product_name}'\n"
        "이 상품명에서 브랜드와, 이 상품을 다른 비슷한 상품과 구분해주는 핵심 모델명/"
        "식별 키워드만 뽑아라. 사이즈·컨디션(새제품/미착용 등)·마케팅 문구는 제외한다.\n"
        "JSON 객체 하나로만 답해라. 설명 문장은 쓰지 마라.\n"
        '형식: {"brand": "브랜드명 또는 빈 문자열", "keywords": ["키워드1", "키워드2"]}'
    )


def _parse_response(response: dict) -> dict | None:
    """관대한 JSON 객체 추출 — `comps.py`의 배열 파싱과 같은 철학, 객체 버전."""
    candidates = response.get("candidates") or []
    if not candidates:
        return None
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def build_attribute_extractor(key: str | None = None) -> AttributeExtractor:
    """활성 속성 추출기 구현체를 만든다."""
    resolved = key or registry.ACTIVE_ATTRIBUTE_EXTRACTOR
    if resolved == "regex":
        return RegexAttributeExtractor()
    if resolved == "llm":
        return LlmAttributeExtractor()
    raise ValueError(f"등록되지 않은 속성 추출기입니다: {resolved!r}")
