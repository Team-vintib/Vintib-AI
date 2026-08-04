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

# 색상 태스크에서 **제외할 소분류**.
#
# JEWELRY는 색상 라벨이 사실상 재질이다 — 실버·골드·로즈골드가 대부분이고, 우리 팔레트로
# 접으면 GRAY·YELLOW·PINK가 된다. 은목걸이를 회색 니트와 같은 클래스로 학습시키면 14-way
# 경계가 금속 광택 쪽으로 끌려간다. 게다가 목걸이+귀걸이 2:1 매핑이라 표본이 두 배다.
#
# **의류 색상 정확도가 이 작업의 1순위 수용 기준**이므로(브리핑 §11), 그걸 흐리면서까지
# 주얼리 색상을 배울 이유가 없다. 주얼리 색상은 zero-shot에 맡긴다.
# HAT·SUNGLASSES는 직물/플라스틱이라 그대로 둔다.
COLOR_EXCLUDED_SUBCATEGORIES = ("JEWELRY",)

# (B) 폴로 헤드의 학습 대상 정의(브리핑 §3-B).
POLO_POSITIVE_TYPE = "02top_02t-shirt"
POLO_NEGATIVE_TYPE = "02top_04shirt"
POLO_NEGATIVE_NECK = "shirts collar"


def head_filename(
    task: str, variant: str, source: str | None = None, label_space: str = "palette"
) -> str:
    """헤드 체크포인트 파일명. 학습·평가가 같은 규칙을 공유해야 한다.

    소스와 라벨공간을 파일명에 넣는다 — 조건별 헤드가 서로 덮어쓰면 비교가 불가능하다.
    """
    name = f"head_{task}_{variant}"
    if source:
        name += f"_{source}"
    if label_space != "palette":
        name += f"_{label_space}"
    return name + ".joblib"


def next_versioned_path(path: Path) -> Path:
    """`path`가 이미 있으면 안 겹치는 `_v2`, `_v3`, … 파일명을 찾아 반환한다.

    없으면 `path`를 그대로 돌려준다(첫 저장은 버전 접미어가 안 붙는다). 학습을 여러 번
    돌리며 조건(C·class-weight 등)을 바꿔볼 때 이전 헤드를 조용히 덮어쓰지 않기 위해서다.
    """
    if not path.exists():
        return path
    version = 2
    while True:
        candidate = path.with_name(f"{path.stem}_v{version}{path.suffix}")
        if not candidate.exists():
            return candidate
        version += 1


def latest_existing_version(path: Path) -> Path | None:
    """`path`와 그 버전들(`_v2`, `_v3`, …) 중 **실제로 존재하는 가장 최신 버전**을 찾는다.

    평가·서빙 쪽이 "가장 최근에 학습한 헤드"를 자동으로 집으려고 쓴다. 아무 버전도 없으면
    `None`.
    """
    latest = path if path.exists() else None
    version = 2
    while True:
        candidate = path.with_name(f"{path.stem}_v{version}{path.suffix}")
        if not candidate.exists():
            return latest
        latest = candidate
        version += 1


def build_collapse_map(rows: list[dict]) -> dict[str, str]:
    """`{원본 색상 문자열: 팔레트 코드}` — 네이티브 헤드의 예측을 접을 때 쓴다.

    데이터에서 직접 뽑는다(양쪽 컬럼이 같은 행에 있으므로). 매핑 테이블을 다시 import해
    맞추는 것보다 안전하다 — 학습에 실제로 쓰인 대응 관계 그대로다.
    """
    mapping: dict[str, str] = {}
    for row in rows:
        raw, palette = row.get("color_raw"), row.get("color")
        if raw and palette:
            mapping.setdefault(raw, palette)
    return mapping


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
    embeddings: Any,
    rows: list[dict],
    task: str,
    only_source: str | None = None,
    label_space: str = "palette",
    color_exclude: tuple[str, ...] = COLOR_EXCLUDED_SUBCATEGORIES,
) -> tuple[Any, list[str], list[dict]]:
    """태스크별로 (X, y, 사용된 행)을 만든다. 라벨이 없는 행은 뺀다.

    `only_source`("clothes"|"accessory")를 주면 그 소스 행만 쓴다. 카테고리 헤드는 두 소스가
    다 필요하고(액세서리가 HAT·SUNGLASSES·JEWELRY를 유일하게 덮는다), 색상 헤드는 상황에
    따라 다르다 — 아래 `label_space` 참고. 소스 선택을 임베딩 추출이 아니라 여기서 하는 건
    GPU를 한 번만 쓰기 위해서다.

    `label_space`(color 태스크 전용):

    - ``palette`` — 우리 13종+MIXED로 **접힌** 라벨(`color`)로 학습한다.
    - ``native``  — AI-Hub **원본 색상 문자열**(`color_raw`)로 학습하고, 접기는 추론 후에 한다.

    네이티브가 유리한 이유: 실버와 그레이를 미리 GRAY 하나로 합치면 그 클래스가 시각적으로
    갈라진 채(금속 광택 vs 직물) 선형 경계를 그려야 해서 불리하다. 따로 배우고 나중에 접으면
    그 문제가 없다. 접히는 손실은 액세서리 쪽에 몰려 있다(23종 → 14종). 덤으로, 팔레트를
    13종→10종으로 줄이기로 해도 **재학습 없이 접는 맵만 갈면 된다.**

    네이티브라도 **팔레트로 접히지 않는 행은 제외한다**(투명·기타) — 최종 출력이 팔레트
    코드여야 하므로 접을 데가 없는 클래스는 배워도 쓸 수 없다.
    """
    import numpy as np

    keep: list[int] = []
    labels: list[str] = []

    for index, row in enumerate(rows):
        if only_source and row.get("source", "clothes") != only_source:
            continue
        if task == "color":
            if color_exclude and row.get("subcategory") in color_exclude:
                continue  # 주얼리 금속색은 의류 색상 경계를 흐린다(모듈 상단 상수 참고)
            palette = row.get("color")
            label = row.get("color_raw") if label_space == "native" else palette
            # palette가 없으면 접을 데가 없다 → 네이티브에서도 버린다.
            if label and palette:
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


