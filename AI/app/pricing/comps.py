"""슬롯 B — 비교 매물(comps) 수집.

`validation/PRICE/pricing-model-check/comps_sources.py`의 프로덕션판. 백엔드가 달라도 결과가 같은
`CompItem` 목록으로 정규화되므로, 가격 산정기는 출처를 몰라도 된다.

**"시세를 못 찾았다"는 예외가 아니다.** comps 0건·파싱 실패·검색 미호출은 전부 빈 목록 +
`reason`으로 돌려준다. 예외(`CompsUnavailable`)는 키 부재·인증 실패·타임아웃 같은 **인프라
오류**에만 쓴다. 이 구분이 job 상태(success / failed)를 가르고, BE의 재시도 여부를 가른다 —
근거 부족을 실패로 만들면 BE가 재시도 루프를 돌고 그대로 과금된다.

설계: .claude/plans/ai/CH003-pricing-service-prototype.md
"""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.config import settings
from app.pricing import registry
from app.pricing.schemas import CompItem, GarmentCategory, ReasonCode

__all__ = [
    "CompsFetch",
    "CompsSource",
    "CompsUnavailable",
    "InternalClipCompsSource",
    "InternalCompsSource",
    "InternalTextCompsSource",
    "LlmWebSearchCompsSource",
    "MockCompsSource",
    "build_comps_source",
    "build_query",
]

# 카테고리를 쿼리에 붙일 때 쓰는 한국어 표기. enum 값을 그대로 넣으면 검색이 안 된다.
_CATEGORY_TERMS: dict[GarmentCategory, str] = {
    GarmentCategory.top_knit: "니트",
    GarmentCategory.top_shirt: "셔츠",
    GarmentCategory.outer_jacket: "자켓",
    GarmentCategory.outer_coat: "코트",
    GarmentCategory.bottom_pants: "팬츠",
    GarmentCategory.bottom_skirt: "스커트",
}

_MOCK_PRICE_RATIOS = (0.82, 0.95, 1.0, 1.12, 1.31)


class CompsUnavailable(RuntimeError):
    """comps를 **수집할 수 없는** 상태. 키 부재·인증 실패·타임아웃 등 인프라 오류 전용.

    근거 부족(0건)은 여기 해당하지 않는다 — 그건 정상 결과이고 `CompsFetch.reason`으로 표현한다.
    """


@dataclass(frozen=True)
class CompsFetch:
    """수집 결과 + 왜 비었는지."""

    items: list[CompItem]
    notes: list[str] = field(default_factory=list)
    reason: ReasonCode | None = None  # 비어 있을 때의 사유. 채워졌으면 None
    # CH017 진단 필드. BE 계약(`PricingResult`)이 아니라 서비스 내부 로깅·관측 로그용이다 —
    # 응답 스키마에 노출하려면 별도 승인이 필요하다.
    finish_reason: str | None = None  # Gemini candidates[0].finishReason. 네트워크 미접촉이면 None
    truncated: bool = False  # finish_reason이 MAX_TOKENS라 부분 복구했으면 True
    # CH030: `internal_text`가 계산한 "동일 상품" 1차(엄격) 매칭 키. `PricingResult.
    # product_match_key`로 그대로 노출된다 — BE 계약 필드라 다른 백엔드는 None으로 둔다.
    product_match_key: str | None = None


def build_query(
    product_name: str, brand: str | None = None, category: GarmentCategory | None = None
) -> str:
    """상품명 + 브랜드 + 카테고리를 검색 쿼리 한 줄로 합친다.

    중복 토큰은 넣지 않는다 — 상품명에 이미 브랜드가 들어 있는 경우가 흔하다.
    """
    parts = [product_name.strip()]
    lowered = product_name.lower()
    if brand and brand.strip() and brand.strip().lower() not in lowered:
        parts.insert(0, brand.strip())
    if category is not None:
        term = _CATEGORY_TERMS.get(category, "")
        if term and term not in product_name:
            parts.append(term)
    return " ".join(p for p in parts if p)


