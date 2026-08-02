"""사이트 스펙(YAML) 로더 — "내가 지정하는 경로"를 코드 수정 없이 받기 위한 층.

쇼핑몰마다 파서를 새로 짜는 대신, **어디를 긁을지(셀렉터)와 원본 카테고리를 우리 코드로
어떻게 옮길지(category_map)** 를 YAML 한 장에 선언한다. 새 쇼핑몰 = 새 YAML 한 장.

PyYAML은 CI에 설치되지 않으므로 **함수 내부에서 지연 import**한다. 이 파일의 dataclass·검증
로직 자체는 표준 라이브러리만 쓰므로 dict로 만든 스펙은 CI에서도 테스트된다
(`spec_from_dict`).

스펙 예시는 `sites/_TEMPLATE.yaml` 참고.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from labels import SHOT_TYPES, is_valid_subcategory

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 "
    "S15P11A108-dataset-collector/0.1 (research; contact via repo)"
)


class SpecError(ValueError):
    """스펙 파일이 잘못된 경우. 크롤링을 시작하기 전에 터뜨린다."""


@dataclass
class ListingSpec:
    """목록 페이지에서 상품을 찾아내는 방법."""

    item_selector: str
    link_selector: str | None = None
    link_attr: str = "href"
    # 상세 페이지를 안 열고 목록에서 바로 이미지를 가져오는 모드(요청 수가 크게 준다).
    image_selector: str | None = None
    image_attr: str = "src"
    name_selector: str | None = None
    # 목록 URL 자체가 카테고리인 경우(예: .../outer/jacket) 그 카테고리 텍스트를 고정한다.
    category: str | None = None
    category_selector: str | None = None
    # 페이지네이션 — {page}가 1부터 채워진다. 없으면 첫 페이지만 본다.
    page_url_template: str | None = None
    page_start: int = 1
    max_pages: int = 1
    # playwright 렌더 시 무한스크롤 횟수.
    scroll_times: int = 0
    wait_selector: str | None = None


@dataclass
class DetailSpec:
    """상세 페이지에서 이미지/카테고리를 뽑는 방법."""

    image_selector: str
    image_attr: str = "src"
    name_selector: str | None = None
    # breadcrumb처럼 여러 노드에 나뉜 카테고리는 전부 모아 " > "로 잇는다.
    category_selector: str | None = None
    category_join: str = " > "
    option_selector: str | None = None  # 색상 옵션 텍스트(색상 힌트용)
    wait_selector: str | None = None


@dataclass
class SiteSpec:
    site: str
    render: str = "static"  # static | playwright
    follow_detail: bool = True
    shot_type_default: str | None = None
    user_agent: str = DEFAULT_USER_AGENT
    delay_seconds: float = 1.5
    listing: ListingSpec | None = None
    detail: DetailSpec | None = None
    category_map: dict[str, str] = field(default_factory=dict)
    notes: str = ""


_TOP_LEVEL_KEYS = {
    "site",
    "render",
    "follow_detail",
    "shot_type_default",
    "user_agent",
    "delay_seconds",
    "listing",
    "detail",
    "category_map",
    "notes",
}


def _build(cls: type, data: dict[str, Any], where: str):
    known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    unknown = sorted(set(data) - known)
    if unknown:
        raise SpecError(
            f"{where}에 모르는 키가 있다: {unknown} (오타 확인 — 허용: {sorted(known)})"
        )
    return cls(**data)


def spec_from_dict(data: dict[str, Any]) -> SiteSpec:
    """dict → SiteSpec. YAML 파싱과 분리해 둬서 테스트에서 그대로 쓸 수 있다."""
    unknown = sorted(set(data) - _TOP_LEVEL_KEYS)
    if unknown:
        raise SpecError(f"스펙 최상위에 모르는 키가 있다: {unknown}")
    if not data.get("site"):
        raise SpecError("`site`(source_site로 기록될 이름)는 필수다")

    payload = dict(data)
    listing = payload.pop("listing", None)
    detail = payload.pop("detail", None)
    spec = _build(SiteSpec, payload, "스펙 최상위")
    if listing is not None:
        spec.listing = _build(ListingSpec, listing, "listing")
    if detail is not None:
        spec.detail = _build(DetailSpec, detail, "detail")

    _validate(spec)
    return spec


def _validate(spec: SiteSpec) -> None:
    if spec.render not in ("static", "playwright"):
        raise SpecError(f"render는 static|playwright 중 하나여야 한다: {spec.render!r}")
    if spec.shot_type_default is not None and spec.shot_type_default not in SHOT_TYPES:
        raise SpecError(f"shot_type_default는 {list(SHOT_TYPES)} 중 하나여야 한다")
    if spec.listing is None:
        raise SpecError("`listing` 섹션은 필수다(목록에서 상품을 찾는 방법)")
    if spec.follow_detail:
        if spec.detail is None:
            raise SpecError("follow_detail: true면 `detail` 섹션이 필요하다")
        if not spec.listing.link_selector:
            raise SpecError("follow_detail: true면 listing.link_selector가 필요하다")
    else:
        if not spec.listing.image_selector:
            raise SpecError("follow_detail: false면 listing.image_selector가 필요하다")
        if not (spec.listing.category or spec.listing.category_selector):
            raise SpecError(
                "follow_detail: false면 listing.category(고정 문자열) 또는 "
                "listing.category_selector 중 하나는 있어야 한다 — 카테고리 없이는 라벨을 만들 수 없다"
            )

    # category_map의 값이 실제 taxonomy 코드인지 — 오타는 조용히 라벨을 오염시킨다.
    bad = sorted({code for code in spec.category_map.values() if not is_valid_subcategory(code)})
    if bad:
        raise SpecError(f"category_map에 taxonomy에 없는 소분류 코드가 있다: {bad}")


def load_spec(path: str | Path) -> SiteSpec:
    """YAML 파일 → SiteSpec. PyYAML은 여기서만 필요하다(지연 import)."""
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - 환경 의존
        raise SpecError(
            "PyYAML이 필요하다: pip install -r validation/CLASS/crawl-collector/requirements-crawl.txt"
        ) from exc

    path = Path(path)
    if not path.exists():
        raise SpecError(f"스펙 파일이 없다: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SpecError(f"스펙 최상위는 매핑이어야 한다: {path}")
    return spec_from_dict(data)
