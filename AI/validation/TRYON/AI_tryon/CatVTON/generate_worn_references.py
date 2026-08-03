"""FLUX.2-Klein-4B로 체형별 "반바지를 실제로 입은 사람" 레퍼런스 3장을 생성한다.

CatVTON의 condition_image로 플랫레이 대신 "사람이 입은 형태"를 주면 마스크(다리 전체)를
원단으로 다 채우지 않고 반바지 길이만큼만 채운다는 걸 철수로 확인했다. 근데 철수(마른
체형) 레퍼런스를 체형이 다른 영희/둘리에게 그대로 재사용했더니 효과가 줄었다 — 체형이
안 맞아서 신호가 약해진 것으로 보여, 각자 체형에 맞는 레퍼런스를 따로 만든다.

이전 버전은 "no shirt"로 상반신을 노출시켰는데, 하의 테스트엔 상의 노출 여부가 중요하지
않으니 이번엔 핏이 있는 티셔츠를 입힌 채로 생성해서 불필요한 노출을 없앤다 — 다리(반바지
길이) 정보는 그대로 유지된다.
"""

import os
import time

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

OUT_DIR = "worn_references"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
NUM_STEPS = 8

PROMPTS = {
    "cheolsu": (
        "full body studio photo of a slim young Korean man standing straight, facing camera, "
        "wearing a fitted plain grey t-shirt and plain dark grey athletic shorts that end "
        "well above the knee, bare legs and shins clearly visible below the shorts down to "
        "the ankles, plain solid white background, soft even studio lighting, "
        "photorealistic, sharp focus, e-commerce fashion model photo"
    ),
    "younghee": (
        "full body studio photo of a slim young Korean woman standing straight, facing camera, "
        "wearing a fitted plain white t-shirt and plain dark grey athletic shorts that end "
        "well above the knee, bare legs and shins clearly visible below the shorts down to "
        "the ankles, plain solid white background, soft even studio lighting, "
        "photorealistic, sharp focus, e-commerce fashion model photo"
    ),
    "dooly": (
        "full body studio photo of a heavyset plus-size Korean man with a bigger, larger "
        "build standing straight, facing camera, wearing a fitted plain grey t-shirt and "
        "plain dark grey athletic shorts that end well above the knee, bare legs and shins "
        "clearly visible below the shorts down to the ankles, plain solid white background, "
        "soft even studio lighting, photorealistic, sharp focus, e-commerce fashion model photo"
    ),
}

print("=== Step 1: 텍스트 인코더 로드 ===")
t0 = time.time()
quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
text_encoder = AutoModelForCausalLM.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    subfolder="text_encoder",
    quantization_config=quant_config,
    torch_dtype=torch.bfloat16,
)
print(f"완료 ({time.time() - t0:.1f}s)")

print("\n=== Step 2: 트랜스포머 로드 ===")
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
pipe = Flux2KleinPipeline.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    transformer=transformer,
    text_encoder=text_encoder,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()

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
        generator=torch.Generator(device="cpu").manual_seed(1),
    ).images[0]
    elapsed = time.time() - t0
    peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9

    out_path = os.path.join(OUT_DIR, f"pants_worn_reference_{name}.png")
    image.save(out_path)
    print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")

print("\n=== 전체 완료 ===")
