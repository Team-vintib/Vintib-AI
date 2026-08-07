"""SAM3 네이티브 findings 추출 로직 검증 — 인스턴스 레벨 필터들.

`filter_by_garment`(의류 겹침 안전망)·`suppress_benign`(구조적/질감형 양성 억제)·
`dedupe_cross_type_overlap`(서로 다른 defect_type의 중복 검출 병합)·`_section_no_of`
(마스크 무게중심 기반 3×3 섹션 매핑)를 지킨다. `extract_findings`가 필터 통과분만
`kept_instances_by_image`에 담는지(overlay.py가 의존하는 불변식)도 여기서 지킨다.
"""

import numpy as np
import pytest
from PIL import Image

from sam3.contracts import DefectType
from sam3.findings import (
    _section_no_of,
    dedupe_cross_type_overlap,
    dedupe_same_type_containment,
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


def _mask_block(r0: int, r1: int, c0: int, c1: int, size: tuple[int, int] = _SIZE) -> np.ndarray:
    mask = np.zeros(size, dtype=np.uint8)
    mask[r0:r1, c0:c1] = 1
    return mask


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


# --- dedupe_cross_type_overlap ------------------------------------------------
# scratch.jpg 실측: DIRT_MARK/HOLE_TEAR가 거의 동일한 bbox/mask로 같은 자리를 중복
# 검출한 사례(bbox 1px 이내로 겹침, IoU 0.9대)에 대한 회귀 방지.


def test_dedupe_cross_type_overlap_drops_lower_confidence_duplicate():
    # 같은 자리, 다른 타입, IoU=1.0(완전 동일 마스크) — confidence 높은 쪽만 남는다.
    higher = _instance(DefectType.dirt_mark, _mask_at(4, 4), confidence=0.91)
    lower = _instance(DefectType.hole_tear, _mask_at(4, 4), confidence=0.79)
    kept, dropped = dedupe_cross_type_overlap([lower, higher], min_iou=0.7)
    assert kept == [higher]
    assert dropped == [lower]


def test_dedupe_cross_type_overlap_uses_defect_type_value_as_tiebreak():
    # confidence가 동률이면 defect_type.value 알파벳 순으로 결정적으로 정한다
    # ("DIRT_MARK" < "HOLE_TEAR").
    dirt_mark = _instance(DefectType.dirt_mark, _mask_at(4, 4), confidence=0.80)
    hole_tear = _instance(DefectType.hole_tear, _mask_at(4, 4), confidence=0.80)
    kept, dropped = dedupe_cross_type_overlap([hole_tear, dirt_mark], min_iou=0.7)
    assert kept == [dirt_mark]
    assert dropped == [hole_tear]


def test_dedupe_cross_type_overlap_keeps_both_when_overlap_is_below_threshold():
    # 부분 겹침(IoU=0.2, 3x3 블록 두 개가 한 열만 공유)은 임계치(0.7) 미만이라 둘 다 생존.
    a = _instance(DefectType.dirt_mark, _mask_block(3, 6, 3, 6), confidence=0.90)
    b = _instance(DefectType.hole_tear, _mask_block(3, 6, 5, 8), confidence=0.80)
    kept, dropped = dedupe_cross_type_overlap([a, b], min_iou=0.7)
    assert len(kept) == 2 and a in kept and b in kept
    assert dropped == []


def test_dedupe_cross_type_overlap_ignores_same_type_overlap():
    # 같은 타입끼리는 비교 대상이 아니다(같은 프롬프트 내부 중복은 SAM3 자체가 처리한다고 가정).
    a = _instance(DefectType.stain, _mask_at(4, 4), confidence=0.90)
    b = _instance(DefectType.stain, _mask_at(4, 4), confidence=0.80)
    kept, dropped = dedupe_cross_type_overlap([a, b], min_iou=0.7)
    assert len(kept) == 2 and a in kept and b in kept
    assert dropped == []


# --- dedupe_same_type_containment ---------------------------------------------
# small_pro.jpg 실측: 같은 STAIN 인스턴스 여러 개가 서로 97~100% 포함되는 "박스 안에 박스"
# 사례에 대한 회귀 방지. IoU가 아니라 포함 비율을 쓰는 이유도 여기서 확인한다 — 작은
# 박스가 큰 박스에 완전히 들어가도(포함 비율=1.0) 합집합 기준 IoU는 낮다.


def test_dedupe_same_type_containment_drops_the_smaller_contained_instance():
    big = _instance(DefectType.stain, _mask_block(0, 7, 0, 7), confidence=0.91)
    small = _instance(DefectType.stain, _mask_block(1, 4, 1, 4), confidence=0.79)
    kept, dropped = dedupe_same_type_containment([small, big], min_containment=0.8)
    assert kept == [big]
    assert dropped == [small]


def test_dedupe_same_type_containment_ignores_different_types():
    # 타입이 다르면 이 함수의 비교 대상이 아니다 — 그건 dedupe_cross_type_overlap의 몫.
    big = _instance(DefectType.stain, _mask_block(0, 7, 0, 7), confidence=0.91)
    small = _instance(DefectType.hole_tear, _mask_block(1, 4, 1, 4), confidence=0.79)
    kept, dropped = dedupe_same_type_containment([small, big], min_containment=0.8)
    assert len(kept) == 2 and big in kept and small in kept
    assert dropped == []


def test_dedupe_same_type_containment_keeps_both_when_below_threshold():
    # 부분 겹침만 있으면(포함 비율이 임계치 미달) 둘 다 생존.
    a = _instance(DefectType.stain, _mask_block(0, 5, 0, 5), confidence=0.90)
    b = _instance(DefectType.stain, _mask_block(3, 8, 3, 8), confidence=0.80)
    kept, dropped = dedupe_same_type_containment([a, b], min_containment=0.8)
    assert len(kept) == 2 and a in kept and b in kept
    assert dropped == []


def test_dedupe_same_type_containment_prefers_larger_area_on_confidence_tie():
    big = _instance(DefectType.stain, _mask_block(0, 7, 0, 7), confidence=0.80)
    small = _instance(DefectType.stain, _mask_block(1, 4, 1, 4), confidence=0.80)
    kept, dropped = dedupe_same_type_containment([small, big], min_containment=0.8)
    assert kept == [big]
    assert dropped == [small]


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


def test_extract_findings_dedupes_cross_type_duplicates_before_numbering():
    # scratch.jpg 실측 재현: 같은 자리를 DIRT_MARK/HOLE_TEAR 두 프롬프트가 동시에 잡은 경우,
    # 낮은 confidence 쪽은 findings에도 kept_instances_by_image에도 남으면 안 된다.
    higher = _instance(DefectType.dirt_mark, _mask_at(4, 4), confidence=0.91)
    lower = _instance(DefectType.hole_tear, _mask_at(4, 4), confidence=0.79)
    result = _segmentation_result(0, [lower, higher], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)

    extracted = extract_findings([result], prompt_set, segmenter_config("mock"))

    assert len(extracted.findings) == 1
    assert extracted.findings[0].defect_type == DefectType.dirt_mark
    assert extracted.findings[0].no == 1
    kept = extracted.kept_instances_by_image[0]
    assert higher in kept
    assert lower not in kept


def test_extract_findings_dedupes_same_type_containment_before_numbering():
    # small_pro.jpg 실측 재현: 같은 STAIN이 "박스 안에 박스"로 겹치면 작은 쪽은 findings에도
    # kept_instances_by_image에도 남으면 안 된다.
    big = _instance(DefectType.stain, _mask_block(0, 7, 0, 7), confidence=0.91)
    small = _instance(DefectType.stain, _mask_block(1, 4, 1, 4), confidence=0.79)
    result = _segmentation_result(0, [small, big], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)

    extracted = extract_findings([result], prompt_set, segmenter_config("mock"))

    assert len(extracted.findings) == 1
    assert extracted.findings[0].no == 1
    kept = extracted.kept_instances_by_image[0]
    assert big in kept
    assert small not in kept


def test_extract_findings_skips_same_type_dedup_when_disabled():
    big = _instance(DefectType.stain, _mask_block(0, 7, 0, 7), confidence=0.91)
    small = _instance(DefectType.stain, _mask_block(1, 4, 1, 4), confidence=0.79)
    result = _segmentation_result(0, [small, big], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    config = dict(segmenter_config("mock"))
    config["dedupe_same_type"] = False

    extracted = extract_findings([result], prompt_set, config)

    assert len(extracted.findings) == 2
    assert small in extracted.kept_instances_by_image[0]


def test_extract_findings_skips_cross_type_dedup_when_disabled():
    higher = _instance(DefectType.dirt_mark, _mask_at(4, 4), confidence=0.91)
    lower = _instance(DefectType.hole_tear, _mask_at(4, 4), confidence=0.79)
    result = _segmentation_result(0, [lower, higher], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    config = dict(segmenter_config("mock"))
    config["dedupe_cross_type"] = False

    extracted = extract_findings([result], prompt_set, config)

    assert len(extracted.findings) == 2
    assert lower in extracted.kept_instances_by_image[0]


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
    assert {s.image_index for s in extracted.section_scores} == {0}


# --- CH020: 앞/뒤 다중 이미지 — section_scores가 이미지별로 독립적인지 -----------


def test_extract_findings_produces_nine_section_scores_per_image():
    # 앞/뒤 2장이면 9개씩 총 18개 — 이미지 수만큼 늘어나야 한다(합쳐지면 안 된다).
    front = _segmentation_result(0, [], garment_mask=_full_mask())
    back = _segmentation_result(1, [], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)

    extracted = extract_findings([front, back], prompt_set, segmenter_config("mock"))

    assert len(extracted.section_scores) == 18
    assert {s.image_index for s in extracted.section_scores} == {0, 1}
    for image_index in (0, 1):
        by_image = [s for s in extracted.section_scores if s.image_index == image_index]
        assert [s.section_no for s in by_image] == list(range(1, 10))


def test_section_scores_do_not_leak_across_images():
    # 회귀 테스트(CH020): 앞면 5번 섹션에 강한 하자가 있어도 뒷면 5번 섹션 점수는 0이어야
    # 한다 — 예전에는 image 간 max()로 합쳐져서 뒷면이 앞면 점수를 그대로 물려받았다.
    front_defect = _instance(DefectType.stain, _mask_at(4, 4), confidence=0.95)
    front = _segmentation_result(0, [front_defect], garment_mask=_full_mask())
    back = _segmentation_result(1, [], garment_mask=_full_mask())
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)

    extracted = extract_findings([front, back], prompt_set, segmenter_config("mock"))

    front_section_5 = next(
        s for s in extracted.section_scores if s.image_index == 0 and s.section_no == 5
    )
    back_section_5 = next(
        s for s in extracted.section_scores if s.image_index == 1 and s.section_no == 5
    )
    assert front_section_5.score > 0.0
    assert back_section_5.score == 0.0


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
