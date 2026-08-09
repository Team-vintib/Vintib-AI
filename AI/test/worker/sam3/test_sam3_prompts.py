"""SAM3 프롬프트 세트 조립 검증.

SAM3의 `PromptSet`은 `clean_prompt`/`all_prompts`가 없고(모듈 docstring 참고 — 이진화 개념이
없어 대조항이 필요 없다) `defect_prompts` 자체가 카테고리·색상과 무관하게 고정이다. 여기서는
그 "조립이 깨지지 않는지"(placeholder 없음, 분류 체계 커버, key만 조합별로 갈라짐)만 지킨다.
"""

import pytest

from sam3 import registry
from sam3.contracts import BaseColor, DefectType, GarmentCategory
from sam3.prompts import (
    BENIGN_PROMPTS,
    STRUCTURAL_BENIGN_PROMPTS,
    TEXTURE_BENIGN_PROMPTS,
    PromptSet,
    select_prompt_set,
)

_ALL_COMBINATIONS = [(c, b) for c in GarmentCategory for b in BaseColor]


@pytest.mark.parametrize(("category", "base_color"), _ALL_COMBINATIONS)
def test_every_combination_builds_a_prompt_set(category, base_color):
    prompt_set = select_prompt_set(category, base_color)
    assert isinstance(prompt_set, PromptSet)
    assert prompt_set.category is category
    assert prompt_set.base_color is base_color


@pytest.mark.parametrize(("category", "base_color"), _ALL_COMBINATIONS)
def test_prompt_set_key_is_the_contract_string(category, base_color):
    prompt_set = select_prompt_set(category, base_color)
    assert prompt_set.key == f"{category.value.lower()}/{base_color.value.lower()}"


def test_no_template_placeholder_survives_in_defect_prompts():
    # SAM3 프롬프트는 애초에 {color}/{garment} 치환을 쓰지 않는다 — 짧은 명사구 고정.
    for prompt, _ in select_prompt_set(GarmentCategory.top_knit, BaseColor.light).defect_prompts:
        assert "{" not in prompt and "}" not in prompt
        assert prompt == prompt.strip()
        assert prompt


def test_prompt_defect_types_are_all_in_taxonomy():
    types = [
        t for _, t in select_prompt_set(GarmentCategory.top_knit, BaseColor.light).defect_prompts
    ]
    assert set(types) <= set(registry.DEFECT_TAXONOMY)
    assert len(types) == len(set(types)), "같은 하자 유형을 가리키는 프롬프트가 중복됩니다"


def test_prompt_set_covers_every_validated_defect_type():
    """discoloration/pilling/fray는 hotfix/472로 미검증 상태라 프롬프트에서 뺐다 —
    `DefectType` 전체가 아니라 검증된 3종(stain/dirt_mark/hole_tear)만 커버하면 된다."""
    types = {
        t for _, t in select_prompt_set(GarmentCategory.top_knit, BaseColor.light).defect_prompts
    }
    assert types == {DefectType.stain, DefectType.dirt_mark, DefectType.hole_tear}


def test_prompt_lookup_returns_matching_defect_type():
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    for prompt, defect_type in prompt_set.defect_prompts:
        assert prompt_set.defect_type_of(prompt) is defect_type


def test_unknown_prompt_has_no_defect_type():
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    assert prompt_set.defect_type_of("a photo of a cat") is None


def test_lab_verified_short_noun_phrases_survive_in_the_prompts():
    """LAB-12/LAB-46이 실측한 짧은 명사구 골격이 유지돼야 한다."""
    prompts = [
        p for p, _ in select_prompt_set(GarmentCategory.top_knit, BaseColor.light).defect_prompts
    ]
    joined = " | ".join(prompts)
    assert "a stain on fabric" in joined
    assert "a dirty mark" in joined
    assert "a hole or tear in fabric" in joined


def test_defect_prompts_do_not_vary_by_category_or_color():
    # SAM3 세트는 실측 결과에 따라 카테고리·색상별 문구 변형이 없다.
    knit_light = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    pants_dark = select_prompt_set(GarmentCategory.bottom_pants, BaseColor.dark)
    assert knit_light.defect_prompts == pants_dark.defect_prompts
    assert knit_light.key != pants_dark.key


def test_prompt_set_is_cached_per_combination():
    first = select_prompt_set(GarmentCategory.outer_coat, BaseColor.dark)
    second = select_prompt_set(GarmentCategory.outer_coat, BaseColor.dark)
    assert first is second


def test_prompt_set_is_immutable():
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    with pytest.raises(AttributeError):
        prompt_set.defect_prompts = ()


def test_prompt_set_has_no_clean_contrast_concept():
    # SAM3 네이티브 경로는 이진화를 안 하므로 clean_prompt/all_prompts가 없다(모듈 docstring).
    prompt_set = select_prompt_set(GarmentCategory.top_knit, BaseColor.light)
    assert not hasattr(prompt_set, "clean_prompt")
    assert not hasattr(prompt_set, "all_prompts")


def test_structural_and_texture_benign_prompts_are_disjoint_and_cover_all():
    assert set(STRUCTURAL_BENIGN_PROMPTS).isdisjoint(TEXTURE_BENIGN_PROMPTS)
    assert set(BENIGN_PROMPTS) == set(STRUCTURAL_BENIGN_PROMPTS) | set(TEXTURE_BENIGN_PROMPTS)


def test_benign_prompts_do_not_collide_with_defect_prompts():
    defect_prompts = {
        p for p, _ in select_prompt_set(GarmentCategory.top_knit, BaseColor.light).defect_prompts
    }
    assert defect_prompts.isdisjoint(BENIGN_PROMPTS)


def test_section_label_covers_the_full_grid():
    from sam3.prompts import SECTION_COUNT, section_label

    for section_no in range(1, SECTION_COUNT + 1):
        label = section_label(GarmentCategory.top_knit, section_no)
        assert label is not None


def test_section_label_rejects_out_of_range():
    from sam3.prompts import section_label

    with pytest.raises(ValueError):
        section_label(GarmentCategory.top_knit, 0)
    with pytest.raises(ValueError):
        section_label(GarmentCategory.top_knit, 10)
