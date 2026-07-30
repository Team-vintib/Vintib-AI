"""리포트 — 표는 항상 나오고, 플롯은 matplotlib 이 있을 때만 붙는다."""

from __future__ import annotations

from pathlib import Path

import pytest

from garment3d.config import EvalConfig, ReportConfig
from garment3d.eval.harness import compare_case
from garment3d.render.synthetic import SyntheticDefects, synth_turntable
from garment3d.report.builder import build_html, build_markdown, metric_means, write_report


def _comparisons(count: int = 2):
    turntable = synth_turntable(num_frames=8, resolution=48)
    degraded = synth_turntable(
        num_frames=8,
        resolution=48,
        defects=SyntheticDefects(scale_drift=0.4, flicker=0.25, identity_shift=1.0),
    )
    return [compare_case(f"case{i}", turntable, degraded, EvalConfig()) for i in range(count)]


def test_metric_means_averages_across_cases():
    comparisons = _comparisons(2)
    means = metric_means(comparisons)
    assert "silhouette_iou_mean" in means
    assert set(means["silhouette_iou_mean"]) == {"turntable", "i2v"}
    # 같은 시퀀스 2건이므로 평균이 개별값과 같아야 한다.
    single = comparisons[0].rows()["silhouette_iou_mean"]["turntable"]
    assert means["silhouette_iou_mean"]["turntable"] == pytest.approx(single)


def test_markdown_contains_direction_marks_and_verdicts():
    text = build_markdown(_comparisons(1), ReportConfig())
    assert "turntable vs I2V" in text
    assert "↑" in text and "↓" in text
    assert "silhouette_iou_mean" in text
    assert "판정" in text


def test_markdown_surfaces_warnings():
    """지표 신뢰도 경고가 리포트에 안 실리면 아무도 안 본다."""
    turntable = synth_turntable(num_frames=8, resolution=48)
    short = synth_turntable(num_frames=5, resolution=48)
    comparison = compare_case("mismatch", turntable, short, EvalConfig())
    text = build_markdown([comparison], ReportConfig())
    assert "경고" in text
    assert "프레임 수" in text


def test_markdown_handles_empty_comparisons():
    text = build_markdown([], ReportConfig())
    assert "케이스 0건" in text


def test_html_is_self_contained_and_escaped():
    html = build_html(_comparisons(1), ReportConfig(title="비교 <테스트>"))
    assert html.startswith("<!doctype html>")
    # 제목이 이스케이프돼야 한다(리포트에 임의 문자열이 들어올 수 있다).
    assert "&lt;테스트&gt;" in html
    # 외부 리소스를 참조하지 않는다.
    assert "http://" not in html and "https://" not in html


def test_write_report_creates_both_formats(tmp_path: Path):
    result = write_report(_comparisons(1), ReportConfig(), tmp_path)
    assert result.markdown_path is not None and result.markdown_path.is_file()
    assert result.html_path is not None and result.html_path.is_file()


def test_write_report_markdown_only(tmp_path: Path):
    config = ReportConfig(formats=["markdown"], plots=False)
    result = write_report(_comparisons(1), config, tmp_path)
    assert result.markdown_path is not None
    assert result.html_path is None
    assert result.plot_path is None


def test_write_report_notes_when_plot_unavailable(tmp_path: Path):
    """matplotlib 이 없으면 표만 남기고 왜 없는지 적는다 — 조용히 사라지면 안 된다."""
    result = write_report(_comparisons(1), ReportConfig(plots=True), tmp_path)
    if result.plot_path is None:
        assert any("플롯 생략" in note for note in result.notes)
    else:
        assert result.plot_path.is_file()


def test_plot_is_written_and_embedded_when_matplotlib_available(tmp_path: Path):
    pytest.importorskip("matplotlib")

    from garment3d.report.builder import build_plot

    comparisons = _comparisons(1)
    path = build_plot(comparisons, tmp_path / "plot.png")
    assert path.is_file() and path.stat().st_size > 0

    html = build_html(comparisons, ReportConfig(), plot_path=path)
    assert "data:image/png;base64," in html


def test_plot_rejects_when_no_directional_metrics(tmp_path: Path):
    pytest.importorskip("matplotlib")

    from garment3d.report.builder import build_plot

    with pytest.raises(ValueError, match="플롯을 그릴 지표"):
        build_plot([], tmp_path / "plot.png")
