"""quality_vlm.describer 검증 — build_describer 스왑 지점, attach_descriptions 배선.

무거운 VLM 추론 자체(Qwen3VlDescriber.describe_batch())는 torch가 필요해 여기서 검증하지
않는다 — CI에서 도는 건 MockDescriber 경로와 attach_descriptions의 순수 로직(이미지별
그룹핑·실패 격리·불변성)뿐이다. 실제 생성 품질은
`worker/validation/quality_vlm_batch_prompt_check.ipynb`에서 확인한다.
"""

from PIL import Image
from quality_vlm.describer import (
    DefectDescriber,
    DescriberNotReady,
    MockDescriber,
    Qwen3VlDescriber,
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
    no: int = 1,
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
        no=no,
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


def test_mock_describer_returns_label_based_static_text_keyed_by_no():
    describer = MockDescriber()
    findings = [_finding("k1", no=1, label="구멍/찢어짐"), _finding("k2", no=2, label="오염")]
    result = describer.describe_batch(None, findings)
    assert result == {1: "구멍/찢어짐 발견", 2: "오염 발견"}


# --- attach_descriptions -------------------------------------------------------


class _RecordingDescriber(DefectDescriber):
    def __init__(self):
        self.calls: list[int] = []

    def describe_batch(self, image, findings):
        self.calls.append(image.size[0] if image else None)
        return {f.no: f"{f.label} 설명" for f in findings}


class _FailingDescriber(DefectDescriber):
    def describe_batch(self, image, findings):
        raise RuntimeError("boom")


def test_attach_descriptions_processes_detected_and_suspected_findings():
    # hotfix/472: DETECTED만 처리하던 v1 범위 제한을 없앴다 — SUSPECTED도 설명이 붙는다.
    detected = _finding("detected", no=1, status=FindingStatus.detected)
    suspected = _finding("suspected", no=2, status=FindingStatus.suspected)
    describer = _RecordingDescriber()

    out = attach_descriptions([_segmentation_result()], [detected, suspected], describer)

    by_key = {f.key: f for f in out}
    assert by_key["detected"].description == "얼룩 설명"
    assert by_key["suspected"].description == "얼룩 설명"


def test_attach_descriptions_calls_describer_once_per_image_not_per_finding():
    a = _finding("a", no=1, image_index=0)
    b = _finding("b", no=2, image_index=0)
    c = _finding("c", no=1, image_index=1)
    describer = _RecordingDescriber()

    attach_descriptions(
        [_segmentation_result(image_index=0), _segmentation_result(image_index=1)],
        [a, b, c],
        describer,
    )

    assert len(describer.calls) == 2  # 이미지 2장 -> 호출 2번(finding 3건이어도)


def test_attach_descriptions_leaves_original_findings_untouched():
    finding = _finding("k1")
    describer = _RecordingDescriber()

    out = attach_descriptions([_segmentation_result()], [finding], describer)

    assert finding.description is None  # frozen dataclass, 원본 불변
    assert out[0].description == "얼룩 설명"
    assert out[0] is not finding


def test_attach_descriptions_isolates_per_image_failure():
    # 이미지 하나에서 describe_batch가 실패해도 다른 이미지의 finding은 영향받지 않는다.
    ok = _finding("ok", no=1, image_index=0)
    boom = _finding("boom", no=1, image_index=1)

    class _MixedDescriber(DefectDescriber):
        def describe_batch(self, image, findings):
            if findings[0].image_index == 1:
                raise RuntimeError("boom")
            return {f.no: f"{f.label} 설명" for f in findings}

    out = attach_descriptions(
        [_segmentation_result(image_index=0), _segmentation_result(image_index=1)],
        [ok, boom],
        _MixedDescriber(),
    )

    by_key = {f.key: f for f in out}
    assert by_key["ok"].description == "얼룩 설명"
    assert by_key["boom"].description is None


def test_attach_descriptions_leaves_missing_batch_number_as_none():
    finding = _finding("k1", no=1)

    class _IncompleteDescriber(DefectDescriber):
        def describe_batch(self, image, findings):
            return {}  # 이 번호는 못 받았다

    out = attach_descriptions([_segmentation_result()], [finding], _IncompleteDescriber())

    assert out[0].description is None


def test_attach_descriptions_skips_finding_with_missing_image_result():
    finding = _finding("k1", image_index=5)  # results에 image_index=5 없음
    describer = _RecordingDescriber()

    out = attach_descriptions([_segmentation_result(image_index=0)], [finding], describer)

    assert describer.calls == []
    assert out[0].description is None
