"""확률 마스크 → 판매자가 소명할 수 있는 하자 항목 리스트.

**이 모듈이 설계의 핵심이다.** LAB-12는 "확률 마스크는 나오는데 그 다음이 없다"에서 멈춰 있었고,
여기가 그 다음이다. 마스크라는 연속적인 히트맵을 "3번 부위에 오염 1건, 확률 0.81, 소명 대상"
같은 **셀 수 있는 항목**으로 바꾼다.

LAB-30의 요구("각 부위 넘버링(분류) / 확률값", "컨벌루션해서 섹션 특정")를 **두 축으로 나눠**
구현한다.

- **축 1 — 섹션 넘버링**(사람이 읽는 위치): 마스크를 3×3으로 나눠 섹션별 확률을 집계한다.
  별도 컨볼루션 층을 학습시키지 않고 **풀링으로 같은 목적을 달성**한다 — 프로토타입에 학습
  단계를 넣지 않기 위한 선택이며, 나중에 학습형 헤드로 바꿔도 출력 스키마는 그대로다.
- **축 2 — blob 추출**(개별 하자 1건): 이진화 후 4-연결 연결요소를 뽑아 각각을 finding 1건으로
  만든다. 순수 numpy + 파이썬 큐라 **scipy 없이** 돌아간다.

**`clean` 대조 정규화가 왜 필요한가**: LAB-12에서 WinCLIP이 프린트·솔기·단추 같은 정상 복잡
영역을 손상으로 오인했다. CLIPSeg 프롬프트에도 `"clean fabric"`이 이미 들어 있었는데 검증
스크립트는 이를 **표시만 하고 활용하지 않았다.** 감산항으로 쓰면 정상 텍스처가 상쇄된다.
세기는 백엔드별 `clean_margin`으로, 0이면 정규화 없음과 동일하다.

**모델이 못 하는 걸 잘하는 척하지 않는다**: LAB-12에서 약점이 확인됐거나 미검증인 유형은
확률이 아무리 높아도 `SUSPECTED`로만 나간다(`registry.DEFECT_TAXONOMY`). 확률이 두 임계치
사이인 미세 오염도 마찬가지다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from app.quality import registry
from app.quality.prompts import SECTION_COUNT, SECTION_GRID, PromptSet, section_label
from app.quality.registry import SegmenterConfig
from app.quality.schemas import DefectType, Finding, FindingStatus, SectionScore, Severity
from app.quality.segmenter import SegmentationResult

# 서로 다른 프롬프트가 같은 하자를 잡았다고 볼 기준.
#
# 실제 CLIPSeg는 하나의 오염에 "a stain on ..."과 "a dirty mark ..."가 함께 반응한다. 병합하지
# 않으면 하자 1건이 항목 6건으로 부풀어 판매자가 같은 자국을 여섯 번 소명하게 된다.
#
# 두 기준을 OR로 쓴다. IoU만 쓰면 **한 blob이 다른 blob에 완전히 포함되는데 크기 차가 큰 경우**
# (확률이 높은 프롬프트일수록 임계치를 넘는 영역이 넓다)를 놓친다 — 포함률 기준이 그걸 잡는다.
BLOB_MERGE_IOU = 0.3
BLOB_MERGE_CONTAINMENT = 0.6

# 4-연결(상하좌우) 이웃. 대각선을 연결로 치지 않아, 모서리만 닿은 두 얼룩은 별개 항목이 된다.
_NEIGHBORS = ((-1, 0), (1, 0), (0, -1), (0, 1))

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _RawBlob:
    """마스크 하나에서 뽑은 연결요소. 아직 어떤 프롬프트/이미지인지 모르는 순수 기하 정보."""

    peak: float
    area_ratio: float
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2) 정규화
    section_no: int


@dataclass(frozen=True)
class _Blob:
    """출처(이미지·프롬프트)가 붙은 연결요소. `Finding`으로 승격되기 전의 중간 표현."""

    image_index: int
    defect_type: DefectType
    prompt: str
    peak: float
    area_ratio: float
    bbox: tuple[float, float, float, float]
    section_no: int


@dataclass(frozen=True)
class FindingsResult:
    """`extract_findings`의 산출물.

    `unreliable_prompts`는 마스크가 과포화돼 blob 추출을 건너뛴 프롬프트다. 조용히 버리면
    "하자 없음"과 구별되지 않으므로 밖으로 드러내 응답 notes에 싣는다.
    """

    findings: list[Finding]
    section_scores: list[SectionScore]
    unreliable_prompts: tuple[str, ...] = ()


def normalize_mask(defect: np.ndarray, clean: np.ndarray, clean_margin: float) -> np.ndarray:
    """`clean` 대조 정규화: `clip(p_defect - clean_margin * p_clean, 0, 1)`.

    `clean_margin`이 0이면 원본 마스크를 그대로 돌려주는 것과 같다(정규화 없음).
    """
    if clean_margin <= 0.0:
        return np.clip(defect, 0.0, 1.0).astype(np.float32)
    return np.clip(defect - clean_margin * clean, 0.0, 1.0).astype(np.float32)


# --- 축 1: 3×3 섹션 집계 ---------------------------------------------------


def _section_bounds(length: int) -> list[int]:
    """길이를 3등분하는 경계. 나누어떨어지지 않아도 모든 픽셀이 정확히 한 섹션에 속한다."""
    return [round(i * length / SECTION_GRID) for i in range(SECTION_GRID + 1)]


def _section_no_at(x: float, y: float) -> int:
    """정규화 좌표(0~1)가 속한 섹션 번호(1~9, 행 우선)."""
    col = min(int(x * SECTION_GRID), SECTION_GRID - 1)
    row = min(int(y * SECTION_GRID), SECTION_GRID - 1)
    return row * SECTION_GRID + col + 1


def _section_peaks(mask: np.ndarray) -> list[float]:
    """섹션별 최대 확률 9개. 최댓값을 쓰는 이유는 작은 하자가 평균에 묻히면 안 되기 때문이다."""
    height, width = mask.shape
    rows, cols = _section_bounds(height), _section_bounds(width)
    return [
        float(mask[rows[r] : rows[r + 1], cols[c] : cols[c + 1]].max())
        for r in range(SECTION_GRID)
        for c in range(SECTION_GRID)
    ]


# --- 축 2: blob 추출 -------------------------------------------------------


def _extract_blobs(mask: np.ndarray, binary: np.ndarray, min_area_ratio: float) -> list[_RawBlob]:
    """4-연결 flood fill로 연결요소를 뽑는다.

    scipy 없이 순수 numpy + `deque`로 구현한다. 방문 후보를 `np.argwhere`로 미리 뽑아
    임계치를 넘은 픽셀만 순회하므로, 비용은 이미지 크기가 아니라 **하자 영역 크기**에 비례한다.
    과포화 마스크는 호출 전에 걸러진다(`registry.MAX_DEFECT_AREA_RATIO`).
    """
    coordinates = np.argwhere(binary)
    if coordinates.size == 0:
        return []

    height, width = mask.shape
    total_pixels = float(height * width)
    visited = np.zeros_like(binary)
    blobs = []

    for seed in coordinates:
        seed_row, seed_col = int(seed[0]), int(seed[1])
        if visited[seed_row, seed_col]:
            continue

        visited[seed_row, seed_col] = True
        queue = deque([(seed_row, seed_col)])
        count = 0
        row_min = row_max = seed_row
        col_min = col_max = seed_col
        row_sum = col_sum = 0
        peak = 0.0

        while queue:
            row, col = queue.popleft()
            count += 1
            row_sum += row
            col_sum += col
            row_min, row_max = min(row_min, row), max(row_max, row)
            col_min, col_max = min(col_min, col), max(col_max, col)
            peak = max(peak, float(mask[row, col]))

            for d_row, d_col in _NEIGHBORS:
                next_row, next_col = row + d_row, col + d_col
                if (
                    0 <= next_row < height
                    and 0 <= next_col < width
                    and binary[next_row, next_col]
                    and not visited[next_row, next_col]
                ):
                    visited[next_row, next_col] = True
                    queue.append((next_row, next_col))

        area_ratio = count / total_pixels
        if area_ratio < min_area_ratio:
            continue  # 노이즈로 생긴 점 몇 개는 하자가 아니다

        # 무게중심이 속한 섹션을 대표 부위로 삼는다(+0.5는 픽셀 인덱스 → 픽셀 중심 보정).
        section_no = _section_no_at(
            (col_sum / count + 0.5) / width,
            (row_sum / count + 0.5) / height,
        )
        blobs.append(
            _RawBlob(
                peak=peak,
                area_ratio=area_ratio,
                bbox=(
                    col_min / width,
                    row_min / height,
                    (col_max + 1) / width,
                    (row_max + 1) / height,
                ),
                section_no=section_no,
            )
        )

    return blobs


# --- 프롬프트 간 병합 ------------------------------------------------------


def _overlap(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, float]:
    """두 bbox의 (IoU, 작은 쪽 대비 포함률)."""
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0, 0.0

    intersection = (x2 - x1) * (y2 - y1)
    left_area = (left[2] - left[0]) * (left[3] - left[1])
    right_area = (right[2] - right[0]) * (right[3] - right[1])
    union = left_area + right_area - intersection
    smaller = min(left_area, right_area)
    return (
        intersection / union if union > 0.0 else 0.0,
        intersection / smaller if smaller > 0.0 else 0.0,
    )


def _is_same_defect(left: _Blob, right: _Blob) -> bool:
    iou, containment = _overlap(left.bbox, right.bbox)
    return iou >= BLOB_MERGE_IOU or containment >= BLOB_MERGE_CONTAINMENT


def _merge_across_prompts(blobs: Sequence[_Blob]) -> list[_Blob]:
    """겹치는 blob을 하나로 합친다. **가장 확률이 높은 프롬프트가 대표**가 된다.

    확률 내림차순으로 훑으면서 이미 채택된 blob과 겹치면 버린다 — 그 결과 남는 건 각 하자
    자리의 최고 확률 항목 하나뿐이고, 그 항목의 `defect_type`이 하자 유형이 된다.
    """
    accepted: list[_Blob] = []
    for blob in sorted(blobs, key=lambda b: (-b.peak, b.defect_type.value)):
        if any(_is_same_defect(blob, kept) for kept in accepted):
            continue
        accepted.append(blob)
    return accepted


# --- 항목 조립 -------------------------------------------------------------


def _severity_of(area_ratio: float, peak: float) -> Severity:
    """`area_ratio × peak`를 3구간으로. 넓고 진할수록 심각하다."""
    low, high = registry.SEVERITY_BOUNDS
    metric = area_ratio * peak
    if metric < low:
        return Severity.minor
    if metric < high:
        return Severity.moderate
    return Severity.major


def _status_of(defect_type: DefectType, peak: float, confident_threshold: float) -> FindingStatus:
    """LAB-12 실측을 반영한 강등 규칙.

    ⑴ 신뢰할 수 없는 유형(찢어짐·미검증 프롬프트)은 확률과 무관하게 `SUSPECTED`.
    ⑵ 신뢰 유형이라도 확률이 `confident_threshold` 미만이면 `SUSPECTED`
       — LAB-12의 "미세 오염은 탐지되나 뚜렷하지 않음"에 대응한다.
    """
    if not registry.defect_policy(defect_type)["trusted"]:
        return FindingStatus.suspected
    return FindingStatus.detected if peak >= confident_threshold else FindingStatus.suspected


def _statement_required(defect_type: DefectType, status: FindingStatus, severity: Severity) -> bool:
    """소명 입력 대상인지. 경미하면서 확신도 낮은 항목은 면제한다(판매자 입력 부담)."""
    if not registry.defect_policy(defect_type)["statement_required"]:
        return False
    exempt = (
        registry.EXEMPT_MINOR_SUSPECTED_FROM_STATEMENT
        and status is FindingStatus.suspected
        and severity is Severity.minor
    )
    return not exempt


def _to_findings(blobs: Sequence[_Blob], prompt_set: PromptSet, confident: float) -> list[Finding]:
    """blob을 `Finding`으로 승격하고 **안정 키**를 매긴다.

    키는 BE가 판매자 소명을 매다는 앵커라서 결정적이어야 한다. 정렬을 먼저 고정하고
    `{유형}_{이미지}_{섹션}_{순번}` 으로 번호를 매긴다 — 같은 입력이면 항상 같은 키가 나온다.
    """
    ordered = sorted(
        blobs,
        key=lambda b: (b.image_index, b.section_no, -b.peak, b.defect_type.value),
    )

    findings: list[Finding] = []
    ordinals: dict[tuple[DefectType, int, int], int] = {}
    for blob in ordered:
        slot = (blob.defect_type, blob.image_index, blob.section_no)
        ordinals[slot] = ordinals.get(slot, 0) + 1

        severity = _severity_of(blob.area_ratio, blob.peak)
        status = _status_of(blob.defect_type, blob.peak, confident)
        findings.append(
            Finding(
                key=f"{blob.defect_type.value.lower()}_{blob.image_index}"
                f"_{blob.section_no}_{ordinals[slot]}",
                defect_type=blob.defect_type,
                status=status,
                image_index=blob.image_index,
                section_no=blob.section_no,
                section=section_label(prompt_set.category, blob.section_no),
                confidence=round(blob.peak, 4),
                area_ratio=round(blob.area_ratio, 6),
                bbox=tuple(round(value, 4) for value in blob.bbox),
                severity=severity,
                matched_prompt=blob.prompt,
                statement_required=_statement_required(blob.defect_type, status, severity),
                needs_seller_review=registry.defect_policy(blob.defect_type)["needs_seller_review"],
            )
        )
    return findings


def extract_findings(
    results: Sequence[SegmentationResult],
    prompt_set: PromptSet,
    config: SegmenterConfig,
) -> FindingsResult:
    """확률 마스크들 → 하자 항목 리스트 + 부위별 확률 9개.

    부위별 확률은 **이미지 전체에 걸쳐 최댓값**으로 모은다 — 앞뒤 사진 중 한 장에서만 보이는
    가슴 오염도 "가슴 부위 확률"로 잡혀야 하기 때문이다. 과포화 마스크도 부위 확률에는
    반영한다(그 부위가 강하게 반응한 건 사실이므로), 항목만 만들지 않는다.
    """
    clean_margin = config["clean_margin"]
    defect_threshold = config["defect_threshold"]
    min_area_ratio = config["min_area_ratio"]

    blobs: list[_Blob] = []
    section_peaks = [0.0] * SECTION_COUNT
    unreliable: list[str] = []

    for result in results:
        per_image: list[_Blob] = []
        for prompt, defect_type in prompt_set.defect_prompts:
            mask = result.masks.get(prompt)
            if mask is None:  # pragma: no cover - 세그멘터가 프롬프트를 빠뜨린 경우 방어
                continue

            normalized = normalize_mask(mask, result.clean_mask, clean_margin)
            section_peaks = [
                max(existing, peak)
                for existing, peak in zip(section_peaks, _section_peaks(normalized), strict=True)
            ]

            binary = normalized >= defect_threshold
            if float(binary.mean()) > registry.MAX_DEFECT_AREA_RATIO:
                # 옷 전체가 하자일 리 없다 — 세그멘테이션 실패로 보고 항목을 만들지 않는다.
                logger.warning(
                    "마스크 과포화로 blob 추출을 건너뜁니다 (image=%d, prompt=%r, ratio=%.2f)",
                    result.image_index,
                    prompt,
                    float(binary.mean()),
                )
                if prompt not in unreliable:
                    unreliable.append(prompt)
                continue

            per_image.extend(
                _Blob(
                    image_index=result.image_index,
                    defect_type=defect_type,
                    prompt=prompt,
                    peak=raw.peak,
                    area_ratio=raw.area_ratio,
                    bbox=raw.bbox,
                    section_no=raw.section_no,
                )
                for raw in _extract_blobs(normalized, binary, min_area_ratio)
            )

        # 병합은 **이미지 안에서만** 한다. 앞뒤 사진의 같은 좌표는 다른 부위다.
        blobs.extend(_merge_across_prompts(per_image))

    section_scores = [
        SectionScore(
            section_no=section_no,
            section=section_label(prompt_set.category, section_no),
            score=round(peak, 4),
        )
        for section_no, peak in enumerate(section_peaks, start=1)
    ]
    return FindingsResult(
        findings=_to_findings(blobs, prompt_set, config["confident_threshold"]),
        section_scores=section_scores,
        unreliable_prompts=tuple(unreliable),
    )
