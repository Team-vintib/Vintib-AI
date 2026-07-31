"""V0 — 정답셋 로더 + 스키마 검증.

`data/ground_truth.json`은 이미지 파일 자체를 담지 않는다 — 이미지는 품질검수 스파이크가
쓰는 `AI/validation/QUAL/sam3-condition-check/sample_images/`를 그대로 재사용한다(사용자
지시, 2026-08-01: "테스트 데이터는 품질 검수에 활용하는 데이터로 테스트할 거야"). `qc_shared.py`의
`SHARED_IMAGE_DIR` 관례와 동일하게 이 파일의 `SAMPLE_IMAGE_DIR`이 그 경로를 가리킨다.

**중요한 한계 — 반드시 리포트에 명시할 것**: 저 폴더에는 실제 사진이 8장뿐이고, 전부 하자
탐지용으로 고른 사진이라 대분류가 TOP/BOTTOM(그중에서도 BOTTOM은 전부 DENIM)에 쏠려 있고
촬영유형도 전부 평면샷/제품샷이다 — OUTER/SHOES/BAG/ACCESSORY가 하나도 없고 착용샷/걸이샷도
없다. `shirt_red.png`는 사실 실제 사진이 아니라 얼룩 하자 데모용 3D 렌더링 일러스트다(육안 확인,
2026-08-01) — `synthetic=True`로 표시하고 기본 평가에서 제외한다. 이 8건은 파이프라인이
끝까지 도는지 확인하는 스모크셋이지, V2~V4의 정확도 숫자를 신뢰할 근거가 되지 못한다.

라벨러: 이 8건은 사람이 아니라 Claude가 사진을 보고 1차로 채웠다(`labeler="claude_seed"`,
`needs_human_review=True`). **사람 라벨러 2명의 독립 라벨링 없이는 라벨러 간 일치율을 계산할
수 없다** — 이 스파이크는 그 계산을 하지 않는다(가짜로 2인 합의를 지어내지 않는다). 사람이
검증/추가 라벨링을 하기 전까지는 V4의 "사람도 안 맞는 항목" 상한선 분석이 성립하지 않는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from taxonomy import ALL_SUBCATEGORIES

_HERE = Path(__file__).resolve().parent

# QUAL 스파이크 세 개가 공유하는 것과 동일한 폴더. gitignore되어 있다(AI/.gitignore).
SAMPLE_IMAGE_DIR = _HERE.parents[1] / "QUAL" / "sam3-condition-check" / "sample_images"

GROUND_TRUTH_PATH = _HERE / "data" / "ground_truth.json"

SHOT_TYPES = ("worn", "flat", "hanging")  # 착용샷 / 평면샷 / 걸이샷


@dataclass
class Sample:
    image_file: str  # SAMPLE_IMAGE_DIR 기준 파일명
    subcategory: str
    primary_color: str
    secondary_color: str | None
    shot_type: str
    labeler: str
    needs_human_review: bool = False
    synthetic: bool = False  # 실제 사진이 아니면 True (기본 평가에서 제외)
    notes: str = ""

    @property
    def image_path(self) -> Path:
        return SAMPLE_IMAGE_DIR / self.image_file

    @property
    def major_category(self) -> str:
        from taxonomy import major_of

        return major_of(self.subcategory)


@dataclass
class ValidationIssue:
    index: int
    image_file: str
    message: str


@dataclass
class LoadResult:
    samples: list[Sample] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)


def _validate_row(index: int, row: dict) -> list[str]:
    """best-effort 검증 — 문제를 리스트로 모아 반환한다(하나 걸려도 전체를 죽이지 않음)."""
    from color import MULTI_LABEL, PALETTE

    problems: list[str] = []
    required = ("image_file", "subcategory", "primary_color", "shot_type", "labeler")
    for field_name in required:
        if not row.get(field_name):
            problems.append(f"필수 필드 누락: {field_name}")
    if problems:
        return problems  # 필수 필드가 없으면 아래 검증은 의미 없음

    if row["subcategory"] not in ALL_SUBCATEGORIES:
        problems.append(f"알 수 없는 subcategory: {row['subcategory']!r}")

    valid_colors = set(PALETTE) | {MULTI_LABEL}
    if row["primary_color"] not in valid_colors:
        problems.append(f"알 수 없는 primary_color: {row['primary_color']!r}")
    secondary = row.get("secondary_color")
    if secondary is not None and secondary not in valid_colors:
        problems.append(f"알 수 없는 secondary_color: {secondary!r}")

    if row["shot_type"] not in SHOT_TYPES:
        problems.append(f"알 수 없는 shot_type: {row['shot_type']!r} (허용: {SHOT_TYPES})")

    image_path = SAMPLE_IMAGE_DIR / row["image_file"]
    if not image_path.exists():
        problems.append(f"이미지 파일 없음: {image_path}")

    return problems


def load_ground_truth(path: Path = GROUND_TRUTH_PATH) -> LoadResult:
    """스키마를 통과한 행만 `Sample`로 담고, 문제 있는 행은 issues에 모아 best-effort로 계속한다."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    result = LoadResult()
    for index, row in enumerate(raw):
        problems = _validate_row(index, row)
        if problems:
            result.issues.append(
                ValidationIssue(
                    index=index,
                    image_file=row.get("image_file", "?"),
                    message="; ".join(problems),
                )
            )
            continue
        result.samples.append(
            Sample(
                image_file=row["image_file"],
                subcategory=row["subcategory"],
                primary_color=row["primary_color"],
                secondary_color=row.get("secondary_color"),
                shot_type=row["shot_type"],
                labeler=row["labeler"],
                needs_human_review=row.get("needs_human_review", False),
                synthetic=row.get("synthetic", False),
                notes=row.get("notes", ""),
            )
        )
    return result


def summarize(result: LoadResult) -> str:
    lines = [
        f"총 {len(result.samples) + len(result.issues)}행 중 유효 {len(result.samples)}행,"
        f" 문제 {len(result.issues)}행",
    ]
    if result.issues:
        lines.append("-- 문제 행 --")
        for issue in result.issues:
            lines.append(f"  [{issue.index}] {issue.image_file}: {issue.message}")

    majors: dict[str, int] = {}
    shots: dict[str, int] = {}
    reviewed = 0
    synthetic = 0
    for s in result.samples:
        majors[s.major_category] = majors.get(s.major_category, 0) + 1
        shots[s.shot_type] = shots.get(s.shot_type, 0) + 1
        reviewed += int(not s.needs_human_review)
        synthetic += int(s.synthetic)
    lines.append(f"-- 대분류 분포 -- {majors}")
    lines.append(f"-- 촬영유형 분포 -- {shots}")
    lines.append(f"-- 사람 검증 완료 -- {reviewed}/{len(result.samples)}")
    lines.append(f"-- synthetic(실제 사진 아님) -- {synthetic}/{len(result.samples)}")
    return "\n".join(lines)


if __name__ == "__main__":
    result = load_ground_truth()
    print(summarize(result))
