"""가격 분포 지표 — **순수 함수만.** 네트워크·무거운 의존성이 없다.

CH015 M4~M7의 통계 부분을 구현한다. 표준 라이브러리만 쓰는 이유는 두 가지다.

1. CI는 `requirements-dev.txt`(ruff/black/pytest/httpx)만 설치한다 — numpy·scipy가 없다.
   여기가 순수 stdlib이면 지표 로직이 **CI에서 그대로 검증**된다.
2. 이 모듈은 GMS 호출과 무관하다. 검색을 한 번도 돌리지 않고 합성 표본으로 전부
   테스트할 수 있어야, 실측 라운드에서 지표 자체를 의심하지 않게 된다.

**로그 스케일이 기본이다.** 중고 가격은 하한 0·우측 꼬리가 긴 로그정규에 가까워서
(CH015 M4), 버킷·이상치 판정을 선형 스케일에서 하면 저가 구간의 해상도가 죽고
고가 이상치 하나가 전체를 삼킨다.

설계: .claude/plans/ai/CH015-comps-price-distribution.md
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

__all__ = [
    "Bucket",
    "Interval",
    "bootstrap_ci",
    "bucket_uniformity",
    "freedman_diaconis_width",
    "histogram",
    "iqr",
    "log_bucket_edges",
    "mad",
    "median",
    "modified_z_scores",
    "normalized_wasserstein",
    "outlier_mask",
    "quantile",
    "spearman",
    "wasserstein_distance",
]

# Iglewicz-Hoaglin modified z-score 상수. 정규분포에서 MAD를 표준편차로 환산한다.
_MAD_TO_SIGMA = 0.6745

DEFAULT_MAD_THRESHOLD = 3.5  # 통상값. |z| > 3.5 를 이상치로 본다
DEFAULT_BOOTSTRAP_ITERATIONS = 2000
DEFAULT_CONFIDENCE = 0.95
DEFAULT_BOOTSTRAP_SEED = 20260803  # 재현성 — 같은 표본이면 같은 CI가 나와야 한다

MIN_BUCKETS = 3
MAX_BUCKETS = 12


# --- 기초 통계 --------------------------------------------------------------


def median(values: Sequence[float]) -> float:
    """중앙값. 빈 표본은 0.0."""
    return quantile(values, 0.5)


def quantile(values: Sequence[float], q: float) -> float:
    """선형 보간 분위수.

    프로덕션(`app/pricing/pricer.py:_percentile`)은 보간 없는 **최근접 순위**를 쓴다 —
    응답 필드로 나가는 p25/p75가 실제 매물 가격과 일치해야 하기 때문이다. 반면 여기서
    쓰는 곳은 IQR·CI 같은 내부 계산이라, 표본이 작을 때 덜 튀는 보간 쪽이 맞다.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = _clamp(q, 0.0, 1.0) * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(ordered[low])
    return float(ordered[low] + (ordered[high] - ordered[low]) * (position - low))


def iqr(values: Sequence[float]) -> float:
    """사분위 범위."""
    return quantile(values, 0.75) - quantile(values, 0.25)


def mad(values: Sequence[float]) -> float:
    """중앙값 절대편차. **표준편차와 달리 이상치 자체에 오염되지 않는다.**"""
    if not values:
        return 0.0
    center = median(values)
    return median([abs(v - center) for v in values])


def modified_z_scores(values: Sequence[float]) -> list[float]:
    """MAD 기반 modified z-score.

    MAD가 0이면(표본 절반 이상이 같은 값) 평균절대편차로 폴백한다 — 0으로 나누는 대신
    "퍼짐이 없다"는 사실을 반영해 전부 0을 돌려주는 쪽이 안전하다.
    """
    if not values:
        return []
    center = median(values)
    scale = mad(values)
    if scale == 0.0:
        deviations = [abs(v - center) for v in values]
        scale = sum(deviations) / len(deviations) * _MAD_TO_SIGMA
    if scale == 0.0:
        return [0.0] * len(values)
    return [_MAD_TO_SIGMA * (v - center) / scale for v in values]


def outlier_mask(
    values: Sequence[float],
    *,
    threshold: float = DEFAULT_MAD_THRESHOLD,
    log_scale: bool = True,
) -> list[bool]:
    """이상치면 True. CH015 M5 — 개수 기반 trim을 대체한다.

    현행 `RuleBaselinePricer`의 trim은 "표본 5건 이상이면 양끝 1건씩"이라 이상치가
    2건이면 못 걷어내고 0건이면 멀쩡한 값을 버린다. 여기는 값의 분포를 보고 판단한다.

    `log_scale=True`면 로그 변환 후 판정한다 — 가격이 로그정규에 가까워서, 선형
    스케일에서는 정상적인 고가 매물이 이상치로 잘못 찍힌다.
    """
    if not values:
        return []
    working = _to_log(values) if log_scale else [float(v) for v in values]
    if working is None:  # 0 이하가 섞여 로그 변환 불가 → 선형으로 폴백
        working = [float(v) for v in values]
    return [abs(z) > threshold for z in modified_z_scores(working)]


