"""스펙 셀렉터로 HTML에서 상품 정보를 뽑는다.

CSS 셀렉터 엔진은 `selectolax`(lxml보다 가볍고 빠르다)를 함수 내부에서 지연 import한다 —
CI에는 설치되지 않으므로 이 모듈은 import만으로 의존성을 요구하지 않는다.

이미지 URL은 쇼핑몰마다 지연로딩 속성(`data-src`, `data-original`, `srcset`)에 들어 있는
경우가 많아, 스펙의 `image_attr`가 비어 있으면 흔한 후보들을 순서대로 훑는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin

# 지연로딩 이미지 속성 후보 — 스펙에 지정한 attr가 비었을 때 순서대로 시도한다.
_IMAGE_ATTR_FALLBACKS = ("src", "data-src", "data-original", "data-lazy-src", "content")


@dataclass
class RawProduct:
    """파싱 직후의 원본 정보(아직 우리 라벨로 매핑되기 전)."""

    source_url: str = ""
    image_url: str = ""
    product_name: str = ""
    category_raw: str = ""
    option_text: str = ""
    extra: dict[str, str] = field(default_factory=dict)


def _parse(html: str):
    try:
        from selectolax.parser import HTMLParser
    except ImportError as exc:  # pragma: no cover - 환경 의존
        raise RuntimeError(
            "selectolax가 필요하다: pip install -r validation/CLASS/crawl-collector/requirements-crawl.txt"
        ) from exc
    return HTMLParser(html)


def _text(node) -> str:
    return " ".join(node.text(separator=" ", strip=True).split()) if node else ""


def _attr(node, attr: str, base_url: str) -> str:
    """속성 값을 절대 URL로. `srcset`은 첫 후보만 취한다."""
    if node is None:
        return ""
    candidates = [attr] if attr else []
    candidates += [a for a in _IMAGE_ATTR_FALLBACKS if a not in candidates]
    for name in candidates:
        value = node.attributes.get(name)
        if value:
            value = value.strip()
            if name == "srcset":
                value = value.split(",")[0].strip().split(" ")[0]
            return urljoin(base_url, value)
    # srcset은 fallback 목록에 없지만 마지막 수단으로 본다.
    srcset = node.attributes.get("srcset")
    if srcset:
        return urljoin(base_url, srcset.split(",")[0].strip().split(" ")[0])
    return ""


def parse_listing(html: str, base_url: str, listing) -> list[RawProduct]:
    """목록 페이지 → 상품 목록.

    `follow_detail: true`면 링크만 채워서 돌려주고, `false`면 이미지·이름·카테고리까지
    목록에서 바로 뽑는다(요청 수가 상품 수만큼 줄어든다).
    """
    tree = _parse(html)
    products: list[RawProduct] = []
    for node in tree.css(listing.item_selector):
        product = RawProduct()
        if listing.link_selector:
            link = node.css_first(listing.link_selector)
            product.source_url = _attr(link, listing.link_attr, base_url)
        elif node.tag == "a":
            product.source_url = _attr(node, "href", base_url)

        if listing.image_selector:
            product.image_url = _attr(
                node.css_first(listing.image_selector), listing.image_attr, base_url
            )
        if listing.name_selector:
            product.product_name = _text(node.css_first(listing.name_selector))
        if listing.category_selector:
            product.category_raw = _text(node.css_first(listing.category_selector))
        if listing.category:
            product.category_raw = listing.category

        if product.source_url or product.image_url:
            products.append(product)
    return products


def parse_detail(html: str, url: str, detail) -> RawProduct:
    """상세 페이지 → 이미지/이름/카테고리(breadcrumb는 이어붙인다)."""
    tree = _parse(html)
    product = RawProduct(source_url=url)
    product.image_url = _attr(tree.css_first(detail.image_selector), detail.image_attr, url)
    if detail.name_selector:
        product.product_name = _text(tree.css_first(detail.name_selector))
    if detail.category_selector:
        segments = [_text(node) for node in tree.css(detail.category_selector)]
        segments = [seg for seg in segments if seg]
        product.category_raw = detail.category_join.join(segments)
    if detail.option_selector:
        options = [_text(node) for node in tree.css(detail.option_selector)]
        product.option_text = " ".join(opt for opt in options if opt)
    return product


def next_page_url(template: str | None, page: int) -> str | None:
    """`page_url_template`의 {page}를 채운다. 템플릿이 없으면 None."""
    if not template:
        return None
    return template.replace("{page}", str(page))
