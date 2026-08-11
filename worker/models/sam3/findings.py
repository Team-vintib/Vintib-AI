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
    instances: Sequence[Instance], min_iou: float, min_containment: float | None = None
) -> tuple[list[Instance], list[Instance]]:
    """서로 다른 defect_type이 같은 실물 부위를 중복 검출했을 때 하나로 합쳐 더 큰 박스로
    만든다. (merged, absorbed) 반환 — `absorbed`는 병합되며 사라진 인스턴스들이다.

    SAM3는 defect_type마다 독립된 프롬프트로 탐지한다("a dirty mark" vs "a hole or tear in
    fabric" 등, `prompts.py`). 같은 자리가 두 프롬프트 모두에 걸리면 defect_type만 다른
    Finding 2개가 생긴다 — 실측(scratch.jpg)에서 bbox가 1px 이내로 겹치는 DIRT_MARK/
    HOLE_TEAR 쌍 5개가 확인됐다. `suppress_benign()`은 이 케이스를 못 거른다(그건 별도
    benign 카테고리 전용이라 defect끼리는 비교하지 않는다).

    confidence 내림차순(동률이면 `defect_type.value`로 결정적 tie-break — `_to_findings()`가
    쓰는 정렬 키와 동일)으로 훑으며, **다른 타입**이면서 이미 merged에 들어간 인스턴스와
    같은 실물을 가리킨다고 판단되면 그 인스턴스에 흡수 병합한다(드롭하지 않는다). 같은
    타입끼리는 비교하지 않는다 — 같은 프롬프트 안에서의 중복은 SAM3 자체 후처리가 이미
    걸렀다고 본다.

    "같은 실물"의 판정 기준은 두 가지를 OR로 본다:
    - `_mask_iou`(대칭)가 `min_iou` 이상 — 거의 같은 크기·위치로 겹치는 전형적인 중복.
    - `min_containment`가 주어졌고, 두 마스크의 포함 비율(둘 중 큰 쪽)이 그 이상 — 크기가
      크게 다른 STAIN/DIRT_MARK 쌍(작은 쪽이 큰 쪽 안에 거의 다 들어감)은 IoU만으로는 못
      잡힌다(합집합 기준으로 계산해 낮게 나옴). hotfix/472: dirt_mark 프롬프트를 되살리며
      이 조건과 병합(merge) 방식을 추가했다 — 원래는 드롭만 했는데, 크기가 큰 쪽이 낮은
      confidence를 가진 채로 드롭당하면 실물 범위(큰 박스)가 사라지는 문제가 있었다.
      `merge_same_type_containment()`가 같은 문제를 같은 방식(비대칭 containment + 합집합
      병합)으로 푸는 것과 동일한 논리.

    ⚠️ 알려진 단순화: 이미 merged에 있는 것과만 비교하는 그리디라, 겹침 관계가 전이적이지
    않은 경우(A-B 겹침, B-C 겹침, A-C는 안 겹침)를 이론상 놓칠 수 있다. 실측 중복은 겹침이
    매우 높아 이 케이스가 실제로 발생할 가능성은 낮다고 보고 1차로는 이 방식을 쓴다.
    """
    ordered = sorted(instances, key=lambda inst: (-inst.confidence, inst.defect_type.value))
    merged: list[Instance] = []
    absorbed: list[Instance] = []
    for inst in ordered:
        hit_index = None
        for index, kept_inst in enumerate(merged):
            if kept_inst.defect_type == inst.defect_type:
                continue
            same_target = _mask_iou(inst.mask, kept_inst.mask) >= min_iou
            if not same_target and min_containment is not None:
                containment = max(
                    _containment(inst.mask, kept_inst.mask),
                    _containment(kept_inst.mask, inst.mask),
                )
                same_target = containment >= min_containment
            if same_target:
                hit_index = index
                break
        if hit_index is None:
            merged.append(inst)
        else:
            merged[hit_index] = _merge_instances(merged[hit_index], inst)
            absorbed.append(inst)
    return merged, absorbed


def _merge_instances(base: Instance, other: Instance) -> Instance:
    """같은 defect_type 인스턴스 둘을 하나로 합친다(CH034).

    `mask`는 두 마스크의 합집합(OR) — `_section_no_of()`(무게중심)·`area_ratio`
    (`inst.mask.mean()`)·attention map(`overlay.py::render_overlay`)이 전부 이 마스크를
    그대로 쓰므로, bbox만 키우고 mask를 안 합치면 셋이 서로 어긋난다. `bbox`는 정규화
    좌표라 mask 재계산 없이 좌표별 min/max로 바로 합집합을 구한다. `confidence`는 둘 중
    최댓값을 쓴다 — 병합은 "같은 실물 하자를 중복 탐지했다"는 뜻이므로, 더 확신했던 쪽의
    신뢰도를 그대로 쓰는 게 맞다(2026-08-09 결정). `defect_type`/`prompt`는 같은 타입이라
    `base`(더 높은 confidence) 것을 그대로 쓴다.
    """
    merged_mask = np.logical_or(base.mask, other.mask).astype(base.mask.dtype)
    bx1, by1, bx2, by2 = base.bbox
    ox1, oy1, ox2, oy2 = other.bbox
    merged_bbox = (min(bx1, ox1), min(by1, oy1), max(bx2, ox2), max(by2, oy2))
    return Instance(
        defect_type=base.defect_type,
        prompt=base.prompt,
        confidence=max(base.confidence, other.confidence),
        mask=merged_mask,
        bbox=merged_bbox,
    )


