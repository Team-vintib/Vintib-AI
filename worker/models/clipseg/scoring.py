"""하자 항목 → 컨디션 점수·등급·요약문.

순수 집계만 한다(I/O 없음). 가격책정(에픽 밖)이 `condition_score`를 소비하게 되므로 계산식은
단순하고 설명 가능해야 한다 — 판매자가 "왜 78점인가"를 물으면 항목별 감점으로 답할 수 있다.

⚠️ **가중치·구간 경계는 근거 없는 임의값이다.** 라벨링된 검증셋이 없어 정량 지표가 없는 상태라,
값은 전부 `registry`에 상수로 노출해 두고 확정은 검증셋 확보 이후의 별도 작업으로 미룬다
(설계 문서 §점수). 이 모듈이 고정하는 건 값이 아니라 **구조**다.

`SUSPECTED` 감점 계수가 낮은 것이 이 설계의 안전장치다 — 모델이 확신하지 못하는 항목이
판매 가격을 그대로 깎으면, 오탐 하나가 판매자에게 실제 손해를 입힌다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import registry
from contracts import ConditionGrade, DefectType, Finding, FindingStatus

MAX_SCORE = 100.0

# 요약문에 쓰는 한국어 라벨. FE가 자체 문구를 쓰면 `defect_type` enum으로 직접 지역화하면 된다 —
# `summary`는 그대로 보여줄 수 있는 편의 문자열이다.
DEFECT_LABELS: dict[DefectType, str] = {
    DefectType.stain: "오염",
    DefectType.dirt_mark: "얼룩",
    DefectType.hole_tear: "구멍·찢어짐",
    DefectType.discoloration: "변색",
    DefectType.pilling: "보풀",
    DefectType.fray: "올풀림",
}

_NO_DEFECT_SUMMARY = "확인된 하자가 없습니다."

# 신뢰도가 낮은 항목이 있을 때 응답 `notes`에 붙는 안내. 모델의 한계를 판매자에게 드러내는
# 문구라, 설계 문서의 "모델이 못 하는 걸 잘하는 척하지 않는다"가 UI까지 이어지는 지점이다.
_REVIEW_NOTE = "일부 항목은 모델 신뢰도가 낮아 판매자 확인이 필요합니다."
_SUSPECTED_NOTE = "의심 항목은 확정된 하자가 아닙니다 — 실물을 확인해 주세요."
_UNRELIABLE_NOTE = (
    "이미지 일부에서 검수 모델이 신뢰할 수 있는 결과를 내지 못했습니다 — "
    "조명·배경이 뚜렷한 사진으로 다시 시도해 주세요."
)


def penalty_of(finding: Finding) -> float:
    """항목 1건의 감점. `유형 가중치 × severity 계수 × status 계수`."""
    return (
        registry.defect_policy(finding.defect_type)["weight"]
        * registry.SEVERITY_FACTORS[finding.severity]
        * registry.STATUS_FACTORS[finding.status]
    )


def grade_for(score: float) -> ConditionGrade:
    """점수를 등급으로. 어떤 하한에도 못 미치면 최하 등급이다."""
    for threshold, grade in registry.GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return ConditionGrade.c


def score_findings(findings: Sequence[Finding]) -> tuple[float, ConditionGrade]:
    """`100 - Σ감점`, 하한 0. 하자가 없으면 100점 / 최고 등급이다.

    감점은 항목마다 **더해지기만** 하므로 하자가 늘면 점수는 반드시 내려간다(단조성).
    """
    penalty = sum(penalty_of(finding) for finding in findings)
    score = round(max(0.0, MAX_SCORE - penalty), 1)
    return score, grade_for(score)


def _counts_by_label(findings: Sequence[Finding], status: FindingStatus) -> list[str]:
    """해당 상태의 항목을 유형별로 세어 "오염 2건" 같은 조각으로 만든다.

    나열 순서는 감점 가중치 내림차순 — 판매자에게 중요한 하자가 먼저 보여야 한다.
    """
    counts = Counter(f.defect_type for f in findings if f.status is status)
    ordered = sorted(
        counts.items(),
        key=lambda item: (-registry.defect_policy(item[0])["weight"], item[0].value),
    )
    # 라벨이 빠진 새 유형이 들어와도 500으로 죽지 않고 enum 값으로 대신 표시한다.
    return [
        f"{DEFECT_LABELS.get(defect_type, defect_type.value)} {count}건"
        for defect_type, count in ordered
    ]


def summarize(findings: Sequence[Finding]) -> str:
    """판매자·구매자에게 보여줄 한 줄 요약.

    확정(`DETECTED`)과 의심(`SUSPECTED`)을 **문장에서부터 구분한다** — 둘을 뭉뚱그려 "3건
    발견"이라고 쓰면 모델이 확신하지 못하는 항목까지 확정처럼 읽힌다.
    """
    if not findings:
        return _NO_DEFECT_SUMMARY

    detected = _counts_by_label(findings, FindingStatus.detected)
    suspected = _counts_by_label(findings, FindingStatus.suspected)

    parts = []
    if detected:
        parts.append(f"{', '.join(detected)}이 확인되었습니다.")
    if suspected:
        prefix = "추가로 " if detected else ""
        parts.append(f"{prefix}{', '.join(suspected)}이 의심됩니다.")
    return " ".join(parts)


def build_notes(findings: Sequence[Finding], unreliable_prompts: Sequence[str] = ()) -> list[str]:
    """모델 한계에서 비롯된 안내 문구. 해당 사유가 없으면 빈 리스트다.

    `unreliable_prompts`(과포화로 건너뛴 프롬프트)를 반드시 드러낸다 — 조용히 넘기면
    "하자 없음"과 "판정 실패"가 응답에서 구별되지 않는다.
    """
    notes = []
    if any(f.needs_seller_review for f in findings):
        notes.append(_REVIEW_NOTE)
    if any(f.status is FindingStatus.suspected for f in findings):
        notes.append(_SUSPECTED_NOTE)
    if unreliable_prompts:
        notes.append(_UNRELIABLE_NOTE)
    return notes
