"""`scoring.summarize()` — 이미지별 넘버링 리스트 요약 검증 (CH018).

부위 정보·VLM 설명·이미지 구분을 반영한 요약 포맷을 지킨다. 순수 로직(Finding 조립 +
문자열 포맷)이라 torch 등 무거운 의존성이 없다.
"""

from sam3.contracts import (
    DefectType,
    Finding,
    FindingStatus,
    GarmentSection,
    Severity,
)
from sam3.scoring import summarize

_BASE_KWARGS = dict(
    confidence=0.9,
    area_ratio=0.05,
    bbox=(0.1, 0.1, 0.2, 0.2),
    severity=Severity.moderate,
    matched_prompt="a stain on fabric",
    statement_required=True,
    needs_seller_review=False,
)


def _finding(**overrides) -> Finding:
    kwargs = dict(
        key="stain_0_5_1",
        defect_type=DefectType.stain,
        status=FindingStatus.detected,
        image_index=0,
        section_no=5,
        section=GarmentSection.sleeve_left,
        **_BASE_KWARGS,
    )
    kwargs.update(overrides)
    return Finding(**kwargs)


def test_no_findings_returns_no_defect_summary():
    assert summarize([]) == "확인된 하자가 없습니다."


def test_single_image_omits_image_header():
    finding = _finding(no=1)
    result = summarize([finding])
    assert "[이미지" not in result
    assert result == "1. 왼쪽 소매 오염"


def test_multi_image_adds_headers_per_image():
    first = _finding(image_index=0, no=1)
    second = _finding(
        image_index=1,
        no=1,
        section=GarmentSection.collar,
        defect_type=DefectType.discoloration,
        status=FindingStatus.suspected,
    )
    result = summarize([first, second])

    assert result == ("[이미지 1]\n1. 왼쪽 소매 오염\n\n[이미지 2]\n1. 목깃 변색 (의심)")


def test_description_is_appended_when_present():
    finding = _finding(no=1, description="옅은 갈색 얼룩이 소매 끝부분에 있습니다.")
    result = summarize([finding])
    assert result == "1. 왼쪽 소매 오염 — 옅은 갈색 얼룩이 소매 끝부분에 있습니다."


def test_suspected_status_is_marked():
    finding = _finding(no=2, status=FindingStatus.suspected)
    result = summarize([finding])
    assert result == "2. 왼쪽 소매 오염 (의심)"


def test_missing_no_falls_back_to_display_order_without_mutating_finding():
    first = _finding(no=None, section=GarmentSection.sleeve_left)
    second = _finding(no=None, section=GarmentSection.hem_center, defect_type=DefectType.pilling)
    result = summarize([first, second])

    assert result == "1. 왼쪽 소매 오염\n2. 밑단 중앙 보풀"
    assert first.no is None
    assert second.no is None


def test_findings_within_image_keep_input_order():
    first = _finding(no=1, section=GarmentSection.sleeve_left)
    second = _finding(no=2, section=GarmentSection.hem_center, defect_type=DefectType.pilling)
    result = summarize([first, second])
    assert result == "1. 왼쪽 소매 오염\n2. 밑단 중앙 보풀"
