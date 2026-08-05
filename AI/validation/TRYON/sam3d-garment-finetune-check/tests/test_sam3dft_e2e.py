"""엔드투엔드 스모크 — 더미 데이터로 전 단계가 한 번씩 도는지.

**외부 데이터·GPU·외부 API 없이** 돌아야 한다. 이게 이 스캐폴드의 DoD 다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from garment3d.cli import main
from garment3d.config import Config
from garment3d.pipeline import run_smoke


def _config() -> Config:
    # 프레임 수·해상도를 줄여 테스트를 가볍게 유지한다(비교 성립 조건인 "양쪽 동일"은 지킨다).
    return Config.from_dict(
        {
            "render": {"num_frames": 8, "resolution": 48, "write_mp4": False},
            "i2v": {"num_frames": 8, "resolution": 48},
            "report": {"plots": False},
        }
    )


def test_smoke_runs_end_to_end(tmp_path: Path):
    result = run_smoke(_config(), work_dir=tmp_path, num_samples=2)

    assert result.preprocess_summary["total"] == 2
    assert result.preprocess_summary["ok"] == 2
    assert len(result.comparisons) == 2
    assert result.aggregate["cases"] == 2

    assert result.report_markdown is not None and result.report_markdown.is_file()
    assert result.report_html is not None and result.report_html.is_file()
    assert "silhouette_iou_mean" in result.report_markdown.read_text(encoding="utf-8")


def test_smoke_leaves_artifacts_under_work_dir_only(tmp_path: Path):
    """리포 안에 산출물을 흘리지 않아야 한다 — config 경로 재지정이 실제로 먹히는지."""
    result = run_smoke(_config(), work_dir=tmp_path, num_samples=1)
    assert (tmp_path / "cache" / "occupancy").is_dir()
    assert (tmp_path / "outputs" / "report").is_dir()
    # 리포트 경로가 work_dir 밖으로 새지 않았는지 — config 기본값("artifacts/…")이 그대로
    # 쓰였다면 리포 안에 파일이 생긴다.
    assert result.report_markdown is not None
    assert tmp_path in result.report_markdown.parents


def test_smoke_turntable_wins_against_dummy_i2v(tmp_path: Path):
    """더미 I2V 는 뒤로 갈수록 흐트러지게 만들어 뒀다 — 하네스가 그 차이를 잡아야 한다."""
    result = run_smoke(_config(), work_dir=tmp_path, num_samples=1)
    comparison = result.comparisons[0]
    assert comparison.verdict() == "turntable"
    assert comparison.tally()["turntable"] > comparison.tally()["i2v"]


def test_smoke_with_media_writes_frames(tmp_path: Path):
    run_smoke(_config(), work_dir=tmp_path, num_samples=1, write_media=True)
    turntable_dir = tmp_path / "outputs" / "turntable"
    assert list(turntable_dir.glob("*.gif"))
    assert list(turntable_dir.glob("dummy_000/frame_0000.png"))


def test_smoke_records_texture_supervision_gap(tmp_path: Path):
    """SLat 인코더가 없다는 사실이 노트로 남아야 한다 (REPORT.md §5)."""
    result = run_smoke(_config(), work_dir=tmp_path, num_samples=1)
    assert result.preprocess_summary["texture_supervisable"] == 0
    assert any("SLat" in note for note in result.notes)


# ── CLI ──────────────────────────────────────────────────────────────────────


def test_cli_smoke_command(tmp_path: Path, capsys):
    exit_code = main(
        [
            "--work-dir",
            str(tmp_path),
            "--dummy",
            "1",
            "--set",
            "render.num_frames=8",
            "--set",
            "i2v.num_frames=8",
            "--set",
            "render.resolution=48",
            "--set",
            "i2v.resolution=48",
            "--set",
            "report.plots=false",
            "smoke",
        ]
    )
    assert exit_code == 0
    assert "리포트:" in capsys.readouterr().out


def test_cli_preprocess_command(tmp_path: Path, capsys):
    exit_code = main(["--work-dir", str(tmp_path), "--dummy", "2", "preprocess", "--no-cache"])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert '"ok": 2' in output


def test_cli_audit_reports_supervision_flags(tmp_path: Path, capsys):
    exit_code = main(["--work-dir", str(tmp_path), "--dummy", "1", "audit"])
    assert exit_code == 0
    output = capsys.readouterr().out
    # geometry·layout 은 되고 texture 는 안 된다 → "GL-"
    assert "[GL-]" in output
    assert "범례" in output


def test_cli_audit_reads_real_index_when_configured(tmp_path: Path, capsys):
    """`paths.sample_index` 를 넣는 순간 더미가 아니라 그걸 읽어야 한다 — 데이터 주입 지점."""
    from garment3d.data import make_dummy_index

    root = tmp_path / "real"
    index = make_dummy_index(root, count=1)
    index.samples[0] = index.samples[0].model_copy(update={"sample_id": "real_sample"})
    index_path = index.to_jsonl(tmp_path / "index.jsonl")

    exit_code = main(
        [
            "--work-dir",
            str(tmp_path),
            "--set",
            f"paths.sample_index={index_path}",
            "--set",
            f"paths.data_root={root}",
            "audit",
        ]
    )
    assert exit_code == 0
    assert "real_sample" in capsys.readouterr().out


def test_cli_rejects_unknown_command():
    with pytest.raises(SystemExit):
        main(["nonexistent"])


def test_cli_sft_smoke(tmp_path: Path, capsys):
    pytest.importorskip("torch")
    pytest.importorskip("peft")

    exit_code = main(
        [
            "--work-dir",
            str(tmp_path),
            "--set",
            "sft.max_steps=2",
            "--set",
            "sft.log_every=1",
            "--set",
            "sft.save_every=2",
            "--set",
            f"paths.checkpoint_dir={tmp_path / 'ckpt'}",
            "sft",
        ]
    )
    assert exit_code == 0
    assert "완료: step=2" in capsys.readouterr().out
    assert (tmp_path / "ckpt" / "sft_step0000002.pt").is_file()


def test_cli_dpo_smoke(tmp_path: Path, capsys):
    pytest.importorskip("torch")
    pytest.importorskip("peft")

    exit_code = main(
        [
            "--work-dir",
            str(tmp_path),
            "--set",
            "dpo.max_steps=2",
            "--set",
            "dpo.save_every=2",
            "--set",
            "dpo.min_margin=0.0",
            "--set",
            f"paths.checkpoint_dir={tmp_path / 'ckpt'}",
            "dpo",
        ]
    )
    assert exit_code == 0
    assert "완료: step=2" in capsys.readouterr().out