def collapse_labels(labels: list[str], mapping: dict[str, str]) -> list[str]:
    """네이티브 색상 라벨을 팔레트 코드로 접는다. 맵에 없으면 원본을 그대로 둔다."""
    return [mapping.get(label, label) for label in labels]


def evaluate_collapsed(model: Any, x: Any, y: list[str], mapping: dict[str, str]) -> dict:
    """네이티브 헤드를 **팔레트 기준**으로 평가한다 — 예측과 정답을 둘 다 접어서 비교한다.

    이게 실제 서비스 출력 기준이고, 팔레트 헤드와 비교할 수 있는 유일한 숫자다.
    """
    from collections import Counter

    from sklearn.metrics import accuracy_score

    predicted = collapse_labels(list(model.predict(x)), mapping)
    truth = collapse_labels(y, mapping)
    confusion: Counter = Counter()
    for actual, guess in zip(truth, predicted):
        if actual != guess:
            confusion[f"{actual} → {guess}"] += 1
    return {
        "n": len(truth),
        "accuracy": float(accuracy_score(truth, predicted)),
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
        help="이 소스 행만 학습에 쓴다(행 필터). 색상 헤드에서 액세서리를 빼고 싶을 때. "
        "다만 --label-space native 쪽이 데이터를 안 버리는 더 나은 해법이다",
    )
    parser.add_argument(
        "--color-exclude",
        nargs="*",
        default=list(COLOR_EXCLUDED_SUBCATEGORIES),
        help="색상 학습에서 뺄 소분류(기본 JEWELRY — 금속색이라 의류 색상 경계를 흐린다). "
        "빈 값으로 주면 아무것도 안 뺀다",
    )
    parser.add_argument(
        "--label-space",
        default="palette",
        choices=("palette", "native"),
        help="color 태스크 전용. native면 AI-Hub 원본 색상(실버·로즈골드 등)으로 학습하고 "
        "접기는 추론 후에 한다. 팔레트를 줄여도 재학습이 필요 없어진다",
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
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="같은 이름의 기존 헤드를 덮어쓴다. 기본은 버전을 올려 저장한다"
        "(head_..._v2.joblib, _v3, …) — 조건 바꿔가며 재학습할 때 이전 결과가 안 지워진다",
    )
    args = parser.parse_args(argv)

    import joblib

    class_weight = None if args.class_weight == "none" else "balanced"
    label_space = args.label_space if args.task == "color" else "palette"
    if args.label_space == "native" and args.task != "color":
        print("--label-space는 color 태스크에만 적용된다(무시함)", file=sys.stderr)

    x_train, y_train, kept_train = build_task_dataset(
        *load_split(args.artifacts, "train", args.variant, args.embed_suffix),
        args.task,
        only_source=args.source,
        label_space=label_space,
        color_exclude=tuple(args.color_exclude),
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

    collapse = build_collapse_map(kept_train) if label_space == "native" else {}

    def report_for(x: Any, y: list[str], name: str) -> list[str]:
        lines = [_format_report(args.task, evaluate(model, x, y), name)]
        if collapse:
            # **네이티브 정확도는 팔레트 헤드와 직접 비교하면 안 된다** — 클래스가 더 많아
            # 불리하게 나온다. 접은 뒤 숫자가 실제 서비스 출력 기준이고, 이게 비교 대상이다.
            folded = evaluate_collapsed(model, x, y, collapse)
            lines.append(f"  ↳ 팔레트로 접은 뒤: accuracy={folded['accuracy']:.4f} (비교 기준)")
        return lines

    reports = report_for(x_train, y_train, "train")
    for split in ("val", "test"):
        try:
            x_eval, y_eval, _ = build_task_dataset(
                *load_split(args.artifacts, split, args.variant, args.embed_suffix),
                args.task,
                only_source=args.source,
                label_space=label_space,
                color_exclude=tuple(args.color_exclude),
            )
        except FileNotFoundError:
            print(f"({split} 임베딩이 없어 건너뜀)", file=sys.stderr)
            continue
        if len(y_eval):
            reports.extend(report_for(x_eval, y_eval, split))

    # 소스·라벨공간을 파일명에 넣는다 — 조건별 헤드가 서로 덮어쓰면 비교가 불가능하다.
    out_path = args.out or args.artifacts / head_filename(
        args.task, args.variant, args.source, label_space
    )
    if not args.overwrite:
        out_path = next_versioned_path(out_path)
    joblib.dump(
        {
            "task": args.task,
            "variant": args.variant,
            "source": args.source,
            "label_space": label_space,
            # 네이티브 헤드의 예측을 팔레트 코드로 접는 표. 평가·서빙이 이걸 그대로 쓴다.
            # 팔레트를 13종→10종으로 줄이려면 재학습 없이 이 dict만 갈아끼우면 된다.
            "collapse": collapse,
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
