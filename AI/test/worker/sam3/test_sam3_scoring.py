"""CH020: 이미지별 요약(`summarize_by_image`) 검증.

앞/뒤 2장처럼 여러 이미지가 들어왔을 때, 하자가 있는 이미지와 없는 이미지 모두 빠짐없이
요약이 나오고, 서로의 findings가 섞이지 않는지 확인한다.
"""

from sam3.contracts import DefectType, Finding, FindingStatus, GarmentSection, Severity
from sam3.scoring import summarize_by_image


def _finding(image_index: int, defect_type: DefectType = DefectType.stain) -> Finding:
    return Finding(
        key=f"{defect_type.value.lower()}_{image_index}_5_1",
        defect_type=defect_type,
        status=FindingStatus.detected,
        image_index=image_index,
        section_no=5,
        section=GarmentSection.chest_center,
        confidence=0.9,
        area_ratio=0.03,
        bbox=(0.4, 0.4, 0.5, 0.5),
        severity=Severity.moderate,
        matched_prompt="a stain on fabric",
        statement_required=True,
        needs_seller_review=False,
    )


def test_summarize_by_image_covers_every_image_including_empty_ones():
    findings = [_finding(0)]

    summaries = summarize_by_image(findings, image_count=2)

    assert [s.image_index for s in summaries] == [0, 1]
    assert "오염" in summaries[0].summary
    assert summaries[1].summary == "확인된 하자가 없습니다."


def test_summarize_by_image_does_not_leak_findings_across_images():
    front = _finding(0, DefectType.stain)
    back = _finding(1, DefectType.hole_tear)

    summaries = summarize_by_image([front, back], image_count=2)

    by_index = {s.image_index: s.summary for s in summaries}
    assert "오염" in by_index[0]
    assert "구멍" in by_index[1] or "찢어짐" in by_index[1]
    assert "오염" not in by_index[1]
