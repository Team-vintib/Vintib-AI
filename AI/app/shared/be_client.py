"""BE 공개 REST API 경량 클라이언트 — 상품 메타(가격·브랜드·판매상태 등) 조회.

CH016은 이 정보를 얻으려고 BE에 DB 뷰 + 읽기 전용 계정을 요청했는데(`docs/requests/BE/034`),
BE 공개 API(`GET /api/products/{id}`)가 이미 필요한 필드를 전부 응답으로 낸다
(`BE/.../product/dto/response/ProductResponse.java`: brandId/title/conditionGrade/saleType/
saleStatus/price/createdAt/categoryId) — `AI/scripts/backfill_garment_embeddings.py`가 같은
API로 상품 목록·이미지를 이미 가져오고 있다. DB 접근이 전혀 필요 없다(CH024).

이 모듈의 함수는 예외를 던지지 않는다 — 호출부(가격책정 `internal` comps, 게이트웨이의
임베딩 카테고리 태깅) 둘 다 "BE 응답 없음"을 정상 경로로 다뤄야 한다(`RetailSource.fetch()`와
같은 계약).

설계: `docs/plans/AI/CH024-classifier-pricing-real-integration.md`
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings

__all__ = ["BeProduct", "fetch_product"]


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
