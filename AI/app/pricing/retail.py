"""슬롯 B' — 신상품(정가) 참고가 수집.

`comps.py`(중고 시세)와 완전히 분리된 인터페이스다. `RuleBaselinePricer.price()`는
`is_used is not False`인 항목만 산정에 쓰는데(`pricer.py`), 신상품가를 comps 목록에
`is_used=False`로 섞으면 가격 계산에서는 자동으로 빠지지만 응답의 `comps_used`에서도 같이
사라져 노출할 방법이 없어진다. 그래서 `RetailSource`를 따로 둔다.

CH002 V2 실측: 네이버 쇼핑 오픈API는 comps 평균 18건·지연 177ms로 빠르지만 중고 비율이
5%뿐이라 중고 시세 소스로는 못 쓴다 — 대신 신상품(정가) 조회에 재배치한다.

**`RetailSource.fetch()`는 절대 예외를 던지지 않는다.** `comps.py`의 `CompsUnavailable`과
계약이 다르다 — 신상품가는 가격 산정의 필수 입력이 아니라 부가 정보이므로, 키 부재·HTTP
오류·타임아웃 무엇이든 빈 `RetailFetch`로 떨어져야 한다. 이번 라운드는 수집·노출까지만이다
— `pricer.py`의 가격 계산에는 아직 반영하지 않는다.

설계: .claude/plans/ai/CH004-naver-retail-price.md
"""

from __future__ import annotations

import hashlib
import html
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.config import settings
from app.pricing import registry
from app.pricing.schemas import CompItem

__all__ = [
    "MockRetailSource",
    "NaverRetailSource",
    "RetailFetch",
    "RetailSource",
    "build_retail_source",
]

# validation/PRICE/pricing-model-check/gms_client.py:26 과 동일 — import는 금지 규약이라 값만 복사한다.
_NAVER_SHOP_URL = "https://openapi.naver.com/v1/search/shop.json"

# 문서상 4·5·6이 중고다(validation/PRICE/pricing-model-check/comps_sources.py 실측 근거).
# 신상품가 소스이므로 섞이면 목적과 어긋나 드롭한다.
_USED_PRODUCT_TYPES = {"4", "5", "6"}

_TAG_RE = re.compile(r"<[^>]+>")

_MOCK_PRICE_RATIOS = (1.0, 1.05, 0.97)


@dataclass(frozen=True)
class RetailFetch:
    """신상품가 수집 결과. comps와 달리 실패해도 여기 담기지 않는다 — 그냥 빈 목록이다."""

    items: list[CompItem]
    notes: list[str] = field(default_factory=list)


class RetailSource(ABC):
    """신상품(정가) 수집기 인터페이스. **`fetch()`는 예외를 던지지 않는 것이 계약이다.**"""

    key: str

    @abstractmethod
    def fetch(self, query: str) -> RetailFetch:
        """쿼리로 신상품가 몇 건을 모은다. 실패하면 빈 `RetailFetch`를 돌려준다."""
        raise NotImplementedError


class MockRetailSource(RetailSource):
    """키 없이 돌리기 위한 결정적 신상품가 생성기. `MockCompsSource`와 같은 패턴."""

    key = "mock"

    def fetch(self, query: str) -> RetailFetch:
        config = registry.retail_config(self.key)
        digest = hashlib.sha256(f"retail:{query}".encode("utf-8")).digest()
        base = 50_000 + int.from_bytes(digest[:4], "big") % 100_000
        items = [
            CompItem(
                title=f"{query} 신상품 {index + 1}",
                price=int(base * ratio),
                source=self.key,
                is_used=False,
            )
            for index, ratio in enumerate(_MOCK_PRICE_RATIOS[: config["max_items"]])
        ]
        return RetailFetch(items=items, notes=["목업 신상품가입니다 — 실제 정가가 아닙니다."])


class NaverRetailSource(RetailSource):
    """네이버 쇼핑 오픈API로 신상품가를 모은다(CH002 V2에서 커버리지 실측 완료).

    ⚠️ 무료지만 쿼터가 있다. 어떤 실패든(키 부재·HTTP 오류·타임아웃·파싱 실패) 예외를 밖으로
    내지 않고 빈 결과로 돌려준다 — `service.py`에서 이중으로도 감싸지만, 계약은 여기서 못박는다.
    """

    key = "naver"

    def __init__(self, config: registry.RetailSourceConfig | None = None) -> None:
        self._config = config or registry.retail_config(self.key)

    def fetch(self, query: str) -> RetailFetch:
        client_id = settings.naver_client_id.strip()
        client_secret = settings.naver_client_secret.strip()
        if not (client_id and client_secret):
            return RetailFetch(items=[], notes=["NAVER_CLIENT_ID/SECRET이 설정되지 않았습니다."])

        import httpx

        try:
            response = httpx.get(
                _NAVER_SHOP_URL,
                params={"query": query, "display": self._config["max_items"] * 4, "sort": "sim"},
                headers={
                    "X-Naver-Client-Id": client_id,
                    "X-Naver-Client-Secret": client_secret,
                },
                timeout=self._config["timeout_seconds"],
            )
        except Exception as exc:  # noqa: BLE001 — 절대 예외를 던지지 않는 것이 이 클래스의 계약
            return RetailFetch(items=[], notes=[f"네이버 호출 실패: {type(exc).__name__}"])

        if response.status_code != 200:
            return RetailFetch(items=[], notes=[f"네이버 응답 오류: HTTP {response.status_code}"])

        try:
            rows = response.json().get("items", [])
        except Exception:  # noqa: BLE001 — 위와 같은 이유
            return RetailFetch(items=[], notes=["네이버 응답을 파싱하지 못했습니다."])

        items = _parse_items(rows)[: self._config["max_items"]]
        if not items:
            return RetailFetch(items=[], notes=["신상품가를 확인할 수 있는 매물이 없었습니다."])
        return RetailFetch(items=items)


def build_retail_source(key: str | None = None) -> RetailSource:
    """활성 신상품가 백엔드 구현체를 만든다."""
    resolved = key or registry.ACTIVE_RETAIL_SOURCE
    if resolved == "mock":
        return MockRetailSource()
    if resolved == "naver":
        return NaverRetailSource()
    raise ValueError(f"등록되지 않은 신상품가 백엔드입니다: {resolved!r}")


# --- 파싱 (네트워크 없이 테스트되는 순수 함수) --------------------------------


def _parse_items(rows: list[dict]) -> list[CompItem]:
    """네이버 쇼핑 API 응답 행을 `CompItem`으로. 중고(productType 4/5/6)는 드롭한다."""
    items: list[CompItem] = []
    for raw in rows:
        price = raw.get("lprice") or "0"
        if not str(price).isdigit() or int(price) <= 0:
            continue
        product_type = str(raw.get("productType", ""))
        if product_type in _USED_PRODUCT_TYPES:
            continue
        items.append(
            CompItem(
                title=html.unescape(_TAG_RE.sub("", raw.get("title", "")))[:200],
                price=int(price),
                source="naver",
                url=str(raw.get("link", "") or ""),
                # 신상품가는 "판별 불가"가 아니라 확실히 신품이다 — 항상 False.
                is_used=False,
            )
        )
    return items
