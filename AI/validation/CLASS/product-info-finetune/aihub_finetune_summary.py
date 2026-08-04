"""`artifacts_finetune/*/meta.json`을 모아 성능 기준으로 정렬한 비교표를 만든다.

LoRA(`aihub_finetune_lora.py`)·last-N 언프리즈(`aihub_finetune_vit.py`) 둘 다 같은
`artifacts_finetune/<run_name>/meta.json` 규약을 쓴다. 이 스크립트는 그 폴더를 훑어 각
run의 하이퍼파라미터 + `best_val_accuracy`/`test_accuracy`를 한 표로 모은다 — 여러
조합(`--r`·`--alpha`·`--dropout`·`--target-modules`·`--lr-adapter` 등)을 스윕한 뒤 어떤
run이 제일 나은지 눈으로 훑기 위해서다.

run을 지우거나 "최고만" 남기지 않는다 — `run_name()`이 조합마다 다른 폴더를 만들어 이미
전부 보존돼 있고(LoRA 체크포인트는 학습 대상 파라미터만 저장해 용량도 작다), 이 스크립트는
그 위에 읽기 전용 요약만 얹는다.

meta.json 구조는 스크립트마다 다르다(LoRA는 `lora_r`, last-N은 `unfreeze_layers` 등) —
그래서 특정 키를 하드코딩하지 않고, 각 meta.json의 **스칼라 필드를 그대로** 열로 편다.
`classes`(라벨 목록)·`history`(epoch별 로그)처럼 표에 넣기엔 너무 길거나 무의미한 리스트는
뺀다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_EXCLUDED_KEYS = frozenset({"classes", "history"})
_PRIORITY_COLUMNS = (
    "run",
    "task",
    "variant",
    "best_epoch",
    "best_val_accuracy",
    "test_accuracy",
)


def _flatten_meta(meta: dict[str, Any]) -> dict[str, Any]:
    """meta.json을 표 한 행으로 편다. 스칼라는 그대로, 원소가 스칼라뿐인 리스트는 문자열로
    합친다(`target_modules` 등). dict·`_EXCLUDED_KEYS`는 뺀다."""
    row: dict[str, Any] = {}
    for key, value in meta.items():
        if key in _EXCLUDED_KEYS or isinstance(value, dict):
            continue
        if isinstance(value, list):
            if all(isinstance(item, (str, int, float, bool)) for item in value):
                row[key] = ",".join(str(item) for item in value)
            continue
        row[key] = value
    return row


def load_runs(artifacts_finetune_dir: Path, pattern: str = "*/meta.json") -> list[dict[str, Any]]:
    """`artifacts_finetune_dir` 아래 `pattern`에 맞는 meta.json을 전부 읽어 행 목록으로 만든다.

    폴더 이름(`run_name()` 산출물)을 `run` 열로 같이 붙인다 — meta.json 안에는 없는 정보다.
    """
    rows = []
    for meta_path in sorted(artifacts_finetune_dir.glob(pattern)):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        row = _flatten_meta(meta)
        row["run"] = meta_path.parent.name
        rows.append(row)
    return rows


def sort_rows(
    rows: list[dict[str, Any]], sort_by: str, *, descending: bool = True
) -> list[dict[str, Any]]:
    """`sort_by` 기준 정렬. 그 필드가 없는 run은 정렬 방향과 무관하게 항상 맨 뒤로 보낸다
    (없다고 0 취급하면 내림차순에서 바닥, 오름차순에서는 반대로 맨 위에 와서 눈에 안 띈다)."""
    present = [row for row in rows if row.get(sort_by) is not None]
    missing = [row for row in rows if row.get(sort_by) is None]
    present.sort(key=lambda row: row[sort_by], reverse=descending)
    return present + missing


def _columns(rows: list[dict[str, Any]]) -> list[str]:
    all_keys: set[str] = set()
    for row in rows:
        all_keys.update(row.keys())
    remaining = sorted(all_keys - set(_PRIORITY_COLUMNS))
    return [column for column in _PRIORITY_COLUMNS if column in all_keys] + remaining


def _format_cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_markdown(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "(비교할 run이 없다)"
    columns = _columns(rows)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format_cell(row.get(column)) for column in columns) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="artifacts_finetune/*/meta.json을 모아 성능 기준 비교표를 출력한다"
    )
    parser.add_argument(
        "--artifacts-finetune-dir",
        type=Path,
        required=True,
        help="aihub_finetune_lora.py/aihub_finetune_vit.py의 --out-dir",
    )
    parser.add_argument("--pattern", default="*/meta.json", help="glob 패턴(하위 폴더 기준)")
    parser.add_argument("--sort-by", default="test_accuracy")
    parser.add_argument(
        "--ascending", action="store_true", help="기본은 내림차순(성능 높은 run이 위)"
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="지정하면 마크다운 표를 파일로도 저장"
    )
    args = parser.parse_args(argv)

    rows = load_runs(args.artifacts_finetune_dir, args.pattern)
    if not rows:
        print(
            f"{args.artifacts_finetune_dir}에서 meta.json을 못 찾았다(pattern={args.pattern})",
            file=sys.stderr,
        )
        return 1

    rows = sort_rows(rows, args.sort_by, descending=not args.ascending)
    table = render_markdown(rows)
    print(table)
    if args.out:
        args.out.write_text(table + "\n", encoding="utf-8")
        print(f"저장: {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
