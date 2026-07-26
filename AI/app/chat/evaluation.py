"""라이브 댓글 관리 정확도 평가 지표 (S15P11A108-196).

리포에 confusion matrix / F1 / 오탐·미탐 리포터가 없어 여기서 새로 만든다. 다만 기존 자산의
모양은 따랐다 — 지연시간은 `test/model_selection/classifier_benchmark.py`의 nearest-rank
방식, 클러스터링 precision/recall은 `embedding_benchmark.py`의 pairwise TP/FP/FN 방식.

평가 대상(`app/chat/`)의 기본 백엔드는 stdlib + numpy만 쓰므로 이 모듈도 무거운 의존성이
없다 — 기존 벤치마크 3종과 달리 **CI에서 그대로 실행된다**.

이 모듈은 "이 구현이 충분하다/부족하다"는 결론을 내리지 않는다. 수치와 실패 사례를 모아
주기만 하고, 판단은 사람이 한다(리포 벤치마크 모듈들과 같은 스탠스).

설계: .claude/plans/ai/004-live-comment-moderation-evaluation.md
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import combinations

from app.chat import registry
from app.chat.classifier import AbuseClassifier
from app.chat.eval_dataset import ABUSIVE, FaqCase, ModerationCase
from app.chat.faq import QuestionDetector, Retriever, cosine, embed

# 클러스터링 임계치 스윕 구간. 목업 임베더의 유사도 스케일이 낮아 0.10부터 본다.
DEFAULT_THRESHOLDS: tuple[float, ...] = tuple(round(0.10 + 0.05 * i, 2) for i in range(17))


def _percentiles(values: list[float]) -> dict[str, float]:
    """mean/p50/p95/p99(nearest-rank). 값이 없으면 빈 dict."""
    if not values:
        return {}
    ordered = sorted(values)
    n = len(ordered)
    return {
        "mean": statistics.mean(ordered),
        "p50": ordered[min(int(n * 0.5), n - 1)],
        "p95": ordered[min(int(n * 0.95), n - 1)],
        "p99": ordered[min(int(n * 0.99), n - 1)],
    }


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


# ---------------------------------------------------------------------------
# 비매너 판정
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Misclassified:
    """오판 한 건. 오탐/미탐 사례 정리의 최소 단위."""

    comment: str
    expected: str
    predicted: str
    score: float
    rule_label: str  # 매칭된 사전 어휘(오탐 원인 추적용). 정상 판정이면 "clean"
    variant: str  # 우회 변형 종류(미탐 원인 추적용)


@dataclass
class ModerationEval:
    """악성=positive 기준 혼동행렬 + 지연시간 + 오판 사례."""

    name: str
    true_positive: int = 0  # 악성 -> 악성
    false_positive: int = 0  # 정상 -> 악성  (오탐)
    false_negative: int = 0  # 악성 -> 정상  (미탐)
    true_negative: int = 0  # 정상 -> 정상
    latencies_ms: list[float] = field(default_factory=list)
    false_positives: list[Misclassified] = field(default_factory=list)
    false_negatives: list[Misclassified] = field(default_factory=list)
    # 우회 변형별 악성 케이스 총수(변형별 recall 분모).
    abusive_variant_totals: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.true_positive + self.false_positive + self.false_negative + self.true_negative

    @property
    def accuracy(self) -> float:
        return _ratio(self.true_positive + self.true_negative, self.total)

    @property
    def abuse_precision(self) -> float:
        """악성으로 판정한 것 중 실제 악성 비율. 낮으면 오탐이 많다."""
        return _ratio(self.true_positive, self.true_positive + self.false_positive)

    @property
    def abuse_recall(self) -> float:
        """실제 악성 중 잡아낸 비율. 낮으면 미탐이 많다."""
        return _ratio(self.true_positive, self.true_positive + self.false_negative)

    @property
    def abuse_f1(self) -> float:
        precision, recall = self.abuse_precision, self.abuse_recall
        denominator = precision + recall
        return 2 * precision * recall / denominator if denominator else 0.0

    @property
    def normal_recall(self) -> float:
        """실제 정상 중 통과시킨 비율(= 1 - 오탐률). 사용자 체감에 직접 영향."""
        return _ratio(self.true_negative, self.true_negative + self.false_positive)

    def latency_stats(self) -> dict[str, float]:
        return _percentiles(self.latencies_ms)

    def variant_recall(self) -> dict[str, tuple[int, int]]:
        """우회 변형별 (잡은 수, 전체 수). 어떤 변형에 약한지 드러낸다."""
        missed: dict[str, int] = {}
        for case in self.false_negatives:
            missed[case.variant] = missed.get(case.variant, 0) + 1
        return {
            variant: (total - missed.get(variant, 0), total)
            for variant, total in sorted(self.abusive_variant_totals.items())
        }


def evaluate_moderation(
    cases: Iterable[ModerationCase],
    classifier: AbuseClassifier,
    *,
    name: str,
    threshold: float = registry.ABUSE_THRESHOLD,
) -> ModerationEval:
    """케이스를 하나씩 분류기에 넣어 혼동행렬과 오판 사례를 모은다."""
    result = ModerationEval(name=name)
    for case in cases:
        started = time.perf_counter()
        scored = classifier.score(case.comment)
        result.latencies_ms.append((time.perf_counter() - started) * 1000)

        predicted = ABUSIVE if scored.score >= threshold else "정상"
        if case.expected == ABUSIVE:
            result.abusive_variant_totals[case.variant] = (
                result.abusive_variant_totals.get(case.variant, 0) + 1
            )
        misclassified = Misclassified(
            comment=case.comment,
            expected=case.expected,
            predicted=predicted,
            score=round(scored.score, 4),
            rule_label=scored.label,
            variant=case.variant,
        )

        if case.expected == ABUSIVE and predicted == ABUSIVE:
            result.true_positive += 1
        elif case.expected == ABUSIVE:
            result.false_negative += 1
            result.false_negatives.append(misclassified)
        elif predicted == ABUSIVE:
            result.false_positive += 1
            result.false_positives.append(misclassified)
        else:
            result.true_negative += 1
    return result


# ---------------------------------------------------------------------------
# 반복질문 — 클러스터링(B-2) + 근거 적절성(B-3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PairSimilarity:
    """질문 쌍 하나의 코사인 유사도와 정답(같은 paraphrase 그룹인지)."""

    a: str
    b: str
    same_group: bool
    similarity: float


@dataclass(frozen=True)
class GroundingCase:
    """근거 검색 결과 한 건."""

    question: str
    expected_doc_id: str | None
    top_doc_id: str
    top_score: float
    answered: bool


@dataclass
class FaqEval:
    """클러스터링 쌍 + 근거 판정 결과. 오답 유형별로 사례를 따로 모은다."""

    pairs: list[PairSimilarity] = field(default_factory=list)
    grounding: list[GroundingCase] = field(default_factory=list)
    question_detection_misses: list[str] = field(default_factory=list)

    # -- 클러스터링 --------------------------------------------------------
    def clustering_metrics(self, threshold: float) -> dict[str, float]:
        """threshold 이상을 "같은 질문"으로 예측했다고 볼 때의 precision/recall."""
        tp = fp = fn = 0
        for pair in self.pairs:
            predicted_same = pair.similarity >= threshold
            if predicted_same and pair.same_group:
                tp += 1
            elif predicted_same:
                fp += 1
            elif pair.same_group:
                fn += 1
        return {
            "threshold": threshold,
            "precision": _ratio(tp, tp + fp),
            "recall": _ratio(tp, tp + fn),
        }

    def threshold_sweep(
        self, thresholds: Iterable[float] = DEFAULT_THRESHOLDS
    ) -> list[dict[str, float]]:
        """구간 전체를 훑어 현재 임계치가 최적 근방인지 스스로 드러나게 한다."""
        return [self.clustering_metrics(t) for t in thresholds]

    def wrongly_clustered(self, threshold: float) -> list[PairSimilarity]:
        """다른 질문인데 묶인 쌍(오탐)."""
        return [p for p in self.pairs if p.similarity >= threshold and not p.same_group]

    def wrongly_split(self, threshold: float) -> list[PairSimilarity]:
        """같은 질문인데 못 묶은 쌍(미탐)."""
        return [p for p in self.pairs if p.similarity < threshold and p.same_group]

    # -- 근거 적절성 -------------------------------------------------------
    @property
    def in_kb(self) -> list[GroundingCase]:
        return [g for g in self.grounding if g.expected_doc_id is not None]

    @property
    def out_of_kb(self) -> list[GroundingCase]:
        return [g for g in self.grounding if g.expected_doc_id is None]

    @property
    def correct_doc_cases(self) -> list[GroundingCase]:
        return [g for g in self.in_kb if g.answered and g.top_doc_id == g.expected_doc_id]

    @property
    def wrong_doc_cases(self) -> list[GroundingCase]:
        """답변은 했지만 근거 문서를 틀린 케이스."""
        return [g for g in self.in_kb if g.answered and g.top_doc_id != g.expected_doc_id]

    @property
    def missed_answer_cases(self) -> list[GroundingCase]:
        """근거가 있는데 임계치 미달로 침묵한 케이스(미탐)."""
        return [g for g in self.in_kb if not g.answered]

    @property
    def hallucinated_cases(self) -> list[GroundingCase]:
        """근거가 없는데 답변한 케이스(환각). 0건이어야 한다."""
        return [g for g in self.out_of_kb if g.answered]

    @property
    def doc_accuracy(self) -> float:
        """지식베이스에 있는 질문 중 올바른 근거로 답한 비율."""
        return _ratio(len(self.correct_doc_cases), len(self.in_kb))

    @property
    def silence_accuracy(self) -> float:
        """지식베이스 밖 질문 중 올바르게 침묵한 비율. 1.0이 아니면 환각이 있다."""
        out = self.out_of_kb
        return _ratio(len(out) - len(self.hallucinated_cases), len(out))


def evaluate_faq(
    cases: Iterable[FaqCase],
    retriever: Retriever,
    *,
    grounding_threshold: float | None = None,
    top_k: int = registry.RETRIEVE_TOP_K,
    detector: QuestionDetector | None = None,
) -> FaqEval:
    """클러스터링 쌍 유사도와 근거 검색 결과를 한 번에 모은다.

    질문 판별(B-1)도 함께 확인한다 — 규칙 필터가 질문으로 잡지 못하면 반복질문 경로에 아예
    진입하지 못하므로, 그 자체가 미탐이다.
    """
    resolved_threshold = (
        grounding_threshold
        if grounding_threshold is not None
        else registry.embedder_config()["grounding_threshold"]
    )
    resolved_detector = detector or QuestionDetector()
    cases = list(cases)
    result = FaqEval()

    # B-1: 질문으로 인식되지 않으면 뒤 단계로 가지 못한다.
    result.question_detection_misses = [
        case.question for case in cases if not resolved_detector.is_question(case.question)
    ]

    # B-2: 모든 쌍의 코사인 유사도 + 같은 그룹 여부.
    vectors = [embed(case.question) for case in cases]
    for i, j in combinations(range(len(cases)), 2):
        result.pairs.append(
            PairSimilarity(
                a=cases[i].question,
                b=cases[j].question,
                same_group=cases[i].group == cases[j].group,
                similarity=round(cosine(vectors[i], vectors[j]), 4),
            )
        )

    # B-3: 근거 검색 + 그라운딩 게이트.
    for case in cases:
        docs = retriever.search(case.question, top_k)
        top = docs[0] if docs else None
        result.grounding.append(
            GroundingCase(
                question=case.question,
                expected_doc_id=case.expected_doc_id,
                top_doc_id=top.doc_id if top else "",
                top_score=top.score if top else 0.0,
                answered=bool(top and top.score >= resolved_threshold),
            )
        )
    return result