# --- 버킷 (M4) --------------------------------------------------------------


@dataclass(frozen=True)
class Bucket:
    """히스토그램 막대 1개. 가격은 원 단위 정수로 되돌려 담는다."""

    min: int
    max: int
    count: int


def freedman_diaconis_width(values: Sequence[float]) -> float:
    """Freedman-Diaconis 규칙의 버킷 폭 `2·IQR / n^(1/3)`.

    IQR 기반이라 이상치에 강하고 치우친 분포에 적합하다. Sturges 규칙
    (`k = ⌈log₂n⌉+1`)을 쓰지 않는 이유는 정규성을 가정하고 작은 n에서 구간을 너무
    적게 잡기 때문이다(CH015 M4).

    IQR이 0이면(표본 절반 이상이 같은 값) 0을 돌려준다 — 호출부가 폴백을 정한다.
    """
    if len(values) < 2:
        return 0.0
    spread = iqr(values)
    if spread <= 0.0:
        return 0.0
    return 2.0 * spread / (len(values) ** (1.0 / 3.0))


def log_bucket_edges(
    prices: Sequence[int],
    *,
    min_buckets: int = MIN_BUCKETS,
    max_buckets: int = MAX_BUCKETS,
) -> list[int]:
    """로그 스케일 + FD 규칙으로 버킷 경계를 만든다. 경계 개수는 버킷 수 + 1.

    반환값은 **원 단위 가격**이다 — 로그는 계산에만 쓰고 노출하지 않는다.
    표본이 2건 미만이거나 전부 같은 값이면 빈 목록(버킷 없음)을 돌려준다.
    """
    usable = [p for p in prices if p > 0]
    if len(usable) < 2 or min(usable) == max(usable):
        return []

    logs = _to_log(usable)
    if logs is None:  # pragma: no cover — 위에서 p > 0 을 걸렀다
        return []

    low, high = min(logs), max(logs)
    width = freedman_diaconis_width(logs)
    count = min_buckets if width <= 0.0 else math.ceil((high - low) / width)
    count = int(_clamp(count, min_buckets, max_buckets))

    step = (high - low) / count
    edges = [math.exp(low + step * i) for i in range(count + 1)]
    # 경계를 원 단위로 반올림하면 인접 경계가 같아질 수 있다 — 그러면 폭 0인 빈 막대가
    # 생기므로 중복을 제거한다. 결과적으로 버킷 수가 count보다 줄 수 있다.
    rounded = sorted({int(round(edge)) for edge in edges})
    return rounded if len(rounded) >= 2 else []


def histogram(prices: Sequence[int], edges: Sequence[int]) -> list[Bucket]:
    """경계로 가격을 센다. 구간은 왼쪽 닫힘·오른쪽 열림, **마지막 버킷만 양끝 포함**.

    CH006 §3이 정한 규칙과 같다 — 최댓값이 어느 버킷에도 안 들어가는 사고를 막는다.
    """
    if len(edges) < 2:
        return []
    counts = [0] * (len(edges) - 1)
    for price in prices:
        if price < edges[0] or price > edges[-1]:
            continue
        index = _bucket_index(price, edges)
        counts[index] += 1
    return [Bucket(min=edges[i], max=edges[i + 1], count=counts[i]) for i in range(len(counts))]


def bucket_uniformity(buckets: Sequence[Bucket]) -> float:
    """버킷 분포의 균일도(정규화 엔트로피) 0~1. 1이면 완전 균등.

    **커버리지 지표이지 시장의 모양이 아니다.** 한 버킷에 다 몰려 있으면(0에 가까움)
    표본이 가격축을 못 덮었다는 뜻이고, 그 상태의 히스토그램은 분포라고 부를 수 없다.
    """
    total = sum(b.count for b in buckets)
    if total <= 0 or len(buckets) < 2:
        return 0.0
    entropy = 0.0
    for bucket in buckets:
        if bucket.count <= 0:
            continue
        share = bucket.count / total
        entropy -= share * math.log(share)
    return entropy / math.log(len(buckets))


# --- 불확실성 (M6) ----------------------------------------------------------


@dataclass(frozen=True)
class Interval:
    """점추정 + 신뢰구간."""

    low: float
    point: float
    high: float

    @property
    def width_ratio(self) -> float:
        """점추정 대비 구간 폭. 신뢰도의 해석 가능한 표현이다."""
        return (self.high - self.low) / self.point if self.point else 0.0


