"""둘리(큰 체형) 전용 "타이트하게 입은" 반바지 레퍼런스를 FLUX.2-Klein-4B로 하나 더 생성한다.

`generate_worn_references.py`의 둘리 레퍼런스는 일반(regular) 핏으로 입은 모습이라, 마스크
폭 조절(§7.5, 침식 -6.2px)만으로는 "타이트함"이 육안상 약하게 느껴진다는 지적이 있었다.
CatVTON의 condition_image는 "옷이 몸에서 어디까지/얼마나 붙어서 덮는지"에 대한 직접적인
시각 신호로 쓰이므로(§8.3), 폭 축을 마스크 침식뿐 아니라 레퍼런스 이미지 자체로도 강화해서
같은 신호를 두 경로로 준다.

**첫 버전은 옷 설명을 손으로 썼는데, 이러면 이 특정 상품(회색 벨트 반바지)에만 맞고 다른
옷에는 재사용이 안 된다.** 대신 실제 상품 사진(`pants.png`)을 프로덕션에 이미 있는
`worker/models/quality_vlm`의 Qwen3-VL 로더로 캡션해서, 그 캡션을 FLUX 프롬프트에 그대로
넣는다 — 옷이 바뀌어도 같은 스크립트가 재사용된다. `quality_vlm.describer`(하자 설명
전용, `sam3` 의존)는 쓰지 않고 범용 `loader.load_qwen_vl`/`generate_from_image`만 가져다
쓴다.
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
GARMENT_PATH = os.path.join("image", "alpha_2", "pants.png")

CAPTION_PROMPT = (
    "Describe this clothing item's color, fabric, and silhouette in one short phrase for a "
    "fashion photo shoot brief, e.g. 'dark charcoal grey tailored shorts with a belted "
    "waistband and pleated front'. Only describe the garment itself, do not mention a person."
)

print("=== Step 0: VLM로 실제 상품 사진 캡션 (Qwen3-VL-4B, 4bit) ===")
t0 = time.time()
vlm_bundle = load_qwen_vl("Qwen/Qwen3-VL-4B-Instruct", quantization="4bit")
garment_image = Image.open(GARMENT_PATH).convert("RGB")
garment_caption = generate_from_image(vlm_bundle, garment_image, CAPTION_PROMPT, max_new_tokens=60)
print(f"캡션: {garment_caption!r} ({time.time() - t0:.1f}s)")

# VLM을 내리고 VRAM을 비운다 -- FLUX 로드와 겹치면 경합으로 느려진다(이전 세션 HRNet 교훈).
del vlm_bundle
torch.cuda.empty_cache()

PROMPT = (
    "full body studio photo of a heavyset plus-size Korean man with a bigger, larger build "
    f"standing straight, facing camera, wearing a fitted plain grey t-shirt and {garment_caption}, "
    "the fabric pulled taut and snug across the thighs showing visible tension because the "
    "shorts are a size too small, ending well above the knee, bare legs and shins clearly "
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
