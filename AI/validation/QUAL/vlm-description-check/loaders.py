"""Qwen-VL 계열 로딩 헬퍼. vlm-description-check 스파이크 전용, 프로덕션 코드 아님.

model_selection/loaders.py 관례(무거운 import는 함수 내부, dataclass 번들 반환)를 따른다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def select_device() -> str:
    """RTX 4070 Laptop 개발 노트북 기준. cuda 없으면 이 스파이크는 사실상 못 돈다(4bit도 GPU 전제)."""
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


def load_qwen_vl(model_id: str, quantization: str = "4bit") -> VLMBundle:
    """Qwen3VLForConditionalGeneration/AutoProcessor 로 로드.

    quantization="4bit"면 bitsandbytes nf4로 양자화한다(RTX 4070 8GB 기준 bf16 풀로드가
    안 들어가서 필수). "none"이면 dtype="auto" + device_map="auto"로 그대로 올린다 —
    8GB보다 큰 GPU에서만 실제로 돈다.
    """
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


def describe_defect(
    bundle: VLMBundle,
    crop_image,
    defect_label: str,
    section_label: str | None = None,
    max_new_tokens: int = 80,
) -> str:
    """크롭 이미지 1장 + 하자 태그(한글)로 한 줄 설명 생성.

    CH009 "검증 축 — 입력 단위"의 "bbox 크롭 이미지 1장 + defect_type/section 컨텍스트"
    조합에 대응한다. section_label이 없으면 그 부분 문구를 프롬프트에서 뺀다.
    """
    import torch

    context = f"'{defect_label}' 하자가 있는 부분"
    if section_label:
        context += f"({section_label} 부위)"
    prompt_text = (
        f"이 이미지는 중고 의류의 {context}을 확대한 사진입니다. "
        "실제로 보이는 상태를 한국어 한 문장으로 짧게 설명해 주세요. "
        "보이지 않는 내용은 지어내지 말고, 사진에서 확인되는 것만 말하세요."
    )
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": crop_image},
                {"type": "text", "text": prompt_text},
            ],
        }
    ]
    inputs = bundle.processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to(bundle.model.device)

    with torch.no_grad():
        generated_ids = bundle.model.generate(**inputs, max_new_tokens=max_new_tokens)
    trimmed = generated_ids[0][inputs["input_ids"].shape[-1] :]
    return bundle.processor.decode(trimmed, skip_special_tokens=True).strip()
