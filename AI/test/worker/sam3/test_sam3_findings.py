"""SAM3 네이티브 findings 추출 로직 검증 — CLIPSeg에는 없는 인스턴스 레벨 필터들.

`filter_by_garment`(의류 겹침 안전망)·`suppress_benign`(구조적/질감형 양성 억제)·
`_section_no_of`(마스크 무게중심 기반 3×3 섹션 매핑)는 SAM3 네이티브 경로(방식 B) 고유의
로직이라 clipseg 쪽에 대응 테스트가 없다. `extract_findings`가 필터 통과분만
`kept_instances_by_image`에 담는지(overlay.py가 의존하는 불변식)도 여기서 지킨다.
"""

import numpy as np
import pytest
from PIL import Image

from sam3.contracts import DefectType
from sam3.findings import (
    _section_no_of,
    extract_findings,
    filter_by_garment,
    suppress_benign,
)
from sam3.prompts import select_prompt_set
from sam3.contracts import BaseColor, GarmentCategory
from sam3.registry import segmenter_config
from sam3.scoring import DEFECT_LABELS
from sam3.segmenter import Instance, SegmentationResult

_SIZE = (9, 9)  # (height, width) — 3x3 그리드가 정확히 3px씩 떨어지도록


def _mask_at(row: int, col: int, size: tuple[int, int] = _SIZE) -> np.ndarray:
    mask = np.zeros(size, dtype=np.uint8)
    mask[row, col] = 1
    return mask


def _full_mask(size: tuple[int, int] = _SIZE) -> np.ndarray:
    return np.ones(size, dtype=np.uint8)


def _instance(
    defect_type,
    mask: np.ndarray,
    *,
    confidence: float = 0.9,
    prompt: str = "a stain on fabric",
) -> Instance:
    return Instance(
        defect_type=defect_type,
        prompt=prompt,
        confidence=confidence,
        mask=mask,
        bbox=(0.0, 0.0, 1.0, 1.0),
    )


# --- _section_no_of ----------------------------------------------------------


@pytest.mark.parametrize(
    ("row", "col", "expected_section"),
    [
        (1, 1, 1),  # 좌상단
        (1, 4, 2),  # 상단 중앙
        (1, 7, 3),  # 우상단
        (4, 1, 4),
        (4, 4, 5),  # 정중앙
        (4, 7, 6),
        (7, 1, 7),
        (7, 4, 8),
        (7, 7, 9),  # 우하단
    ],
)
def test_section_no_of_maps_centroid_to_the_right_grid_cell(row, col, expected_section):
    assert _section_no_of(_mask_at(row, col)) == expected_section


def test_section_no_of_empty_mask_defaults_to_1():
    assert _section_no_of(np.zeros(_SIZE, dtype=np.uint8)) == 1


# --- filter_by_garment --------------------------------------------------------


def test_filter_by_garment_keeps_instance_fully_inside_the_garment():
    inst = _instance(DefectType.stain, _mask_at(4, 4))
    kept, dropped = filter_by_garment([inst], _full_mask(), min_overlap=0.6)
    assert kept == [inst]
    assert dropped == []


def test_filter_by_garment_drops_instance_outside_the_garment():
    garment = np.zeros(_SIZE, dtype=np.uint8)
    garment[0:3, :] = 1  # 의류는 위쪽 1/3에만 존재
    inst = _instance(DefectType.stain, _mask_at(7, 7))  # 아래쪽, 의류 밖
    kept, dropped = filter_by_garment([inst], garment, min_overlap=0.6)
    assert kept == []
    assert dropped == [inst]


def test_filter_by_garment_skips_filtering_when_garment_mask_is_none():
    # 의류 탐지 실패 시 아무것도 버리지 않는다 — "하자 없음"과 "판정 실패"를 구별하기 위해서다.
    inst = _instance(DefectType.stain, _mask_at(7, 7))
    kept, dropped = filter_by_garment([inst], None, min_overlap=0.6)
    assert kept == [inst]
    assert dropped == []


def test_filter_by_garment_uses_containment_not_iou():
    # 인스턴스 마스크가 의류 마스크보다 훨씬 작아도(단일 픽셀) 의류 안이면 통과해야 한다.
    inst = _instance(DefectType.stain, _mask_at(4, 4))
    kept, _ = filter_by_garment([inst], _full_mask(), min_overlap=0.99)
    assert kept == [inst]


# --- suppress_benign -----------------------------------------------------------


def test_structural_benign_suppresses_regardless_of_confidence():
    # 구조적 개구부(넥라인 등)는 겹치기만 하면 confidence와 무관하게 억제한다.
    defect = _instance(DefectType.hole_tear, _mask_at(4, 4), confidence=0.95)
    benign = _instance(None, _mask_at(4, 4), confidence=0.10, prompt="a neckline")
    kept, dropped = suppress_benign([defect], [benign], min_containment=0.6)
    assert kept == []
    assert dropped == [defect]


def test_texture_benign_suppresses_only_when_more_confident_than_defect():
    defect = _instance(DefectType.stain, _mask_at(4, 4), confidence=0.50)
    benign = _instance(None, _mask_at(4, 4), confidence=0.90, prompt="a wrinkle on fabric")
    kept, dropped = suppress_benign([defect], [benign], min_containment=0.6)
    assert kept == []
    assert dropped == [defect]


