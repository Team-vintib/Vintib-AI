"""비교 리포트 생성기 — 케이스별 turntable vs I2V 를 표 + 플롯으로 markdown/html 출력.

**표는 항상 나온다.** 플롯은 matplotlib 이 있을 때만 붙고, 없으면 리포트에 "왜 없는지"를 남긴다.

플롯 설계 메모 (이유가 있어서 이렇게 했다):

- **지표별 small multiples 다.** 하나의 막대차트에 전 지표를 넣지 않는다 — IoU(≈0.9)와
  변동계수(≈0.02)와 드리프트(≈0.25)는 스케일이 달라서 같은 축에 놓으면 작은 지표가 0 처럼
  보이고 비교가 왜곡된다. 패널마다 자기 축을 갖는다.
- 색은 2계열 categorical 로 **고정 순서**로 배정한다(turntable=slot1 blue, i2v=slot2 orange).
  계열이 늘 두 개뿐이므로 순환 배정 문제가 없다.
- 값은 막대 끝에 직접 라벨한다(계열 2개 = 직접 라벨 가능 범위). 범례도 함께 둬서 색 단독으로
  식별하지 않게 한다.
- 지표 이름 옆에 방향 화살표(↑/↓)를 붙인다 — `METRIC_DIRECTIONS` 를 단일 출처로 읽는다.
"""

from __future__ import annotations

import base64
import html
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..config import ReportConfig
from ..eval.harness import METRIC_DIRECTIONS, CaseComparison, aggregate

# ── 색 (dataviz 레퍼런스 팔레트의 검증된 categorical slot 1·2, light 모드) ────
SERIES_COLORS = {"turntable": "#2a78d6", "i2v": "#eb6834"}
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e3e2df"

DIRECTION_MARK = {"higher": "↑", "lower": "↓", "info": "·"}


@dataclass
class ReportResult:
    markdown_path: Path | None = None
    html_path: Path | None = None
    plot_path: Path | None = None
    #: 플롯을 못 그린 사유 등
    notes: list[str] = field(default_factory=list)


def _direction_label(metric: str) -> str:
    return DIRECTION_MARK.get(METRIC_DIRECTIONS.get(metric, "info"), "·")


def _fmt(value: float) -> str:
    if abs(value) >= 100 or (value != 0 and abs(value) < 1e-4):
        return f"{value:.3e}"
    return f"{value:.4f}"


def metric_means(comparisons: list[CaseComparison]) -> dict[str, dict[str, float]]:
    """지표별 두 방식의 케이스 평균. `{지표: {"turntable": v, "i2v": v}}`"""
    buckets: dict[str, dict[str, list[float]]] = {}
    for comparison in comparisons:
        for metric, values in comparison.rows().items():
            slot = buckets.setdefault(metric, {"turntable": [], "i2v": []})
            slot["turntable"].append(values["turntable"])
            slot["i2v"].append(values["i2v"])
    return {
        metric: {method: float(np.mean(values)) for method, values in slots.items()}
        for metric, slots in sorted(buckets.items())
    }


