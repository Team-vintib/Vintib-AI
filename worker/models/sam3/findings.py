"""SAM3 인스턴스 → 판매자가 소명할 수 있는 하자 항목 리스트 (네이티브 경로).

**확률 히트맵을 이진화·flood-fill 하지 않는다.** SAM3가 이미 인스턴스(마스크+박스+score)를
직접 주므로, `segmenter.py`가 낸 `Instance`를 그대로 `Finding`으로 승격한다 — 정규화
(`normalize_mask`)/3×3 풀링(연속값 기준)/blob 추출이 전부 없고, 섹션 번호만 마스크 무게중심으로
계산한다. 이게 이 계획 문서가 "방식 B(네이티브 경로)"라고 부른 것의 실체다 — SAM3의 장점(이미
분리된 정밀 인스턴스)을 그대로 살리고, 확률 히트맵 전용 개념(clean 대조, 이진화 임계치)을
억지로 끼워 맞추지 않는다.

대신 인스턴스 레벨 필터 두 가지가 그 이진화·병합 자리를 대신한다.

⑴ **의류 겹침 필터** — `segmenter.py`가 이미 마스킹 전처리로 배경을 지웠지만, 크롭 bbox
여백·마스크 경계 반올림 때문에 일부 인스턴스가 여전히 의류 밖에 걸칠 수 있어 사후 안전망으로
한 번 더 확인한다(의류를 못 찾았으면 필터 자체를 건너뛴다).

⑵ **양성(benign) 억제** — 구조적 개구부(암홀·넥라인·밑단·소매끝)는 겹치면 무조건 억제하고,
질감형(주름·접힘·그림자·솔기·프린트)은 겹치고 + confidence가 하자보다 높을 때만 억제한다.
`AI/validation/QUAL/qc_shared.py`의 `suppress_benign()`을 그대로 이식했다 — LAB-46이 실측한
"SAM3의 hole_tear 오탐이 암홀·넥라인·밑단·소매끝에서 반복된다"는 문제에 대한 직접 대응이다.

설계: `.claude/plans/ai/CH006-sam3-quality-segmenter.md`
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from . import registry
from .contracts import Finding, FindingStatus, SectionScore, Severity
from .prompts import (
    SECTION_COUNT,
    SECTION_GRID,
    STRUCTURAL_BENIGN_PROMPTS,
    PromptSet,
    section_label,
)
from .registry import SegmenterConfig
from .scoring import DEFECT_LABELS
from .segmenter import Instance, SegmentationResult


@dataclass(frozen=True)
class FindingsResult:
    """`extract_findings`의 산출물.

    `unreliable_prompts`는 게이트웨이 계약과 필드 모양을 맞추기 위해 남겨 뒀지만 SAM3 네이티브
    경로에서는 항상 빈 튜플이다 — 과포화 인스턴스는 `segmenter.py`가 개별적으로 걸러서 로그만
    남긴다(SAM3는 인스턴스 단위라 "이 프롬프트 전체를 못 믿는다"는 개념 자체가 성립하지
    않는다), BE에 별도로 드러낼 근거가 약하다.

    `kept_instances_by_image`는 의류 겹침 필터·양성 억제를 **통과한** 인스턴스만 담는다 —
    `overlay.py`가 이 값을 그대로 써야 한다. `SegmentationResult.instances`(원본, 필터 전)를
    쓰면 억제됐어야 할 인스턴스까지 Attention Map에 그려지는 불일치가 생긴다.
    """

    findings: list[Finding]
    section_scores: list[SectionScore]
    kept_instances_by_image: dict[int, tuple[Instance, ...]]
    unreliable_prompts: tuple[str, ...] = ()


def _containment(a: np.ndarray, b: np.ndarray) -> float:
    """|a ∩ b| / |a| — a가 b 안에 얼마나 잠겨 있는가. a가 비면 0."""
    a_bool = a.astype(bool)
    area = int(a_bool.sum())
    if area == 0:
        return 0.0
    return float(np.logical_and(a_bool, b.astype(bool)).sum() / area)


def _mask_iou(a: np.ndarray, b: np.ndarray) -> float:
    """|a ∩ b| / |a ∪ b| — 대칭 겹침 비율. 둘 다 비면 0.

    `_containment`(비대칭, "a가 b에 얼마나 잠겼는가")와 달리, 두 마스크가 **같은 대상을
    가리키는지** 볼 때는 대칭 비교가 맞다 — `dedupe_cross_type_overlap`이 이걸 쓴다.
    `AI/validation/QUAL/qc_shared.py`의 `mask_iou()`와 같은 계산이지만, 프로덕션은
    validation을 import하지 않으므로(레포 규율) 로컬 사본을 둔다 — `_containment`도
    이미 같은 이유로 중복돼 있다.
    """
    a_bool, b_bool = a.astype(bool), b.astype(bool)
    union = int(np.logical_or(a_bool, b_bool).sum())
    if union == 0:
        return 0.0
    return float(np.logical_and(a_bool, b_bool).sum() / union)


def _section_no_of(mask: np.ndarray) -> int:
    """마스크 무게중심이 속한 3×3 섹션 번호(1~9, 행 우선). 마스크가 비면 1(방어적 기본값)."""
    rows_idx, cols_idx = np.nonzero(mask)
    if rows_idx.size == 0:
        return 1
    height, width = mask.shape
    cy = (float(rows_idx.mean()) + 0.5) / height
    cx = (float(cols_idx.mean()) + 0.5) / width
    col = min(int(cx * SECTION_GRID), SECTION_GRID - 1)
    row = min(int(cy * SECTION_GRID), SECTION_GRID - 1)
    return row * SECTION_GRID + col + 1


def filter_by_garment(
    instances: Sequence[Instance],
    garment_mask: np.ndarray | None,
    min_overlap: float,
) -> tuple[list[Instance], list[Instance]]:
    """의류 영역 밖의 인스턴스를 떨어뜨린다. (kept, dropped) 반환.

    `garment_mask`가 `None`이면(의류를 못 찾음) **아무것도 거르지 않는다** — 의류 탐지가
    실패했는데 전부 버리면 "하자 없음"과 "판정 실패"가 구별되지 않는다.
    """
    if garment_mask is None:
        return list(instances), []
    kept: list[Instance] = []
    dropped: list[Instance] = []
    for inst in instances:
        (kept if _containment(inst.mask, garment_mask) >= min_overlap else dropped).append(inst)
    return kept, dropped


def suppress_benign(
    defects: Sequence[Instance],
    benigns: Sequence[Instance],
    min_containment: float,
    structural_prompts: frozenset[str] = frozenset(STRUCTURAL_BENIGN_PROMPTS),
) -> tuple[list[Instance], list[Instance]]:
    """정상 영역에 잠긴 하자 인스턴스를 억제한다. (kept, dropped) 반환.

    - **구조적 개구부**(`structural_prompts`): 겹치기만 하면(`min_containment` 이상)
      confidence 비교 없이 곧바로 억제한다. 실제 손상이 정확히 그 구조물 자체와 같은 모양·
      위치일 수는 없으니, 겹침 자체가 "이건 그 구조물이다"의 충분한 증거다.
    - **질감형**(그 외): 겹침 + 양성 쪽 confidence가 하자보다 높을 때만 억제한다 — 이 위에는
      실제 하자가 진짜로 생길 수 있어서(솔기 근처 실밥 뜯김 등), 확신이 더 강한 쪽을 믿는다.
    """
    kept: list[Instance] = []
    dropped: list[Instance] = []
    for defect in defects:
        hit = None
        for benign in benigns:
            structural = benign.prompt in structural_prompts
            if not structural and benign.confidence < defect.confidence:
                continue
            if _containment(defect.mask, benign.mask) >= min_containment:
                hit = benign
                break
        (dropped if hit is not None else kept).append(defect)
    return kept, dropped


def dedupe_cross_type_overlap(
    instances: Sequence[Instance], min_iou: float
) -> tuple[list[Instance], list[Instance]]:
    """서로 다른 defect_type이 같은 실물 부위를 중복 검출했을 때 병합한다. (kept, dropped) 반환.

    SAM3는 defect_type마다 독립된 프롬프트로 탐지한다("a dirty mark" vs "a hole or tear in
    fabric" 등, `prompts.py`). 같은 자리가 두 프롬프트 모두에 걸리면 defect_type만 다른
    Finding 2개가 생긴다 — 실측(scratch.jpg)에서 bbox가 1px 이내로 겹치는 DIRT_MARK/
    HOLE_TEAR 쌍 5개가 확인됐다. `suppress_benign()`은 이 케이스를 못 거른다(그건 별도
    benign 카테고리 전용이라 defect끼리는 비교하지 않는다).

    confidence 내림차순(동률이면 `defect_type.value`로 결정적 tie-break — `_to_findings()`가
    쓰는 정렬 키와 동일)으로 훑으며, **다른 타입**이면서 이미 kept에 들어간 인스턴스와
    `_mask_iou`가 `min_iou` 이상이면 버린다. 같은 타입끼리는 비교하지 않는다 — 같은
    프롬프트 안에서의 중복은 SAM3 자체 후처리가 이미 걸렀다고 본다.

    ⚠️ 알려진 단순화: 이미 kept된 것과만 비교하는 그리디라, IoU가 전이적이지 않은 경우
    (A-B 겹침, B-C 겹침, A-C는 안 겹침)를 이론상 놓칠 수 있다. 실측 중복은 IoU가 매우
    높아(거의 동일 bbox) 이 케이스가 실제로 발생할 가능성은 낮다고 보고 1차로는 이 방식을
    쓴다.
    """
    ordered = sorted(instances, key=lambda inst: (-inst.confidence, inst.defect_type.value))
    kept: list[Instance] = []
    dropped: list[Instance] = []
    for inst in ordered:
        hit = None
        for kept_inst in kept:
            if kept_inst.defect_type == inst.defect_type:
                continue
            if _mask_iou(inst.mask, kept_inst.mask) >= min_iou:
                hit = kept_inst
                break
        (dropped if hit is not None else kept).append(inst)
    return kept, dropped


def _severity_of(area_ratio: float, peak: float) -> Severity:
    """`area_ratio × peak`를 3구간으로. 넓고 확신할수록 심각하다."""
    low, high = registry.SEVERITY_BOUNDS
    metric = area_ratio * peak
    if metric < low:
        return Severity.minor
    if metric < high:
        return Severity.moderate
    return Severity.major


def _status_of(defect_type, peak: float, confident_threshold: float) -> FindingStatus:
    """LAB-12/LAB-46 실측을 반영한 강등 규칙."""
    if not registry.defect_policy(defect_type)["trusted"]:
        return FindingStatus.suspected
    return FindingStatus.detected if peak >= confident_threshold else FindingStatus.suspected


def _statement_required(defect_type, status: FindingStatus, severity: Severity) -> bool:
    """소명 입력 대상인지. 경미하면서 확신도 낮은 항목은 면제한다."""
    if not registry.defect_policy(defect_type)["statement_required"]:
        return False
    exempt = (
        registry.EXEMPT_MINOR_SUSPECTED_FROM_STATEMENT
        and status is FindingStatus.suspected
        and severity is Severity.minor
    )
    return not exempt


def _section_peaks_from(instances: Sequence[Instance]) -> list[float]:
    """섹션별 최대 confidence 9개. 인스턴스 confidence의 섹션별 최댓값으로 계산한다."""
    peaks = [0.0] * SECTION_COUNT
    for inst in instances:
        section_no = _section_no_of(inst.mask)
        peaks[section_no - 1] = max(peaks[section_no - 1], inst.confidence)
    return peaks


def _to_findings(
    instances: Sequence[tuple[int, Instance]],
    prompt_set: PromptSet,
    confident: float,
) -> list[Finding]:
    """(image_index, Instance) 쌍을 `Finding`으로 승격하고 **안정 키 + 표시 번호**를 매긴다.

    키는 BE가 판매자 소명을 매다는 앵커라서 결정적이어야 한다 — 정렬을 먼저 고정하고
    `{유형}_{이미지}_{섹션}_{순번}`으로 번호를 매긴다.

    `no`(CH007)는 별개다 — 같은 image_index 안에서 정렬 순서 그대로 1부터 매기는 **표시용**
    번호로, `overlay.py`의 넘버링 bbox 이미지가 그리는 숫자와 정확히 같은 값이어야 한다(같은
    정렬 기준을 재사용하는 이유). BE 소명 앵커(`key`)와 섞어 쓰지 않는다.
    """
    enriched = [
        (image_index, inst, _section_no_of(inst.mask), float(inst.mask.mean()))
        for image_index, inst in instances
    ]
    ordered = sorted(
        enriched,
        key=lambda row: (row[0], row[2], -row[1].confidence, row[1].defect_type.value),
    )

    findings: list[Finding] = []
    ordinals: dict[tuple, int] = {}
    display_no_by_image: dict[int, int] = {}
    for image_index, inst, section_no, area_ratio in ordered:
        slot = (inst.defect_type, image_index, section_no)
        ordinals[slot] = ordinals.get(slot, 0) + 1
        display_no_by_image[image_index] = display_no_by_image.get(image_index, 0) + 1

        severity = _severity_of(area_ratio, inst.confidence)
        status = _status_of(inst.defect_type, inst.confidence, confident)
        findings.append(
            Finding(
                key=f"{inst.defect_type.value.lower()}_{image_index}_{section_no}_{ordinals[slot]}",
                defect_type=inst.defect_type,
                status=status,
                image_index=image_index,
                section_no=section_no,
                section=section_label(prompt_set.category, section_no),
                confidence=round(inst.confidence, 4),
                area_ratio=round(area_ratio, 6),
                bbox=tuple(round(v, 4) for v in inst.bbox),
                severity=severity,
                matched_prompt=inst.prompt,
                statement_required=_statement_required(inst.defect_type, status, severity),
                needs_seller_review=registry.defect_policy(inst.defect_type)["needs_seller_review"],
                no=display_no_by_image[image_index],
                label=DEFECT_LABELS.get(inst.defect_type, inst.defect_type.value),
            )
        )
    return findings


def extract_findings(
    results: Sequence[SegmentationResult],
    prompt_set: PromptSet,
    config: SegmenterConfig,
) -> FindingsResult:
    """인스턴스들 → 하자 항목 리스트 + 부위별 확률 9개.

    이미지별로 ⑴ 의류 겹침 필터 ⑵ 양성 억제 ⑶ **cross-type 중복 병합**을 거친 뒤 `Finding`으로
    승격한다. SAM3 인스턴스는 defect_type별 독립 프롬프트로 나오다 보니 동일 영역이 여러
    프롬프트에 동시에 반응하는 경우가 실측(scratch.jpg)에서 확인됐다 — `dedupe_cross_type_overlap()`
    이 그 병합을 담당한다(설계: `.claude/plans/ai/CH010-sam3-cross-type-dedup.md`).
    """
    section_peaks = [0.0] * SECTION_COUNT
    kept_by_image: list[tuple[int, Instance]] = []
    kept_instances_by_image: dict[int, tuple[Instance, ...]] = {}

    for result in results:
        after_garment, _off_garment = filter_by_garment(
            result.instances, result.garment_mask, config["garment_overlap_min"]
        )
        if config["suppress_benign"]:
            final, _on_benign = suppress_benign(
                after_garment, result.benign_instances, config["benign_containment"]
            )
        else:
            final = after_garment

        # benign 억제 다음, 넘버링/누적 전 — 구조적 개구부 오탐(hole_tear)을 먼저 걷어내야
        # cross-type dedup이 "진짜 하자끼리의 중복"만 보게 된다.
        if config["dedupe_cross_type"]:
            final, _cross_type_dupes = dedupe_cross_type_overlap(
                final, config["cross_type_iou_min"]
            )

        section_peaks = [
            max(existing, peak)
            for existing, peak in zip(section_peaks, _section_peaks_from(final), strict=True)
        ]
        kept_by_image.extend((result.image_index, inst) for inst in final)
        kept_instances_by_image[result.image_index] = tuple(final)

    section_scores = [
        SectionScore(
            section_no=section_no,
            section=section_label(prompt_set.category, section_no),
            score=round(peak, 4),
        )
        for section_no, peak in enumerate(section_peaks, start=1)
    ]
    return FindingsResult(
        findings=_to_findings(kept_by_image, prompt_set, config["confident_threshold"]),
        section_scores=section_scores,
        kept_instances_by_image=kept_instances_by_image,
        unreliable_prompts=(),
    )
