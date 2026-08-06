"""heedongi 아우터 L 재생성 -- 원래 시드(42)에서 왼팔 소매 부근에 이음선 아티팩트가
보여서 시드만 바꿔 재시도한다. worn-reference(FLUX 결과)는 이미 있는 걸 재사용하고
CatVTON 합성 단계만 다시 돈다.

설계: `verify_outer_worn_ref_as_person.py`와 동일 파이프라인, SEED만 인자로 받는다.
"""

import os
import sys

import numpy as np
import torch
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image

from model.cloth_masker import AutoMasker, vis_mask
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding

OUT_DIR = "result/outer_worn_ref_as_person"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

PERSON_NAME = "heedongi"
SIZE_LABEL = "L"
REAL_GARMENT_PATH = os.path.join("image", "alpha_3", "outer.jpg")
SEEDS = [int(s) for s in sys.argv[1:]] or [7, 123, 2026]

print("=== 파이프라인 초기화 ===")
repo_path = snapshot_download(repo_id="zhengchong/CatVTON")
pipeline = CatVTONPipeline(
    base_ckpt="booksforcharlie/stable-diffusion-inpainting",
    attn_ckpt=repo_path,
    attn_ckpt_version="mix",
    weight_dtype=init_weight_dtype("bf16"),
    use_tf32=True,
    device="cuda",
)
pipeline.safety_checker = None


def _bypass_safety_checker(self, image):
    has_nsfw_concept = [False] * len(image) if isinstance(image, list) else [False]
    return image, has_nsfw_concept


pipeline.run_safety_checker = _bypass_safety_checker.__get__(pipeline)

mask_processor = VaeImageProcessor(vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True)
automasker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device="cuda",
)
print("초기화 완료")


def composite_with_original(original_image, generated_image, mask):
    original_np = np.array(original_image.resize(generated_image.size)).astype(np.float32)
    generated_np = np.array(generated_image).astype(np.float32)
    mask_np = np.array(mask.resize(generated_image.size).convert("L")).astype(np.float32) / 255.0
    mask_np = np.expand_dims(mask_np, axis=-1)
    composited = generated_np * mask_np + original_np * (1 - mask_np)
    return Image.fromarray(composited.astype(np.uint8))


real_garment_image = Image.open(REAL_GARMENT_PATH).convert("RGB")
real_garment_image = resize_and_padding(real_garment_image, (WIDTH, HEIGHT))

worn_ref_path = os.path.join("result", "worn_references", f"outer_worn_reference_{PERSON_NAME}_{SIZE_LABEL}.png")
worn_ref_image = Image.open(worn_ref_path).convert("RGB")
worn_ref_image = resize_and_crop(worn_ref_image, (WIDTH, HEIGHT))

upper_mask = automasker(worn_ref_image, mask_type="upper", fit_type="regular")["mask"]
upper_mask_blurred = mask_processor.blur(upper_mask, blur_factor=2)

for seed in SEEDS:
    generator = torch.Generator(device="cuda").manual_seed(seed)

    print(f"\n=== 생성: {PERSON_NAME}_{SIZE_LABEL} seed={seed} ===")
    result_image = pipeline(
        image=worn_ref_image,
        condition_image=real_garment_image,
        mask=upper_mask_blurred,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]
    final = composite_with_original(worn_ref_image, result_image, upper_mask_blurred)

    out_path = os.path.join(OUT_DIR, f"tryon_{PERSON_NAME}_{SIZE_LABEL}_wornrefasperson_seed{seed}.png")
    final.save(out_path)
    print(f"완료 -> {out_path}")

print("\n=== 전체 완료 ===")
