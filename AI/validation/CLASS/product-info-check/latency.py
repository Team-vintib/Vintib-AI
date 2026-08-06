"""V1 — CPU 추론 지연 실측. 반드시 먼저 돌린다(설계: `.claude/plans/ai/CH012-~2.MD` §11 순서와
별개로, 이 스파이크 자체의 실행 순서로 사용자가 지정함 — 지연이 기준을 못 넘으면 후보 자체가
바뀌어 V2 이후를 다시 돌려야 하기 때문).

classifier_benchmark.py(`model_selection/`) 관례를 그대로 따른다: `BenchResult` 데이터클래스에
mean/p50/p95/p99 지연시간, 로드 시간, 피크 메모리(tracemalloc)를 담는다.

**"품질검수 동시 실행" 조건을 어떻게 만드는가.** 이 스파이크는 실제 SAM3+Qwen-VL 워커를
직접 띄우지 않는다 — 그건 GPU 리소스를 쓰는 무거운 실행이라 스크립트가 자동으로 켜면 안
되고(AI/CLAUDE.md 하드 룰과 같은 취지: 무거운 실행은 사용자가 명시적으로 켠다), 대신 두
가지 방법을 모두 지원한다:

  1. `stress="synthetic"`(기본값) — CPU 코어를 인위적으로 점유하는 프로세스를 백그라운드로
     띄워 놓고 그 상태에서 지연을 잰다. 실제 SAM3/Qwen-VL의 부하 패턴과 100% 같지는 않지만
     재현 가능하고 자동화할 수 있다.
  2. `stress="external"` — 아무것도 띄우지 않는다. **사용자가 실제 품질검수 워커를 수동으로
     따로 띄워 둔 상태에서** 이 스크립트를 실행하면 그게 진짜 (b) 조건 숫자다. CH012 §6.3이
     "유휴 상태 측정치는 의미가 없다"고 못박은 조건을 가장 정확히 재현하는 방법이지만, 실행은
     사용자 몫이다.

리포트에는 어느 방법으로 쟀는지(`stress` 필드)를 반드시 같이 남긴다 — synthetic과 external을
같은 숫자처럼 섞어 비교하면 안 된다.
"""

from __future__ import annotations

import multiprocessing
import statistics
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path

from classify import CATEGORY_BACKENDS, get_category_classifier
from taxonomy import ALL_SUBCATEGORIES, PROMPT_TEMPLATES

_HERE = Path(__file__).resolve().parent
DEFAULT_WARMUP = 2


@dataclass
class LatencyResult:
    backend: str
    stress: str  # "idle" | "synthetic" | "external"
    load_time_s: float
    peak_mem_mb: float
    latencies_ms: list[float] = field(default_factory=list)

    def stats(self) -> dict[str, float]:
        if not self.latencies_ms:
            return {}
        s = sorted(self.latencies_ms)
        n = len(s)
        return {
            "mean": statistics.mean(s),
            "p50": s[int(n * 0.5)],
            "p95": s[min(int(n * 0.95), n - 1)],
            "p99": s[min(int(n * 0.99), n - 1)],
        }


def _cpu_burn(stop_flag) -> None:
    """단순 행렬곱 반복 — SAM3/Qwen-VL 실제 부하와 정확히 같지는 않지만 CPU 코어를
    실제로 포화시키는 합성 부하. numpy 없이도 돌게 순수 파이썬 연산으로 둔다(무거운
    의존성 없이도 이 프로세스 자체는 뜰 수 있어야 하므로)."""
    x = 0.0
    while not stop_flag.value:
        for i in range(200_000):
            x = (x * 1.000001 + i) % 1_000_003.0


class SyntheticStress:
    """`with SyntheticStress(workers=N):` 블록 동안 CPU N코어를 인위적으로 점유한다."""

    def __init__(self, workers: int | None = None):
        self.workers = workers or max(1, (multiprocessing.cpu_count() or 2) - 1)
        self._procs: list[multiprocessing.Process] = []
        self._stop_flag = multiprocessing.Value("b", False)

    def __enter__(self):
        for _ in range(self.workers):
            p = multiprocessing.Process(target=_cpu_burn, args=(self._stop_flag,), daemon=True)
            p.start()
            self._procs.append(p)
        return self

    def __exit__(self, *exc):
        self._stop_flag.value = True
        for p in self._procs:
            p.join(timeout=2)


