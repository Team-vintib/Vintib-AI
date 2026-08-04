"""동결 백본 위 **선형 분류 헤드** 학습 — 브리핑 §3의 2단계(CPU 수 초).

`aihub_embed.py`가 떨군 `.npy` 임베딩과 라벨만 쓴다. **백본은 이 파일에서 아예 로드하지도
않는다** — 그래서 GPU가 필요 없고, 재학습이 초 단위라 하이퍼파라미터 탐색이 사실상 공짜다.

학습 대상 3개 (브리핑 §3의 우선순위)
------------------------------------
- ``color``    : (A) 14-way 로지스틱 회귀. 색상은 라벨 커버리지 100%라 정석대로 된다.
- ``polo``     : (B) 폴로 이진 판별기. **35-way를 건드리지 않는다.** zero-shot이 top-2로
                 {TSHIRT, SHIRT}를 뽑았을 때만 발동한다 → 나머지 클래스 회귀 위험 0.
                 양성 = `02top_02t-shirt` + topneck에 polo / 음성 = `02top_04shirt` +
                 topneck == "shirts collar".
- ``category`` : 커버 클래스 N-way. **미커버 클래스(신발·가방 등)는 여전히 zero-shot이
                 담당한다** — 이 헤드는 커버 클래스 안에서만 쓰거나, (C) 하이브리드
                 프로토타입의 재료로 쓴다. 단독으로 35-way를 대체하지 않는다.

`class_weight`가 소스/클래스 비중을 맞추는 두 번째 손잡이다(첫 번째는 `aihub_dataset.py`의
층화 샘플링 상한). 표본 수가 클래스마다 다를 때 `balanced`가 손실에 역가중을 준다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TASKS = ("color", "polo", "category")

# 로지스틱 회귀 기본값 — 임베딩이 이미 L2 정규화돼 있어 스케일링이 필요 없다.
DEFAULT_C = 1.0
DEFAULT_MAX_ITER = 2000
SEED = 42

# (B) 폴로 헤드의 학습 대상 정의(브리핑 §3-B).
POLO_POSITIVE_TYPE = "02top_02t-shirt"
POLO_NEGATIVE_TYPE = "02top_04shirt"
POLO_NEGATIVE_NECK = "shirts collar"


def load_split(
    out_dir: Path, split: str, variant: str, source: str | None = None
) -> tuple[Any, list[dict]]:
    """`aihub_embed.py` 산출물 한 쌍(.npy + .jsonl)을 읽는다. 행 순서가 일치한다."""
    import numpy as np

    tag = f"{split}_{variant}" + (f"_{source}" if source else "")
    npy_path = out_dir / f"{tag}.npy"
    jsonl_path = out_dir / f"{tag}.jsonl"
    if not npy_path.exists():
        raise FileNotFoundError(f"임베딩이 없다: {npy_path} — aihub_embed.py를 먼저 돌릴 것")

    embeddings = np.load(npy_path)
    rows = [
        json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line
    ]
    if len(rows) != len(embeddings):
        raise ValueError(f"행 수 불일치: {npy_path}={len(embeddings)} vs {jsonl_path}={len(rows)}")
    return embeddings, rows


def build_task_dataset(
    embeddings: Any, rows: list[dict], task: str
) -> tuple[Any, list[str], list[dict]]:
    """태스크별로 (X, y, 사용된 행)을 만든다. 라벨이 없는 행은 뺀다."""
    import numpy as np

    keep: list[int] = []
    labels: list[str] = []

    for index, row in enumerate(rows):
        if task == "color":
            label = row.get("color")
            if label:
                keep.append(index)
                labels.append(label)
        elif task == "category":
            label = row.get("subcategory")
            if label:
                keep.append(index)
                labels.append(label)
        elif task == "polo":
            source_type = row.get("source_type")
            neck = (row.get("neck") or "").strip().casefold()
            if source_type == POLO_POSITIVE_TYPE and row.get("is_polo"):
                keep.append(index)
                labels.append("TSHIRT")
            elif source_type == POLO_NEGATIVE_TYPE and neck == POLO_NEGATIVE_NECK:
                keep.append(index)
                labels.append("SHIRT")
        else:  # pragma: no cover - argparse가 막는다
            raise ValueError(f"unknown task: {task}")

    if not keep:
        return np.zeros((0, embeddings.shape[1] if embeddings.ndim == 2 else 0)), [], []
    return embeddings[keep], labels, [rows[i] for i in keep]


def train(
    x_train: Any,
    y_train: list[str],
    *,
    C: float = DEFAULT_C,
    max_iter: int = DEFAULT_MAX_ITER,
    class_weight: str | None = "balanced",
) -> Any:
    from sklearn.linear_model import LogisticRegression

    model = LogisticRegression(
        C=C,
        max_iter=max_iter,
        class_weight=class_weight,
        multi_class="auto",
        n_jobs=None,
        random_state=SEED,
    )
    model.fit(x_train, y_train)
    return model


def evaluate(model: Any, x: Any, y: list[str]) -> dict:
    """정확도 + 클래스별 리포트 + 상위 혼동쌍."""
    from collections import Counter

    from sklearn.metrics import accuracy_score, classification_report

    predicted = model.predict(x)
    confusion: Counter = Counter()
    for truth, guess in zip(y, predicted):
        if truth != guess:
            confusion[f"{truth} → {guess}"] += 1
    return {
        "n": len(y),
        "accuracy": float(accuracy_score(y, predicted)),
        "per_class": classification_report(y, predicted, output_dict=True, zero_division=0),
        "top_confusions": confusion.most_common(10),
    }


def _format_report(task: str, result: dict, label: str) -> str:
    lines = [f"[{label}] n={result['n']:,}  accuracy={result['accuracy']:.4f}"]
    per_class = result["per_class"]
    rows = [
        (code, f"{stats['precision']:.3f}", f"{stats['recall']:.3f}", f"{int(stats['support']):,}")
        for code, stats in sorted(per_class.items())
        if isinstance(stats, dict) and code not in {"accuracy", "macro avg", "weighted avg"}
    ]
    width = max((len(r[0]) for r in rows), default=8)
    lines.append(f"  {'클래스'.ljust(width)}  precision  recall  support")
    for code, precision, recall, support in rows:
        lines.append(f"  {code.ljust(width)}  {precision:>9}  {recall:>6}  {support:>7}")
    if result["top_confusions"]:
        lines.append(f"  상위 혼동({task}):")
        for pair, count in result["top_confusions"]:
            lines.append(f"    {pair}: {count}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="동결 백본 위 선형 헤드 학습 (CPU, 수 초)")
    parser.add_argument("--artifacts", type=Path, required=True, help="aihub_embed.py의 --out-dir")
    parser.add_argument("--task", required=True, choices=TASKS)
    parser.add_argument("--variant", default="masked", choices=("raw", "masked"))
    parser.add_argument("--source", default=None, choices=("clothes", "accessory"))
    parser.add_argument("--C", type=float, default=DEFAULT_C)
    parser.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITER)
    parser.add_argument(
        "--class-weight",
        default="balanced",
        choices=("balanced", "none"),
        help="클래스 불균형 보정. 층화 상한과 함께 쓰는 두 번째 비중 손잡이",
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="기본값: <artifacts>/head_<task>_<variant>.joblib"
    )
    args = parser.parse_args(argv)

    import joblib

    class_weight = None if args.class_weight == "none" else "balanced"

    x_train, y_train, _ = build_task_dataset(
        *load_split(args.artifacts, "train", args.variant, args.source), args.task
    )
    if len(y_train) == 0:
        print(f"학습 표본이 0개다 (task={args.task}) — 인덱스/필터를 확인할 것", file=sys.stderr)
        return 1
    if len(set(y_train)) < 2:
        print(f"클래스가 1종뿐이다: {set(y_train)} — 학습할 수 없다", file=sys.stderr)
        return 1

    print(
        f"task={args.task} variant={args.variant} train={len(y_train):,} classes={len(set(y_train))}"
    )
    model = train(x_train, y_train, C=args.C, max_iter=args.max_iter, class_weight=class_weight)

    reports = [_format_report(args.task, evaluate(model, x_train, y_train), "train")]
    for split in ("val", "test"):
        try:
            x_eval, y_eval, _ = build_task_dataset(
                *load_split(args.artifacts, split, args.variant, args.source), args.task
            )
        except FileNotFoundError:
            print(f"({split} 임베딩이 없어 건너뜀)", file=sys.stderr)
            continue
        if len(y_eval):
            reports.append(_format_report(args.task, evaluate(model, x_eval, y_eval), split))

    out_path = args.out or args.artifacts / f"head_{args.task}_{args.variant}.joblib"
    joblib.dump(
        {
            "task": args.task,
            "variant": args.variant,
            "source": args.source,
            "classes": sorted(set(y_train)),
            "class_weight": args.class_weight,
            "C": args.C,
            "model": model,
        },
        out_path,
    )

    print("\n".join(reports))
    print(f"\n저장: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
