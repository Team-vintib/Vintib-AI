"""철수 전용 "알파테스트3 반바지를 실제로 입은" 레퍼런스를 FLUX.2-Klein-4B로 생성한다.

§8/§9에서 확립한 기법(worn-reference condition_image + self-attention 부스팅)을 재사용해
철수의 원본 사진(긴바지)에 알파테스트3의 버뮤다 반바지(짧은 레퍼런스)를 입힐 때 길이가
정확히 렌더링되게 한다. 옷 설명은 손으로 쓰지 않고 `generate_worn_reference_dooly_tight.py`
에서 확립한 대로 VLM(Qwen3-VL, `worker/models/quality_vlm`)로 실제 상품 사진을 캡션해서
재사용한다 -- 옷이 바뀌어도 같은 스크립트가 그대로 동작한다.

이 레퍼런스는 사이즈(M/L/XL/4XL)와 무관한 "일반적으로 입은 모습"이다 -- 사이즈별
타이트/루즈 차이는 `verify_size_fit_alpha3_cheolsu.py`에서 마스크 폭 축(§7.5)으로 준다.
"""

import os
import sys
import time
from pathlib import Path

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from PIL import Image
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

_REPO_ROOT = Path(__file__).resolve().parents[5]
_WORKER_MODELS_PATH = _REPO_ROOT / "worker" / "models"
if str(_WORKER_MODELS_PATH) not in sys.path:
    sys.path.insert(0, str(_WORKER_MODELS_PATH))

from quality_vlm.loader import generate_from_image, load_qwen_vl  # noqa: E402

OUT_DIR = "result/worn_references"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
NUM_STEPS = 8
GARMENT_PATH = os.path.join("image", "alpha_3", "pants_cropped.png")

CAPTION_PROMPT = (
    "Describe this clothing item's color, fabric, and silhouette in one short phrase for a "
    "fashion photo shoot brief, e.g. 'black wide-fit bermuda shorts with a drawstring waist "
    "and a back pocket'. Only describe the garment itself, do not mention a person."
)

print("=== Step 0: VLM로 실제 상품 사진 캡션 (Qwen3-VL-4B, 4bit) ===")
t0 = time.time()
vlm_bundle = load_qwen_vl("Qwen/Qwen3-VL-4B-Instruct", quantization="4bit")
garment_image = Image.open(GARMENT_PATH).convert("RGB")
garment_caption = generate_from_image(vlm_bundle, garment_image, CAPTION_PROMPT, max_new_tokens=60)
print(f"캡션: {garment_caption!r} ({time.time() - t0:.1f}s)")

del vlm_bundle
torch.cuda.empty_cache()

PROMPT = (
    "full body studio photo of a slim young Korean man standing straight, facing camera, "
    f"wearing a fitted plain grey t-shirt and {garment_caption}, bare legs and shins clearly "
    "visible below the shorts down to the ankles, plain solid white background, soft even "
    "studio lighting, photorealistic, sharp focus, e-commerce fashion model photo"
)
print(f"FLUX 프롬프트: {PROMPT!r}")

print("\n=== Step 1: 텍스트 인코더 로드 ===")
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

print("\n=== 생성: alpha3_cheolsu ===")
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

out_path = os.path.join(OUT_DIR, "pants_worn_reference_alpha3_cheolsu.png")
image.save(out_path)
print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")