def test_texture_benign_keeps_defect_when_defect_is_more_confident():
    defect = _instance(DefectType.stain, _mask_at(4, 4), confidence=0.90)
    benign = _instance(None, _mask_at(4, 4), confidence=0.50, prompt="a wrinkle on fabric")
    kept, dropped = suppress_benign([defect], [benign], min_containment=0.6)
    assert kept == [defect]
    assert dropped == []


def test_suppress_benign_keeps_defect_when_no_overlap():
    defect = _instance(DefectType.stain, _mask_at(1, 1), confidence=0.90)
    benign = _instance(None, _mask_at(7, 7), confidence=0.99, prompt="a wrinkle on fabric")
    kept, dropped = suppress_benign([defect], [benign], min_containment=0.6)
    assert kept == [defect]
    assert dropped == []


def test_suppress_benign_passes_through_when_no_benign_instances():
    defect = _instance(DefectType.stain, _mask_at(4, 4), confidence=0.90)
    kept, dropped = suppress_benign([defect], [], min_containment=0.6)
    assert kept == [defect]
    assert dropped == []


# --- extract_findings: kept_instances_by_image 불변식 -------------------------


def _segmentation_result(image_index, instances, benign_instances=(), garment_mask=None):
    return SegmentationResult(
        image_index=image_index,
        instances=tuple(instances),
        benign_instances=tuple(benign_instances),
        garment_mask=garment_mask,
        base_image=Image.new("RGB", (_SIZE[1], _SIZE[0])),
        size=_SIZE,
    )


def test_extract_findings_keeps_only_post_filter_instances_for_overlay():
    # overlay.py가 kept_instances_by_image만 렌더해야 한다 — 억제된 인스턴스가 여기 남으면
    # findings 리스트와 attention map이 어긋난다.
    survivor = _instance(DefectType.stain, _mask_at(4, 4), confidence=0.90)
    suppressed = _instance(DefectType.hole_tear, _mask_at(1, 1), confidence=0.95)
    benign = _instance(None, _mask_at(1, 1), confidence=0.10, prompt="a neckline")

    result = _segmentation_result(
        0, [survivor, suppressed], benign_instances=[benign], garment_mask=_full_mask()
    )
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    config = segmenter_config("mock")

    extracted = extract_findings([result], prompt_set, config)

    kept = extracted.kept_instances_by_image[0]
    assert survivor in kept
    assert suppressed not in kept
    assert {f.defect_type for f in extracted.findings} == {DefectType.stain}


def test_extract_findings_skips_benign_suppression_when_disabled():
    defect = _instance(DefectType.hole_tear, _mask_at(1, 1), confidence=0.95)
    benign = _instance(None, _mask_at(1, 1), confidence=0.99, prompt="a neckline")
    result = _segmentation_result(0, [defect], benign_instances=[benign], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    config = dict(segmenter_config("mock"))
    config["suppress_benign"] = False

    extracted = extract_findings([result], prompt_set, config)

    assert defect in extracted.kept_instances_by_image[0]
    assert len(extracted.findings) == 1


def test_extract_findings_unreliable_prompts_is_always_empty():
    # SAM3 네이티브 경로는 인스턴스 단위라 "프롬프트 전체를 못 믿는다"는 개념이 없다.
    result = _segmentation_result(0, [], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    extracted = extract_findings([result], prompt_set, segmenter_config("mock"))
    assert extracted.unreliable_prompts == ()


def test_extract_findings_produces_nine_section_scores():
    result = _segmentation_result(0, [], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    extracted = extract_findings([result], prompt_set, segmenter_config("mock"))
    assert len(extracted.section_scores) == 9
    assert [s.section_no for s in extracted.section_scores] == list(range(1, 10))


# --- CH007: Finding.no / Finding.label ----------------------------------------


def test_finding_no_starts_at_1_per_image_and_has_no_gaps():
    first = _instance(DefectType.stain, _mask_at(1, 1), confidence=0.9)
    second = _instance(DefectType.fray, _mask_at(7, 7), confidence=0.5)
    result = _segmentation_result(0, [first, second], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)

    extracted = extract_findings([result], prompt_set, segmenter_config("mock"))

    numbers = sorted(f.no for f in extracted.findings)
    assert numbers == list(range(1, len(extracted.findings) + 1))


def test_finding_no_resets_per_image():
    inst_image0 = _instance(DefectType.stain, _mask_at(1, 1), confidence=0.9)
    inst_image1 = _instance(DefectType.stain, _mask_at(1, 1), confidence=0.9)
    result0 = _segmentation_result(0, [inst_image0], garment_mask=_full_mask())
    result1 = _segmentation_result(1, [inst_image1], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)

    extracted = extract_findings([result0, result1], prompt_set, segmenter_config("mock"))

    by_image = {f.image_index: f.no for f in extracted.findings}
    assert by_image[0] == 1
    assert by_image[1] == 1  # 새 이미지라 다시 1부터


def test_finding_label_uses_the_korean_defect_label():
    inst = _instance(DefectType.stain, _mask_at(4, 4), confidence=0.9)
    result = _segmentation_result(0, [inst], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)

    extracted = extract_findings([result], prompt_set, segmenter_config("mock"))

    assert extracted.findings[0].label == DEFECT_LABELS[DefectType.stain]
