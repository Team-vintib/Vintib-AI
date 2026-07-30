"""리포트 — turntable vs I2V 비교 표/플롯 출력."""

from .builder import (
    SERIES_COLORS,
    ReportResult,
    build_html,
    build_markdown,
    build_plot,
    metric_means,
    write_report,
)

__all__ = [
    "SERIES_COLORS",
    "ReportResult",
    "build_html",
    "build_markdown",
    "build_plot",
    "metric_means",
    "write_report",
]
