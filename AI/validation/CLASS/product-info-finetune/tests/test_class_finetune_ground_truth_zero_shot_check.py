"""`aihub_ground_truth_zero_shot_check.py`의 순수 함수 테스트.

원본 vs 파인튜닝 backbone 인코딩·zero-shot 비교 본체는 torch/transformers/PIL이
필요해 CI에서 못 돈다. 여기서 고정하는 건 그 앞단 — 정답셋 로딩(synthetic 제외)과
이미지 경로 해석(inputs/ 또는 공유 폴더 폴백)이다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import aihub_ground_truth_zero_shot_check as check


def test_load_ground_truth_rows_drops_synthetic(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    rows = [
        {"image_file": "a.jpg", "subcategory": "CROSS_BAG"},
        {"image_file": "b.jpg", "subcategory": "DRESS_SHOES", "synthetic": True},
    ]
    (tmp_path / "data" / "ground_truth.json").write_text(json.dumps(rows), encoding="utf-8")

    loaded = check.load_ground_truth_rows(tmp_path)

    assert len(loaded) == 1
    assert loaded[0]["image_file"] == "a.jpg"


def test_load_ground_truth_rows_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        check.load_ground_truth_rows(tmp_path)


def test_resolve_ground_truth_image_finds_in_inputs_dir(tmp_path: Path) -> None:
    ground_truth_dir = tmp_path / "product-info-check"
    inputs_dir = ground_truth_dir / "inputs"
    inputs_dir.mkdir(parents=True)
    (inputs_dir / "apc.png").write_bytes(b"fake")

    resolved = check.resolve_ground_truth_image(ground_truth_dir, "apc.png")

    assert resolved == inputs_dir / "apc.png"


def test_resolve_ground_truth_image_returns_none_when_missing(tmp_path: Path) -> None:
    ground_truth_dir = tmp_path / "product-info-check"
    (ground_truth_dir / "inputs").mkdir(parents=True)

    assert check.resolve_ground_truth_image(ground_truth_dir, "missing.png") is None
