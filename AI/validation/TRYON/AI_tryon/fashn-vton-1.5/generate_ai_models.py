"""FLUX.2-Klein-4B(GGUF)로 배경이 깔끔한 AI 모델 인물 사진 두 장을 생성한다.

alpha_1/alpha_2의 실제 인물 사진(레드카펫 배경, 다른 사람들이 잔뜩 나옴)이 핏 비교
결과물을 눈으로 볼 때 시선을 분산시켜서, 배경이 없는 스튜디오풍 사진으로 대체한다.
FLUX.2-Klein-4B는 이미 이 세션에서 검증된 모델이라(`verify_flux.py`,
`flux_benchmark_results.json` — 4스텝/1024x1024 기준 49초, Peak VRAM 4.34GB) 새 환경
없이 기존 `flux-test` conda 환경을 그대로 재사용한다.
"""

import time

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

WIDTH, HEIGHT = 768, 1152  # 전신이 잘 나오는 세로 비율(alpha_1/2 인물 사진과 비슷한 구도)
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
