"""엔드투엔드 스모크 파이프라인 — 더미 데이터로 전 단계를 한 번씩 통과시킨다.

`더미 인덱스 → 전처리 → 턴테이블 렌더 → I2V → 평가 → 리포트`

**GPU·외부 데이터·외부 API 없이 돈다.** 실데이터/실백엔드로 바꿀 때 손대는 곳은 config 뿐이고
이 함수의 구조는 그대로다 — 그게 이 스캐폴드의 존재 이유다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .config import Config
from .data import make_dummy_index
from .eval.harness import CaseComparison, aggregate, compare_case
from .i2v import build_i2v_adapter, request_from_config
from .preprocess import preprocess_index, summarize
from .render import build_renderer, save_frames
from .report import write_report


@dataclass
class SmokeResult:
    preprocess_summary: dict[str, int] = field(default_factory=dict)
    comparisons: list[CaseComparison] = field(default_factory=list)
    aggregate: dict[str, Any] = field(default_factory=dict)
    report_markdown: Path | None = None
    report_html: Path | None = None
    notes: list[str] = field(default_factory=list)


def run_smoke(
    config: Config,
    *,
    work_dir: Path,
    num_samples: int = 2,
    write_media: bool = False,
) -> SmokeResult:
    """더미로 전 단계를 통과시킨다.

    Args:
        work_dir: 더미 데이터·산출물 루트. 테스트는 tmp_path 를 준다.
        write_media: True 면 PNG 시퀀스/GIF 까지 저장한다(느려서 기본 off).
    """
    work_dir = Path(work_dir)
    data_root = work_dir / "data"
    result = SmokeResult()

    # config 의 경로를 work_dir 아래로 옮긴다 — 스모크가 리포 안에 쓰레기를 남기지 않게.
    config = config.merged(
        {
            "paths": {
                "data_root": str(data_root),
                "cache_dir": str(work_dir / "cache"),
                "checkpoint_dir": str(work_dir / "checkpoints"),
                "output_dir": str(work_dir / "outputs"),
            }
        }
    )

    # 1. 더미 데이터
    index = make_dummy_index(data_root, count=num_samples)
    samples = index.resolved()

    # 2. 전처리 (mesh → occupancy → latent)
    preprocess_results = preprocess_index(samples, config)
    result.preprocess_summary = summarize(preprocess_results)
    for entry in preprocess_results:
        result.notes.extend(f"[{entry.sample_id}] {reason}" for reason in entry.reasons)

    # 3~5. 케이스마다 턴테이블 / I2V 를 뽑아 같은 지표로 비교
    renderer = build_renderer(config.render, config.paths.expanded().sam3d_repo)
    adapter = build_i2v_adapter(config.i2v)
    output_dir = config.paths.expanded().output_dir

    for entry in preprocess_results:
        if not entry.ok:
            continue
        turntable_frames = renderer.render(entry.sample_id, config.render)
        response = adapter.generate(request_from_config(turntable_frames[0], config.i2v, seed=0))
        result.notes.extend(f"[{entry.sample_id}] i2v: {w}" for w in response.warnings)

        if write_media:
            save_frames(
                turntable_frames,
                output_dir / "turntable",
                entry.sample_id,
                fps=config.render.fps,
                mp4=config.render.write_mp4,
            )
            save_frames(
                response.frames, output_dir / "i2v", entry.sample_id, fps=config.i2v.fps, mp4=False
            )

        result.comparisons.append(
            compare_case(
                entry.sample_id,
                turntable_frames,
                response.frames,
                config.eval,
                reference=np.asarray(turntable_frames[0]),
            )
        )

    result.aggregate = aggregate(result.comparisons)

    # 6. 리포트
    report = write_report(result.comparisons, config.report, output_dir / "report")
    result.report_markdown = report.markdown_path
    result.report_html = report.html_path
    result.notes.extend(report.notes)
    return result