class CompsSource(ABC):
    """comps 수집기 인터페이스. **모델 교체는 이 구현체를 갈아끼우는 것으로 끝난다.**

    `image_url`은 `internal_clip`(CH020, CLIP 이미지 유사도 검색)만 쓴다 — 텍스트 쿼리
    기반 백엔드(mock/llm_web_search)는 키워드를 받아도 무시한다. `product_id`는
    `internal`(CH024, 실데이터 CLIP 임베딩 매칭)만 쓴다 — 이미 저장된 자기 임베딩을
    조회하는 키다. 백엔드마다 필요한 입력이 다르다고 호출부(`service.py`)가 분기하게
    만들지 않으려고 시그니처에 얹었다.
    """

    key: str

    @abstractmethod
    def fetch(
        self, query: str, *, image_url: str | None = None, product_id: int | None = None
    ) -> CompsFetch:
        """쿼리(+선택적 이미지/product_id)로 비교 매물을 모은다. 인프라 오류면
        `CompsUnavailable`."""
        raise NotImplementedError


class MockCompsSource(CompsSource):
    """키 없이 전 경로를 돌리기 위한 결정적 매물 생성기.

    `hash()`가 아니라 sha256을 쓴다 — 파이썬의 문자열 해시는 프로세스마다 시드가 달라
    `hash()` 기반이면 실행할 때마다 값이 바뀐다(`validation/` 쪽 구현의 알려진 결함).
    """

    key = "mock"

    def fetch(
        self, query: str, *, image_url: str | None = None, product_id: int | None = None
    ) -> CompsFetch:
        digest = hashlib.sha256(query.encode("utf-8")).digest()
        base = 40_000 + int.from_bytes(digest[:4], "big") % 60_000
        items = [
            CompItem(
                title=f"{query} 중고 매물 {index + 1}",
                price=int(base * ratio),
                source=self.key,
                is_used=True,
            )
            for index, ratio in enumerate(_MOCK_PRICE_RATIOS)
        ]
        return CompsFetch(items=items, notes=["목업 매물입니다 — 실제 시세가 아닙니다."])


class LlmWebSearchCompsSource(CompsSource):
    """LLM 웹검색(Gemini `google_search` 그라운딩)으로 중고 매물을 모은다.

    2026-07-31부로 Claude(Anthropic Messages API)에서 Gemini(`generateContent`)로
    전환했다 — GMS가 그라운딩을 통과시키는 것은 LAB-47(웹검색 테스트) V1에서 확인됐다.
    Anthropic 쪽처럼 날짜 버저닝된 툴 규격 폴백이 없다 — `google_search` 선언 하나로
    끝이라 규격 폴백 루프가 필요 없다.

    ⚠️ **호출마다 과금된다.** 검색 라운드당 비용 + 결과 본문이 입력 토큰으로 들어온다.
    """

    key = "llm_web_search"

    def __init__(self, config: registry.CompsSourceConfig | None = None) -> None:
        self._config = config or registry.comps_config(self.key)

    def fetch(
        self, query: str, *, image_url: str | None = None, product_id: int | None = None
    ) -> CompsFetch:
        # 키 확인을 build가 아니라 fetch에서 하는 이유: 서비스 조립은 @lru_cache라
        # build 시점에 던지면 잘못 설정된 컨테이너가 모든 요청에 500을 뱉는다.
        # 여기서 던지면 job result의 error로 내려가 BE가 원인을 본다.
        api_key = settings.gms_api_key.strip()
        if not api_key:
            raise CompsUnavailable("GMS_API_KEY가 설정되지 않았습니다")

        from app.pricing import gms

        model = self._config["model_id"] or ""
        try:
            response = gms.generate_content(
                api_key=api_key,
                model=model,
                prompt=_comps_prompt(query),
                timeout=self._config["timeout_seconds"],
                max_output_tokens=self._config["max_output_tokens"],
            )
        except gms.GmsError as exc:
            raise CompsUnavailable(str(exc)) from exc
        return self._parse(response)

    def _parse(self, response: dict) -> CompsFetch:
        candidates = response.get("candidates") or []
        if not candidates:
            return CompsFetch(
                items=[],
                notes=["응답에 candidates가 없습니다."],
                reason=ReasonCode.no_search_performed,
            )

        finish_reason = candidates[0].get("finishReason") or None

        grounding = candidates[0].get("groundingMetadata") or {}
        searched = bool(grounding.get("groundingChunks") or grounding.get("webSearchQueries"))
        if not searched:
            # 그라운딩이 안 일어났다 — 검색 없이 지어낸 가격일 수 있으므로 응답을 통째로
            # 버린다. 근거 없는 시세가 comps로 섞이는 것이 최악이다.
            return CompsFetch(
                items=[],
                notes=["모델이 웹검색을 수행하지 않아 응답을 사용하지 않았습니다."],
                reason=ReasonCode.no_search_performed,
                finish_reason=finish_reason,
            )

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        rows, truncated = _extract_json_array_lenient(text)
        if not rows:
            return CompsFetch(
                items=[],
                notes=["검색 결과를 구조화하지 못했습니다."],
                reason=ReasonCode.parse_failed,
                finish_reason=finish_reason,
            )

        items = _rows_to_items(rows, self.key)[: self._config["max_comps"]]
        if not items:
            return CompsFetch(
                items=[],
                notes=["가격을 확인할 수 있는 매물이 없었습니다."],
                reason=ReasonCode.insufficient_comps,
                finish_reason=finish_reason,
            )
        notes = ["응답이 도중에 잘려 완결된 매물만 사용했습니다."] if truncated else []
        return CompsFetch(
            items=items, notes=notes, finish_reason=finish_reason, truncated=truncated
        )


