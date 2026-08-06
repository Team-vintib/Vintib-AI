"""SAM3 오버레이 산출물(히트맵/넘버링 bbox) 검증.

`overlay.py`는 모듈 최상단에서 cv2를 import하지 않는다(CI엔 opencv-python-headless가
없다 — `worker/models/sam3/requirements.txt`에만 있음). 그래서 모듈 import 자체와 히트맵
경로(`build_attention_maps`, 순수 PIL/numpy)는 cv2 없이도 CI에서 그대로 돈다. 넘버링 bbox
렌더(`render_numbered_boxes`)만 실제로 그림을 그릴 때 cv2가 필요해 그 테스트만 가드한다.
"""

import numpy as np
import pytest
from PIL import Image

from sam3 import overlay
from sam3.contracts import DefectType, Finding, FindingStatus, GarmentSection, Severity
from sam3.segmenter import SegmentationResult

_SIZE = (20, 30)  # (height, width)


def _finding(image_index, no, *, bbox=(0.1, 0.1, 0.4, 0.4), label="오염"):
    return Finding(
        key=f"stain_{image_index}_5_{no}",
        defect_type=DefectType.stain,
        status=FindingStatus.detected,
        image_index=image_index,
        section_no=5,
        section=GarmentSection.chest_center,
        confidence=0.8,
        area_ratio=0.01,
        bbox=bbox,
        severity=Severity.minor,
        matched_prompt="a stain on fabric",
        statement_required=True,
        needs_seller_review=False,
        no=no,
        label=label,
    )


def _segmentation_result(image_index):
    height, width = _SIZE
    return SegmentationResult(
        image_index=image_index,
        instances=(),
        benign_instances=(),
        garment_mask=None,
        base_image=Image.new("RGB", (width, height), color=(200, 200, 200)),
        size=_SIZE,
    )


def test_module_imports_without_cv2_installed():
    # cv2가 모듈 최상단에 있으면 CI(설치 안 함)에서 이 import 자체가 죽는다.
    assert hasattr(overlay, "render_numbered_boxes")
    assert hasattr(overlay, "build_annotated_images")


def test_build_annotated_images_only_covers_images_with_findings():
    pytest.importorskip("cv2")

    results = [_segmentation_result(0), _segmentation_result(1)]
    findings = [_finding(image_index=0, no=1)]  # image_index=1엔 findings 없음

    calls = []

    def fake_upload(image, prefix):
        calls.append((image.size, prefix))
        return f"https://x/{prefix}.png"

    images = overlay.build_annotated_images(results, findings, fake_upload)

    assert len(images) == 1
    assert images[0].image_index == 0
    assert calls[0][1] == overlay.ANNOTATED_PREFIX


def test_render_numbered_boxes_keeps_image_size():
    pytest.importorskip("cv2")

    height, width = _SIZE
    base = Image.new("RGB", (width, height), color=(0, 0, 0))
    findings = [
        _finding(image_index=0, no=1),
        _finding(image_index=0, no=2, bbox=(0.5, 0.5, 0.9, 0.9)),
    ]

    annotated = overlay.render_numbered_boxes(base, findings)

    assert annotated.size == (width, height)
    # 박스를 그렸으니 완전히 검정으로 남아있으면 안 된다(빨간 픽셀이 어딘가 생겼는지 확인).
    arr = np.array(annotated)
    assert arr.max() > 0


def test_render_numbered_boxes_handles_no_findings():
    pytest.importorskip("cv2")

    height, width = _SIZE
    base = Image.new("RGB", (width, height), color=(50, 60, 70))
    annotated = overlay.render_numbered_boxes(base, [])
    assert annotated.size == (width, height)
