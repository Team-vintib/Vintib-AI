"""`aihub_finetune_latency.py`의 순수 함수 테스트.

실제 forward 시간 측정 본체는 torch/transformers가 필요해 CI에서 못 돈다. 여기서
고정하는 건 `compute_stats()`뿐이다 — p50/p95 계산이 틀리면 지연시간 실측 자체가
잘못된 숫자를 낸다.
"""

from __future__ import annotations

import aihub_finetune_latency as latency


def test_compute_stats_p50_is_the_median_for_odd_count() -> None:
    stats = latency.compute_stats([10.0, 20.0, 30.0, 40.0, 50.0])
    assert stats["p50"] == 30.0
    assert stats["n"] == 5


def test_compute_stats_p95_picks_near_the_top() -> None:
    values = [float(i) for i in range(1, 101)]  # 1.0 ~ 100.0
    stats = latency.compute_stats(values)
    assert stats["p95"] == 96.0  # index int(100*0.95)=95 -> values[95] == 96.0


def test_compute_stats_mean_matches_manual_average() -> None:
    stats = latency.compute_stats([10.0, 20.0, 30.0])
    assert stats["mean"] == 20.0