class InternalClipCompsSource(CompsSource):
    """내부 데이터 CLIP 이미지 유사도 검색(CH020). 텍스트 쿼리는 안 쓰고 `image_url`만 본다.

    ⚠️ 이번 라운드의 코퍼스는 **전부 합성 데이터**다(AI-Hub 학습 이미지 + 가상 가격) —
    실제 시세가 아니다. `internal_corpus.CorpusItem.data_source`에 그 표식이 남는다.
    """

    key = "internal_clip"

    def __init__(self, config: registry.CompsSourceConfig | None = None) -> None:
        self._config = config or registry.comps_config(self.key)
        self._clip_config = registry.INTERNAL_CLIP_CONFIG

    def fetch(
        self, query: str, *, image_url: str | None = None, product_id: int | None = None
    ) -> CompsFetch:
        if not image_url:
            return CompsFetch(
                items=[],
                notes=["이미지가 없어 내부 CLIP 유사도 검색을 할 수 없습니다."],
                reason=ReasonCode.no_image_provided,
            )

        from app.pricing import clip_embed, internal_corpus

        try:
            embedding = clip_embed.embed_image_from_url(
                image_url,
                checkpoint_path=self._clip_config["checkpoint_path"],
                model_id=self._config["model_id"] or "",
            )
        except clip_embed.ClipEmbedNotReady as exc:
            raise CompsUnavailable(str(exc)) from exc

        try:
            corpus = internal_corpus.get_corpus(self._clip_config["corpus_dir"])
        except internal_corpus.CorpusNotReady as exc:
            raise CompsUnavailable(str(exc)) from exc

        matches = internal_corpus.query_similar(
            embedding,
            corpus,
            top_k=self._config["max_comps"],
            min_similarity=self._clip_config["similarity_floor"],
        )
        if not matches:
            return CompsFetch(
                items=[],
                notes=["유사도 기준을 넘는 내부 매물이 없습니다."],
                reason=ReasonCode.insufficient_comps,
            )

        items = [
            CompItem(
                title=f"{item.aihub_category} 유사 상품(내부 CLIP 유사도 검색)",
                price=item.synthetic_price,
                source=self.key,
                is_used=None,  # AI-Hub 학습 이미지 출처라 중고 여부를 판별할 수 없다
            )
            for item, _score in matches
        ]
        return CompsFetch(
            items=items,
            notes=["⚠️ 합성 코퍼스(AI-Hub 학습 이미지 기반) 결과입니다 — 실거래 시세가 아닙니다."],
        )