def build_plot(comparisons: list[CaseComparison], path: Path) -> Path:
    """지표별 small multiples 를 PNG 로 저장한다. matplotlib 이 없으면 ImportError."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    means = {
        metric: values
        for metric, values in metric_means(comparisons).items()
        if METRIC_DIRECTIONS.get(metric, "info") != "info"
    }
    if not means:
        raise ValueError("플롯을 그릴 지표가 없습니다")

    metrics = list(means)
    columns = min(3, len(metrics))
    rows = int(np.ceil(len(metrics) / columns))
    figure, axes = plt.subplots(
        rows, columns, figsize=(4.2 * columns, 1.9 * rows), squeeze=False, facecolor=SURFACE
    )

    for index, metric in enumerate(metrics):
        axis = axes[index // columns][index % columns]
        axis.set_facecolor(SURFACE)
        methods = ["turntable", "i2v"]
        values = [means[metric][m] for m in methods]
        # 얇은 막대 + 사이 간격. 막대 두께 0.42 로 두 막대 사이에 여백이 남는다.
        positions = [0.0, 0.55]
        for position, method, value in zip(positions, methods, values):
            axis.barh(
                position, value, height=0.42, color=SERIES_COLORS[method], label=method, zorder=3
            )
        span = max(abs(v) for v in values) or 1.0
        axis.set_xlim(min(0.0, min(values) * 1.25), span * 1.35)
        for position, value in zip(positions, values):
            axis.text(
                value + span * 0.04,
                position,
                _fmt(value),
                va="center",
                fontsize=7.5,
                color=TEXT_SECONDARY,
            )
        axis.set_yticks(positions)
        axis.set_yticklabels(methods, fontsize=7.5, color=TEXT_SECONDARY)
        # 플롯 텍스트는 ASCII + 화살표만 쓴다. matplotlib 기본 폰트(DejaVu Sans)에 한글이 없어
        # 제목에 한글을 넣으면 PNG 에 두부(□□)가 찍힌다. 한글 설명은 표/HTML 쪽에 둔다.
        axis.set_title(
            f"{metric}  {_direction_label(metric)} better",
            fontsize=8.5,
            color=TEXT_PRIMARY,
            loc="left",
        )
        axis.tick_params(axis="x", labelsize=7, colors=TEXT_SECONDARY)
        axis.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
        axis.set_axisbelow(True)
        for side in ("top", "right", "left"):
            axis.spines[side].set_visible(False)
        axis.spines["bottom"].set_color(GRID)

    for index in range(len(metrics), rows * columns):
        axes[index // columns][index % columns].axis("off")

    handles = [
        plt.Line2D([], [], marker="s", linestyle="", color=SERIES_COLORS[m], label=m)
        for m in ("turntable", "i2v")
    ]
    figure.legend(
        handles=handles,
        loc="lower center",
        ncol=2,
        frameon=False,
        fontsize=8,
        labelcolor=TEXT_SECONDARY,
    )
    figure.tight_layout(rect=(0, 0.05, 1, 1))

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(figure)
    return path


def _markdown_table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def build_markdown(
    comparisons: list[CaseComparison],
    config: ReportConfig,
    *,
    plot_path: Path | None = None,
    notes: list[str] | None = None,
) -> str:
    """markdown 리포트 본문."""
    summary = aggregate(comparisons)
    parts = [f"# {config.title}", ""]
    parts.append(f"케이스 {summary['cases']}건. 케이스별 승자 집계: {summary['verdicts']}")
    parts.append("")
    parts.append(
        "> 지표 방향: `↑` 는 클수록 좋음, `↓` 는 작을수록 좋음, `·` 는 진단용(승패 판정 제외)."
    )
    parts.append("")

    if notes:
        parts.append("## 읽기 전 주의")
        parts.extend(f"- {note}" for note in notes)
        parts.append("")

    all_warnings = [
        (comparison.case_id, warning)
        for comparison in comparisons
        for warning in (
            comparison.warnings + comparison.turntable.warnings + comparison.i2v.warnings
        )
    ]
    if all_warnings:
        parts.append("## 경고 (지표 신뢰도에 영향)")
        parts.extend(f"- `{case_id}`: {warning}" for case_id, warning in all_warnings)
        parts.append("")

    parts.append("## 지표 평균 (전 케이스)")
    parts.append("")
    means = metric_means(comparisons)
    rows = []
    for metric, values in means.items():
        turntable, i2v = values["turntable"], values["i2v"]
        direction = METRIC_DIRECTIONS.get(metric, "info")
        if direction == "info":
            winner = "n/a"
        elif turntable == i2v:
            winner = "tie"
        elif (direction == "higher") == (turntable > i2v):
            winner = "turntable"
        else:
            winner = "i2v"
        rows.append(
            [
                f"`{metric}` {_direction_label(metric)}",
                _fmt(turntable),
                _fmt(i2v),
                _fmt(turntable - i2v),
                winner,
            ]
        )
    parts.append(_markdown_table(["지표", "turntable", "i2v", "델타", "승자"], rows))
    parts.append("")

    parts.append("## 케이스별")
    parts.append("")
    for comparison in comparisons:
        tally = comparison.tally()
        parts.append(f"### `{comparison.case_id}` — 판정: **{comparison.verdict()}** ({tally})")
        parts.append("")
        parts.append(f"백엔드: turntable[{comparison.turntable.backend_note()}]")
        parts.append("")
        case_rows = [
            [
                f"`{metric}` {_direction_label(metric)}",
                _fmt(values["turntable"]),
                _fmt(values["i2v"]),
                _fmt(values["delta"]),
                comparison.winners()[metric],
            ]
            for metric, values in comparison.rows().items()
        ]
        parts.append(_markdown_table(["지표", "turntable", "i2v", "델타", "승자"], case_rows))
        parts.append("")

    if plot_path is not None:
        parts.append("## 플롯")
        parts.append("")
        parts.append(f"![지표별 비교]({Path(plot_path).name})")
        parts.append("")

    return "\n".join(parts)


def build_html(
    comparisons: list[CaseComparison],
    config: ReportConfig,
    *,
    plot_path: Path | None = None,
    notes: list[str] | None = None,
) -> str:
    """자기완결 HTML. 플롯은 base64 로 **임베드**해서 파일 하나만 옮겨도 깨지지 않게 한다."""
    means = metric_means(comparisons)
    summary = aggregate(comparisons)

    def _cell(text: str) -> str:
        return f"<td>{html.escape(str(text))}</td>"

    rows_html = []
    for metric, values in means.items():
        turntable, i2v = values["turntable"], values["i2v"]
        rows_html.append(
            "<tr>"
            + _cell(f"{metric} {_direction_label(metric)}")
            + _cell(_fmt(turntable))
            + _cell(_fmt(i2v))
            + _cell(_fmt(turntable - i2v))
            + "</tr>"
        )

    plot_html = ""
    if plot_path is not None and Path(plot_path).is_file():
        encoded = base64.b64encode(Path(plot_path).read_bytes()).decode("ascii")
        plot_html = (
            f'<img alt="지표별 turntable vs I2V 비교" '
            f'src="data:image/png;base64,{encoded}" style="max-width:100%">'
        )

    warning_items = "".join(
        f"<li><code>{html.escape(c.case_id)}</code>: {html.escape(w)}</li>"
        for c in comparisons
        for w in (c.warnings + c.turntable.warnings + c.i2v.warnings)
    )
    note_items = "".join(f"<li>{html.escape(n)}</li>" for n in (notes or []))

    return f"""<!doctype html>
