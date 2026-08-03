"""수집 산출물 스키마(JSONL) + 커버리지 집계.

브리핑 §4.1의 최소 요구 스키마를 그대로 담는다. 학습 스크립트가 이 JSONL 한 파일만 읽으면
되게, 이미지 경로·라벨·출처·매핑 근거를 한 행에 모은다.

파일 3개로 나눠 쓴다(`crawl.py`가 씀):
- `items.jsonl`      — 매핑 성공(status=mapped). 바로 학습에 쓸 수 있는 행.
- `review.jsonl`     — status=needs_review. 사람이 사진 보고 확정할 대상.
- `unmapped.jsonl`   — status=unmapped. taxonomy 확장 논의용(브리핑 §5.5).

표준 라이브러리만 쓴다.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

from labels import ALL_SUBCATEGORIES, CONFUSION_PAIRS, TAXONOMY_VERSION, major_of

SCHEMA_VERSION = "class-crawl-v1"


@dataclass
class CollectedItem:
    """수집한 상품 1건. 필드 이름은 브리핑 §4.1 표기를 그대로 따른다."""

    # --- 필수 ---
    image: str  # 저장된 이미지 파일의 상대 경로(out_dir 기준)
    subcategory_code: str | None  # 우리 30종 코드. 미매핑이면 None
    primary_color: str | None = None  # 자동 채우지 않는다 — 사람/후처리 몫
    # --- 선택/권장 ---
    secondary_color: str | None = None
    shot_type: str | None = None  # worn / flat / hanging. 사이트 스펙 기본값 또는 사후 라벨
    source_site: str = ""
    source_category_raw: str = ""
    # --- 추적/검수용 ---
    source_url: str = ""
    image_url: str = ""
    image_sha256: str = ""
    product_name: str = ""
    major_category: str | None = None
    mapping_status: str = "unmapped"  # mapped / needs_review / unmapped
    mapping_confidence: float = 0.0
    mapping_method: str = "none"
    mapping_reason: str = ""
    mapping_runner_up: str | None = None
    color_hints: list[str] = field(default_factory=list)
    color_ambiguous: bool = False
    taxonomy_version: str = TAXONOMY_VERSION
    schema_version: str = SCHEMA_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def write_jsonl(path: Path, items: Iterable[CollectedItem], *, append: bool = True) -> int:
    """JSONL로 저장. 이어받기를 지원하려고 기본이 append다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a" if append else "w", encoding="utf-8") as fp:
        for item in items:
            fp.write(item.to_json() + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_seen_keys(paths: Iterable[Path], key: str = "source_url") -> set[str]:
    """이미 수집한 항목 키 집합 — 재실행 시 이어받기(중복 요청 방지)에 쓴다."""
    seen: set[str] = set()
    for path in paths:
        for row in read_jsonl(path):
            value = row.get(key)
            if value:
                seen.add(value)
    return seen


def coverage_report(items: Iterable[CollectedItem]) -> str:
    """브리핑 §4.3의 편향(대분류 쏠림·혼동쌍 부족)을 바로 보게 하는 요약.

    수집이 끝난 뒤 "무엇이 부족한지"를 이 출력만 보고 판단할 수 있어야 한다 —
    1차 검증이 TOP/BOTTOM·flat에만 몰려 근거로 못 쓰였던 게 이 리포트를 넣는 이유다.
    """
    items = list(items)
    by_sub = Counter(i.subcategory_code for i in items if i.subcategory_code)
    by_major = Counter(major_of(code) for code in by_sub.elements())
    by_shot = Counter(i.shot_type or "(unlabeled)" for i in items)
    by_status = Counter(i.mapping_status for i in items)

    lines: list[str] = []
    lines.append(
        f"총 {len(items)}건 | " + ", ".join(f"{k}={v}" for k, v in by_status.most_common())
    )
    lines.append("")
    lines.append("[대분류]")
    for major in ("OUTER", "TOP", "BOTTOM", "SHOES", "BAG", "ACCESSORY"):
        lines.append(f"  {major:<10} {by_major.get(major, 0):>5}")

    lines.append("")
    lines.append("[소분류 — 0건인 코드는 학습 전에 반드시 채울 것]")
    missing = [code for code in ALL_SUBCATEGORIES if by_sub.get(code, 0) == 0]
    for code in ALL_SUBCATEGORIES:
        lines.append(f"  {code:<16} {by_sub.get(code, 0):>5}")
    if missing:
        lines.append(f"  ! 미수집 {len(missing)}종: {', '.join(missing)}")

    lines.append("")
    lines.append("[촬영유형]")
    for shot, count in by_shot.most_common():
        lines.append(f"  {shot:<12} {count:>5}")

    lines.append("")
    lines.append("[혼동쌍 — 양쪽 다 충분해야 구분 학습이 된다]")
    for left, right in CONFUSION_PAIRS:
        lines.append(
            f"  {left:<16}{by_sub.get(left, 0):>5}  vs  {right:<16}{by_sub.get(right, 0):>5}"
        )

    return "\n".join(lines)