class InternalCompsSource(CompsSource):
    """실데이터 CLIP 임베딩 매칭(CH024).

    `app/recommend/similar/`가 쓰는 실제 pgvector 코퍼스(`product_garment_embedding`,
    `app.recommend.personalize.embedding_store`)를 그대로 재사용한다 — 품질검수가 끝난
    상품마다 자동으로 쌓이는 실데이터다(CH020의 AI-Hub 합성 코퍼스와 다르다). 후보
    product_id의 가격·브랜드·판매방식·판매상태는 BE 공개 API(`app.shared.be_client`)로
    조회한다 — CH016이 요청했던 DB 뷰·읽기 전용 계정이 필요 없다, BE가 그 필드를 이미
    공개로 낸다.

    **쿼리 임베딩을 요청 시점에 새로 계산하지 않는다** — `product_id`로 **이미 저장된**
    자기 임베딩만 조회한다. 대상 상품이 아직 품질검수를 거치지 않았으면(임베딩 없음)
    `NO_IMAGE_PROVIDED`로 정상 처리한다(`app/recommend/similar/service.py`가 "임베딩
    없으면 빈 결과, 에러 아님"으로 다루는 것과 같은 원칙). 이 컨테이너엔 torch/SAM3가
    없어(`docs/infra-architecture.md` §6) 요청 시점 임베딩 계산 자체가 불가능하다 —
    `internal_clip`(CH020)과 다른 점이다.
    """

    key = "internal"

    def __init__(self, config: registry.CompsSourceConfig | None = None) -> None:
        self._config = config or registry.comps_config(self.key)

    def fetch(
        self, query: str, *, image_url: str | None = None, product_id: int | None = None
    ) -> CompsFetch:
        if product_id is None:
            return CompsFetch(
                items=[],
                notes=["상품 id가 없어 내부 시세 비교를 할 수 없습니다."],
                reason=ReasonCode.no_image_provided,
            )

        from datetime import UTC, datetime

        from app.pricing import hedge
        from app.recommend.personalize import embedding_store
        from app.shared import be_client

        if embedding_store.fetch_garment_embedding(product_id) is None:
            return CompsFetch(
                items=[],
                notes=["아직 이 상품의 의류 임베딩이 없습니다(품질검수 완료 전일 수 있습니다)."],
                reason=ReasonCode.no_image_provided,
            )

        matches = embedding_store.find_similar(product_id, self._config["max_comps"])
        if not matches:
            return CompsFetch(
                items=[],
                notes=["유사도 기준을 넘는 내부 매물이 없습니다."],
                reason=ReasonCode.insufficient_comps,
            )

        candidates = []
        for match in matches:
            product = be_client.fetch_product(
                match.product_id, timeout=self._config["timeout_seconds"]
            )
            if product is None:
                continue
            candidates.append(
                hedge.InternalCandidate(
                    product_id=product.product_id,
                    title=product.title,
                    price=product.price,
                    sale_type=product.sale_type,
                    sale_status=product.sale_status,
                    created_at=product.created_at,
                )
            )

        kept, notes = hedge.apply_hedge_filters(candidates, now=datetime.now(UTC))
        if not kept:
            return CompsFetch(
                items=[],
                notes=[*notes, "정제 후 남은 내부 매물이 없습니다."],
                reason=ReasonCode.insufficient_comps,
            )

        items = [
            CompItem(
                title=c.title,
                price=c.price,
                source=self.key,
                is_used=True,  # 세컨핸드 플랫폼 등록 매물이라 기본적으로 중고다
                price_kind=c.price_kind,
            )
            for c in kept
            if c.price is not None
        ]
        return CompsFetch(items=items, notes=notes)


