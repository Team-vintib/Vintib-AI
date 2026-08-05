"""`artifacts_finetune/*/meta.json`의 epoch별 `history`를 방법별로 겹쳐 그린다.

`aihub_finetune_summary.py`가 성능 숫자를 표로 보여준다면, 이 스크립트는 그 안의
`history`(epoch별 train_loss/val_accuracy)를 그래프로 보여준다 — 과적합이 언제부터
시작되는지, 방법마다 수렴 양상이 어떻게 다른지는 표로는 안 보인다.

노트북 셀에 긴 matplotlib 코드를 직접 붙여넣다가 복사가 반복적으로 깨지는 문제가
있었다(2026-08-05, `SyntaxError: unterminated string literal` / `f-string: expecting
'=', or '!', or ':', or '}'`) — 그래서 이 파이프라인의 다른 무거운 단계들과 같은 원칙
(무거운 건 `.py` 스크립트로, 노트북은 짧게 호출만)을 그대로 따른다.

산출물 2종(`--out-dir`, 기본값은 `--artifacts-finetune-dir`와 동일):
- `compare_<method>.png`        — 방법별 1장, 그 안의 하이퍼파라미터(run)를 전부 겹쳐 그림
- `compare_best_per_method.png` — 방법별 최고 run(`best_val_accuracy` 기준)만 모아 비교
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_METHOD_PREFIXES = (
    ("vit_last", "last-N 언프리즈"),
    ("lora_", "LoRA"),
    ("full_", "전체 파인튜닝"),
)


def method_of(run_name: str) -> str:
    """run 폴더 이름(`run_name()` 산출물) 접두어로 방법을 분류한다.

    새 파인튜닝 스크립트를 추가할 때 그 스크립트의 `run_name()`도 여기 접두어로
    시작해야 자동으로 분류된다(안 맞으면 "기타"로 묶여 눈에 띈다).
    """
    for prefix, label in _METHOD_PREFIXES:
        if run_name.startswith(prefix):
            return label
    return "기타"


def load_runs(artifacts_finetune_dir: Path) -> list[dict[str, Any]]:
    """`history`를 보존한 채로 meta.json을 전부 읽는다.

    `aihub_finetune_summary.py`의 `load_runs()`는 표에 넣기엔 너무 길어서 `history`를
    빼므로, 그래프용으로 여기서 따로 읽는다.
    """
    runs = []
    for meta_path in sorted(artifacts_finetune_dir.glob("*/meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        name = meta_path.parent.name
        runs.append({"name": name, "method": method_of(name), "meta": meta})
    return runs


def parse_baseline(spec: str) -> tuple[str, float]:
    """`"라벨=값"` 문자열을 (라벨, 값)으로 파싱한다. 베스트-run 비교 플랏의 기준선(수평선)에 쓴다."""
    label, separator, value = spec.rpartition("=")
    if not separator:
        raise ValueError(f"'라벨=값' 형식이 아니다: {spec!r}")
    return label, float(value)


def plot_per_method(runs: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    """방법별로 1장씩 — 그 안의 run(하이퍼파라미터 조합)을 전부 겹쳐 그린다."""
    import matplotlib.pyplot as plt

    by_method: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_method.setdefault(run["method"], []).append(run)

    saved = []
    for method, method_runs in by_method.items():
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        for run in method_runs:
            history = run["meta"]["history"]
            epochs = [h["epoch"] for h in history]
            axes[0].plot(epochs, [h["train_loss"] for h in history], marker="o", label=run["name"])
            axes[1].plot(
                epochs, [h["val_accuracy"] for h in history], marker="o", label=run["name"]
            )
        axes[0].set_title(f"{method} — train loss")
        axes[1].set_title(f"{method} — val accuracy")
        for ax in axes:
            ax.set_xlabel("epoch")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
        fig.tight_layout()
        safe_name = method.replace(" ", "_").replace("/", "_")
        out_path = out_dir / f"compare_{safe_name}.png"
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        saved.append(out_path)
    return saved


def plot_best_per_method(
    runs: list[dict[str, Any]], out_dir: Path, baselines: list[tuple[str, float]]
) -> Path:
    """방법별 최고 run(`best_val_accuracy` 기준)만 뽑아 한 플랏에서 비교한다."""
    import matplotlib.pyplot as plt

    best_per_method: dict[str, dict[str, Any]] = {}
    for run in runs:
        acc = run["meta"]["best_val_accuracy"]
        current = best_per_method.get(run["method"])
        if current is None or acc > current["meta"]["best_val_accuracy"]:
            best_per_method[run["method"]] = run

    fig, ax = plt.subplots(figsize=(7, 5))
    for method, run in best_per_method.items():
        history = run["meta"]["history"]
        epochs = [h["epoch"] for h in history]
        label = f"{method} ({run['name']})"
        ax.plot(epochs, [h["val_accuracy"] for h in history], marker="o", label=label)

    linestyles = ("--", ":", "-.")
    for index, (label, value) in enumerate(baselines):
        ax.axhline(value, linestyle=linestyles[index % len(linestyles)], color="gray", label=label)

    ax.set_title("방법별 베스트 run — val accuracy")
    ax.set_xlabel("epoch")
    ax.set_ylabel("val accuracy")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_path = out_dir / "compare_best_per_method.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="artifacts_finetune/*/meta.json의 epoch별 history를 방법별로 비교 플랏"
    )
    parser.add_argument("--artifacts-finetune-dir", type=Path, required=True)
    parser.add_argument(
        "--out-dir", type=Path, default=None, help="기본값: --artifacts-finetune-dir와 동일"
    )
    parser.add_argument(
        "--baseline",
        action="append",
        default=[],
        metavar="라벨=값",
        help="베스트-run 비교 플랏에 그릴 수평 기준선(예: '선형 프로브 val=0.8058'). 여러 번 줄 수 있다",
    )
    args = parser.parse_args(argv)

    out_dir = args.out_dir or args.artifacts_finetune_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    runs = load_runs(args.artifacts_finetune_dir)
    if not runs:
        print(f"{args.artifacts_finetune_dir}에서 meta.json을 못 찾았다", file=sys.stderr)
        return 1

    baselines = [parse_baseline(spec) for spec in args.baseline]

    saved = plot_per_method(runs, out_dir)
    saved.append(plot_best_per_method(runs, out_dir, baselines))

    for path in saved:
        print(f"저장: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
