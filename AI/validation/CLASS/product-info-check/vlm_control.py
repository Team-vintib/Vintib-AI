"""V5 — VLM(Qwen3-VL) 대조군 + SAM3 동시 적재 VRAM 실측.

로딩 헬퍼는 `QUAL/vlm-description-check/loaders.py`와 의도적으로 거의 동일하다 — 그 문서의
관례("무거운 import는 함수 내부, dataclass 번들 반환")를 그대로 따르되, 이 스파이크
(`CLASS/product-info-check/`)가 `QUAL/`을 직접 import하지는 않는다. CH012 §6이 프로덕션
워커 구조에서 "패키지 격리 — product_info가 quality_vlm을 직접 임포트하면 도메인 격리가
깨진다"고 못박은 것과 같은 이유다. 검증 스파이크 단계에서부터 그 경계를 지킨다.

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

_COLOR_PROMPT_TEMPLATE = (
    "다음은 중고 거래 플랫폼에 올라온 상품 사진이다. 아래 색상 코드 목록 중 이 상품의 주 색상과 "
    "보조 색상을 하나씩 골라 JSON으로만 답하라. 보조 색상이 뚜렷하지 않으면 null로 두고, "
    '여러 색이 비슷한 비중으로 섞여 있으면 "MULTI"를 골라도 된다. 다른 설명은 붙이지 마라.\n'
    '형식: {{"primary": "코드", "secondary": "코드 또는 null"}}\n'
    "색상 코드 목록: {codes}"
)


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


def query_category(image_path: Path, model_key: str = ACTIVE_VLM) -> tuple[str | None, str]:
    """소분류 30종 중 하나를 VLM에게 직접 고르게 한다. (예측 코드 또는 None, 원본 응답 텍스트)."""
    from PIL import Image

    bundle = _get_bundle()
    with Image.open(image_path) as img:
        image = img.convert("RGB")
    prompt = _CATEGORY_PROMPT_TEMPLATE.format(labels=", ".join(ALL_SUBCATEGORIES))
    raw = generate_from_image(bundle, image, prompt)
    return _match_label(raw, list(ALL_SUBCATEGORIES)), raw


def query_color(image_path: Path, model_key: str = ACTIVE_VLM) -> tuple[str, str | None, dict]:
    """color.py의 VLMColorExtractor가 호출하는 진입점. (primary, secondary, raw) 반환.

    파싱 실패 시 예외를 던지지 않고 primary="UNKNOWN"으로 폴백한다 — evaluate.py가 이걸
    "팔레트 밖으로 나가는 비율" 지표에 그대로 잡을 수 있게 하기 위해서다(실패도 데이터다)."""
    from PIL import Image

    bundle = _get_bundle()
    with Image.open(image_path) as img:
        image = img.convert("RGB")
    valid_codes = list(PALETTE) + [MULTI_LABEL]
    prompt = _COLOR_PROMPT_TEMPLATE.format(codes=", ".join(valid_codes))
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
