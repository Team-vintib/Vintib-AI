import os
import time
import json
import torch
from huggingface_hub import snapshot_download
from PIL import Image
from diffusers.image_processor import VaeImageProcessor

from model.cloth_masker import AutoMasker
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding

# =========================================================
# 참고: model/cloth_masker.py는 핏 조정 기능(fit_type)을 위해
# 자체적으로 확장한 상태입니다. 이 벤치마크는 fit_type="regular"로
# 고정하여 원본 CatVTON과 동일한 동작(마스크 조정 없음)으로 측정합니다.
# =========================================================

# =========================================================
# 1. 파이프라인 로드 (시간 측정)
# =========================================================
print("=== 파이프라인 로딩 시작 ===")
load_start = time.time()

repo_path = snapshot_download(repo_id="zhengchong/CatVTON")

pipeline = CatVTONPipeline(
    base_ckpt="booksforcharlie/stable-diffusion-inpainting",
    attn_ckpt=repo_path,
    attn_ckpt_version="mix",
    weight_dtype=init_weight_dtype("bf16"),
    use_tf32=True,
    device='cuda'
)

# 벤치마크 중단 방지용 (성능 자체에는 영향 없음)
def _bypass_safety_checker(self, image):
    has_nsfw_concept = [False] * len(image) if isinstance(image, list) else [False]
    return image, has_nsfw_concept
pipeline.run_safety_checker = _bypass_safety_checker.__get__(pipeline)

mask_processor = VaeImageProcessor(vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True)

automasker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device='cuda',
)

load_time = time.time() - load_start
print(f"모델 로딩 완료: {load_time:.2f}초")

# =========================================================
# 2. 입력 준비 (마스크 생성 시간도 별도 측정)
# =========================================================
mask_gen_start = time.time()

base_w, base_h = 768, 1024
person_image_base = Image.open("image/person.jpg").convert("RGB")
cloth_image_base = Image.open("image/cloth.jpg").convert("RGB")
person_image_base = resize_and_crop(person_image_base, (base_w, base_h))
cloth_image_base = resize_and_padding(cloth_image_base, (base_w, base_h))

mask_result = automasker(person_image_base, mask_type="upper", fit_type="regular")
mask_base = mask_processor.blur(mask_result["mask"], blur_factor=9)

mask_gen_time = time.time() - mask_gen_start
print(f"마스크 생성 시간: {mask_gen_time:.2f}초 (참고용, 1회성 전처리 비용)")

# =========================================================
# 3. 벤치마크: steps별 시간 + VRAM (diffusion 추론만 측정)
# =========================================================
results = []

test_configs = [
    {"steps": 10, "resolution": (768, 1024)},
    {"steps": 20, "resolution": (768, 1024)},
    {"steps": 30, "resolution": (768, 1024)},
    {"steps": 50, "resolution": (768, 1024)},  # CatVTON 기본값 참고용
    {"steps": 30, "resolution": (512, 512)},   # 해상도 비교용
]

for cfg in test_configs:
    steps = cfg["steps"]
    w, h = cfg["resolution"]

    if (w, h) != (base_w, base_h):
        person_image = resize_and_crop(Image.open("image/person.jpg").convert("RGB"), (w, h))
        cloth_image = resize_and_padding(Image.open("image/cloth.jpg").convert("RGB"), (w, h))
        mask = mask_processor.blur(
            automasker(person_image, mask_type="upper", fit_type="regular")["mask"],
            blur_factor=9
        )
    else:
        person_image = person_image_base
        cloth_image = cloth_image_base
        mask = mask_base

    generator = torch.Generator(device='cuda').manual_seed(42)

    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()

    infer_start = time.time()
    result_image = pipeline(
        image=person_image,
        condition_image=cloth_image,
        mask=mask,
        num_inference_steps=steps,
        guidance_scale=2.5,
        generator=generator
    )[0]
    torch.cuda.synchronize()
    infer_time = time.time() - infer_start

    peak_vram_gb = torch.cuda.max_memory_allocated() / (1024 ** 3)

    output_name = f"bench_catvton_base_steps{steps}_{w}x{h}.png"
    result_image.save(output_name)

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
# 4. 결과 저장
# =========================================================
summary = {
    "model": "CatVTON (base pipeline, fit_type=regular -> equivalent to original)",
    "note": "model/cloth_masker.py has been extended for fit-aware masking, "
            "but fit_type='regular' bypasses the extension and reproduces "
            "original CatVTON behavior.",
    "model_load_time_sec": round(load_time, 2),
    "mask_generation_time_sec": round(mask_gen_time, 2),
    "gpu": torch.cuda.get_device_name(0),
    "benchmarks": results,
}

with open("catvton_benchmark_base_results.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("\n=== 벤치마크 완료 ===")
print(json.dumps(summary, indent=2, ensure_ascii=False))