def merge_same_type_containment(
    instances: Sequence[Instance], min_containment: float
) -> tuple[list[Instance], list[Instance]]:
    """같은 defect_type 인스턴스가 "박스 안에 박스"로 겹칠 때 하나로 합쳐 더 큰 박스로
    만든다(CH034). (merged, absorbed) 반환 — `absorbed`는 병합되며 사라진 인스턴스들이다.

    `dedupe_cross_type_overlap()`은 **다른** defect_type끼리만 비교하고, 같은 타입끼리는
    "SAM3 자체 후처리가 이미 걸렀다"고 가정하고 의도적으로 건너뛴다(그 함수의 회귀 테스트
    `test_dedupe_cross_type_overlap_ignores_same_type_overlap`이 그 전제를 문서화한다).
    실측(small_pro.jpg)에서 그 전제가 깨지는 사례가 확인됐다 — 같은 STAIN 인스턴스 여러 개가
    서로 97~100% 포함되는 관계였다. 그래서 같은 타입 전용 병합 단계를 별도로 둔다.

    `dedupe_cross_type_overlap()`은 `_mask_iou`(대칭)를 쓰지만 여기는 `_containment`
    (비대칭)를 쓴다 — 두 박스 크기가 크게 다르면(작은 박스가 큰 박스 안에 거의 다 들어가는
    경우) 합집합 기준 IoU는 낮게 나와도 포함 비율은 매우 높다. 어느 쪽이 어느 쪽에 담겼는지
    모르니 양방향 포함 비율 중 큰 값을 쓴다.

    confidence 내림차순(동률이면 마스크 면적이 큰 쪽 우선 — 작은 중복 박스를 큰 박스 쪽으로
    흡수한다는 직관)으로 훑으며, **같은 타입**이면서 이미 merged에 들어간 인스턴스와의 포함
    비율이 `min_containment` 이상이면 그 인스턴스에 흡수 병합한다(드롭하지 않는다).

    ⚠️ 알려진 단순화: `dedupe_cross_type_overlap()`과 동일하게 이미 merged에 있는 것과만
    비교하는 그리디라 IoU/포함 비율이 전이적이지 않은 경우를 이론상 놓칠 수 있다. 실측 사례는
    포함 비율이 매우 높아(0.97 이상) 문제가 될 가능성은 낮다.
    """
    ordered = sorted(instances, key=lambda inst: (-inst.confidence, -float(inst.mask.sum())))
    merged: list[Instance] = []
    absorbed: list[Instance] = []
    for inst in ordered:
        hit_index = None
        for index, kept_inst in enumerate(merged):
            if kept_inst.defect_type != inst.defect_type:
                continue
            containment = max(
                _containment(inst.mask, kept_inst.mask),
                _containment(kept_inst.mask, inst.mask),
            )
            if containment >= min_containment:
                hit_index = index
                break
        if hit_index is None:
            merged.append(inst)
        else:
            merged[hit_index] = _merge_instances(merged[hit_index], inst)
            absorbed.append(inst)
    return merged, absorbed


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

    이미지별로 ⑴ 의류 겹침 필터 ⑵ 양성 억제 ⑶ **같은/다른 유형 중복 병합**을 거친 뒤
    `Finding`으로 승격한다. `merge_same_type_containment()`가 같은 defect_type의 "박스 안에
    박스" 중복을, `dedupe_cross_type_overlap()`이 서로 다른 defect_type의 중복(IoU 또는
    포함 비율 기준)을 각각 더 큰 박스 하나로 합친다(설계: `.claude/plans/ai/
    CH010-sam3-cross-type-dedup.md`). 둘 다 `config["dedupe_same_type"]`/
    `config["dedupe_cross_type"]`로 독립적으로 on/off된다.

    `section_scores`는 이미지마다 독립적으로 9개씩 낸다(CH020) — 예전에는 이미지 간 `max()`로
    섞어서 앞/뒤 같은 섹션 번호의 확률이 서로를 덮어썼다.
    """
    section_scores: list[SectionScore] = []
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
        # 이후 병합 단계가 "진짜 하자끼리의 중복"만 보게 된다. 같은 타입 포함 병합을
        # cross-type dedup(기본 꺼짐, CH034)보다 먼저 둔다 — 켜져 있을 경우에도 같은 타입
        # 중복을 먼저 줄여야 그쪽이 더 적은 후보로 깨끗하게 동작한다.
        if config["dedupe_same_type"]:
            final, _same_type_merged = merge_same_type_containment(
                final, config["same_type_containment_min"]
            )
        if config["dedupe_cross_type"]:
            final, _cross_type_merged = dedupe_cross_type_overlap(
                final, config["cross_type_iou_min"], config["cross_type_containment_min"]
            )

        section_scores.extend(
            SectionScore(
                image_index=result.image_index,
                section_no=section_no,
                section=section_label(prompt_set.category, section_no),
                score=round(peak, 4),
            )
            for section_no, peak in enumerate(_section_peaks_from(final), start=1)
        )
        kept_by_image.extend((result.image_index, inst) for inst in final)
        kept_instances_by_image[result.image_index] = tuple(final)

    return FindingsResult(
        findings=_to_findings(kept_by_image, prompt_set, config["confident_threshold"]),
        section_scores=section_scores,
        kept_instances_by_image=kept_instances_by_image,
        unreliable_prompts=(),
    )
