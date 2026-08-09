"""SAM3용 프롬프트 세트 — **짧은 명사구**(긴 문장 아님) + 3×3 부위 라벨 맵.

**왜 짧은 명사구인가**: SAM3는 논문상 짧은 명사구(예: "yellow school bus")로 학습돼 있어,
색상·의류 명사를 문장에 섞어 길게 늘이면 오히려 반응이 약해진다 — `AI/validation/QUAL/
sam3-condition-check/sam3_qc_test.ipynb` 스파이크에서 "a scratch" → "a scratch on fabric"로
늘렸을 때 실측 반응이 약해지는 게 확인됐다. 그래서 SAM3 세트는 카테고리·색상을 프롬프트
문구에 섞지 않는다.

**`clean` 대조 프롬프트가 없다.** SAM3 네이티브 경로는 확률 히트맵을 이진화하지 않으므로
대조 정규화 감산항이라는 개념 자체가 필요 없다(계획 문서 "왜 단순 스왑이 아닌가" 참고). 오탐
억제는 대신 `findings.py`의 양성(benign) 억제 로직이 맡는다.

설계: `.claude/plans/ai/CH006-sam3-quality-segmenter.md`
"""

from dataclasses import dataclass
from functools import lru_cache

from .contracts import BaseColor, DefectType, GarmentCategory, GarmentSection

# 3×3 그리드 부위 라벨 맵. 섹션 번호의 의미는 어느 세그멘터를 쓰든 같아야 한다.
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

# 부위 한글 라벨 — CH011(하자 설명 sVLM)이 최종 문장을 조립할 때 쓴다("왼쪽 허리 부분 —
# 작은 흰색 얼룩이 있습니다" 형태). VLM에게 위치를 직접 묻지 않고(hallucination 유발이
# 검증에서 확인됨, AI/validation/QUAL/vlm-description-check/) 이미 카테고리별로 정확히
# 계산된 `Finding.section` 값을 그대로 한글로만 바꾼다.
SECTION_LABELS_KO: dict[GarmentSection, str] = {
    GarmentSection.shoulder_left: "왼쪽 어깨",
    GarmentSection.collar: "목깃",
    GarmentSection.shoulder_right: "오른쪽 어깨",
    GarmentSection.sleeve_left: "왼쪽 소매",
    GarmentSection.chest_center: "가슴 중앙",
    GarmentSection.sleeve_right: "오른쪽 소매",
    GarmentSection.hem_left: "왼쪽 밑단",
    GarmentSection.hem_center: "밑단 중앙",
    GarmentSection.hem_right: "오른쪽 밑단",
    GarmentSection.waist_left: "왼쪽 허리",
    GarmentSection.waist_center: "허리 중앙",
    GarmentSection.waist_right: "오른쪽 허리",
    GarmentSection.thigh_left: "왼쪽 허벅지",
    GarmentSection.crotch: "사타구니",
    GarmentSection.thigh_right: "오른쪽 허벅지",
    GarmentSection.shin_center: "정강이 중앙",
}

# 의류 존재 확인 프롬프트 — 마스킹 전처리(크롭 + 배경 검정)의 1단계가 쓴다.
# `segmenter.py`의 크롭 로직이 이 상수를 참조한다.
GARMENT_PROMPT = "clothing"

# --- 양성(benign) 억제 프롬프트 ---------------------------------------------
# 정상인데 하자로 오인되는 것들. LAB-46 실측(AI/validation/QUAL/qc_shared.py)에서 그대로
# 가져온다 — 억제 조건이 종류별로 다르다(segmenter.py 의 _suppress_benign 참고).
#
# 구조적 개구부: "a hole or tear in fabric" 프롬프트 자체가 손상된 구멍과 의류가 원래 갖고
# 있는 개구부를 구분하지 못한다. 실측(검정 티셔츠 1장)에서 넥라인·밑단·소매끝이 전부 HOLE_TEAR
# 오탐이었다 — 겹치면 confidence 비교 없이 곧바로 억제한다.
STRUCTURAL_BENIGN_PROMPTS: tuple[str, ...] = ("an armhole", "a neckline", "a hem", "a cuff")

