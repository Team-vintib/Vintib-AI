"""둘리만 최신 fit-aware worn-reference(% 편차 + 총장 반영 로직)로 재검증한다.

기존 배치(size_fit_alpha3_jeans_fitaware_20260804_113209)는 버킷 충돌 버그(L=0.773,
XL=0.818이 같은 "0.75~0.85" 구간이라 문구가 완전히 동일)와 총장 미반영 버그가 있던
버전이라, L/XL 간 차이가 거의 안 보였다. `verify_size_fit_alpha3_jeans_fitaware_younghee.py`
와 동일한 패턴으로 둘리만 다시 돈다.
"""

import os
from datetime import datetime

import numpy as np
import torch
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image

from model.cloth_masker import AutoMasker
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding

OUT_DIR = os.path.join("result", "size_fit_alpha3_jeans_fitaware_dooly_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

PERSON_NAME = "dooly"
SIZES = ["M", "L", "XL", "2XL"]

_MODELS_DIR = os.path.join("..", "models_ai_generated")
_WORN_REF_DIR = os.path.join("result", "worn_references")

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


person_image = Image.open(os.path.join(_MODELS_DIR, f"{PERSON_NAME}.png")).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

lower_mask = automasker(person_image, mask_type="lower", fit_type="regular")["mask"]
lower_mask = mask_processor.blur(lower_mask, blur_factor=2)  # §9.3

for size_label in SIZES:
    generator = torch.Generator(device="cuda").manual_seed(42)

    worn_ref_path = os.path.join(_WORN_REF_DIR, f"jeans_worn_reference_{PERSON_NAME}_{size_label}.png")
    worn_ref_image = Image.open(worn_ref_path).convert("RGB")
    worn_ref_image = resize_and_padding(worn_ref_image, (WIDTH, HEIGHT))

    print(f"\n=== {PERSON_NAME} {size_label} ===")
    result_image = pipeline(
        image=person_image,
        condition_image=worn_ref_image,
        mask=lower_mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]
    final = composite_with_original(person_image, result_image, lower_mask)

    out_path = os.path.join(OUT_DIR, f"tryon_{PERSON_NAME}_{size_label}.png")
    final.save(out_path)
    print(f"완료 -> {out_path}")

print(f"\n둘리 전체 사이즈 처리 완료 -> {OUT_DIR}")
