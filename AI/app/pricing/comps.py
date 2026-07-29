"""슬롯 B — 비교 매물(comps) 수집.

`validation/pricing-model-check/comps_sources.py`의 프로덕션판. 백엔드가 달라도 결과가 같은
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
    """comps 수집기 인터페이스. **모델 교체는 이 구현체를 갈아끼우는 것으로 끝난다.**"""

    key: str

    @abstractmethod
    def fetch(self, query: str) -> CompsFetch:
        """쿼리로 비교 매물을 모은다. 인프라 오류면 `CompsUnavailable`."""
        raise NotImplementedError


class MockCompsSource(CompsSource):
    """키 없이 전 경로를 돌리기 위한 결정적 매물 생성기.

    `hash()`가 아니라 sha256을 쓴다 — 파이썬의 문자열 해시는 프로세스마다 시드가 달라
    `hash()` 기반이면 실행할 때마다 값이 바뀐다(`validation/` 쪽 구현의 알려진 결함).
    """

    key = "mock"

    def fetch(self, query: str) -> CompsFetch:
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
    """LLM 서버사이드 웹검색으로 중고 매물을 모은다(CH002 V1에서 동작 확인).

    ⚠️ **호출마다 과금된다.** 검색 라운드당 비용 + 결과 본문이 입력 토큰으로 들어온다.
    """

    key = "llm_web_search"

    def __init__(self, config: registry.CompsSourceConfig | None = None) -> None:
        self._config = config or registry.comps_config(self.key)

    def fetch(self, query: str) -> CompsFetch:
        # 키 확인을 build가 아니라 fetch에서 하는 이유: 서비스 조립은 @lru_cache라
        # build 시점에 던지면 잘못 설정된 컨테이너가 모든 요청에 500을 뱉는다.
        # 여기서 던지면 job result의 error로 내려가 BE가 원인을 본다.
        api_key = settings.gms_api_key.strip()
        if not api_key:
            raise CompsUnavailable("GMS_API_KEY가 설정되지 않았습니다")

        from app.pricing import gms

        model = self._config["model_id"] or ""
        last_error: gms.GmsError | None = None
        for tool_type in self._config["tool_types"]:
            try:
                response = gms.messages_create(
                    api_key=api_key,
                    model=model,
                    prompt=_comps_prompt(query),
                    tools=[{"type": tool_type, "name": "web_search"}],
                    timeout=self._config["timeout_seconds"],
                )
            except gms.GmsError as exc:
                # 400은 "이 모델이 그 툴 규격을 못 쓴다"는 뜻 — 구형 규격으로 폴백한다.
                # 그 외(401/5xx/타임아웃)는 폴백해도 같은 결과라 즉시 포기한다.
                last_error = exc
                if exc.status == 400:
                    continue
                raise CompsUnavailable(str(exc)) from exc
            return self._parse(response)

        raise CompsUnavailable(f"지원되는 웹검색 규격이 없습니다: {last_error or '후보 없음'}")

    def _parse(self, response: object) -> CompsFetch:
        blocks = getattr(response, "content", []) or []
        searched = any(getattr(b, "type", "") == "server_tool_use" for b in blocks)
        if not searched:
            # 툴은 통과했는데 모델이 호출하지 않았다 — 검색 없이 지어낸 가격일 수 있으므로
            # 응답을 통째로 버린다. 근거 없는 시세가 comps로 섞이는 것이 최악이다.
            return CompsFetch(
                items=[],
                notes=["모델이 웹검색을 수행하지 않아 응답을 사용하지 않았습니다."],
                reason=ReasonCode.no_search_performed,
            )

        text = "".join(getattr(b, "text", "") for b in blocks if getattr(b, "type", "") == "text")
        rows = _extract_json_array(text)
        if not rows:
            return CompsFetch(
                items=[],
                notes=["검색 결과를 구조화하지 못했습니다."],
                reason=ReasonCode.parse_failed,
            )

        items = _rows_to_items(rows, self.key)[: self._config["max_comps"]]
        if not items:
            return CompsFetch(
                items=[],
                notes=["가격을 확인할 수 있는 매물이 없었습니다."],
                reason=ReasonCode.insufficient_comps,
            )
        return CompsFetch(items=items)


def build_comps_source(key: str | None = None) -> CompsSource:
    """활성 comps 백엔드 구현체를 만든다."""
    resolved = key or registry.ACTIVE_COMPS_SOURCE
    if resolved == "mock":
        return MockCompsSource()
    if resolved == "llm_web_search":
        return LlmWebSearchCompsSource()
    raise ValueError(f"등록되지 않은 comps 백엔드입니다: {resolved!r}")


# --- 파싱 (네트워크 없이 테스트되는 순수 함수들) ------------------------------


def _comps_prompt(query: str) -> str:
    return (
        f"'{query}' 의 **중고** 거래 시세를 웹에서 검색해라. "
        "번개장터·당근마켓·중고나라 등 중고 거래 매물을 우선한다.\n"
        "찾은 매물을 JSON 배열로만 답해라. 설명 문장은 쓰지 마라.\n"
        '형식: [{"title": "상품명", "price": 숫자(원, 쉼표 없이), "url": "링크", '
        '"listed_at": "YYYY-MM-DD 또는 빈 문자열", "is_used": true/false}]\n'
        "가격을 확인할 수 없는 매물은 넣지 마라. 추측한 가격도 넣지 마라."
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