<meta charset="utf-8">
<title>{html.escape(config.title)}</title>
<style>
  body {{ background:{SURFACE}; color:{TEXT_PRIMARY};
         font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
         margin:0 auto; max-width:960px; padding:2rem 1.25rem; line-height:1.6; }}
  h1 {{ font-size:1.5rem; }}
  h2 {{ font-size:1.1rem; margin-top:2rem; }}
  table {{ border-collapse:collapse; width:100%; font-size:0.85rem; }}
  th, td {{ text-align:left; padding:0.35rem 0.5rem; border-bottom:1px solid {GRID}; }}
  th {{ color:{TEXT_SECONDARY}; font-weight:600; }}
  td:first-child {{ font-family:ui-monospace,monospace; }}
  .legend span {{ display:inline-flex; align-items:center; gap:0.35rem;
                  margin-right:1rem; color:{TEXT_SECONDARY}; font-size:0.8rem; }}
  .swatch {{ width:10px; height:10px; border-radius:2px; display:inline-block; }}
  .muted {{ color:{TEXT_SECONDARY}; font-size:0.85rem; }}
  .scroll {{ overflow-x:auto; }}
</style>
<h1>{html.escape(config.title)}</h1>
<p class="muted">케이스 {summary["cases"]}건 · 승자 집계 {html.escape(str(summary["verdicts"]))}</p>
<p class="legend">
  <span><i class="swatch" style="background:{SERIES_COLORS["turntable"]}"></i>turntable</span>
  <span><i class="swatch" style="background:{SERIES_COLORS["i2v"]}"></i>i2v</span>
</p>
<p class="muted">↑ 클수록 좋음 · ↓ 작을수록 좋음 · · 진단용(판정 제외)</p>
{"<h2>읽기 전 주의</h2><ul>" + note_items + "</ul>" if note_items else ""}
{"<h2>경고</h2><ul>" + warning_items + "</ul>" if warning_items else ""}
<h2>지표 평균</h2>
<div class="scroll">
<table>
  <thead><tr><th>지표</th><th>turntable</th><th>i2v</th><th>델타</th></tr></thead>
  <tbody>{"".join(rows_html)}</tbody>
</table>
</div>
<h2>플롯</h2>
{plot_html or '<p class="muted">matplotlib 이 없어 플롯을 생략했습니다.</p>'}
"""


def write_report(
    comparisons: list[CaseComparison],
    config: ReportConfig,
    out_dir: Path,
    *,
    stem: str = "comparison",
) -> ReportResult:
    """설정된 형식으로 리포트를 쓴다. 플롯 실패는 치명적이지 않다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = ReportResult()

    if not comparisons:
        result.notes.append("비교 케이스가 없습니다")

    plot_path: Path | None = None
    if config.plots and comparisons:
        try:
            plot_path = build_plot(comparisons, out_dir / f"{stem}.png")
            result.plot_path = plot_path
        except Exception as exc:
            result.notes.append(f"플롯 생략 ({type(exc).__name__}: {exc})")

    if "markdown" in config.formats:
        result.markdown_path = out_dir / f"{stem}.md"
        result.markdown_path.write_text(
            build_markdown(comparisons, config, plot_path=plot_path, notes=result.notes),
            encoding="utf-8",
        )
    if "html" in config.formats:
        result.html_path = out_dir / f"{stem}.html"
        result.html_path.write_text(
            build_html(comparisons, config, plot_path=plot_path, notes=result.notes),
            encoding="utf-8",
        )
    return result
