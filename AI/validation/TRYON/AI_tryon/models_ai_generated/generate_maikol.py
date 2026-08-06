"""AI 모델 마이콜(흑인, 키 크고 마른 체형)을 CatVTON 작업 해상도(768x1024)로 생성한다.

기존 cheolsu/younghee/dooly와 같은 스타일(플레인 배경, 핏 있는 티셔츠+청바지, 노출 없음)로
`regenerate_at_catvton_resolution.py`와 동일한 FLUX.2-Klein-4B 설정을 재사용한다 -- 체형
다양성(마른/평균/큰 체형)에 이어 키 축 다양성을 하나 더한다.
"""

import time

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

WIDTH, HEIGHT = 768, 1024
NUM_STEPS = 8

PROMPT = (
    "full body studio photo of a tall, slim young Black man standing straight, facing "
    "camera, neutral relaxed pose, plain solid white background, wearing a simple plain "
    "grey t-shirt and jeans, soft even studio lighting, photorealistic, sharp focus, "
    "e-commerce fashion model photo"
)

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
pipe = Flux2KleinPipeline.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    transformer=transformer,
    text_encoder=text_encoder,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()

print("\n=== 생성: maikol ===")
torch.cuda.reset_peak_memory_stats()
t0 = time.time()
image = pipe(
    prompt=PROMPT,
    height=HEIGHT,
    width=WIDTH,
    num_inference_steps=NUM_STEPS,
    guidance_scale=4.0,
    generator=torch.Generator(device="cpu").manual_seed(0),
).images[0]
elapsed = time.time() - t0
peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9

out_path = "maikol.png"
image.save(out_path)
print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")
