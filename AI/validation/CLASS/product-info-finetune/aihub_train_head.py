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


def head_filename(task: str, variant: str, source: str | None = None) -> str:
    """헤드 체크포인트 파일명. 학습·평가가 같은 규칙을 공유해야 한다."""
    return f"head_{task}_{variant}" + (f"_{source}" if source else "") + ".joblib"


def load_split(
    out_dir: Path, split: str, variant: str, embed_suffix: str | None = None
) -> tuple[Any, list[dict]]:
    """`aihub_embed.py` 산출물 한 쌍(.npy + .jsonl)을 읽는다. 행 순서가 일치한다.

    `embed_suffix`는 **파일명 태그**다(`aihub_embed.py --source`로 소스별로 따로 뽑았을 때만
    쓴다). 소스별 학습은 이걸로 하지 말고 `build_task_dataset(only_source=...)`를 써라 —
    임베딩은 한 번만 뽑고 행 단위로 거르는 게 GPU를 아낀다.
    """
    import numpy as np

    tag = f"{split}_{variant}" + (f"_{embed_suffix}" if embed_suffix else "")
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
    embeddings: Any, rows: list[dict], task: str, only_source: str | None = None
) -> tuple[Any, list[str], list[dict]]:
    """태스크별로 (X, y, 사용된 행)을 만든다. 라벨이 없는 행은 뺀다.

    `only_source`("clothes"|"accessory")를 주면 그 소스 행만 쓴다. **색상 헤드에 이게
    필요하다** — 액세서리의 금속 색상(실버→GRAY, 골드→YELLOW, 로즈골드→PINK)은
    `color.py` 팔레트가 상정한 의류 색상과 시각적으로 전혀 다른 물건이라, 은목걸이를
    회색 니트와 같은 클래스로 학습시키면 14-way 결정 경계가 금속 광택 쪽으로 끌려간다.
    JEWELRY는 목걸이+귀걸이 2:1로 접혀 표본이 두 배라 영향이 더 크다.

    카테고리 헤드는 반대로 두 소스가 다 필요하다(액세서리가 HAT·SUNGLASSES·JEWELRY를
    유일하게 덮는다). 그래서 소스 선택은 임베딩 추출이 아니라 **여기서** 한다.
    """
    import numpy as np

    keep: list[int] = []
    labels: list[str] = []

    for index, row in enumerate(rows):
        if only_source and row.get("source", "clothes") != only_source:
            continue
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
    parser.add_argument(
        "--source",
        default=None,
        choices=("clothes", "accessory"),
        help="이 소스 행만 학습에 쓴다(행 필터). 색상 헤드는 'clothes' 권장 — "
        "액세서리 금속색(실버→GRAY, 골드→YELLOW)이 의류 색상 경계를 흐린다",
    )
    parser.add_argument(
        "--embed-suffix",
        default=None,
        help="임베딩을 소스별로 따로 뽑았을 때의 파일명 접미사. 보통 필요 없다",
    )
    parser.add_argument("--C", type=float, default=DEFAULT_C)
    parser.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITER)
    parser.add_argument(
        "--class-weight",
        default="balanced",
        choices=("balanced", "none"),
        help="클래스 불균형 보정. 층화 상한과 함께 쓰는 두 번째 비중 손잡이",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="기본값: <artifacts>/head_<task>_<variant>[_<source>].joblib",
    )
    args = parser.parse_args(argv)

    import joblib

    class_weight = None if args.class_weight == "none" else "balanced"

    x_train, y_train, _ = build_task_dataset(
        *load_split(args.artifacts, "train", args.variant, args.embed_suffix),
        args.task,
        only_source=args.source,
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
                *load_split(args.artifacts, split, args.variant, args.embed_suffix),
                args.task,
                only_source=args.source,
            )
        except FileNotFoundError:
            print(f"({split} 임베딩이 없어 건너뜀)", file=sys.stderr)
            continue
        if len(y_eval):
            reports.append(_format_report(args.task, evaluate(model, x_eval, y_eval), split))

    # 소스를 파일명에 넣는다 — `--source clothes`로 학습한 색상 헤드가 전체 소스로 학습한
    # 헤드를 덮어써 버리면 두 조건을 비교할 수가 없다.
    out_path = args.out or args.artifacts / head_filename(args.task, args.variant, args.source)
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
