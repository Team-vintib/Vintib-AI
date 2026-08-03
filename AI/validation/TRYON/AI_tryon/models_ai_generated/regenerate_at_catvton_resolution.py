"""AI 모델 사진(cheolsu/younghee/dooly)을 CatVTON 작업 해상도(768x1024)로 재생성한다.

기존 사진은 768x1152(`fashn-vton-1.5/generate_ai_models.py`, FASHN VTON PoC의 다른 구도용
해상도)였는데, CatVTON 스크립트들은 `resize_and_crop(image, (768, 1024))`로 리사이즈한다.
이 함수는 세로를 중앙 기준으로 대칭 크롭한다 -- 1152 -> 1024면 위/아래 각 64px씩 잘려서,
사람 사진 구도에 따라 신발(발목 아래)이 잘려나가는 문제가 있었다. 처음부터 768x1024로
생성하면 크롭이 사실상 no-op이 되어 이 문제가 사라진다.

프롬프트/시드는 기존 스크립트(`fashn-vton-1.5/generate_ai_models.py`)와 동일하게 유지해서
인물 스타일 일관성을 유지하고, HEIGHT만 1024로 바꾼다.
"""

import time

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

WIDTH, HEIGHT = 768, 1024  # CatVTON 작업 해상도와 동일 -- resize_and_crop이 사실상 no-op이 됨
NUM_STEPS = 8

PROMPTS = {
    "cheolsu": (
        "full body studio photo of a young Korean man standing straight, facing camera, "
        "neutral relaxed pose, plain solid white background, wearing a simple plain grey "
        "t-shirt and jeans, soft even studio lighting, photorealistic, sharp focus, "
        "e-commerce fashion model photo"
    ),
    "younghee": (
        "full body studio photo of a young Korean woman standing straight, facing camera, "
        "neutral relaxed pose, plain solid white background, wearing a simple plain white "
        "t-shirt and jeans, soft even studio lighting, photorealistic, sharp focus, "
        "e-commerce fashion model photo"
    ),
    "dooly": (
        "full body studio photo of a heavyset plus-size Korean man with a bigger, larger "
        "build standing straight, facing camera, neutral relaxed pose, plain solid white "
        "background, wearing a simple plain grey t-shirt and jeans, soft even studio "
        "lighting, photorealistic, sharp focus, e-commerce fashion model photo"
    ),
}

print("=== Step 1: 텍스트 인코더 로드 (4bit 양자화) ===")
t0 = time.time()
quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
text_encoder = AutoModelForCausalLM.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    subfolder="text_encoder",
    quantization_config=quant_config,
    torch_dtype=torch.bfloat16,
)
print(f"완료 ({time.time() - t0:.1f}s)")

print("\n=== Step 2: 트랜스포머 로드 (GGUF Q4_0) ===")
t0 = time.time()
transformer = Flux2Transformer2DModel.from_single_file(
    "https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF/blob/main/flux-2-klein-4b-Q4_0.gguf",
    config="black-forest-labs/FLUX.2-klein-4B",
    subfolder="transformer",
    quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
    torch_dtype=torch.bfloat16,
)
print(f"완료 ({time.time() - t0:.1f}s)")

print("\n=== Step 3: 파이프라인 조립 ===")
t0 = time.time()
pipe = Flux2KleinPipeline.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    transformer=transformer,
    text_encoder=text_encoder,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()
print(f"완료 ({time.time() - t0:.1f}s)")

for name, prompt in PROMPTS.items():
    print(f"\n=== 생성: {name} ===")
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    image = pipe(
        prompt=prompt,
        height=HEIGHT,
        width=WIDTH,
        num_inference_steps=NUM_STEPS,
        guidance_scale=4.0,
        generator=torch.Generator(device="cpu").manual_seed(0),
    ).images[0]
    elapsed = time.time() - t0
    peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9

    out_path = f"{name}.png"
    image.save(out_path)
    print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")

print("\n=== 전체 완료 ===")
