"""하자 항목 → 컨디션 점수·등급·요약문 (SAM3 백엔드용).

이 모듈은 `Finding`/`FindingStatus`/`DefectType`만 갖고 순수 집계하므로 어느 세그멘터가
findings를 뽑았는지와 무관하다(백엔드 비종속) — "같은 하자는 어느 모델이 찾았든 같은 점수"라는
정책 일관성이 이 구조에서 나온다.

⚠️ **가중치·구간 경계는 근거 없는 임의값이다.** `registry.py`에 상수로 노출해 두고 확정은
검증셋 확보 이후의 별도 작업으로 미룬다. 이 모듈이 고정하는 건 값이 아니라 **구조**다.

설계: `.claude/plans/ai/CH006-sam3-quality-segmenter.md`
"""

from __future__ import annotations

from collections.abc import Sequence

from . import registry
from .contracts import ConditionGrade, DefectType, Finding, FindingStatus, ImageSummary
from .prompts import SECTION_LABELS_KO

MAX_SCORE = 100.0

# 요약문·Finding.label 에 쓰는 한국어 라벨.
DEFECT_LABELS: dict[DefectType, str] = {
    DefectType.stain: "오염",
    DefectType.dirt_mark: "얼룩",
    DefectType.hole_tear: "구멍·찢어짐",
    DefectType.discoloration: "변색",
    DefectType.pilling: "보풀",
    DefectType.fray: "올풀림",
}

_NO_DEFECT_SUMMARY = "확인된 하자가 없습니다."

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


def _finding_line(finding: Finding, display_no: int) -> str:
    """항목 1건 = 넘버링 리스트 한 줄. `{번호}. {부위} {태그}` + (설명) + (의심 표기).

    번호는 `Finding.no`(CH007)를 우선 쓴다 — `annotated_images`의 bbox 숫자와 정확히
    일치해야 사용자가 이미지와 리스트를 매칭할 수 있다. `no`가 없는(레거시/미채움) 백엔드는
    표시 전용 임시 번호(`display_no`)로 대체한다 — `Finding.no` 필드 자체는 건드리지 않는다.
    """
    no = finding.no if finding.no is not None else display_no
    section = SECTION_LABELS_KO.get(finding.section, finding.section.value)
    label = DEFECT_LABELS.get(finding.defect_type, finding.defect_type.value)
    line = f"{no}. {section} {label}"
    if finding.description:
        line += f" — {finding.description}"
    if finding.status is FindingStatus.suspected:
        line += " (의심)"
    return line


def summarize(findings: Sequence[Finding]) -> str:
    """판매자·구매자에게 보여줄 요약 — 이미지별 넘버링 리스트.

    항목별로 부위·태그를 펼쳐 쓰므로(유형별 개수 집계가 아니다) 위치를 알 수 있고,
    `Finding.description`(sVLM, CH011)이 채워져 있으면 그대로 이어 붙인다. `no`는
    `annotated_images`(CH007)의 bbox 숫자와 같은 값이라 이미지-리스트 매칭에 쓸 수 있다.
    """
    if not findings:
        return _NO_DEFECT_SUMMARY

    by_image: dict[int, list[Finding]] = {}
    for finding in findings:
        by_image.setdefault(finding.image_index, []).append(finding)

    multi_image = len(by_image) > 1
    blocks: list[str] = []
    for image_index in sorted(by_image):
        lines = [
            _finding_line(finding, display_no)
            for display_no, finding in enumerate(by_image[image_index], start=1)
        ]
        block = "\n".join(lines)
        if multi_image:
            block = f"[이미지 {image_index + 1}]\n{block}"
        blocks.append(block)

    return "\n\n".join(blocks)


def summarize_by_image(findings: Sequence[Finding], image_count: int) -> list[ImageSummary]:
    """이미지별 한 줄 요약(CH020). 하자가 없는 이미지도 "확인된 하자가 없습니다"로 채운다.

    `image_count`를 따로 받는 이유: findings에 안 나타나는 이미지(하자 0건인 뒷면 등)도
    빠짐없이 요약을 내야 캐러셀에서 이미지 개수와 요약 개수가 어긋나지 않는다.
    """
    return [
        ImageSummary(
            image_index=image_index,
            summary=summarize([f for f in findings if f.image_index == image_index]),
        )
        for image_index in range(image_count)
    ]


def build_notes(findings: Sequence[Finding], unreliable_prompts: Sequence[str] = ()) -> list[str]:
    """모델 한계에서 비롯된 안내 문구. 해당 사유가 없으면 빈 리스트다."""
    notes = []
    if any(f.needs_seller_review for f in findings):
        notes.append(_REVIEW_NOTE)
    if any(f.status is FindingStatus.suspected for f in findings):
        notes.append(_SUSPECTED_NOTE)
    if unreliable_prompts:
        notes.append(_UNRELIABLE_NOTE)
    return notes