def bootstrap_ci(
    values: Sequence[float],
    statistic: Callable[[Sequence[float]], float] = median,
    *,
    iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    confidence: float = DEFAULT_CONFIDENCE,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> Interval:
    """부트스트랩 백분위 신뢰구간. 분포 가정이 필요 없고 **API 호출이 0건**이다.

    현행 `confidence`(임의 가중합 `_W_SAMPLE 0.5 / _W_USED 0.2 / _W_DISPERSION 0.3`)를
    대체하려고 만든다 — "0.62가 무슨 뜻이냐"에 답할 수 없던 값을 "중앙값 82,000원
    (95% CI 74,000~91,000)"으로 바꾼다(CH015 M6).

    `seed` 고정이 중요하다 — 재현성 축(축 B)을 재는 도구 자체가 실행마다 흔들리면 안 된다.
    """
    if not values:
        return Interval(0.0, 0.0, 0.0)
    point = statistic(values)
    if len(values) == 1:
        return Interval(point, point, point)

    rng = random.Random(seed)
    size = len(values)
    samples = [
        statistic([values[rng.randrange(size)] for _ in range(size)]) for _ in range(iterations)
    ]
    tail = (1.0 - confidence) / 2.0
    return Interval(low=quantile(samples, tail), point=point, high=quantile(samples, 1.0 - tail))


# --- 분포 비교 (M7 / 축 B·D) -------------------------------------------------


def wasserstein_distance(left: Sequence[float], right: Sequence[float]) -> float:
    """1차원 Wasserstein(EMD) 거리 — 두 경험분포 CDF 사이 면적.

    분포 간 거리로 L1(버킷별 차이 합)을 쓰지 않는 이유: L1은 버킷 경계에 의존해서,
    값이 경계 하나를 사이에 두고 갈리면 실제로는 가까운 분포인데 최대 거리가 나온다.
    Wasserstein은 **값이 얼마나 멀리 이동해야 하는지**를 재므로 그 문제가 없다.
    """
    if not left or not right:
        return 0.0
    a, b = sorted(left), sorted(right)
    points = sorted(set(a) | set(b))
    total = 0.0
    for i in range(len(points) - 1):
        width = points[i + 1] - points[i]
        if width <= 0:
            continue
        total += abs(_ecdf(a, points[i]) - _ecdf(b, points[i])) * width
    return total


def normalized_wasserstein(left: Sequence[float], right: Sequence[float]) -> float:
    """가격 규모로 나눈 Wasserstein. 상품마다 가격대가 달라 원본 거리는 비교가 안 된다."""
    scale = median(list(left) + list(right))
    if scale <= 0:
        return 0.0
    return wasserstein_distance(left, right) / scale


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    """스피어만 순위상관. 동점은 평균 순위로 처리한다.

    **쓰이는 곳은 출력 B(상태별 가격)의 단조성 검증뿐이다**(CH015 M9). 상품 간 비교에는
    쓰지 않는다 — 개별 중고 의류에 "알려진 참 가격 순서"가 없기 때문이다.
    """
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    rank_x, rank_y = _ranks(xs), _ranks(ys)
    mean_x = sum(rank_x) / len(rank_x)
    mean_y = sum(rank_y) / len(rank_y)
    covariance = sum((a - mean_x) * (b - mean_y) for a, b in zip(rank_x, rank_y, strict=True))
    var_x = sum((a - mean_x) ** 2 for a in rank_x)
    var_y = sum((b - mean_y) ** 2 for b in rank_y)
    if var_x <= 0 or var_y <= 0:
        return 0.0
    return covariance / math.sqrt(var_x * var_y)


# --- 내부 헬퍼 --------------------------------------------------------------


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _to_log(values: Sequence[float]) -> list[float] | None:
    """전부 양수면 자연로그 목록, 아니면 None."""
    if any(v <= 0 for v in values):
        return None
    return [math.log(v) for v in values]


def _bucket_index(price: int, edges: Sequence[int]) -> int:
    """왼쪽 닫힘·오른쪽 열림, 마지막 버킷만 양끝 포함."""
    for i in range(len(edges) - 1):
        if price < edges[i + 1]:
            return i
    return len(edges) - 2


def _ecdf(ordered: Sequence[float], point: float) -> float:
    """정렬된 표본의 경험적 CDF 값 F(point) = P(X <= point)."""
    count = 0
    for value in ordered:
        if value > point:
            break
        count += 1
    return count / len(ordered)


def _ranks(values: Sequence[float]) -> list[float]:
    """동점 평균 순위."""
    indexed = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position
        while end + 1 < len(indexed) and values[indexed[end + 1]] == values[indexed[position]]:
            end += 1
        average = (position + end) / 2.0 + 1.0
        for i in range(position, end + 1):
            ranks[indexed[i]] = average
        position = end + 1
    return ranks
