import torch
import time
import json
from PIL import Image
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel
from diffusers import GGUFQuantizationConfig
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

# =========================================================
# 1. 파이프라인 로드 (시간 측정)
# =========================================================
print("=== 파이프라인 로딩 시작 ===")
load_start = time.time()

quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

text_encoder = AutoModelForCausalLM.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    subfolder="text_encoder",
    quantization_config=quant_config,
    torch_dtype=torch.bfloat16,
)

transformer = Flux2Transformer2DModel.from_single_file(
    "https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF/blob/main/flux-2-klein-4b-Q4_0.gguf",
    config="black-forest-labs/FLUX.2-klein-4B",
    subfolder="transformer",
    quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
    torch_dtype=torch.bfloat16,
)

pipe = Flux2KleinPipeline.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    transformer=transformer,
    text_encoder=text_encoder,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()

load_time = time.time() - load_start
print(f"모델 로딩 완료: {load_time:.2f}초")

# =========================================================
# 2. 입력 준비 (고정 - 순수 성능 비교 목적)
# =========================================================
person_img = Image.open("image/person.jpg").convert("RGB").resize((1024, 1024))
cloth_img = Image.open("image/cloth.jpg").convert("RGB").resize((1024, 1024))

prompt = (
    "The person from the first reference image, keeping their exact face, "
    "hairstyle, skin tone, and identity unchanged. "
    "The person is now wearing the exact garment shown in the second reference image — "
    "same color, pattern, and fabric texture as the reference. "
    "Photorealistic, natural studio lighting, full body visible from head to feet."
)

# =========================================================
# 3. 벤치마크: steps별 시간 + VRAM
# =========================================================
results = []

test_configs = [
    {"steps": 4, "resolution": (1024, 1024)},
    {"steps": 10, "resolution": (1024, 1024)},
    {"steps": 20, "resolution": (1024, 1024)},
    {"steps": 30, "resolution": (1024, 1024)},
    {"steps": 20, "resolution": (512, 512)},  # 해상도 비교용
]

for cfg in test_configs:
    steps = cfg["steps"]
    w, h = cfg["resolution"]

    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()

    infer_start = time.time()
    image = pipe(
        prompt=prompt,
        image=[person_img, cloth_img],
        height=h,
        width=w,
        num_inference_steps=steps,
        generator=torch.Generator(device="cpu").manual_seed(0),
    ).images[0]
    torch.cuda.synchronize()
    infer_time = time.time() - infer_start

    peak_vram_gb = torch.cuda.max_memory_allocated() / (1024**3)

    output_name = f"bench_steps{steps}_{w}x{h}.png"
    image.save(output_name)

    result = {
        "steps": steps,
        "resolution": f"{w}x{h}",
        "inference_time_sec": round(infer_time, 2),
        "peak_vram_gb": round(peak_vram_gb, 2),
        "output_file": output_name,
    }
    results.append(result)
    print(f"[steps={steps}, {w}x{h}] 시간={infer_time:.2f}s, VRAM={peak_vram_gb:.2f}GB")

# =========================================================
# 4. 결과 저장 (JSON — 보고서에 표로 옮기기 편함)
# =========================================================
summary = {
    "model_load_time_sec": round(load_time, 2),
    "gpu": torch.cuda.get_device_name(0),
    "benchmarks": results,
}

with open("flux_benchmark_results.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("\n=== 벤치마크 완료 ===")
print(json.dumps(summary, indent=2, ensure_ascii=False))
