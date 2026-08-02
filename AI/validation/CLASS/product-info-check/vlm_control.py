"""V5 — VLM(Qwen3-VL) 대조군 + SAM3 동시 적재 VRAM 실측.

로딩 헬퍼는 `QUAL/vlm-description-check/loaders.py`와 의도적으로 거의 동일하다 — 그 문서의
관례("무거운 import는 함수 내부, dataclass 번들 반환")를 그대로 따르되, 이 스파이크
(`CLASS/product-info-check/`)가 `QUAL/`을 직접 import하지는 않는다. CH012 §6이 프로덕션
워커 구조에서 "패키지 격리 — product_info가 quality_vlm을 직접 임포트하면 도메인 격리가
깨진다"고 못박은 것과 같은 이유다. 검증 스파이크 단계에서부터 그 경계를 지킨다.

**양자화 설정은 실제 프로덕션과 byte-for-byte 동일함을 확인했다(2026-08-01)** —
`worker/models/quality_vlm/loader.py:46-57`(하자 설명을 생성하는 마지막 단계,
`Qwen3VlDescriber.describe()`가 쓰는 바로 그 로더)가 쓰는
`BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)`와 아래 `load_qwen_vl()`의 설정이
글자 하나까지 같다(둘 다 `QUAL/vlm-description-check/loaders.py`에서 파생됐다 — model_id,
`generate_from_image()` 구현도 동일). 따라서 이 스파이크가 재는 지연·VRAM·정확도는 프로덕션과
다른 양자화를 쓴 결과가 아니다.

**이 모듈은 무거운 GPU 실행을 스크립트가 자동으로 하지 않는다.** mock 백엔드 경로
(classify.py/color.py의 "vlm"이 아닌 다른 백엔드)는 이 모듈을 아예 import하지 않는다.
V5 실측(정확도/지연/VRAM)은 아래 `if __name__ == "__main__":` 블록을 **사용자가 직접**
실행해야 한다 — RTX 4070 Laptop(8GB) 기준 4bit 양자화가 전제이고, SAM3와 동시 적재까지
검증하려면 두 모델을 한 프로세스에 올려야 하므로 절대 가볍지 않다.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from color import MULTI_LABEL, PALETTE
from taxonomy import ALL_SUBCATEGORIES

VLM_MODELS: dict[str, str] = {
    # QUAL/vlm-description-check/model_registry.py와 동일 후보 — 하자 설명 sVLM 검증 때
    # 이미 gated 아님/로드 가능 확인된 모델이라 여기서도 그대로 1차 후보로 쓴다.
    "qwen3-vl-4b-instruct": "Qwen/Qwen3-VL-4B-Instruct",
    "qwen3-vl-2b-instruct": "Qwen/Qwen3-VL-2B-Instruct",
}
ACTIVE_VLM = "qwen3-vl-4b-instruct"
QUANTIZATION_MODES = ("4bit", "none")
ACTIVE_QUANTIZATION = "4bit"


def select_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


@dataclass
class VLMBundle:
    name: str
    model: Any
    processor: Any
    device: str


def load_qwen_vl(model_id: str, quantization: str = ACTIVE_QUANTIZATION) -> VLMBundle:
    import torch
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    device = select_device()
    processor = AutoProcessor.from_pretrained(model_id)

    if quantization == "4bit":
        from transformers import BitsAndBytesConfig

        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_id, quantization_config=quant_config, device_map="auto"
        )
    elif quantization == "none":
        model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_id, dtype="auto", device_map="auto"
        )
    else:
        raise ValueError(f"unknown quantization mode: {quantization!r}")

    model.eval()
    return VLMBundle(name=model_id, model=model, processor=processor, device=device)


def generate_from_image(
    bundle: VLMBundle, image, prompt_text: str, max_new_tokens: int = 60
) -> str:
    import torch

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt_text},
            ],
        }
    ]
    inputs = bundle.processor.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt"
    ).to(bundle.model.device)

    with torch.no_grad():
        output_ids = bundle.model.generate(**inputs, max_new_tokens=max_new_tokens)
    generated = output_ids[:, inputs["input_ids"].shape[1] :]
    return bundle.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()


# --------------------------------------------------------------------------
# 이 프로세스 안에서 재사용할 번들 캐시 — color.py의 VLMColorExtractor와 classify.py 쪽 VLM
# 대조군이 모델을 두 번 로드하지 않게 한다(둘 다 같은 프로세스에서 호출되는 경우).
# --------------------------------------------------------------------------
_bundle: VLMBundle | None = None


def _get_bundle() -> VLMBundle:
    global _bundle
    if _bundle is None:
        _bundle = load_qwen_vl(VLM_MODELS[ACTIVE_VLM])
    return _bundle


_CATEGORY_PROMPT_TEMPLATE = (
    "다음은 중고 거래 플랫폼에 올라온 상품 사진이다. 아래 카테고리 목록 중 이 상품에 가장 "
    "가까운 것을 정확히 하나만, 목록에 있는 단어 그대로 답하라. 다른 설명은 절대 붙이지 마라.\n"
    "목록: {labels}"
)

# v2 — 2026-08-02 추가. 실측(N=10, en_clip_style 등)에서 반복 확인된 오답 패턴(T_SHIRT↔SHIRT,
# 3/10)과 taxonomy.py의 CONFUSION_PAIRS(JACKET/COAT 등)를 프롬프트에 구분 기준으로 직접
# 명시한다. **T_SHIRT↔SHIRT는 CONFUSION_PAIRS에 없던, 이번에 새로 발견된 혼동 쌍이다** —
# taxonomy.py에도 추가할지 검토할 것. 위치를 안 묻는 quality_vlm 프롬프트 관례와 같은 이유로,
# 기준은 전부 크롭 없이도 사진에서 바로 보이는 시각적 특징(카라 유무·원단 질감·끈 길이)만
# 썼다 — "캐주얼해서/포멀해서" 같은 주관적 기준은 hallucination 위험이 있어 뺐다.
_CATEGORY_PROMPT_TEMPLATE_V2 = (
    "다음은 중고 거래 플랫폼에 올라온 상품 사진이다. 아래 카테고리 목록 중 이 상품에 가장 "
    "가까운 것을 정확히 하나만, 목록에 있는 단어 그대로 답하라. 다른 설명은 절대 붙이지 마라.\n"
    "\n"
    "헷갈리기 쉬운 항목 구분 기준:\n"
    "- SHIRT vs T_SHIRT: 카라(옷깃)와 세로 단추가 있고 뻣뻣한 원단이면 SHIRT, "
    "카라 없이 둥근/브이넥이고 신축성 있는 저지 원단이면 T_SHIRT\n"
    "- JACKET vs COAT: 기장이 허벅지를 넘으면 COAT, 엉덩이 정도면 JACKET\n"
    "- HOODIE vs HOODIE_ZIP_UP: 앞이 막혀 있어 머리로 뒤집어 입으면 HOODIE, "
    "지퍼로 앞이 열리면 HOODIE_ZIP_UP\n"
    "- CARDIGAN vs HOODIE_ZIP_UP: 후드가 없고 편물(니트) 질감이면 CARDIGAN, "
    "후드가 있으면 HOODIE_ZIP_UP\n"
    "- KNIT vs SWEATSHIRT: 골지·케이블 같은 짜임 무늬가 보이면 KNIT, "
    "매끈한 원단에 안감이 있으면 SWEATSHIRT\n"
    "- SLACKS vs CARGO_PANTS: 옆에 플랩 달린 큰 주머니가 있으면 CARGO_PANTS, 없으면 SLACKS\n"
    "- SHOULDER_BAG vs CROSS_BAG vs TOTE_BAG: 몸을 가로지르는 긴 끈이면 CROSS_BAG, "
    "한쪽 어깨에 거는 중간 길이 끈이면 SHOULDER_BAG, 짧은 손잡이에 위가 트여 있으면 TOTE_BAG\n"
    "\n"
    "목록: {labels}"
)

# v3 — 2026-08-02 추가. v2를 N=10에 실측한 결과 9/10→7/10으로 **오히려 떨어졌다** — v2가
# 새로 틀린 2건(small_pro.jpg/black_stain.png)이 전부 폴로 셔츠였다. "카라+단추=SHIRT" 규칙을
# 모델이 문자 그대로 적용해서, 이 정답셋에서 T_SHIRT로 라벨링해 둔 폴로를 SHIRT로 판정해버린
# 것 — 규칙 자체가 틀린 게 아니라 **폴로라는 예외를 안 적어서 생긴 문제**다(두 이미지 모두
# `data/ground_truth.json` 라벨링 당시에도 "SHIRT와 경계 애매"로 직접 표시해 둔 케이스).
# v2에 폴로 예외 한 줄만 추가한 버전.
_CATEGORY_PROMPT_TEMPLATE_V3 = (
    "다음은 중고 거래 플랫폼에 올라온 상품 사진이다. 아래 카테고리 목록 중 이 상품에 가장 "
    "가까운 것을 정확히 하나만, 목록에 있는 단어 그대로 답하라. 다른 설명은 절대 붙이지 마라.\n"
    "\n"
    "헷갈리기 쉬운 항목 구분 기준:\n"
    "- SHIRT vs T_SHIRT: 카라(옷깃)와 세로 단추가 있고 뻣뻣한 원단이면 SHIRT, "
    "카라 없이 둥근/브이넥이고 신축성 있는 저지 원단이면 T_SHIRT. "
    "단, 카라와 단추가 있어도 니트/피케 원단의 반팔 폴로 셔츠는 T_SHIRT로 분류한다\n"
    "- JACKET vs COAT: 기장이 허벅지를 넘으면 COAT, 엉덩이 정도면 JACKET\n"
    "- HOODIE vs HOODIE_ZIP_UP: 앞이 막혀 있어 머리로 뒤집어 입으면 HOODIE, "
    "지퍼로 앞이 열리면 HOODIE_ZIP_UP\n"
    "- CARDIGAN vs HOODIE_ZIP_UP: 후드가 없고 편물(니트) 질감이면 CARDIGAN, "
    "후드가 있으면 HOODIE_ZIP_UP\n"
    "- KNIT vs SWEATSHIRT: 골지·케이블 같은 짜임 무늬가 보이면 KNIT, "
    "매끈한 원단에 안감이 있으면 SWEATSHIRT\n"
    "- SLACKS vs CARGO_PANTS: 옆에 플랩 달린 큰 주머니가 있으면 CARGO_PANTS, 없으면 SLACKS\n"
    "- SHOULDER_BAG vs CROSS_BAG vs TOTE_BAG: 몸을 가로지르는 긴 끈이면 CROSS_BAG, "
    "한쪽 어깨에 거는 중간 길이 끈이면 SHOULDER_BAG, 짧은 손잡이에 위가 트여 있으면 TOTE_BAG\n"
    "\n"
    "목록: {labels}"
)

# v4 — 2026-08-02 추가. v3의 "폴로는 예외"는 모델이 먼저 "이게 폴로다"라고 개념적으로
# 인식해야만 적용되는 규칙이라, 정작 그 인식 자체가 실패하면(small_pro.jpg처럼 클로즈업
# 크롭 등) 예외가 발동하지 않았다(v3 실측: 폴로 2건 중 1건만 회복). 사용자 제안대로,
# "폴로 개념을 아는지"에 기대지 않고 **단추가 이어지는 길이**라는 더 저수준·구조적인
# 시각 기준으로 바꿨다 — 셔츠는 단추가 목~밑단까지 쭉 이어지고, 폴로는 목 부근 2~4개뿐이고
# 그 아래는 막혀 있다. 크롭 범위와 무관하게 "단추가 어디서 끝나는지"만 보면 되므로 v3보다
# 크롭에 덜 민감할 것으로 기대한다.
_CATEGORY_PROMPT_TEMPLATE_V4 = (
    "다음은 중고 거래 플랫폼에 올라온 상품 사진이다. 아래 카테고리 목록 중 이 상품에 가장 "
    "가까운 것을 정확히 하나만, 목록에 있는 단어 그대로 답하라. 다른 설명은 절대 붙이지 마라.\n"
    "\n"
    "헷갈리기 쉬운 항목 구분 기준:\n"
    "- SHIRT vs T_SHIRT: 단추가 목 아래부터 밑단까지 쭉 이어지면 SHIRT. "
    "카라가 있어도 단추가 목 부근 2~4개에서 끝나고 그 아래는 막혀 있으면(폴로 셔츠) T_SHIRT. "
    "카라 자체가 없으면(둥근넥·브이넥) 당연히 T_SHIRT\n"
    "- JACKET vs COAT: 기장이 허벅지를 넘으면 COAT, 엉덩이 정도면 JACKET\n"
    "- HOODIE vs HOODIE_ZIP_UP: 앞이 막혀 있어 머리로 뒤집어 입으면 HOODIE, "
    "지퍼로 앞이 열리면 HOODIE_ZIP_UP\n"
    "- CARDIGAN vs HOODIE_ZIP_UP: 후드가 없고 편물(니트) 질감이면 CARDIGAN, "
    "후드가 있으면 HOODIE_ZIP_UP\n"
    "- KNIT vs SWEATSHIRT: 골지·케이블 같은 짜임 무늬가 보이면 KNIT, "
    "매끈한 원단에 안감이 있으면 SWEATSHIRT\n"
    "- SLACKS vs CARGO_PANTS: 옆에 플랩 달린 큰 주머니가 있으면 CARGO_PANTS, 없으면 SLACKS\n"
    "- SHOULDER_BAG vs CROSS_BAG vs TOTE_BAG: 몸을 가로지르는 긴 끈이면 CROSS_BAG, "
    "한쪽 어깨에 거는 중간 길이 끈이면 SHOULDER_BAG, 짧은 손잡이에 위가 트여 있으면 TOTE_BAG\n"
    "\n"
    "목록: {labels}"
)

# taxonomy.py의 PROMPT_TEMPLATES/ACTIVE_* 관례와 동일 — 키 하나만 바꾸면 스왑된다.
CATEGORY_PROMPT_VERSIONS: dict[str, str] = {
    "v1": _CATEGORY_PROMPT_TEMPLATE,
    "v2_disambiguation": _CATEGORY_PROMPT_TEMPLATE_V2,
    "v3_polo_exception": _CATEGORY_PROMPT_TEMPLATE_V3,
    "v4_button_length": _CATEGORY_PROMPT_TEMPLATE_V4,
}
ACTIVE_CATEGORY_PROMPT_VERSION = "v4_button_length"  # 2026-08-02: N=10 실측 10/10, 사용자 확정

_COLOR_PROMPT_TEMPLATE = (
    "다음은 중고 거래 플랫폼에 올라온 상품 사진이다. 아래 색상 코드 목록 중 이 상품의 주 색상과 "
    "보조 색상을 하나씩 골라 JSON으로만 답하라. 보조 색상이 뚜렷하지 않으면 null로 두고, "
    '여러 색이 비슷한 비중으로 섞여 있으면 "MULTI"를 골라도 된다. 다른 설명은 붙이지 마라.\n'
    '형식: {{"primary": "코드", "secondary": "코드 또는 null"}}\n'
    "색상 코드 목록: {codes}"
)

# 색상 개선안 1·2번(팔레트 코드 시각적 앵커 + 색상 혼동쌍 명시, Notion "실험실/[CLASS] 색상
# 판정 정확도 개선 방안 고찰" 참고, 2026-08-03). 카테고리 v2(위 `_CATEGORY_PROMPT_TEMPLATE_V2`)
# 와 같은 형식 — 사진에서 직접 관찰 가능한 밝기/색조 기준만 쓴다(주관적 인상 배제). 근접색
# 그룹은 정답셋 라벨링 정정 이력이 근거다(logo_test.jpg BEIGE->WHITE, small_pro.jpg
# SKYBLUE->WHITE).
_COLOR_PROMPT_TEMPLATE_V2 = (
    "다음은 중고 거래 플랫폼에 올라온 상품 사진이다. 아래 색상 코드 목록 중 이 상품의 주 색상과 "
    "보조 색상을 하나씩 골라 JSON으로만 답하라. 보조 색상이 뚜렷하지 않으면 null로 두고, "
    '여러 색이 비슷한 비중으로 섞여 있으면 "MULTI"를 골라도 된다. 다른 설명은 절대 붙이지 마라.\n'
    "\n"
    "헷갈리기 쉬운 색상 구분 기준(사진에 실제로 보이는 밝기·색조로만 판단):\n"
    "- WHITE vs IVORY vs BEIGE: WHITE는 더 밝힐 수 없는 순백. IVORY는 흰색보다 살짝 "
    "노르스름한 미색(약간 누런 흰색). BEIGE는 IVORY보다 더 진하고 갈색기가 도는 살구/모래색\n"
    "- BLACK vs NAVY: BLACK은 푸른기 없는 순수 무채색 검정. NAVY는 검정처럼 보여도 자세히 "
    "보면 푸른기가 도는 아주 짙은 남색\n"
    "- GRAY vs SILVER: GRAY는 광택 없이 밝지도 어둡지도 않은 중간 회색. SILVER는 GRAY보다 "
    "밝고 은은한 광택/금속 느낌이 있다\n"
    "- BROWN vs KHAKI: BROWN은 채도 높은 순수 갈색. KHAKI는 갈색과 국방색이 섞인 듯한 탁한 "
    "황갈색\n"
    "- SKYBLUE vs BLUE vs NAVY: SKYBLUE는 연하고 밝은 하늘색. BLUE는 그보다 진하고 선명한 "
    "파랑. NAVY는 그보다 훨씬 어두운 남색\n"
    "\n"
    '형식: {{"primary": "코드", "secondary": "코드 또는 null"}}\n'
    "색상 코드 목록: {codes}"
)

COLOR_PROMPT_VERSIONS: dict[str, str] = {
    "v1": _COLOR_PROMPT_TEMPLATE,
    "v2_anchored": _COLOR_PROMPT_TEMPLATE_V2,
}
# 카테고리(v4)와 달리 아직 실측 검증 전이라 기본값은 v1 그대로 둔다 — 실측 후 결정.
ACTIVE_COLOR_PROMPT_VERSION = "v1"


def _match_label(raw_text: str, labels: list[str]) -> str | None:
    """VLM 출력은 자유 텍스트라 정확히 안 맞을 수 있다 — 대소문자/공백 무시하고
    포함 관계까지 넓게 봐서 매칭한다. 못 찾으면 None(실패 격리: 호출부가 결정)."""
    normalized = raw_text.strip().upper()
    for label in labels:
        if normalized == label.upper():
            return label
    for label in labels:
        if label.upper() in normalized:
            return label
    return None


def query_category(
    image_path: Path,
    model_key: str = ACTIVE_VLM,
    prompt_version: str = ACTIVE_CATEGORY_PROMPT_VERSION,
) -> tuple[str | None, str]:
    """소분류 30종 중 하나를 VLM에게 직접 고르게 한다. (예측 코드 또는 None, 원본 응답 텍스트).

    `prompt_version`: `CATEGORY_PROMPT_VERSIONS`의 키(`"v1"` 기본 / `"v2_disambiguation"`
    — 혼동쌍 구분 기준을 프롬프트에 명시한 버전, 2026-08-02 추가)."""
    from PIL import Image

    bundle = _get_bundle()
    with Image.open(image_path) as img:
        image = img.convert("RGB")
    template = CATEGORY_PROMPT_VERSIONS[prompt_version]
    prompt = template.format(labels=", ".join(ALL_SUBCATEGORIES))
    raw = generate_from_image(bundle, image, prompt)
    return _match_label(raw, list(ALL_SUBCATEGORIES)), raw


def query_color(
    image_path: Path,
    model_key: str = ACTIVE_VLM,
    prompt_version: str = ACTIVE_COLOR_PROMPT_VERSION,
) -> tuple[str, str | None, dict]:
    """color.py의 VLMColorExtractor가 호출하는 진입점. (primary, secondary, raw) 반환.

    파싱 실패 시 예외를 던지지 않고 primary="UNKNOWN"으로 폴백한다 — evaluate.py가 이걸
    "팔레트 밖으로 나가는 비율" 지표에 그대로 잡을 수 있게 하기 위해서다(실패도 데이터다).

    `prompt_version`: `COLOR_PROMPT_VERSIONS`의 키(`"v1"` 기본 / `"v2_anchored"` — 팔레트
    코드 시각적 앵커 + 근접색 구분 기준을 명시한 버전, 2026-08-03 추가)."""
    from PIL import Image

    bundle = _get_bundle()
    with Image.open(image_path) as img:
        image = img.convert("RGB")
    valid_codes = list(PALETTE) + [MULTI_LABEL]
    template = COLOR_PROMPT_VERSIONS[prompt_version]
    prompt = template.format(codes=", ".join(valid_codes))
    raw_text = generate_from_image(bundle, image, prompt)

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return "UNKNOWN", None, {"raw_text": raw_text, "parse_error": "no JSON object found"}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        return "UNKNOWN", None, {"raw_text": raw_text, "parse_error": str(exc)}

    primary = _match_label(str(parsed.get("primary", "")), valid_codes) or "UNKNOWN"
    secondary_raw = parsed.get("secondary")
    secondary = _match_label(str(secondary_raw), valid_codes) if secondary_raw else None
    return primary, secondary, {"raw_text": raw_text}


_CATEGORY_AND_COLOR_PROMPT_TEMPLATE = (
    "다음은 중고 거래 플랫폼에 올라온 상품 사진이다. 아래 두 목록을 보고 JSON으로만 답하라. "
    "다른 설명은 절대 붙이지 마라.\n"
    "1) 카테고리: 목록에 있는 단어 중 이 상품에 가장 가까운 것 정확히 하나\n"
    "2) 색상: 색상 코드 목록 중 주 색상 하나(필수), 보조 색상 하나(뚜렷하지 않으면 null, 여러 "
    '색이 비슷한 비중이면 "MULTI")\n'
    '형식: {{"subcategory": "코드", "primary_color": "코드", "secondary_color": "코드 또는 null"}}\n'
    "카테고리 목록: {labels}\n"
    "색상 코드 목록: {codes}"
)


@dataclass
class CombinedVLMResult:
    subcategory: str | None
    primary: str
    secondary: str | None
    raw_text: str


def query_category_and_color(image_path: Path, model_key: str = ACTIVE_VLM) -> CombinedVLMResult:
    """카테고리+색상을 **한 번의 호출**로 같이 질의한다 — "VLM만 쓰는 파이프라인"용.

    `query_category()` + `query_color()`를 따로 부르면 같은 이미지를 두 번 인코딩하게 된다.
    VLM을 카테고리·색상 둘 다에 쓰기로 한 경우엔 이 함수로 이미지 인코딩 1회 + 생성 1회로
    합쳐서 그 비용을 아낀다(2026-08-01 논의). **카테고리를 CLIP(CPU)에 남겨두는 기본 권고와는
    별개다** — 이 함수는 "VLM-only 파이프라인"을 실제로 잴 때만 쓴다(`product_info_check.ipynb`
    §7-2 참고). 파싱 실패는 예외 대신 필드별 폴백으로 처리한다(`query_color()`와 동일한 실패
    격리 원칙 — 실패도 데이터다).
    """
    from PIL import Image

    bundle = _get_bundle()
    with Image.open(image_path) as img:
        image = img.convert("RGB")
    valid_codes = list(PALETTE) + [MULTI_LABEL]
    prompt = _CATEGORY_AND_COLOR_PROMPT_TEMPLATE.format(
        labels=", ".join(ALL_SUBCATEGORIES), codes=", ".join(valid_codes)
    )
    raw_text = generate_from_image(bundle, image, prompt, max_new_tokens=100)

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return CombinedVLMResult(None, "UNKNOWN", None, raw_text)
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return CombinedVLMResult(None, "UNKNOWN", None, raw_text)

    subcategory = _match_label(str(parsed.get("subcategory", "")), list(ALL_SUBCATEGORIES))
    primary = _match_label(str(parsed.get("primary_color", "")), valid_codes) or "UNKNOWN"
    secondary_raw = parsed.get("secondary_color")
    secondary = _match_label(str(secondary_raw), valid_codes) if secondary_raw else None
    return CombinedVLMResult(subcategory, primary, secondary, raw_text)


# --------------------------------------------------------------------------
# VRAM 동시 적재 실측 — CH012 §12 "노트북 VRAM 미측정" 리스크를 직접 확인한다.
# 실제 API: `worker/models/sam3/segmenter.py`의 `build_segmenter() -> DefectSegmenter`
# (`Sam3PcsSegmenter`는 `_ensure_loaded()`가 실제 로드를 트리거하는 지연 로딩 구조 —
# 공개 프리로드 진입점이 따로 없어 밑줄 붙은 메서드를 직접 부른다. 진단 전용 스크립트라
# 이 정도 계층 위반은 감수한다).
# --------------------------------------------------------------------------
def measure_vram_with_sam3() -> dict:
    """**사용자가 직접, 명시적으로만 실행할 것.** Qwen3-VL(4bit) + SAM3를 같은 프로세스에
    순서대로 올리면서 각 단계의 `torch.cuda.memory_allocated()`를 잰다."""
    import sys
    from pathlib import Path

    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA 없음 — 이 측정은 GPU가 있는 노트북에서만 의미가 있다")

    repo_root = Path(__file__).resolve().parents[4]  # .../CLASS/product-info-check -> repo root
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    readings = {"baseline_mb": torch.cuda.memory_allocated() / (1024**2)}

    t0 = time.perf_counter()
    _get_bundle()
    readings["after_qwen_vl_mb"] = torch.cuda.memory_allocated() / (1024**2)
    readings["qwen_vl_load_s"] = time.perf_counter() - t0

    try:
        from worker.models.sam3.segmenter import build_segmenter
    except ImportError as exc:
        readings["sam3_load_error"] = (
            f"worker.models.sam3.segmenter import 실패: {exc}. "
            f"repo_root로 추정한 경로가 틀렸을 수 있다: {repo_root}"
        )
        return readings

    t0 = time.perf_counter()
    segmenter = build_segmenter("sam3_pcs")  # 기본값 "mock"이 아니라 실모델을 명시로 켠다
    segmenter._ensure_loaded()  # noqa: SLF001 — 공개 프리로드 API 없음(위 주석 참고)
    readings["after_sam3_mb"] = torch.cuda.memory_allocated() / (1024**2)
    readings["sam3_load_s"] = time.perf_counter() - t0

    return readings


if __name__ == "__main__":
    print(
        "이 스크립트는 실제로 Qwen3-VL(4bit)을 GPU에 로드한다 — 명시적으로 실행한 것으로 간주한다."
    )
    print(measure_vram_with_sam3())
