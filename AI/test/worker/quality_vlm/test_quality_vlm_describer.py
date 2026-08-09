"""quality_vlm.describer 검증 — build_describer 스왑 지점, attach_descriptions 배선.

무거운 VLM 추론 자체(Qwen3VlDescriber.describe())는 torch가 필요해 여기서 검증하지
않는다 — CI에서 도는 건 MockDescriber 경로와 attach_descriptions의 순수 로직(필터링·
실패 격리·불변성)뿐이다. 실제 생성 품질은 AI/validation/QUAL/vlm-description-check/
vlm_description_check.ipynb에서 확인한다.
"""

from PIL import Image
from quality_vlm.describer import (
    DefectDescriber,
    DescriberNotReady,
    MockDescriber,
    Qwen3VlDescriber,
    _crop_finding,
    _expand_bbox_to_min_size,
    attach_descriptions,
    build_describer,
)
import pytest
from sam3.contracts import DefectType, Finding, FindingStatus, GarmentSection, Severity
from sam3.segmenter import SegmentationResult

_SIZE = (200, 200)  # (height, width)


def _finding(
    key: str,
    *,
    status: FindingStatus = FindingStatus.detected,
    image_index: int = 0,
    section: GarmentSection = GarmentSection.waist_left,
    label: str = "얼룩",
    bbox: tuple[float, float, float, float] = (0.1, 0.1, 0.2, 0.2),
) -> Finding:
    return Finding(
        key=key,
        defect_type=DefectType.stain,
        status=status,
        image_index=image_index,
        section_no=1,
        section=section,
        confidence=0.9,
        area_ratio=0.01,
        bbox=bbox,
        severity=Severity.minor,
        matched_prompt="a stain on fabric",
        statement_required=True,
        needs_seller_review=False,
        no=1,
        label=label,
    )


def _segmentation_result(image_index: int = 0, size: tuple[int, int] = _SIZE) -> SegmentationResult:
    height, width = size
    return SegmentationResult(
        image_index=image_index,
        instances=(),
        benign_instances=(),
        garment_mask=None,
        base_image=Image.new("RGB", (width, height)),
        size=size,
    )


# --- build_describer ----------------------------------------------------------


def test_build_describer_mock_returns_mock_describer():
    describer = build_describer("mock")
    assert isinstance(describer, MockDescriber)


def test_build_describer_qwen3_vl_returns_qwen3_vl_describer_without_loading():
    # 생성자는 모델을 즉시 로드하지 않는다(지연 로드) — torch 없이도 인스턴스화만 가능해야 한다.
    describer = build_describer("qwen3_vl")
    assert isinstance(describer, Qwen3VlDescriber)


def test_build_describer_rejects_unknown_backend():
    with pytest.raises(DescriberNotReady):
        build_describer("no_such_backend")


def test_mock_describer_returns_label_based_static_text():
    describer = MockDescriber()
    finding = _finding("k1", label="구멍/찢어짐")
    assert describer.describe(None, finding) == "구멍/찢어짐 발견"


# --- _expand_bbox_to_min_size / _crop_finding ---------------------------------


def test_expand_bbox_to_min_size_enforces_floor():
    # 작은 bbox(10x10)는 min_size(160)까지 확장돼야 한다.
    bbox_px = (95.0, 95.0, 105.0, 105.0)
    x1, y1, x2, y2 = _expand_bbox_to_min_size(
        bbox_px, pad_ratio=0.6, min_size=160, image_size=(200, 200)
    )
    assert (x2 - x1) >= 160
    assert (y2 - y1) >= 160


def test_expand_bbox_to_min_size_clamps_to_image_bounds():
    bbox_px = (0.0, 0.0, 10.0, 10.0)
    x1, y1, x2, y2 = _expand_bbox_to_min_size(
        bbox_px, pad_ratio=0.6, min_size=160, image_size=(50, 50)
    )
    assert x1 >= 0 and y1 >= 0
    assert x2 <= 50 and y2 <= 50


def test_crop_finding_returns_image_crop_from_normalized_bbox():
    result = _segmentation_result()
    finding = _finding("k1", bbox=(0.4, 0.4, 0.6, 0.6))
    crop = _crop_finding(result.base_image, finding, result.size)
    assert isinstance(crop, Image.Image)
    assert crop.size[0] > 0 and crop.size[1] > 0


# --- attach_descriptions -------------------------------------------------------


class _RecordingDescriber(DefectDescriber):
    def __init__(self):
        self.calls: list[str] = []

    def describe(self, image, finding):
        self.calls.append(finding.key)
        return f"{finding.label} 설명"


class _FailingDescriber(DefectDescriber):
    def describe(self, image, finding):
        raise RuntimeError("boom")


def test_attach_descriptions_processes_detected_and_suspected_findings():
    # hotfix/472: SUSPECTED도 설명을 채운다 — 원래 DETECTED만 처리하던 v1 범위 제한을 없앴다.
    detected = _finding("detected", status=FindingStatus.detected)
    suspected = _finding("suspected", status=FindingStatus.suspected)
    describer = _RecordingDescriber()

    out = attach_descriptions([_segmentation_result()], [detected, suspected], describer)

    assert describer.calls == ["detected", "suspected"]
    by_key = {f.key: f for f in out}
    assert by_key["detected"].description == "얼룩 설명"
    assert by_key["suspected"].description == "얼룩 설명"


def test_attach_descriptions_leaves_original_findings_untouched():
    finding = _finding("k1")
    describer = _RecordingDescriber()

    out = attach_descriptions([_segmentation_result()], [finding], describer)

    assert finding.description is None  # frozen dataclass, 원본 불변
    assert out[0].description == "얼룩 설명"
    assert out[0] is not finding


def test_attach_descriptions_isolates_per_finding_failure():
    ok = _finding("ok")
    boom = _finding("boom")
    describer = _FailingDescriber()

    out = attach_descriptions([_segmentation_result()], [ok, boom], describer)

    # 둘 다 describer가 실패하지만, 예외가 attach_descriptions 밖으로 새어나가지 않고
    # 각 finding은 description=None으로 남아 나머지 처리를 막지 않는다.
    assert len(out) == 2
    assert all(f.description is None for f in out)


def test_attach_descriptions_skips_finding_with_missing_image_result():
    finding = _finding("k1", image_index=5)  # results에 image_index=5 없음
    describer = _RecordingDescriber()

    out = attach_descriptions([_segmentation_result(image_index=0)], [finding], describer)

    assert describer.calls == []
    assert out[0].description is None
