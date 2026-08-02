"""CLI — 지정한 경로(URL)를 긁어 VLM 학습용 (사진, 소분류 코드) 데이터셋을 만든다.

    # 1) 스펙 없이 매핑 규칙만 빠르게 확인
    python crawl.py --map-only "아우터 > 자켓 > 블루종"

    # 2) 새 사이트 스펙 시험 — 요청은 하되 아무것도 저장하지 않는다
    python crawl.py --spec sites/example-static-mall.yaml --url "https://..." --limit 5 --dry-run

    # 3) 실제 수집
    python crawl.py --spec sites/example-static-mall.yaml --url "https://..." --limit 200 --out ./out

산출물(`--out`, 기본 `./out`):
    out/images/<site>/<hash>.jpg
    out/items.jsonl      — 자동 확정된 학습용 행
    out/review.jsonl     — 사람이 확인해야 하는 행(모호/저신뢰)
    out/unmapped.jsonl   — 우리 taxonomy에 없는 카테고리(확장 논의용)

재실행하면 `source_url`·이미지 해시로 이미 수집한 건을 건너뛴다(이어받기).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 이 디렉터리를 import 경로에 넣는다 — 스파이크라 패키지로 만들지 않았다.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from color_hint import extract_color_hints, is_color_ambiguous  # noqa: E402
from downloader import ImageRejected, ImageStore  # noqa: E402
from fetcher import Fetcher, FetchError  # noqa: E402
from labels import major_of  # noqa: E402
from mapping import map_category  # noqa: E402
from parser import RawProduct, next_page_url, parse_detail, parse_listing  # noqa: E402
from schema import (  # noqa: E402
    CollectedItem,
    coverage_report,
    load_seen_keys,
    write_jsonl,
)
from site_spec import SiteSpec, load_spec  # noqa: E402

_STATUS_FILE = {
    "mapped": "items.jsonl",
    "needs_review": "review.jsonl",
    "unmapped": "unmapped.jsonl",
}


def build_item(
    raw: RawProduct,
    spec: SiteSpec,
    *,
    image_path: str = "",
    image_sha256: str = "",
) -> CollectedItem:
    """원본 파싱 결과 + 스펙 → 라벨링된 수집 행. 네트워크를 타지 않는 순수 변환."""
    result = map_category(
        raw.category_raw,
        site_table=spec.category_map,
        product_name=raw.product_name,
    )
    hints = extract_color_hints(raw.product_name, raw.option_text)
    return CollectedItem(
        image=image_path,
        subcategory_code=result.subcategory_code,
        primary_color=None,  # 자동으로 채우지 않는다(사용자 결정 2026-08-01)
        shot_type=spec.shot_type_default,
        source_site=spec.site,
        source_category_raw=raw.category_raw,
        source_url=raw.source_url,
        image_url=raw.image_url,
        image_sha256=image_sha256,
        product_name=raw.product_name,
        major_category=major_of(result.subcategory_code) if result.subcategory_code else None,
        mapping_status=result.status,
        mapping_confidence=result.confidence,
        mapping_method=result.method,
        mapping_reason=result.reason,
        mapping_runner_up=result.runner_up_code,
        color_hints=hints,
        color_ambiguous=is_color_ambiguous(hints, raw.product_name, raw.option_text),
    )


def _listing_urls(
    spec: SiteSpec, start_url: str | None, max_pages: int
) -> list[tuple[str, str | None]]:
    """긁을 (목록 URL, 그 URL의 카테고리) 목록.

    우선순위: `--url` > 스펙의 `category_urls` > `page_url_template`.
    카테고리가 URL로만 구분되는 사이트(대부분)에서는 두 번째가 기본 경로다.
    """
    listing = spec.listing
    assert listing is not None
    if start_url:
        # 스펙에 등록된 URL을 그대로 넘긴 경우 그 카테고리를 잃지 않게 먼저 찾아본다.
        for entry in listing.category_urls:
            if entry["url"] == start_url:
                return [(start_url, entry["category"])]
        return [(start_url, listing.category)]
    if listing.category_urls:
        return [(entry["url"], entry["category"]) for entry in listing.category_urls]
    template = listing.page_url_template
    if template:
        pages = range(listing.page_start, listing.page_start + max_pages)
        return [(url, listing.category) for p in pages if (url := next_page_url(template, p))]
    raise SystemExit(
        "URL이 필요하다 — --url을 주거나 스펙에 category_urls/page_url_template을 넣어라"
    )


def crawl(spec: SiteSpec, args: argparse.Namespace) -> list[CollectedItem]:
    out_dir = Path(args.out)
    jsonl_paths = [out_dir / name for name in _STATUS_FILE.values()]
    seen_urls = set() if args.dry_run else load_seen_keys(jsonl_paths)
    store = None if args.dry_run else ImageStore(out_dir / "images", spec.site)

    collected: list[CollectedItem] = []
    listing = spec.listing
    assert listing is not None
    max_pages = args.max_pages if args.max_pages is not None else listing.max_pages

    with Fetcher(
        user_agent=spec.user_agent,
        render=spec.render,
        delay_seconds=args.delay if args.delay is not None else spec.delay_seconds,
        respect_robots=not args.ignore_robots,
    ) as fetcher:
        for page_url, category in _listing_urls(spec, args.url, max_pages):
            print(f"[목록] {page_url}" + (f"  ({category})" if category else ""), file=sys.stderr)
            try:
                html = fetcher.get_html(
                    page_url,
                    wait_selector=listing.wait_selector,
                    scroll_times=listing.scroll_times,
                )
            except FetchError as exc:
                print(f"  ! {exc}", file=sys.stderr)
                continue

            products = parse_listing(html, page_url, listing)
            print(f"  상품 {len(products)}건 발견", file=sys.stderr)
            if not products:
                print(
                    "  ! 0건 — item_selector가 맞는지, SPA라면 render: playwright가 필요한지 확인",
                    file=sys.stderr,
                )

            for raw in products:
                if args.limit and len(collected) >= args.limit:
                    return collected
                if raw.source_url and raw.source_url in seen_urls:
                    continue
                # 카드 안에 카테고리 표기가 없는 사이트(대부분의 SPA)는 URL이 곧 카테고리다.
                if category and not raw.category_raw:
                    raw.category_raw = category
                item = _collect_one(raw, spec, fetcher, store, args)
                if item is None:
                    continue
                if raw.source_url:
                    seen_urls.add(raw.source_url)
                collected.append(item)
                if not args.dry_run:
                    write_jsonl(out_dir / _STATUS_FILE[item.mapping_status], [item])
                _print_row(item)
    return collected


def _collect_one(
    raw: RawProduct,
    spec: SiteSpec,
    fetcher: Fetcher,
    store: ImageStore | None,
    args: argparse.Namespace,
) -> CollectedItem | None:
    if spec.follow_detail:
        assert spec.detail is not None
        if not raw.source_url:
            return None
        try:
            html = fetcher.get_html(raw.source_url, wait_selector=spec.detail.wait_selector)
        except FetchError as exc:
            print(f"  ! {exc}", file=sys.stderr)
            return None
        detail = parse_detail(html, raw.source_url, spec.detail)
        # 목록에서 이미 얻은 값은 상세가 비어 있을 때만 유지한다(상세가 더 정확하다).
        raw = RawProduct(
            source_url=raw.source_url,
            image_url=detail.image_url or raw.image_url,
            product_name=detail.product_name or raw.product_name,
            category_raw=detail.category_raw or raw.category_raw,
            option_text=detail.option_text,
        )

    if not raw.image_url:
        print(f"  ! 이미지 URL 없음: {raw.source_url}", file=sys.stderr)
        return None

    image_path, digest = "", ""
    if store is not None:
        try:
            data = fetcher.get_bytes(raw.image_url)
            image_path, digest = store.save(data, raw.image_url)
        except (FetchError, ImageRejected) as exc:
            print(f"  - 건너뜀: {exc}", file=sys.stderr)
            return None

    return build_item(raw, spec, image_path=image_path, image_sha256=digest)


def _print_row(item: CollectedItem) -> None:
    mark = {"mapped": "OK ", "needs_review": "REV", "unmapped": "UNM"}[item.mapping_status]
    print(
        f"  {mark} {item.subcategory_code or '-':<16} "
        f"conf={item.mapping_confidence:<5} "
        f"[{item.source_category_raw[:40]}] {item.product_name[:40]}",
        file=sys.stderr,
    )


def _map_only(texts: list[str]) -> None:
    """크롤링 없이 매핑 규칙만 시험한다 — 새 사이트의 카테고리 트리를 조사할 때 쓴다."""
    for text in texts:
        result = map_category(text)
        print(
            f"{text}\n  -> {result.subcategory_code or '(미매핑)'} "
            f"[{result.status}] conf={result.confidence} "
            f"({result.reason})"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="쇼핑몰 상품 사진·카테고리 수집기 (VLM 카테고리 분류 파인튜닝용)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--spec", help="사이트 스펙 YAML 경로 (sites/*.yaml)")
    parser.add_argument("--url", help="긁을 목록 페이지 URL. 스펙의 page_url_template보다 우선한다")
    parser.add_argument("--out", default="./out", help="산출물 디렉터리 (기본 ./out)")
    parser.add_argument("--limit", type=int, default=0, help="최대 수집 건수 (0=제한 없음)")
    parser.add_argument(
        "--max-pages", type=int, default=None, help="목록 페이지 수 (스펙 값 덮어쓰기)"
    )
    parser.add_argument(
        "--delay", type=float, default=None, help="요청 간 지연(초). 스펙 값 덮어쓰기"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="이미지·JSONL을 저장하지 않고 파싱/매핑 결과만 출력 (새 스펙 검증용)",
    )
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        help="robots.txt 무시 (기본은 준수). 수집이 허용된 대상에만 쓸 것",
    )
    parser.add_argument(
        "--map-only",
        nargs="+",
        metavar="CATEGORY",
        help="크롤링 없이 카테고리 문자열 매핑 결과만 출력",
    )
    args = parser.parse_args(argv)

    if args.map_only:
        _map_only(args.map_only)
        return 0
    if not args.spec:
        parser.error("--spec 또는 --map-only 중 하나는 필요하다")

    spec = load_spec(args.spec)
    items = crawl(spec, args)

    print("\n" + "=" * 60)
    print(coverage_report(items))
    if not args.dry_run:
        print(f"\n산출물: {Path(args.out).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
