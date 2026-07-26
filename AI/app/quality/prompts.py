"""카테고리 × 기본색 프롬프트 세트와 3×3 부위 라벨 맵.

**프롬프트를 갈아끼우는 지점이다.** CLIPSeg는 텍스트 프롬프트로 세그멘테이션 대상을 지정하므로,
모델을 그대로 두고 문구만 바꿔도 성능이 달라진다(설계 문서 §고도화 경로 2).

LAB-12가 실측한 프롬프트는 `"a stain on fabric"`, `"a dirty mark"`,
`"a hole or tear in fabric"`, `"clean fabric"` 네 개다. 여기서는 그 문구를 골격으로 두고
카테고리(의류 명사)와 기본색(밝은/어두운/프린트)을 끼워 넣는다.

**`clean` 프롬프트가 단순 참고항이 아니다.** 대조 정규화
`p_norm = p_defect - clean_margin * p_clean`의 감산항으로 쓰여 정상 텍스처를 상쇄한다
(`registry.SEGMENTER_BACKENDS[*]["clean_margin"]`). LAB-12에서 WinCLIP이 프린트·솔기·단추 같은
정상 복잡 영역을 손상으로 오인했는데, 검증 스크립트는 `"clean fabric"` 마스크를 표시만 하고
활용하지 않았다. PATTERNED에서 clean 프롬프트가 프린트를 명시적으로 포함하는 이유도 이것이다 —
디자인을 "정상"으로 강하게 끌어올려 감산으로 지워지게 만든다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from dataclasses import dataclass
from functools import lru_cache

from app.quality.schemas import BaseColor, DefectType, GarmentCategory, GarmentSection

# 3×3 그리드. 섹션 번호는 행 우선(좌상단 1 → 우하단 9)이다.
#
# LAB-30이 요구한 "각 부위 넘버링(분류)"을 **평균 풀링으로** 달성한다 — 별도 컨볼루션 층을
# 학습시키지 않기 위한 선택이다. 나중에 학습형 헤드로 바꿔도 이 라벨 맵과 출력 스키마는 그대로다.
SECTION_GRID = 3
SECTION_COUNT = SECTION_GRID * SECTION_GRID

_TOP_SECTIONS: tuple[GarmentSection, ...] = (
    GarmentSection.shoulder_left,
    GarmentSection.collar,
    GarmentSection.shoulder_right,
    GarmentSection.sleeve_left,
    GarmentSection.chest_center,
    GarmentSection.sleeve_right,
    GarmentSection.hem_left,
    GarmentSection.hem_center,
    GarmentSection.hem_right,
)

_BOTTOM_SECTIONS: tuple[GarmentSection, ...] = (
    GarmentSection.waist_left,
    GarmentSection.waist_center,
    GarmentSection.waist_right,
    GarmentSection.thigh_left,
    GarmentSection.crotch,
    GarmentSection.thigh_right,
    GarmentSection.hem_left,
    GarmentSection.shin_center,
    GarmentSection.hem_right,
)

SECTION_LABELS: dict[GarmentCategory, tuple[GarmentSection, ...]] = {
    GarmentCategory.top_knit: _TOP_SECTIONS,
    GarmentCategory.top_shirt: _TOP_SECTIONS,
    GarmentCategory.outer_jacket: _TOP_SECTIONS,
    GarmentCategory.outer_coat: _TOP_SECTIONS,
    GarmentCategory.bottom_pants: _BOTTOM_SECTIONS,
    GarmentCategory.bottom_skirt: _BOTTOM_SECTIONS,
}

# 프롬프트에 들어갈 의류 명사.
_GARMENT_NOUNS: dict[GarmentCategory, str] = {
    GarmentCategory.top_knit: "knit sweater",
    GarmentCategory.top_shirt: "shirt",
    GarmentCategory.outer_jacket: "jacket",
    GarmentCategory.outer_coat: "coat",
    GarmentCategory.bottom_pants: "pants",
    GarmentCategory.bottom_skirt: "skirt",
}

# 기본색 수식어. 밝은 옷과 어두운 옷은 오염이 드러나는 방식이 반대라 문구를 나눈다.
_COLOR_ADJECTIVES: dict[BaseColor, str] = {
    BaseColor.light: "light-colored",
    BaseColor.dark: "dark",
    BaseColor.patterned: "patterned",
}

# 하자 유형별 프롬프트 템플릿. `{color}` / `{garment}` 가 치환된다.
# stain / dirt_mark / hole_tear 는 LAB-12 실측 문구를 확장한 것이고, 나머지 셋은 미검증이다
# (→ registry.DEFECT_TAXONOMY 에서 trusted=False 로 SUSPECTED 로만 노출된다).
_DEFECT_TEMPLATES: tuple[tuple[str, DefectType], ...] = (
    ("a stain on {color} {garment} fabric", DefectType.stain),
    ("a dirty mark on a {garment}", DefectType.dirt_mark),
    ("a hole or tear in {garment} fabric", DefectType.hole_tear),
    ("a discolored faded area on {color} {garment} fabric", DefectType.discoloration),
    ("fabric pilling and fuzz balls on a {garment}", DefectType.pilling),
    ("a frayed worn edge of a {garment}", DefectType.fray),
)

# clean 대조항 템플릿. PATTERNED는 프린트 자체를 "정상"으로 명시해 감산으로 지워지게 한다.
_CLEAN_TEMPLATE = "clean undamaged {color} {garment} fabric"
_CLEAN_TEMPLATE_PATTERNED = "clean undamaged {garment} fabric with a printed design"


@dataclass(frozen=True)
class PromptSet:
    """한 (카테고리, 기본색) 조합에 쓰는 프롬프트 묶음.

    `defect_prompts`의 순서가 세그멘터에 넘기는 프롬프트 순서이며, `clean_prompt`는 마지막에
    한 번 더 붙는다(대조 정규화의 감산항).
    """

    key: str  # 예: "top_knit/light" — 응답 model.prompt_set 에 그대로 실린다
    category: GarmentCategory
    base_color: BaseColor
    clean_prompt: str
    defect_prompts: tuple[tuple[str, DefectType], ...]

    @property
    def all_prompts(self) -> tuple[str, ...]:
        """세그멘터에 넘길 전체 프롬프트(하자 프롬프트들 + clean 대조항)."""
        return tuple(prompt for prompt, _ in self.defect_prompts) + (self.clean_prompt,)

    def defect_type_of(self, prompt: str) -> DefectType | None:
        """프롬프트 문구로 하자 유형을 되찾는다. clean 프롬프트면 None."""
        for candidate, defect_type in self.defect_prompts:
            if candidate == prompt:
                return defect_type
        return None


@lru_cache
def select_prompt_set(category: GarmentCategory, base_color: BaseColor) -> PromptSet:
    """카테고리 × 기본색에 맞는 프롬프트 세트를 조립한다(조합별로 캐시)."""
    garment = _GARMENT_NOUNS[category]
    color = _COLOR_ADJECTIVES[base_color]
    clean_template = (
        _CLEAN_TEMPLATE_PATTERNED if base_color is BaseColor.patterned else _CLEAN_TEMPLATE
    )
    return PromptSet(
        key=f"{category.value.lower()}/{base_color.value.lower()}",
        category=category,
        base_color=base_color,
        clean_prompt=clean_template.format(color=color, garment=garment),
        defect_prompts=tuple(
            (template.format(color=color, garment=garment), defect_type)
            for template, defect_type in _DEFECT_TEMPLATES
        ),
    )


def section_label(category: GarmentCategory, section_no: int) -> GarmentSection:
    """섹션 번호(1~9)를 카테고리별 부위 라벨로 바꾼다."""
    if not 1 <= section_no <= SECTION_COUNT:
        raise ValueError(f"섹션 번호는 1~{SECTION_COUNT} 범위여야 합니다: {section_no}")
    return SECTION_LABELS[category][section_no - 1]
