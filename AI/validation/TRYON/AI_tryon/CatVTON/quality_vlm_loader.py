"""Qwen-VL 계열 모델 로딩/생성 헬퍼.

`worker/models/quality_vlm/loader.py`를 그대로 복사해왔다. 이 폴더 자체가 `worker/models/
catvton`을 건드리지 않고 자유롭게 실험하기 위한 스냅샷(`NOTE.md`)인데, VLM 캡션 로더만
`sys.path`로 프로덕션 경로(`worker/models/quality_vlm`)를 실시간 참조하면 그 원칙에서
벗어난다 -- 다른 팀원/작업이 그 모듈을 리팩터링/삭제하면 여기 검증 스크립트가 예고 없이
깨질 수 있다. 로더 하나만 쓰고(describer.py/prompts.py/registry.py는 안 씀) 의존성도
없어서 그대로 복사해 고정한다. 프로덕션 쪽이 바뀌어도 여기는 자동 동기화되지 않는다 --
필요해지면 다시 수동으로 맞춘다.
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
    안 들어가서 필수). "none"이면 dtype="auto" + device_map="auto"로 그대로 올린다 --
    더 큰 GPU에서만 실제로 돈다.
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