# 질감형: 주름·접힘·그림자·솔기·프린트. 이 위에는 실제 하자가 생길 수 있어(솔기 근처 실밥
# 뜯김 등) 겹침만으로 억제하면 안 되고, 양성 쪽 confidence 가 하자보다 높을 때만 억제한다.
TEXTURE_BENIGN_PROMPTS: tuple[str, ...] = (
    "a wrinkle on fabric",
    "a fold in fabric",
    "a shadow",
    "a seam",
    "a printed pattern on fabric",
)

BENIGN_PROMPTS: tuple[str, ...] = STRUCTURAL_BENIGN_PROMPTS + TEXTURE_BENIGN_PROMPTS

# 하자 유형별 프롬프트. stain/dirt_mark/hole_tear 세 개는 LAB-12/LAB-46이 실측한 문구를
# 그대로 쓴다(AI/validation/QUAL/qc_shared.py 의 "fabric" 세트와 동일 문자열).
#
# discoloration/pilling/fray(미검증 프롬프트)는 hotfix/472로 잠시 뺐다 — 검증 노트북
# (sam3_qc_test_masking.ipynb)과 프로덕션 탐지 결과가 벌어지는 원인 중 하나가 프로덕션만
# 이 3종을 추가로 돌리는 것이었다. `DefectType.discoloration`/`pilling`/`fray` 자체와
# `registry.py`/`scoring.py`의 대응 항목은 그대로 둔다 — 나중에 재검증되면 여기 한 줄만
# 다시 추가하면 된다.
#
# hotfix/472: dirt_mark("a dirty mark")는 한 차례 뺐다가 다시 되살렸다 — stain과 실물상
# 같은 얼룩을 거의 항상 같이 잡는 문제(실측: 소매 STAIN bbox가 DIRT_MARK bbox에 크기만
# 다르게 포함) 자체는 여전하지만, 프롬프트를 줄여 유형 구분(설명 다양성)을 잃는 대신
# `findings.dedupe_cross_type_overlap()`에 포함 비율(containment) 기준을 추가해 크기
# 차이가 큰 중복도 병합되게 했다(`registry.cross_type_containment_min` 참고) — 원인을
# 프롬프트가 아니라 dedup 로직 쪽에서 고치는 쪽으로 방향을 바꿨다.
_DEFECT_PROMPTS: tuple[tuple[str, DefectType], ...] = (
    ("a stain on fabric", DefectType.stain),
    ("a dirty mark", DefectType.dirt_mark),
    ("a hole or tear in fabric", DefectType.hole_tear),
)


@dataclass(frozen=True)
class PromptSet:
    """한 (카테고리, 기본색) 조합에 쓰는 프롬프트 묶음.

    `defect_prompts`의 순서가 세그멘터에 넘기는 프롬프트 순서다. `clean_prompt`/`all_prompts`가
    없다 — 위 모듈 docstring 참고.
    """

    key: str  # 예: "top_knit/light" — 응답 model.prompt_set 에 그대로 실린다
    category: GarmentCategory
    base_color: BaseColor
    defect_prompts: tuple[tuple[str, DefectType], ...]

    def defect_type_of(self, prompt: str) -> DefectType | None:
        """프롬프트 문구로 하자 유형을 되찾는다."""
        for candidate, defect_type in self.defect_prompts:
            if candidate == prompt:
                return defect_type
        return None


@lru_cache
def select_prompt_set(category: GarmentCategory, base_color: BaseColor) -> PromptSet:
    """카테고리 × 기본색에 맞는 프롬프트 세트를 돌려준다(조합별로 캐시).

    지금은 프롬프트 문구 자체가 카테고리·색상에 안 갈린다(짧은 명사구가 이미 일반적이라
    실측에서 구분할 필요가 없었다) — `key`만 조합별로 달라지고 `defect_prompts`는 고정이다.
    나중에 카테고리별 실험이 필요해지면 이 함수 안에서만 분기하면 된다(호출부 계약은 그대로
    유지된다).
    """
    return PromptSet(
        key=f"{category.value.lower()}/{base_color.value.lower()}",
        category=category,
        base_color=base_color,
        defect_prompts=_DEFECT_PROMPTS,
    )


def section_label(category: GarmentCategory, section_no: int) -> GarmentSection:
    """섹션 번호(1~9)를 카테고리별 부위 라벨로 바꾼다."""
    if not 1 <= section_no <= SECTION_COUNT:
        raise ValueError(f"섹션 번호는 1~{SECTION_COUNT} 범위여야 합니다: {section_no}")
    return SECTION_LABELS[category][section_no - 1]
