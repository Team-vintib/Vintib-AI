"""VLM 하자 설명 프롬프트 — `AI/validation/QUAL/vlm-description-check/`에서 검증된 문구.

**위치를 묻지 않는다.** 크롭 이미지만으로는 옷 전체에서 어디인지 알 수 없는데, 검증
과정(2026-07-31)에서 모델이 "청바지의 허리 부분" 식으로 위치를 그럴듯하게 지어내는
hallucination이 반복 확인됐다 — 크롭 범위 밖 정보를 요구해서 생기는 문제였다. 위치는
이미 정확한 `Finding.section`(`worker/models/sam3/prompts.py`의 `SECTION_LABELS_KO`로
한글 변환)에서 가져오고, VLM에게는 시각적 특징만 맡긴다.

# TODO: 프롬프트 엔지니어링 — AI/validation/QUAL/vlm-description-check/vlm_description_check.ipynb
#       §4/§5(PROMPT_VARIANTS)에서 먼저 검증한 뒤 이 함수에 반영한다.
# TODO: One-shot / Few-shot 프롬프팅 — 텍스트 기반 예시로 답변 형식을 고정하는 실험도
#       같은 노트북에서 먼저 검증한다(이미지 few-shot은 지연시간 비용이 커서 텍스트
#       예시부터 시도 — vlm_description_check.ipynb의 "TO-DO: 프롬프트 실험 백로그" 참고).

설계: `.claude/plans/ai/CH011-quality-vlm-production-wiring.md`
"""


def build_defect_prompt(defect_label: str) -> str:
    """하자 라벨(한글) -> VLM에게 줄 프롬프트 텍스트. 위치는 절대 묻지 않는다."""
    return (
        f"이 이미지는 중고 의류의 '{defect_label}' 하자 부분을 확대한 사진입니다. "
        "옷의 어느 부위인지는 추측하거나 언급하지 마세요. "
        "색상, 모양, 크기, 질감 등 사진에서 실제로 보이는 시각적 특징만 한국어 한 문장으로 "
        "설명해 주세요. 보이지 않는 내용은 지어내지 마세요."
    )


def compose_finding_bullet(section_label_ko: str, description: str) -> str:
    """부위(신뢰 가능 — `Finding.section` 기반) + VLM 시각 설명을 한 줄로 합친다."""
    return f"{section_label_ko} 부분 — {description}"
