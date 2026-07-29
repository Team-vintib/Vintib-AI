"""라이브 댓글 관리 정확도 평가 러너 (S15P11A108-196).

사용 예:
    python -m app.chat.pipeline.evaluate                # 전체(A/B/C) + 리포트 기록
    python -m app.chat.pipeline.evaluate --sets A       # 호환셋만
    python -m app.chat.pipeline.evaluate --no-report    # 콘솔만

콘솔 표와 `artifacts/eval_report.md`를 만든다. 리포트는 생성물이라 gitignore 대상이다.
사람이 읽는 결론·정리는 계획서(`.claude/plans/ai/004-*.md`)의 "측정 결과" 절에 커밋한다.

**이 러너는 채택/반려 결론을 내지 않는다.** 수치와 실패 사례만 모아 보여 준다.

설계: .claude/plans/ai/004-live-comment-moderation-evaluation.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.chat import registry
from app.chat.classifier import build_classifier
from app.chat.eval_dataset import (
    build_set_a,
    build_set_b,
    build_set_c,
    label_distribution,
)
from app.chat.evaluation import (
    FaqEval,
    ModerationEval,
    evaluate_faq,
    evaluate_moderation,
)
from app.chat.faq import build_retriever

_DEFAULT_OUT = Path(__file__).resolve().parent.parent / "artifacts"
_REPORT_FILE = "eval_report.md"

# 모델 선정 단계 실측치 — `test/model_selection/classifier_benchmark.ipynb` §5 기록값.
# **이번에 재측정한 값이 아니다**(torch 미설치). Set A와 같은 210건 기준이라 대조만 한다.
_DOCUMENTED_BASELINES = (
    ("kor_unsmile (기존 baseline)", 0.833, 0.583, "문서 인용"),
    ("kcelectra_base_hate (1순위 후보)", 0.995, 0.988, "문서 인용"),
)


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _moderation_lines(result: ModerationEval, *, comparable: bool) -> list[str]:
    """비매너 판정 결과를 표·사례 목록으로 렌더링한다."""
    stats = result.latency_stats()
    lines = [
        f"### 비매너 판정 — {result.name}",
        "",
        f"- 표본 {result.total}건 (혼동행렬: TP {result.true_positive} / "
        f"FP {result.false_positive} / FN {result.false_negative} / TN {result.true_negative})",
        f"- accuracy {_fmt_pct(result.accuracy)}",
        f"- 악성 precision {_fmt_pct(result.abuse_precision)} · "
        f"recall {_fmt_pct(result.abuse_recall)} · F1 {_fmt_pct(result.abuse_f1)}",
        f"- 정상 recall {_fmt_pct(result.normal_recall)} (= 1 − 오탐률)",
        f"- 지연 mean {stats.get('mean', 0):.2f}ms · p95 {stats.get('p95', 0):.2f}ms · "
        f"p99 {stats.get('p99', 0):.2f}ms (설계 목표 p95 300ms)",
        "",
    ]

    variants = result.variant_recall()
    if variants:
        lines += ["| 우회 변형 | 잡은 수 / 전체 | recall |", "| --- | --- | --- |"]
        lines += [
            f"| {variant} | {caught}/{total} | {_fmt_pct(caught / total if total else 0)} |"
            for variant, (caught, total) in variants.items()
        ]
        lines.append("")

    if comparable:
        lines += [
            "동일 210건 기준 모델 선정 단계 수치와의 대조 "
            "(**모델 수치는 문서 인용값이며 이번에 재측정한 것이 아니다**):",
            "",
            "| 분류기 | accuracy | 악성 recall | 출처 |",
            "| --- | --- | --- | --- |",
            f"| rule_based (현재 기본값) | {_fmt_pct(result.accuracy)} | "
            f"{_fmt_pct(result.abuse_recall)} | 이번 실측 |",
        ]
        lines += [
            f"| {name} | {_fmt_pct(acc)} | {_fmt_pct(recall)} | {source} |"
            for name, acc, recall, source in _DOCUMENTED_BASELINES
        ]
        lines.append("")

    lines += _case_lines("오탐 (정상 → 악성)", result.false_positives, show_rule=True)
    lines += _case_lines("미탐 (악성 → 정상)", result.false_negatives, show_rule=False)
    return lines


def _case_lines(title: str, cases: list, *, show_rule: bool) -> list[str]:
    if not cases:
        return [f"**{title}**: 없음", ""]
    header = "| 문장 | 매칭 어휘 |" if show_rule else "| 문장 | 변형 |"
    lines = [f"**{title}** — {len(cases)}건", "", header, "| --- | --- |"]
    for case in cases:
        detail = case.rule_label if show_rule else case.variant
        lines.append(f"| {case.comment} | {detail} |")
    lines.append("")
    return lines


def _faq_lines(result: FaqEval, cluster_threshold: float, grounding_threshold: float) -> list[str]:
    """반복질문 클러스터링·근거 결과를 렌더링한다."""
    metrics = result.clustering_metrics(cluster_threshold)
    lines = [
        "### 반복질문 — 클러스터링(B-2)",
        "",
        f"- 쌍 {len(result.pairs)}개 (같은 그룹 {sum(1 for p in result.pairs if p.same_group)}쌍)",
        f"- 임계치 {cluster_threshold}: precision {_fmt_pct(metrics['precision'])} · "
        f"recall {_fmt_pct(metrics['recall'])}",
        "",
        "| 임계치 | precision | recall |",
        "| --- | --- | --- |",
    ]
    lines += [
        f"| {point['threshold']:.2f} | {_fmt_pct(point['precision'])} | "
        f"{_fmt_pct(point['recall'])} |"
        for point in result.threshold_sweep()
    ]
    lines.append("")

    for label, pairs in (
        ("잘못 묶인 쌍 (다른 질문인데 클러스터링)", result.wrongly_clustered(cluster_threshold)),
        ("못 묶은 쌍 (같은 질문인데 분리)", result.wrongly_split(cluster_threshold)),
    ):
        if not pairs:
            lines += [f"**{label}**: 없음", ""]
            continue
        lines += [f"**{label}** — {len(pairs)}건", "", "| A | B | 유사도 |", "| --- | --- | --- |"]
        lines += [f"| {p.a} | {p.b} | {p.similarity:.4f} |" for p in pairs]
        lines.append("")

    lines += [
        "### 반복질문 — 근거 적절성(B-3)",
        "",
        f"- 그라운딩 임계치 {grounding_threshold}",
        f"- 지식베이스 내 {len(result.in_kb)}건: 근거 정확도 {_fmt_pct(result.doc_accuracy)} "
        f"(정답 {len(result.correct_doc_cases)} / 근거오답 {len(result.wrong_doc_cases)} / "
        f"침묵 {len(result.missed_answer_cases)})",
        f"- 지식베이스 밖 {len(result.out_of_kb)}건: 침묵 정확도 "
        f"{_fmt_pct(result.silence_accuracy)} (환각 {len(result.hallucinated_cases)}건)",
        "",
    ]
    if result.question_detection_misses:
        lines += [
            f"**B-1 질문 판별 실패** — {len(result.question_detection_misses)}건 "
            "(질문으로 인식되지 않아 반복질문 경로에 진입하지 못함)",
            "",
        ]
        lines += [f"- {q}" for q in result.question_detection_misses]
        lines.append("")

    for label, cases in (
        ("근거 있는데 침묵 (미탐)", result.missed_answer_cases),
        ("근거 문서 오답", result.wrong_doc_cases),
        ("근거 없는데 답변 (환각)", result.hallucinated_cases),
    ):
        if not cases:
            lines += [f"**{label}**: 없음", ""]
            continue
        lines += [
            f"**{label}** — {len(cases)}건",
            "",
            "| 질문 | 기대 문서 | top1 문서 | 유사도 |",
            "| --- | --- | --- | --- |",
        ]
        lines += [
            f"| {c.question} | {c.expected_doc_id or '(없음)'} | {c.top_doc_id} | "
            f"{c.top_score:.4f} |"
            for c in cases
        ]
        lines.append("")
    return lines


def run(sets: tuple[str, ...]) -> list[str]:
    """선택한 세트를 평가하고 리포트 본문(마크다운 줄 목록)을 돌려준다."""
    embedder = registry.embedder_config()
    lines = [
        "# 라이브 댓글 관리 정확도 평가 리포트",
        "",
        f"평가 대상: `app/chat/` — 분류기 `{registry.ACTIVE_CLASSIFIER}`, "
        f"임베더 `{registry.ACTIVE_EMBEDDER}`, retriever `{registry.ACTIVE_RETRIEVER}`",
        "",
        "> 이 리포트는 생성물이다. 결론·정리는 "
        "`.claude/plans/ai/004-live-comment-moderation-evaluation.md`에 기록한다.",
        "",
    ]

    classifier = build_classifier()

    if "A" in sets:
        cases = build_set_a()
        print(f"[evaluate] Set A 호환셋 {len(cases)}건 {label_distribution(cases)}")
        result = evaluate_moderation(cases, classifier, name="Set A 호환셋 (210건)")
        lines += _moderation_lines(result, comparable=True)
        _print_summary(result)

    if "B" in sets:
        cases = build_set_b()
        print(f"[evaluate] Set B 확장셋 {len(cases)}건 {label_distribution(cases)}")
        result = evaluate_moderation(cases, classifier, name="Set B 확장셋 (수제)")
        lines += _moderation_lines(result, comparable=False)
        _print_summary(result)

    if "C" in sets:
        faq_cases = build_set_c()
        print(f"[evaluate] Set C 반복질문셋 {len(faq_cases)}건")
        faq_result = evaluate_faq(faq_cases, build_retriever())
        lines += _faq_lines(
            faq_result,
            embedder["cluster_similarity"],
            embedder["grounding_threshold"],
        )
        print(
            f"[evaluate]   근거 정확도 {_fmt_pct(faq_result.doc_accuracy)} · "
            f"침묵 정확도 {_fmt_pct(faq_result.silence_accuracy)} · "
            f"환각 {len(faq_result.hallucinated_cases)}건"
        )

    return lines


def _print_summary(result: ModerationEval) -> None:
    stats = result.latency_stats()
    print(
        f"[evaluate]   accuracy {_fmt_pct(result.accuracy)} · "
        f"악성 P {_fmt_pct(result.abuse_precision)} / R {_fmt_pct(result.abuse_recall)} · "
        f"오탐 {result.false_positive}건 / 미탐 {result.false_negative}건 · "
        f"p95 {stats.get('p95', 0):.2f}ms"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="라이브 댓글 관리 정확도 평가(오프라인).")
    parser.add_argument(
        "--sets",
        default="ABC",
        help="평가할 세트 조합. A=호환셋 B=확장셋 C=반복질문셋 (기본 ABC)",
    )
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="리포트 출력 디렉터리")
    parser.add_argument("--no-report", action="store_true", help="파일로 쓰지 않고 콘솔만")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    sets = tuple(ch for ch in args.sets.upper() if ch in "ABC")
    if not sets:
        raise SystemExit("--sets 에 A/B/C 중 하나 이상을 지정하세요")

    lines = run(sets)

    if args.no_report:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    report_path = args.out / _REPORT_FILE
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[evaluate] 리포트 기록 완료 → {report_path}")


if __name__ == "__main__":
    main()
