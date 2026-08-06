"""FLUX.2-Klein-4B로 "반바지를 실제로 입은 사람" 레퍼런스 사진을 생성한다.

CatVTON의 condition_image는 지금까지 플랫레이(제품 단독) 사진(pants.png)이었는데, 이게
"옷이 실제로 어디까지 덮는지"에 대한 정보가 약하다는 가설을 테스트한다. 사람이 입은
형태의 레퍼런스를 주면 CatVTON이 마스크를 다 채우지 않고 반바지 길이만큼만 채울지 확인.
"""

import time

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

WIDTH, HEIGHT = 768, 1024  # CatVTON 기본 해상도와 맞춤
NUM_STEPS = 8

PROMPT = (
    "full body studio photo of a young Korean man standing straight, facing camera, "
    "wearing plain dark grey athletic shorts that end well above the knee, "
    "bare legs and shins clearly visible below the shorts down to the ankles, "
    "no shirt, plain solid white background, soft even studio lighting, "
    "photorealistic, sharp focus, e-commerce fashion model photo"
)

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

print("\n=== 생성 ===")
torch.cuda.reset_peak_memory_stats()
t0 = time.time()
image = pipe(
    prompt=PROMPT,
    height=HEIGHT,
    width=WIDTH,
    num_inference_steps=NUM_STEPS,
    guidance_scale=4.0,
    generator=torch.Generator(device="cpu").manual_seed(1),
).images[0]
elapsed = time.time() - t0
peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9

out_path = "pants_worn_reference.png"
image.save(out_path)
print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")
