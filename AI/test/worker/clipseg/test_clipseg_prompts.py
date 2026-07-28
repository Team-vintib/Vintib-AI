"""프롬프트 세트 조립 검증.

프롬프트는 CLIPSeg의 실질적인 입력이라 문구 하나가 판정을 바꾼다. 여기서는 문구 자체의 성능이
아니라 **조립이 깨지지 않는지**를 지킨다 — 템플릿 치환 누락, clean 대조항과 하자 프롬프트의 충돌,
카테고리·색상이 실제로 반영되는지.
"""

import pytest

import registry
from prompts import PromptSet, select_prompt_set
from contracts import BaseColor, DefectType, GarmentCategory

_ALL_COMBINATIONS = [(c, b) for c in GarmentCategory for b in BaseColor]


@pytest.mark.parametrize(("category", "base_color"), _ALL_COMBINATIONS)
def test_every_combination_builds_a_prompt_set(category, base_color):
    prompt_set = select_prompt_set(category, base_color)
    assert isinstance(prompt_set, PromptSet)
    assert prompt_set.category is category
    assert prompt_set.base_color is base_color


@pytest.mark.parametrize(("category", "base_color"), _ALL_COMBINATIONS)
def test_prompt_set_key_is_the_contract_string(category, base_color):
    # 응답 model.prompt_set 에 그대로 실려 BE/FE가 보는 값이다.
    prompt_set = select_prompt_set(category, base_color)
    assert prompt_set.key == f"{category.value.lower()}/{base_color.value.lower()}"


@pytest.mark.parametrize(("category", "base_color"), _ALL_COMBINATIONS)
def test_no_template_placeholder_survives_substitution(category, base_color):
    for prompt in select_prompt_set(category, base_color).all_prompts:
        assert "{" not in prompt and "}" not in prompt
        assert prompt == prompt.strip()
        assert prompt


@pytest.mark.parametrize(("category", "base_color"), _ALL_COMBINATIONS)
def test_prompt_defect_types_are_all_in_taxonomy(category, base_color):
    # 분류 체계에 없는 유형을 프롬프트가 가리키면 findings 단계에서 정책을 못 찾는다.
    types = [t for _, t in select_prompt_set(category, base_color).defect_prompts]
    assert set(types) <= set(registry.DEFECT_TAXONOMY)
    assert len(types) == len(set(types)), "같은 하자 유형을 가리키는 프롬프트가 중복됩니다"


@pytest.mark.parametrize(("category", "base_color"), _ALL_COMBINATIONS)
def test_prompt_set_covers_every_defect_type(category, base_color):
    types = {t for _, t in select_prompt_set(category, base_color).defect_prompts}
    assert types == set(DefectType)


@pytest.mark.parametrize(("category", "base_color"), _ALL_COMBINATIONS)
def test_clean_prompt_is_not_one_of_the_defect_prompts(category, base_color):
    # 대조항이 하자 프롬프트와 같아지면 정규화가 자기 자신을 지운다.
    prompt_set = select_prompt_set(category, base_color)
    assert prompt_set.clean_prompt not in {p for p, _ in prompt_set.defect_prompts}
    assert prompt_set.defect_type_of(prompt_set.clean_prompt) is None


@pytest.mark.parametrize(("category", "base_color"), _ALL_COMBINATIONS)
def test_all_prompts_are_unique_and_end_with_the_clean_contrast(category, base_color):
    prompt_set = select_prompt_set(category, base_color)
    assert len(set(prompt_set.all_prompts)) == len(prompt_set.all_prompts)
    assert prompt_set.all_prompts[-1] == prompt_set.clean_prompt
    assert len(prompt_set.all_prompts) == len(prompt_set.defect_prompts) + 1


def test_prompt_lookup_returns_matching_defect_type():
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    for prompt, defect_type in prompt_set.defect_prompts:
        assert prompt_set.defect_type_of(prompt) is defect_type


def test_unknown_prompt_has_no_defect_type():
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    assert prompt_set.defect_type_of("a photo of a cat") is None


def test_lab12_verified_wording_survives_in_the_prompts():
    """LAB-12가 실측한 문구의 골격("stain", "dirty mark", "hole or tear")이 유지돼야 한다."""
    prompts = select_prompt_set(GarmentCategory.top_knit, BaseColor.light).all_prompts
    joined = " | ".join(prompts)
    assert "a stain on" in joined
    assert "a dirty mark" in joined
    assert "a hole or tear" in joined
    assert "clean undamaged" in joined


def test_patterned_clean_prompt_absorbs_printed_design():
    # 프린트를 "정상"으로 강하게 끌어올려야 감산 정규화가 디자인을 지운다.
    patterned = select_prompt_set(GarmentCategory.top_knit, BaseColor.patterned)
    light = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    assert "printed design" in patterned.clean_prompt
    assert "printed design" not in light.clean_prompt


def test_base_color_changes_the_prompt_wording():
    light = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    dark = select_prompt_set(GarmentCategory.top_knit, BaseColor.dark)
    assert light.all_prompts != dark.all_prompts


def test_category_changes_the_prompt_wording():
    knit = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    pants = select_prompt_set(GarmentCategory.bottom_pants, BaseColor.light)
    assert knit.all_prompts != pants.all_prompts


def test_every_combination_produces_a_distinct_prompt_set():
    keys = {select_prompt_set(c, b).key for c, b in _ALL_COMBINATIONS}
    prompts = {select_prompt_set(c, b).all_prompts for c, b in _ALL_COMBINATIONS}
    assert len(keys) == len(_ALL_COMBINATIONS)
    assert len(prompts) == len(_ALL_COMBINATIONS)


def test_prompt_set_is_cached_per_combination():
    first = select_prompt_set(GarmentCategory.outer_coat, BaseColor.dark)
    second = select_prompt_set(GarmentCategory.outer_coat, BaseColor.dark)
    assert first is second


def test_prompt_set_is_immutable():
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    with pytest.raises(AttributeError):
        prompt_set.clean_prompt = "something else"
