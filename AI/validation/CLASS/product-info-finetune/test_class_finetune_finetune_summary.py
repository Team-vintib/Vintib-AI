"""`aihub_finetune_summary.py`의 순수 로직 테스트. 표준 라이브러리만 써서 무거운 의존성
가드가 필요 없다."""

from __future__ import annotations

import json
from pathlib import Path

import aihub_finetune_summary as summary


def _write_meta(run_dir: Path, **fields: object) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "meta.json").write_text(json.dumps(fields), encoding="utf-8")


def test_load_runs_reads_run_name_from_folder_and_drops_huge_lists(tmp_path: Path) -> None:
    _write_meta(
        tmp_path / "lora_r8_a16_d0.05_qv_category_masked_lr0.0001",
        task="category",
        lora_r=8,
        target_modules=["q_proj", "v_proj"],
        classes=["A", "B", "C"],
        history=[{"epoch": 1, "val_accuracy": 0.5}],
        test_accuracy=0.8,
    )

    rows = summary.load_runs(tmp_path)

    assert len(rows) == 1
    row = rows[0]
    assert row["run"] == "lora_r8_a16_d0.05_qv_category_masked_lr0.0001"
    assert row["method"] == "LoRA"  # run_name 접두어로 자동 분류
    assert row["target_modules"] == "q_proj,v_proj"  # 리스트라도 스칼라뿐이면 문자열로 접힘
    assert "classes" not in row  # 표에 넣기엔 무의미한 라벨 목록
    assert "history" not in row  # dict가 섞인 리스트라 제외


def test_best_per_group_keeps_top_run_per_method_and_task(tmp_path: Path) -> None:
    """color 파인튜닝을 시작하면서 실제로 필요해진 사용례 — last-N·LoRA 각각 category·color
    베스트만 뽑아 4행짜리 리더보드를 만든다. 같은 (method, task) 안에서 진 run은 빠져야 한다."""

    def _row(run: str, method: str, task: str, test_accuracy: float) -> dict:
        return {"run": run, "method": method, "task": task, "test_accuracy": test_accuracy}

    rows = [
        _row("vit_last2_category_masked_lr1e-05", "last-N", "category", 0.8210),
        _row("vit_last4_category_masked_lr1e-05", "last-N", "category", 0.8435),
        _row("lora_r8_category", "LoRA", "category", 0.8307),
        _row("lora_r16_category", "LoRA", "category", 0.8290),
        _row("vit_last4_color_masked_lr1e-05", "last-N", "color", 0.79),
    ]

    best = summary.best_per_group(rows, ["method", "task"], "test_accuracy")

    names = {row["run"] for row in best}
    assert names == {
        "vit_last4_category_masked_lr1e-05",  # last-N/category 1위(0.8210 탈락)
        "lora_r8_category",  # LoRA/category 1위(r16 탈락)
        "vit_last4_color_masked_lr1e-05",  # last-N/color는 이거 하나뿐이라 그대로
    }


def test_best_per_group_respects_ascending_order() -> None:
    rows = [
        {"run": "a", "method": "LoRA", "task": "category", "test_accuracy": 0.9},
        {"run": "b", "method": "LoRA", "task": "category", "test_accuracy": 0.1},
    ]

    best = summary.best_per_group(rows, ["method", "task"], "test_accuracy", descending=False)

    assert [row["run"] for row in best] == ["b"]


def test_sort_rows_puts_missing_metric_last_regardless_of_direction() -> None:
    rows = [
        {"run": "a", "test_accuracy": 0.5},
        {"run": "b"},  # test_accuracy 없음
        {"run": "c", "test_accuracy": 0.9},
    ]

    descending = summary.sort_rows(rows, "test_accuracy", descending=True)
    assert [row["run"] for row in descending] == ["c", "a", "b"]

    ascending = summary.sort_rows(rows, "test_accuracy", descending=False)
    assert [row["run"] for row in ascending] == ["a", "c", "b"]


def test_render_markdown_orders_priority_columns_first() -> None:
    rows = [{"run": "r1", "lora_r": 8, "test_accuracy": 0.8, "best_epoch": 3}]

    table = summary.render_markdown(rows)
    header = table.splitlines()[0]

    assert header.index("run") < header.index("best_epoch") < header.index("test_accuracy")
    assert "lora_r" in header


def test_render_markdown_on_empty_rows_does_not_crash() -> None:
    assert summary.render_markdown([]) == "(비교할 run이 없다)"


def test_main_writes_table_to_out_file(tmp_path: Path, capsys) -> None:
    _write_meta(tmp_path / "run_a", task="category", test_accuracy=0.7)
    _write_meta(tmp_path / "run_b", task="category", test_accuracy=0.9)
    out_path = tmp_path / "summary.md"

    exit_code = summary.main(["--artifacts-finetune-dir", str(tmp_path), "--out", str(out_path)])

    assert exit_code == 0
    assert out_path.exists()
    printed = capsys.readouterr().out
    lines = out_path.read_text(encoding="utf-8").splitlines()
    run_b_line = next(line for line in lines if "run_b" in line)
    run_a_line = next(line for line in lines if "run_a" in line)
    assert lines.index(run_b_line) < lines.index(run_a_line)  # 0.9가 0.7보다 위(내림차순)
    assert "run_b" in printed


def test_main_returns_error_when_no_meta_json_found(tmp_path: Path) -> None:
    assert summary.main(["--artifacts-finetune-dir", str(tmp_path)]) == 1
