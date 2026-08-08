"""BE 공개 REST API 경량 클라이언트 — 상품 메타(가격·브랜드·판매상태 등) 조회.

CH016은 이 정보를 얻으려고 BE에 DB 뷰 + 읽기 전용 계정을 요청했는데(`docs/requests/BE/034`),
BE 공개 API(`GET /api/products/{id}`)가 이미 필요한 필드를 전부 응답으로 낸다
(`BE/.../product/dto/response/ProductResponse.java`: brandId/title/conditionGrade/saleType/
saleStatus/price/createdAt/categoryId) — `AI/scripts/backfill_garment_embeddings.py`가 같은
API로 상품 목록·이미지를 이미 가져오고 있다. DB 접근이 전혀 필요 없다(CH024).

`fetch_products_page()`/`fetch_brands()`(CH030)는 같은 원칙으로 목록 API(`GET /api/products`,
`GET /api/brands`)를 그대로 재사용한다 — 텍스트 기반 동일 상품 매칭(`app/pricing/
product_corpus.py`)이 카테고리별 후보 코퍼스를 만드는 데 쓴다. 새 검색 API가 필요 없다.

이 모듈의 함수는 예외를 던지지 않는다 — 호출부(가격책정 `internal`/`internal_text` comps,
게이트웨이의 임베딩 카테고리 태깅) 전부 "BE 응답 없음"을 정상 경로로 다뤄야 한다
(`RetailSource.fetch()`와 같은 계약).

설계: `docs/plans/AI/CH024-classifier-pricing-real-integration.md`,
`docs/plans/AI/CH030-pricing-text-match.md`
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings

__all__ = [
    "BeBrand",
    "BeProduct",
    "BeProductPage",
    "fetch_brands",
    "fetch_product",
    "fetch_products_page",
]


@dataclass(frozen=True)
class BeProduct:
    """`GET /api/products/{id}` 응답 중 가격책정·임베딩 태깅에 쓰는 필드만 뽑은 사본."""

    product_id: int
    title: str
    brand_id: int | None
    category_id: int | None
    condition_grade: str | None
    sale_type: str | None
    sale_status: str | None
    price: int | None
    created_at: str | None


def fetch_product(product_id: int, *, timeout: float = 5.0) -> BeProduct | None:
    """`GET /api/products/{id}` 1회 호출. 실패(네트워크·404·파싱 무엇이든)는 전부 `None`이다.

    가벼운 조회 실패로 가격 산정·임베딩 저장 전체가 막히면 안 된다 — `RetailSource.fetch()`와
    같은 관용 원칙.
    """
    import httpx

    try:
        response = httpx.get(f"{settings.be_base_url}/api/products/{product_id}", timeout=timeout)
    except Exception:  # noqa: BLE001 — 네트워크 오류 전부, 호출부는 None만 본다
        return None
    if response.status_code != 200:
        return None

    try:
        body = response.json()["data"]
        return BeProduct(
            product_id=int(body["id"]),
            title=str(body.get("title", "")),
            brand_id=body.get("brandId"),
            category_id=body.get("categoryId"),
            condition_grade=body.get("conditionGrade"),
            sale_type=body.get("saleType"),
            sale_status=body.get("saleStatus"),
            price=body.get("price"),
            created_at=body.get("createdAt"),
        )
    except Exception:  # noqa: BLE001 — 응답 형태가 계약과 어긋나도 None으로 흡수
        return None


@dataclass(frozen=True)
class BeProductPage:
    """`GET /api/products` 응답 1페이지. `has_next`로 다음 페이지 호출 여부만 판단하면 된다."""

    items: list[BeProduct]
    has_next: bool


def fetch_products_page(
    category_id: int, *, page: int = 0, size: int = 100, timeout: float = 5.0
) -> BeProductPage | None:
    """`GET /api/products?categoryIds={category_id}&page={page}&size={size}` 1페이지 조회.

    DRAFT 상태 상품은 BE가 이미 제외하고 응답한다. 실패(네트워크·비200·파싱 무엇이든)는
    전부 `None`이다 — 호출부(`product_corpus.py`)는 그 카테고리의 코퍼스 갱신만 건너뛰고
    다른 카테고리 갱신은 계속한다.
    """
    import httpx

    try:
        response = httpx.get(
            f"{settings.be_base_url}/api/products",
            params={"categoryIds": category_id, "page": page, "size": size},
            timeout=timeout,
        )
    except Exception:  # noqa: BLE001 — 네트워크 오류 전부, 호출부는 None만 본다
        return None
    if response.status_code != 200:
        return None

    try:
        data = response.json()["data"]
        items = [
            BeProduct(
                product_id=int(row["id"]),
                title=str(row.get("title", "")),
                brand_id=row.get("brandId"),
                category_id=row.get("categoryId"),
                condition_grade=row.get("conditionGrade"),
                sale_type=row.get("saleType"),
                sale_status=row.get("saleStatus"),
                price=row.get("price"),
                created_at=row.get("createdAt"),
            )
            for row in data.get("content", [])
        ]
        return BeProductPage(items=items, has_next=bool(data.get("hasNext")))
    except Exception:  # noqa: BLE001 — 응답 형태가 계약과 어긋나도 None으로 흡수
        return None


@dataclass(frozen=True)
class BeBrand:
    """`GET /api/brands` 응답 1건. `name`/`name_en` 둘 다 브랜드 별칭 사전의 키가 된다."""

    brand_id: int
    name: str
    name_en: str


def fetch_brands(*, timeout: float = 5.0) -> list[BeBrand] | None:
    """`GET /api/brands` 전체 목록 조회(21개 고정 마스터, 페이지네이션 없음).

    실패는 `None` — 호출부(`product_corpus.get_brand_alias_map()`)가 빈 사전으로 폴백한다.
    """
    import httpx

    try:
        response = httpx.get(f"{settings.be_base_url}/api/brands", timeout=timeout)
    except Exception:  # noqa: BLE001 — 네트워크 오류 전부, 호출부는 None만 본다
        return None
    if response.status_code != 200:
        return None

    try:
        data = response.json()["data"]
        return [
            BeBrand(
                brand_id=int(row["id"]),
                name=str(row.get("name", "")),
                name_en=str(row.get("nameEn", "")),
            )
            for row in data
        ]
    except Exception:  # noqa: BLE001 — 응답 형태가 계약과 어긋나도 None으로 흡수
        return None
