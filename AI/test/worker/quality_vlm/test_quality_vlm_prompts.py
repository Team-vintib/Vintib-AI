"""`quality_vlm.prompts.build_batch_prompt()`/`parse_batch_response()` 검증 (hotfix/472).

순수 문자열 조립/파싱이라 torch 불필요.
"""

from quality_vlm.prompts import _FEW_SHOT_EXAMPLES, build_batch_prompt, parse_batch_response
from sam3.contracts import DefectType, Finding, FindingStatus, GarmentSection, Severity


def _finding(
    no: int, *, label: str = "오염", section: GarmentSection = GarmentSection.chest_center
) -> Finding:
    return Finding(
        key=f"k{no}",
        defect_type=DefectType.stain,
        status=FindingStatus.detected,
        image_index=0,
        section_no=1,
        section=section,
        confidence=0.9,
        area_ratio=0.01,
        bbox=(0.1, 0.1, 0.2, 0.2),
        severity=Severity.minor,
        matched_prompt="a stain on fabric",
        statement_required=True,
        needs_seller_review=False,
        no=no,
        label=label,
    )


def test_few_shot_examples_are_included():
    prompt = build_batch_prompt([_finding(1)])
    for example in _FEW_SHOT_EXAMPLES:
        assert example in prompt


def test_finding_number_label_and_section_are_listed():
    prompt = build_batch_prompt([_finding(1, label="올풀림", section=GarmentSection.collar)])
    assert "1번 (목깃 부근): '올풀림' 하자" in prompt


def test_multiple_findings_all_appear_in_listing():
    prompt = build_batch_prompt([_finding(1), _finding(2, label="얼룩")])
    assert "1번" in prompt
    assert "2번" in prompt


def test_location_repeat_is_forbidden():
    prompt = build_batch_prompt([_finding(1)])
    assert "다시 언급하지 마세요" in prompt


def test_hallucination_guard_is_still_present():
    prompt = build_batch_prompt([_finding(1)])
    assert "지어내지 마세요" in prompt


def test_examples_appear_before_the_listing():
    prompt = build_batch_prompt([_finding(1)])
    example_pos = prompt.index(_FEW_SHOT_EXAMPLES[0])
    listing_pos = prompt.index("1번")
    assert example_pos < listing_pos


def test_parse_batch_response_matches_numbered_lines():
    text = "1. 색이 옅게 바랜 부분이 확인됩니다.\n2: 실밥이 풀린 자리가 확인됩니다."
    parsed = parse_batch_response(text, [1, 2])
    assert parsed[1] == "색이 옅게 바랜 부분이 확인됩니다."
    assert parsed[2] == "실밥이 풀린 자리가 확인됩니다."


def test_parse_batch_response_accepts_korean_counter_and_bullets():
    # "1번. 설명"처럼 모델이 프롬프트의 "1번" 표기를 응답에도 따라 하는 경우(실측).
    text = "- 1번. 색상 차이가 확인됩니다.\n* 2번) 해짐이 확인됩니다."
    parsed = parse_batch_response(text, [1, 2])
    assert parsed[1] == "색상 차이가 확인됩니다."
    assert parsed[2] == "해짐이 확인됩니다."


def test_parse_batch_response_leaves_missing_numbers_as_none():
    text = "1. 색상 차이가 확인됩니다."
    parsed = parse_batch_response(text, [1, 2])
    assert parsed[1] == "색상 차이가 확인됩니다."
    assert parsed[2] is None
