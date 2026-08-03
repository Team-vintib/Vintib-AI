"""둘리(큰 체형) 전용 "타이트하게 입은" 반바지 레퍼런스를 FLUX.2-Klein-4B로 하나 더 생성한다.

`generate_worn_references.py`의 둘리 레퍼런스는 일반(regular) 핏으로 입은 모습이라, 마스크
폭 조절(§7.5, 침식 -6.2px)만으로는 "타이트함"이 육안상 약하게 느껴진다는 지적이 있었다.
CatVTON의 condition_image는 "옷이 몸에서 어디까지/얼마나 붙어서 덮는지"에 대한 직접적인
시각 신호로 쓰이므로(§8.3), 폭 축을 마스크 침식뿐 아니라 레퍼런스 이미지 자체로도 강화해서
같은 신호를 두 경로로 준다.
"""

import os
import time

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

OUT_DIR = "result/worn_references"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
NUM_STEPS = 8

PROMPT = (
    "full body studio photo of a heavyset plus-size Korean man with a bigger, larger build "
    "standing straight, facing camera, wearing a fitted plain grey t-shirt and very tight "
    "skin-hugging compression shorts that end well above the knee, the shorts fabric "
    "stretched snugly against the thighs with visible tension, bare legs and shins clearly "
    "visible below the shorts down to the ankles, plain solid white background, soft even "
    "studio lighting, photorealistic, sharp focus, e-commerce fashion model photo"
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

print("\n=== 생성: dooly_tight ===")
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

out_path = os.path.join(OUT_DIR, "pants_worn_reference_dooly_tight.png")
image.save(out_path)
print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")
