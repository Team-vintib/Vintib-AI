"""SAM3 인스턴스 → 판매자가 소명할 수 있는 하자 항목 리스트 (네이티브 경로).

CLIPSeg 쪽(`worker/models/clipseg/findings.py`)과 근본적으로 다른 점: **확률 히트맵을
이진화·flood-fill 하지 않는다.** SAM3가 이미 인스턴스(마스크+박스+score)를 직접 주므로,
`segmenter.py`가 낸 `Instance`를 그대로 `Finding`으로 승격한다 — 정규화(`normalize_mask`)/
3×3 풀링(연속값 기준)/blob 추출이 전부 없고, 섹션 번호만 마스크 무게중심으로 계산한다.

이게 이 계획 문서가 "방식 B(네이티브 경로)"라고 부른 것의 실체다 — SAM3의 장점(이미 분리된
정밀 인스턴스)을 그대로 살리고, CLIPSeg 전용 개념(clean 대조, 이진화 임계치)을 억지로
끼워 맞추지 않는다.

대신 인스턴스 레벨 필터 두 가지가 CLIPSeg의 이진화·병합 자리를 대신한다.

⑴ **의류 겹침 필터** — `segmenter.py`가 이미 마스킹 전처리로 배경을 지웠지만, 크롭 bbox
여백·마스크 경계 반올림 때문에 일부 인스턴스가 여전히 의류 밖에 걸칠 수 있어 사후 안전망으로
한 번 더 확인한다(clipseg의 `filter_by_garment`와 같은 원칙 — 의류를 못 찾았으면 필터
자체를 건너뛴다).

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
from .prompts import SECTION_COUNT, SECTION_GRID, STRUCTURAL_BENIGN_PROMPTS, PromptSet, section_label
from .registry import SegmenterConfig
from .segmenter import Instance, SegmentationResult


@dataclass(frozen=True)
class FindingsResult:
    """`extract_findings`의 산출물.

    `unreliable_prompts`는 CLIPSeg 쪽과 필드 모양을 맞추기 위해 남겨 뒀지만 SAM3 네이티브
    경로에서는 항상 빈 튜플이다 — 과포화 인스턴스는 `segmenter.py`가 개별적으로 걸러서 로그만
    남기고(프롬프트 단위 마스크 전체가 과포화되는 CLIPSeg와 달리 인스턴스 단위라 "이 프롬프트
    전체를 못 믿는다"는 개념 자체가 성립하지 않는다), BE에 별도로 드러낼 근거가 약하다.

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
    """LAB-12/LAB-46 실측을 반영한 강등 규칙. clipseg의 `_status_of`와 같은 규칙이다."""
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
    """섹션별 최대 confidence 9개. CLIPSeg의 `_section_peaks`(연속 마스크 풀링)와 같은 목적을
    인스턴스 confidence의 섹션별 최댓값으로 달성한다."""
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
    """(image_index, Instance) 쌍을 `Finding`으로 승격하고 **안정 키**를 매긴다.

    키는 BE가 판매자 소명을 매다는 앵커라서 결정적이어야 한다 — 정렬을 먼저 고정하고
    `{유형}_{이미지}_{섹션}_{순번}`으로 번호를 매긴다(clipseg와 같은 키 형식).
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
    for image_index, inst, section_no, area_ratio in ordered:
        slot = (inst.defect_type, image_index, section_no)
        ordinals[slot] = ordinals.get(slot, 0) + 1

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
            )
        )
    return findings


def extract_findings(
    results: Sequence[SegmentationResult],
    prompt_set: PromptSet,
    config: SegmenterConfig,
) -> FindingsResult:
    """인스턴스들 → 하자 항목 리스트 + 부위별 확률 9개.

    이미지별로 ⑴ 의류 겹침 필터 ⑵ 양성 억제를 거친 뒤 `Finding`으로 승격한다. CLIPSeg 경로의
    이진화·flood-fill·프롬프트 간 병합이 없다 — SAM3 인스턴스는 이미 분리돼 있어 병합 대상이
    원천적으로 적다(동일 영역에 여러 프롬프트가 동시에 반응할 가능성 자체가 없어지는 건
    아니라서, 실측에서 중복 검출이 관찰되면 후속 작업으로 병합 로직을 추가한다).
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