class InternalTextCompsSource(CompsSource):
    """이미지 임베딩 없이 텍스트(상품명+브랜드+카테고리)만으로 "동일 상품"을 판정하는 내부
    조회(CH030).

    `InternalCompsSource`(CH024)와 하단 파이프라인(hedge 필터·BE 조회·CompItem 조립)은
    같다 — 다른 건 후보를 찾는 방식뿐이다. CLIP 임베딩 유사도 대신 `app/pricing/
    product_match.py`의 정규화 매칭 키로 `app/pricing/product_corpus.py` 코퍼스(BE 목록
    API를 pull해 만든 자체 캐시)를 조회한다.

    1차(엄격) 키로 먼저 찾고, 표본이 `min_comps_for_pricing` 미만이면 2차(완화, 브랜드+
    카테고리만)로 재조회한다 — 사용자가 지정한 폴백 순서. 1차 키는 `CompsFetch.
    product_match_key`로 돌려준다 — BE가 상품 저장 시 `product.match_key`에 그대로
    반영하면, 구매자 화면은 이 값으로 DB 조회만 해서 동일 상품 시세를 보여줄 수 있다
    (RAG/AI 호출 없음, CH030 §5).

    자유텍스트(상품명) → 브랜드+핵심 토큰 추출(당근마켓 1단계, CH031)은
    `attribute_extraction.build_attribute_extractor()`가 만드는 구현체(regex 기본값/llm
    옵트인)에 위임한다 — 이 클래스는 그 결과로 매칭 키만 조합한다.
    """

    key = "internal_text"

    def __init__(self, config: registry.CompsSourceConfig | None = None) -> None:
        self._config = config or registry.comps_config(self.key)

    def fetch(
        self, query: str, *, image_url: str | None = None, product_id: int | None = None
    ) -> CompsFetch:
        if product_id is None:
            return CompsFetch(
                items=[],
                notes=["상품 id가 없어 내부 시세 비교를 할 수 없습니다."],
                reason=ReasonCode.no_image_provided,
            )

        from datetime import UTC, datetime

        from app.pricing import attribute_extraction, hedge, product_corpus
        from app.pricing.product_match import build_match_keys
        from app.shared import be_client

        product = be_client.fetch_product(product_id, timeout=self._config["timeout_seconds"])
        if product is None:
            return CompsFetch(
                items=[],
                notes=["상품 정보를 조회할 수 없어 내부 시세 비교를 할 수 없습니다."],
                reason=ReasonCode.insufficient_comps,
            )

        extractor = attribute_extraction.build_attribute_extractor()
        extracted = extractor.extract(
            product_name=product.title,
            brand_name=product.brand,
            brand_alias_map=product_corpus.get_brand_alias_map(),
        )
        keys = build_match_keys(
            tokens=extracted.tokens,
            brand_id=extracted.brand_id,
            category=str(product.category_id),
        )

        candidates = product_corpus.find_by_match_key(
            keys.strict, exclude_product_id=product_id, limit=self._config["max_comps"]
        )
        if len(candidates) < self._config["min_comps_for_pricing"]:
            candidates = product_corpus.find_by_match_key(
                keys.relaxed, exclude_product_id=product_id, limit=self._config["max_comps"]
            )
        if not candidates:
            return CompsFetch(
                items=[],
                notes=["동일 상품으로 판정되는 다른 매물이 없습니다."],
                reason=ReasonCode.insufficient_comps,
                product_match_key=keys.strict,
            )

        internal_candidates = [
            hedge.InternalCandidate(
                product_id=c.product_id,
                title=c.title,
                price=c.price,
                sale_type=c.sale_type,
                sale_status=c.sale_status,
                created_at=c.created_at,
            )
            for c in candidates
        ]
        kept, notes = hedge.apply_hedge_filters(internal_candidates, now=datetime.now(UTC))
        if not kept:
            return CompsFetch(
                items=[],
                notes=[*notes, "정제 후 남은 내부 매물이 없습니다."],
                reason=ReasonCode.insufficient_comps,
                product_match_key=keys.strict,
            )

        items = [
            CompItem(
                title=c.title,
                price=c.price,
                source=self.key,
                is_used=True,  # 세컨핸드 플랫폼 등록 매물이라 기본적으로 중고다
                price_kind=c.price_kind,
            )
            for c in kept
            if c.price is not None
        ]
        return CompsFetch(items=items, notes=notes, product_match_key=keys.strict)


def build_comps_source(key: str | None = None) -> CompsSource:
    """활성 comps 백엔드 구현체를 만든다."""
    resolved = key or registry.ACTIVE_COMPS_SOURCE
    if resolved == "mock":
        return MockCompsSource()
    if resolved == "llm_web_search":
        return LlmWebSearchCompsSource()
    if resolved == "internal_clip":
        return InternalClipCompsSource()
    if resolved == "internal":
        return InternalCompsSource()
    if resolved == "internal_text":
        return InternalTextCompsSource()
    raise ValueError(f"등록되지 않은 comps 백엔드입니다: {resolved!r}")


# --- 파싱 (네트워크 없이 테스트되는 순수 함수들) ------------------------------


# 프롬프트 안 예시 하나(few-shot) — quality_vlm/prompts.py(CH019)가 실측으로 확인한 것과
# 같은 문제(지시문만 있으면 모델이 경계 판단을 지어냄)에 대한 같은 처방이다. 브랜드가 한글로만
# 주어져도 모델이 영문 표기까지 스스로 고려하게 만드는 것도 이 예시가 보여준다 — 국내 중고
# 플랫폼(번개장터 등)은 명품·편집샵 브랜드를 영문 그대로 쓰는 매물이 흔해서, 한글 쿼리만
# 그대로 검색하면 그런 매물을 놓친다.
_COMPS_FEW_SHOT_QUERY = "메종키츠네 폭스헤드 니트 그레이"
_COMPS_FEW_SHOT_ANSWER = (
    '[{"title": "Maison Kitsune 폭스헤드 니트 그레이 M", "price": 95000, '
    '"url": "https://web.joongna.com/product/123456", "listed_at": "2026-07-02", '
    '"is_used": true}]'
)