def benchmark_backend(
    backend_key: str,
    image_paths: list[Path],
    *,
    template_key: str = "kr_plain",
    warmup: int = DEFAULT_WARMUP,
    stress: str = "idle",
) -> LatencyResult:
    """`image_paths`를 순회하며 소분류 30-way 전체를 한 번씩 물어보는 데 걸리는 시간을 잰다
    (실제 워크로드와 동일 — 라벨 30개를 한 번에 스코어링)."""
    tracemalloc.start()

    t0 = time.perf_counter()
    classifier = get_category_classifier(backend_key)
    labels = [PROMPT_TEMPLATES[template_key](c) for c in ALL_SUBCATEGORIES]

    # 로드 시간에는 첫 추론(모델 초기화 완료)까지 포함시킨다 — HF 모델은 흔히 첫 forward에서
    # 지연 초기화가 더 있다.
    if image_paths:
        classifier.score_labels(image_paths[0], labels)
    load_time = time.perf_counter() - t0

    paths = list(image_paths)
    for p in paths[:warmup]:
        classifier.score_labels(p, labels)

    result = LatencyResult(
        backend=backend_key, stress=stress, load_time_s=load_time, peak_mem_mb=0.0
    )
    for p in paths:
        t0 = time.perf_counter()
        classifier.score_labels(p, labels)
        result.latencies_ms.append((time.perf_counter() - t0) * 1000)

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result.peak_mem_mb = peak / (1024 * 1024)
    return result


def run_latency_suite(
    backend_keys: list[str], image_paths: list[Path], *, stress_mode: str = "synthetic"
) -> list[LatencyResult]:
    """각 백엔드를 idle 조건과 지정한 stress 조건 둘 다에서 측정한다.

    `stress_mode="none"`이면 idle만 측정한다(파이프라인 스모크 테스트용 — mock 백엔드로
    전 경로가 도는지만 빠르게 확인할 때).
    """
    results: list[LatencyResult] = []
    for key in backend_keys:
        try:
            results.append(benchmark_backend(key, image_paths, stress="idle"))
        except Exception as exc:  # noqa: BLE001 — 실패 격리: 한 백엔드가 죽어도 나머지는 계속
            print(f"[latency] {key} idle 측정 실패: {exc}")
            continue

        if stress_mode == "none":
            continue
        if stress_mode == "synthetic":
            with SyntheticStress():
                try:
                    results.append(benchmark_backend(key, image_paths, stress="synthetic"))
                except Exception as exc:  # noqa: BLE001
                    print(f"[latency] {key} synthetic-stress 측정 실패: {exc}")
        elif stress_mode == "external":
            try:
                results.append(benchmark_backend(key, image_paths, stress="external"))
            except Exception as exc:  # noqa: BLE001
                print(f"[latency] {key} external-stress 측정 실패: {exc}")
    return results


if __name__ == "__main__":
    from dataset import load_ground_truth

    gt = load_ground_truth()
    real_images = [s.image_path for s in gt.samples if not s.synthetic]
    print(f"이미지 {len(real_images)}장(synthetic 제외)으로 측정")
    print(f"등록된 백엔드: {list(CATEGORY_BACKENDS)}")

    # mock만 기본 실행(무거운 의존성 없이 파이프라인 스모크 테스트). 실백엔드는
    # PRODUCT_INFO_BACKEND 환경변수 규약을 따르는 각 팀원이 명시적으로 켠다.
    for r in run_latency_suite(["mock"], real_images, stress_mode="synthetic"):
        stats = r.stats()
        print(
            f"{r.backend:20s} stress={r.stress:9s} load={r.load_time_s * 1000:.1f}ms "
            f"p50={stats.get('p50', float('nan')):.2f}ms p95={stats.get('p95', float('nan')):.2f}ms "
            f"peak_mem={r.peak_mem_mb:.2f}MB"
        )
