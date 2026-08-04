"""`quality_vlm.prompts.build_defect_prompt()` — few-shot 반영 검증 (CH019).

순수 문자열 조립이라 torch 불필요.
"""

from quality_vlm.prompts import _FEW_SHOT_EXAMPLES, build_defect_prompt


def test_few_shot_examples_are_included():
    prompt = build_defect_prompt("오염")
    for example in _FEW_SHOT_EXAMPLES:
        assert example in prompt


def test_defect_label_is_reflected():
    prompt = build_defect_prompt("올풀림")
    assert "'올풀림'" in prompt


def test_location_is_still_forbidden():
    prompt = build_defect_prompt("오염")
    assert "부위인지는 추측하거나 언급하지 마세요" in prompt


def test_hallucination_guard_is_still_present():
    prompt = build_defect_prompt("오염")
    assert "지어내지 마세요" in prompt


def test_examples_appear_before_the_instruction():
    prompt = build_defect_prompt("오염")
    example_pos = prompt.index(_FEW_SHOT_EXAMPLES[0])
    instruction_pos = prompt.index("옷의 어느 부위인지는")
    assert example_pos < instruction_pos