def _comps_prompt(query: str) -> str:
    return (
        "너는 중고거래 시세 조사원이다. **목적은 이 상품과 동일한 상품(같은 브랜드 + 같은 "
        "모델/디자인)의 실제 거래가를 찾는 것**이다 — 브랜드나 모델이 다르면 카테고리가 같아도"
        " 시세 산정에 쓸모가 없으니 제외한다.\n\n"
        f"검색 대상: '{query}'\n"
        "후르츠패밀리·번개장터·중고나라 등 중고 거래 매물을 우선한다. 브랜드명이 한글로만"
        " 주어졌으면 영어/원어 표기도 함께 고려해서 검색하고(국내 중고 플랫폼은 브랜드를 영문"
        " 그대로 쓰는 매물이 많다), 반대로 영문이면 한글 표기도 같이 찾아본다.\n\n"
        "아래는 좋은 답변 예시다.\n"
        f"검색 대상: '{_COMPS_FEW_SHOT_QUERY}'\n"
        f"답변: {_COMPS_FEW_SHOT_ANSWER}\n\n"
        "찾은 매물을 JSON 배열로만 답해라. 설명 문장은 쓰지 마라.\n"
        '형식: [{"title": "상품명", "price": 숫자(원, 쉼표 없이), "url": "링크", '
        '"listed_at": "YYYY-MM-DD 또는 빈 문자열", "is_used": true/false}]\n'
        "가격을 확인할 수 없는 매물은 넣지 마라. 추측한 가격도 넣지 마라. 브랜드나 모델이"
        " 다른(동일 상품이 아닌) 매물도 넣지 마라."
    )


def _extract_json_array(text: str) -> list[dict]:
    """응답에서 첫 JSON 배열을 관대하게 건져낸다.

    structured output(`output_config.format`)을 쓰지 않는 이유: GMS 프록시가 그 파라미터를
    통과시키는지 미확인이고, 거기서 400이 나면 원인 파악이 어려워진다. 파싱 실패는 그 자체를
    `PARSE_FAILED`로 노출한다.
    """
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [row for row in parsed if isinstance(row, dict)]


def _extract_json_array_lenient(text: str) -> tuple[list[dict], bool]:
    """`_extract_json_array()`가 실패하면 완결된 객체만이라도 건진다(CH017 B2).

    응답이 `maxOutputTokens`에 걸려 잘리면 배열이 `]`로 안 끝나 `_extract_json_array()`가
    통째로 빈 리스트를 돌려준다. 그런데 잘린 건 보통 마지막 객체뿐이고 앞쪽은 완결돼 있다 —
    중괄호 짝이 맞는 조각만 하나씩 파싱해서 살린다. 둘째 반환값은 이 부분 복구 경로를
    탔는지(=응답이 잘렸다고 볼 수 있는지)다.
    """
    strict = _extract_json_array(text)
    if strict:
        return strict, False
    return _salvage_json_objects(text), True


def _salvage_json_objects(text: str) -> list[dict]:
    """중괄호 짝이 맞는 `{...}` 조각만 개별적으로 파싱한다. 짝이 안 맞는 마지막 조각(잘린
    부분)은 짝이 끝까지 맞지 않으므로 자연히 버려진다."""
    rows: list[dict] = []
    depth = 0
    start: int | None = None
    for index, char in enumerate(text):
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start is not None:
                chunk = text[start : index + 1]
                start = None
                try:
                    parsed = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    rows.append(parsed)
    return rows


def _rows_to_items(rows: list[dict], source: str) -> list[CompItem]:
    """LLM이 준 dict 목록을 `CompItem`으로. 가격을 못 읽는 행은 버린다."""
    items: list[CompItem] = []
    for row in rows:
        price = _coerce_price(row.get("price"))
        if price is None or price <= 0:
            continue
        raw_used = row.get("is_used")
        items.append(
            CompItem(
                title=str(row.get("title", ""))[:200],
                price=price,
                source=source,
                url=str(row.get("url", "") or ""),
                listed_at=str(row.get("listed_at", "") or ""),
                # bool이 아니면 None — 판별 불가를 False로 뭉개면 신품과 구별이 사라진다.
                is_used=raw_used if isinstance(raw_used, bool) else None,
            )
        )
    return items


def _coerce_price(value: object) -> int | None:
    """`45000` / `"45,000원"` / `45000.0` 을 정수 원 단위로."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = re.sub(r"[^0-9]", "", value)
        return int(digits) if digits else None
    return None
