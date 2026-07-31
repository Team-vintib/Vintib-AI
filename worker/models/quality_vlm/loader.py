"""Qwen-VL 계열 모델 로딩/생성 헬퍼.

`AI/validation/QUAL/vlm-description-check/loaders.py`에서 검증된 코드를 그대로 승격했다.
무거운 라이브러리(torch/transformers/bitsandbytes)는 함수 내부에서 지연 import한다 —
`mock` 백엔드 경로는 이 파일을 아예 건드리지 않는다.

설계: `.claude/plans/ai/CH011-quality-vlm-production-wiring.md`
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def select_device() -> str:
    """CUDA 없으면 이 백엔드는 사실상 못 돈다(4bit 양자화도 GPU 전제)."""
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
    """Qwen3VLForConditionalGeneration/AutoProcessor로 로드.

    quantization="4bit"면 bitsandbytes nf4로 양자화한다(8GB급 GPU 기준 bf16 풀로드가
    안 들어가서 필수 — AI/validation/QUAL/vlm-description-check/ 실측). "none"이면
    dtype="auto" + device_map="auto"로 그대로 올린다 — 더 큰 GPU에서만 실제로 돈다.
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


def generate_from_image(
    bundle: VLMBundle, image, prompt_text: str, max_new_tokens: int = 80
) -> str:
    """이미지 1장 + 프롬프트 텍스트로 한 문장 생성."""
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
