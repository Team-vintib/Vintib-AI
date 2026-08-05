"""`run_scan`의 `--color-top` 요약 동작 테스트.

다색 콤마 조합("Black,White" 등)이 값 종류를 수백 개로 불려서 게이트 2 표가 감당 안 될
만큼 길어진다(2026-08-04 실측: 500줄 이상). 기본값이 실제로 줄여 주는지, `--color-top 0`이
전체를 그대로 보여 주는지 여기서 고정한다.
"""

from __future__ import annotations

import json

import aihub_dataset as ad


def _write_label(
    tmp_path,
    name: str,
    *,
    color: str,
    source_type: str = "02top_04shirt",
    shot_type: str = "front",
) -> None:
    payload = {
        "dataset": {"dataset.name": name, "dataset.width": 100, "dataset.height": 100},
        "annotation": [],
        "metadata.model": {"metadata.model.type": shot_type},
        "metadata.clothes": {
            "metadata.clothes.type": source_type,
            "metadata.clothes.color": color,
        },
    }
    (tmp_path / f"{name}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _make_tree(tmp_path):
    """Black 10건 + 서로 다른 다색 조합 30건(각 1건씩) — 매핑 안 되는 꼬리를 흉내낸다."""
    for i in range(10):
        _write_label(tmp_path, f"black_{i}", color="Black")
    for i in range(30):
        _write_label(tmp_path, f"multi_{i}", color=f"Black,White,{i}")


def test_default_color_top_truncates_the_long_tail(tmp_path) -> None:
    _make_tree(tmp_path)
    report = ad.run_scan(
        tmp_path, limit=None, sample_paths=1, short_pants_max_cm=None, progress_every=0
    )

    assert "Black" in report  # 상위 값(건수 10)은 그대로 보인다
    assert "이하" in report and "생략" in report
    assert "--color-top 0" in report


def test_color_top_zero_shows_everything(tmp_path) -> None:
    _make_tree(tmp_path)
    report = ad.run_scan(
        tmp_path,
        limit=None,
        sample_paths=1,
        short_pants_max_cm=None,
        progress_every=0,
        color_top=0,
    )

    assert "생략" not in report
    # 다색 조합 30종이 전부 개별 행으로 찍혀야 한다
    assert "Black,White,29" in report


def test_color_top_n_keeps_exactly_n_rows(tmp_path) -> None:
    _make_tree(tmp_path)
    report = ad.run_scan(
        tmp_path,
        limit=None,
        sample_paths=1,
        short_pants_max_cm=None,
        progress_every=0,
        color_top=5,
    )

    # 값 종류: "Black"(1종) + 서로 다른 "Black,White,i"(30종) = 총 31종. 상위 5개만 남기면
    # 26종이 생략된다.
    assert "이하 26종 생략" in report
