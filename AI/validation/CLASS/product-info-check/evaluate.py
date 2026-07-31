"""V2~V4 지표 집계 + 리포트.

`dataset.py`가 로드한 정답셋에 `classify.py`/`color.py` 백엔드를 돌려 정확도·혼동행렬·
캘리브레이션을 계산한다. **synthetic 샘플(`shirt_red.png` 등 실제 사진이 아닌 것)은 기본적으로
전 지표에서 제외한다** — 포함하면 "정확도"가 실제 사진 성능이 아닌 걸 재는 셈이 된다.

실패 격리: 샘플 하나에서 예외가 나도 나머지 계산은 계속한다(best-effort) — 백엔드 초기화
자체가 실패하는 경우(예: 모델 다운로드 실패)만 예외를 그대로 올린다.

**N이 작을 때 지표를 과신하지 말 것.** 이 스파이크의 초기 정답셋은 8건(그중 실제 사진
7건)뿐이다 — 아래 모든 함수가 정상 동작하지만, 결과 숫자는 "파이프라인이 도는지"를
확인하는 용도지 실제 정확도로 인용하면 안 된다. `min_n_for_confidence` 미만이면 리포트가
경고를 명시한다.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from classify import (
    CategoryClassifier,
    ClassificationResult,
    classify_one_stage,
    classify_two_stage,
    get_category_classifier,
)
from color import ColorExtractor, MULTI_LABEL, PALETTE, get_color_extractor
from dataset import LoadResult, Sample, load_ground_truth
from taxonomy import ALL_SUBCATEGORIES, PROMPT_TEMPLATES, major_of

MIN_N_FOR_CONFIDENCE = 30  # 이보다 적으면 리포트가 "표본 부족" 경고를 붙인다

_HERE = Path(__file__).resolve().parent
OUTPUT_DIR = _HERE / "outputs"


# --------------------------------------------------------------------------
# V2a — 카테고리(소분류) 평가
# --------------------------------------------------------------------------
@dataclass
class CategoryPrediction:
    image_file: str
    truth: str
    predicted: str | None
    score: float
    top3: list[str]
    correct_top1: bool
    correct_top3: bool
    major: str
    shot_type: str
    error: str | None = None


def evaluate_category(
    samples: list[Sample],
    backend_key: str,
    template_key: str,
    mode: str = "one_stage",
) -> list[CategoryPrediction]:
    classifier = get_category_classifier(backend_key)
    fn = classify_one_stage if mode == "one_stage" else classify_two_stage
    out: list[CategoryPrediction] = []
    for s in samples:
        if s.synthetic:
            continue
        try:
            result: ClassificationResult = fn(classifier, s.image_path, template_key)
            top3 = [c.code for c in result.candidates]
            out.append(
                CategoryPrediction(
                    image_file=s.image_file,
                    truth=s.subcategory,
                    predicted=result.predicted,
                    score=result.score,
                    top3=top3,
                    correct_top1=result.predicted == s.subcategory,
                    correct_top3=s.subcategory in top3,
                    major=s.major_category,
                    shot_type=s.shot_type,
                )
            )
        except Exception as exc:  # noqa: BLE001 — 실패 격리: 샘플 하나가 죽어도 계속
            out.append(
                CategoryPrediction(
                    image_file=s.image_file,
                    truth=s.subcategory,
                    predicted=None,
                    score=0.0,
                    top3=[],
                    correct_top1=False,
                    correct_top3=False,
                    major=s.major_category,
                    shot_type=s.shot_type,
                    error=str(exc),
                )
            )
    return out


def majority_baseline_accuracy(samples: list[Sample]) -> tuple[str, float]:
    """항상 최빈 소분류를 답하는 더미 분류기의 top-1 정확도. (최빈 코드, 정확도)."""
    real = [s for s in samples if not s.synthetic]
    if not real:
        return "N/A", 0.0
    majority = Counter(s.subcategory for s in real).most_common(1)[0][0]
    correct = sum(1 for s in real if s.subcategory == majority)
    return majority, correct / len(real)


def confusion_matrix(preds: list[CategoryPrediction]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {code: {} for code in ALL_SUBCATEGORIES}
    for p in preds:
        if p.predicted is None:
            continue
        matrix[p.truth][p.predicted] = matrix[p.truth].get(p.predicted, 0) + 1
    return matrix


def accuracy_by(preds: list[CategoryPrediction], key: str) -> dict[str, dict[str, float]]:
    """key: "major" 또는 "shot_type". {그룹: {"n":.., "top1":.., "top3":..}}."""
    groups: dict[str, list[CategoryPrediction]] = {}
    for p in preds:
        groups.setdefault(getattr(p, key), []).append(p)
    out = {}
    for g, items in groups.items():
        n = len(items)
        out[g] = {
            "n": n,
            "top1": sum(p.correct_top1 for p in items) / n if n else 0.0,
            "top3": sum(p.correct_top3 for p in items) / n if n else 0.0,
        }
    return out


# --------------------------------------------------------------------------
# V3 — 색상 평가
# --------------------------------------------------------------------------
@dataclass
class ColorPrediction:
    image_file: str
    truth_primary: str
    truth_secondary: str | None
    predicted_primary: str
    predicted_secondary: str | None
    confidence: float
    correct_primary: bool
    correct_secondary: bool
    off_palette: bool  # 예측값이 PALETTE에도 MULTI_LABEL에도 없음(예: VLM 파싱 실패 UNKNOWN)
    major: str
    error: str | None = None


def evaluate_color(samples: list[Sample], backend_key: str) -> list[ColorPrediction]:
    extractor = get_color_extractor(backend_key)
    valid = set(PALETTE) | {MULTI_LABEL}
    out: list[ColorPrediction] = []
    for s in samples:
        if s.synthetic:
            continue
        try:
            r = extractor.extract(s.image_path)
            out.append(
                ColorPrediction(
                    image_file=s.image_file,
                    truth_primary=s.primary_color,
                    truth_secondary=s.secondary_color,
                    predicted_primary=r.primary,
                    predicted_secondary=r.secondary,
                    confidence=r.confidence,
                    correct_primary=r.primary == s.primary_color,
                    correct_secondary=r.secondary == s.secondary_color,
                    off_palette=r.primary not in valid,
                    major=s.major_category,
                )
            )
        except Exception as exc:  # noqa: BLE001
            out.append(
                ColorPrediction(
                    image_file=s.image_file,
                    truth_primary=s.primary_color,
                    truth_secondary=s.secondary_color,
                    predicted_primary="ERROR",
                    predicted_secondary=None,
                    confidence=0.0,
                    correct_primary=False,
                    correct_secondary=False,
                    off_palette=True,
                    major=s.major_category,
                    error=str(exc),
                )
            )
    return out


# --------------------------------------------------------------------------
# V4 — score 분포 / 캘리브레이션
# --------------------------------------------------------------------------
@dataclass
class CalibrationBin:
    score_lo: float
    score_hi: float
    n: int
    accuracy: float
    avg_confidence: float


def reliability_bins(scored: list[tuple[float, bool]], n_bins: int = 5) -> list[CalibrationBin]:
    """`scored`: (score, 정답여부) 쌍 목록. 등간격 bin으로 나눠 각 bin의 실제 정확도와
    평균 confidence를 비교한다 — 둘이 가까울수록 잘 캘리브레이션된 것이다."""
    bins: list[CalibrationBin] = []
    for i in range(n_bins):
        lo, hi = i / n_bins, (i + 1) / n_bins
        items = [(sc, ok) for sc, ok in scored if lo <= sc < hi or (i == n_bins - 1 and sc == hi)]
        if not items:
            bins.append(CalibrationBin(lo, hi, 0, 0.0, 0.0))
            continue
        n = len(items)
        acc = sum(ok for _, ok in items) / n
        avg_conf = sum(sc for sc, _ in items) / n
        bins.append(CalibrationBin(lo, hi, n, acc, avg_conf))
    return bins


def expected_calibration_error(bins: list[CalibrationBin], total_n: int) -> float:
    if total_n == 0:
        return float("nan")
    return sum(b.n * abs(b.accuracy - b.avg_confidence) for b in bins) / total_n


def recommend_threshold(scored: list[tuple[float, bool]], max_wrong_rate: float = 0.10) -> dict:
    """score 내림차순으로 누적하면서, "이 임계값 이상만 자동 채움" 했을 때 오답률이
    `max_wrong_rate` 이하가 되는 가장 낮은(=커버리지가 가장 큰) 임계값을 찾는다.

    표본이 작으면(특히 이 스파이크의 초기 8건) 오답률이 계단식으로 뛰어서 신뢰할 수 없는
    임계값이 나온다 — `n`이 `MIN_N_FOR_CONFIDENCE` 미만이면 결과에 경고를 남긴다.
    """
    ordered = sorted(scored, key=lambda x: -x[0])
    best_threshold = None
    best_coverage = 0
    for cutoff_idx in range(1, len(ordered) + 1):
        subset = ordered[:cutoff_idx]
        wrong = sum(1 for _, ok in subset if not ok)
        wrong_rate = wrong / len(subset)
        if wrong_rate <= max_wrong_rate:
            best_threshold = subset[-1][0]
            best_coverage = len(subset)
    return {
        "threshold": best_threshold,
        "coverage": best_coverage,
        "total": len(ordered),
        "coverage_ratio": best_coverage / len(ordered) if ordered else 0.0,
        "low_confidence_warning": len(ordered) < MIN_N_FOR_CONFIDENCE,
    }


# --------------------------------------------------------------------------
# 리포트 조립
# --------------------------------------------------------------------------
def build_report(
    load_result: LoadResult,
    category_runs: dict[str, list[CategoryPrediction]],
    color_runs: dict[str, list[ColorPrediction]],
) -> dict:
    real_samples = [s for s in load_result.samples if not s.synthetic]
    majority_code, majority_acc = majority_baseline_accuracy(load_result.samples)

    report: dict = {
        "n_total": len(load_result.samples),
        "n_real": len(real_samples),
        "n_synthetic": len(load_result.samples) - len(real_samples),
        "n_issues": len(load_result.issues),
        "low_n_warning": len(real_samples) < MIN_N_FOR_CONFIDENCE,
        "majority_baseline": {"predicted_always": majority_code, "top1_accuracy": majority_acc},
        "category_runs": {},
        "color_runs": {},
    }

    for run_key, preds in category_runs.items():
        n = len(preds)
        top1 = sum(p.correct_top1 for p in preds) / n if n else 0.0
        top3 = sum(p.correct_top3 for p in preds) / n if n else 0.0
        scored = [(p.score, p.correct_top1) for p in preds if p.predicted is not None]
        bins = reliability_bins(scored)
        report["category_runs"][run_key] = {
            "n": n,
            "top1_accuracy": top1,
            "top3_accuracy": top3,
            "beats_majority_baseline": top1 > majority_acc,
            "by_major": accuracy_by(preds, "major"),
            "by_shot_type": accuracy_by(preds, "shot_type"),
            "confusion_matrix": confusion_matrix(preds),
            "ece": expected_calibration_error(bins, len(scored)),
            "reliability_bins": [asdict(b) for b in bins],
            "recommended_threshold": recommend_threshold(scored),
            "errors": [{"image": p.image_file, "error": p.error} for p in preds if p.error],
        }

    for backend_key, preds in color_runs.items():
        n = len(preds)
        primary_acc = sum(p.correct_primary for p in preds) / n if n else 0.0
        secondary_eligible = [p for p in preds if p.truth_secondary is not None]
        secondary_acc = (
            sum(p.correct_secondary for p in secondary_eligible) / len(secondary_eligible)
            if secondary_eligible
            else None
        )
        off_palette_rate = sum(p.off_palette for p in preds) / n if n else 0.0
        scored = [(p.confidence, p.correct_primary) for p in preds]
        bins = reliability_bins(scored)
        report["color_runs"][backend_key] = {
            "n": n,
            "primary_accuracy": primary_acc,
            "secondary_accuracy": secondary_acc,
            "secondary_eligible_n": len(secondary_eligible),
            "off_palette_rate": off_palette_rate,
            "by_major": {
                major: {
                    "n": len(items),
                    "primary_accuracy": sum(p.correct_primary for p in items) / len(items),
                }
                for major, items in _group_by(preds, lambda p: p.major).items()
            },
            "ece": expected_calibration_error(bins, len(scored)),
            "recommended_threshold": recommend_threshold(scored),
            "errors": [{"image": p.image_file, "error": p.error} for p in preds if p.error],
        }

    return report


def _group_by(items, key_fn):
    groups: dict = {}
    for item in items:
        groups.setdefault(key_fn(item), []).append(item)
    return groups


def save_report(report: dict, name: str = "report.json") -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / name
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    load_result = load_ground_truth()
    print(f"정답셋: 유효 {len(load_result.samples)}행, 문제 {len(load_result.issues)}행")

    category_runs = {}
    for template_key in PROMPT_TEMPLATES:
        for mode in ("one_stage", "two_stage"):
            key = f"mock/{template_key}/{mode}"
            category_runs[key] = evaluate_category(load_result.samples, "mock", template_key, mode)

    color_runs = {}
    for backend_key in ("mock", "mean_color", "kmeans_palette"):
        color_runs[backend_key] = evaluate_color(load_result.samples, backend_key)

    report = build_report(load_result, category_runs, color_runs)
    path = save_report(report)
    print(f"리포트 저장: {path}")
    print(f"majority baseline top1={report['majority_baseline']['top1_accuracy']:.2f}")
    for key, r in report["category_runs"].items():
        print(f"  {key}: top1={r['top1_accuracy']:.2f} top3={r['top3_accuracy']:.2f}")
    for key, r in report["color_runs"].items():
        print(
            f"  color/{key}: primary_acc={r['primary_accuracy']:.2f} off_palette={r['off_palette_rate']:.2f}"
        )
