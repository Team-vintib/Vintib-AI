"""CatVTON의 fit_type(regular/oversized/cropped)이 상의(shirt)에서 실제로 다르게
작동하는지 철수로 확인한다.

AutoMasker의 fit_type별 동작(model/cloth_masker.py:165-198):
- regular: 기본 마스크
- oversized: 팔(forearm) 영역까지 마스크 포함 + 추가 팽창(여유 볼륨)
- cropped: torso 하단부를 마스크에서 제외(기장을 짧게)

레퍼런스는 alpha_1/shirt.png(플랫레이) 그대로 사용 -- 상의는 오늘 길이 불일치 문제가
없었던 케이스라(철수 원본도 반팔) worn-reference 없이도 비교 가능하다.
"""

import os

import numpy as np
import torch
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image

from model.cloth_masker import AutoMasker
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding

OUT_DIR = "fit_types_result"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
FIT_TYPES = ["regular", "oversized", "cropped"]

PERSON_PATH = os.path.join("..", "models_ai_generated", "cheolsu.png")
SHIRT_PATH = os.path.join("image", "alpha_1", "shirt.png")

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


person_image = Image.open(PERSON_PATH).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))
shirt_image = Image.open(SHIRT_PATH).convert("RGB")
shirt_image = resize_and_padding(shirt_image, (WIDTH, HEIGHT))

generator = torch.Generator(device="cuda").manual_seed(42)

for fit_type in FIT_TYPES:
    upper_mask = automasker(person_image, mask_type="upper", fit_type=fit_type)["mask"]
    upper_mask = mask_processor.blur(upper_mask, blur_factor=9)

    print(f"=== 생성: cheolsu + shirt, fit_type={fit_type} ===")
    result_image = pipeline(
        image=person_image,
        condition_image=shirt_image,
        mask=upper_mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]

    final = composite_with_original(person_image, result_image, upper_mask)
    out_path = os.path.join(OUT_DIR, f"tryon_cheolsu_upper_{fit_type}.png")
    final.save(out_path)
    mask_out_path = os.path.join(OUT_DIR, f"mask_cheolsu_upper_{fit_type}.png")
    upper_mask.save(mask_out_path)
    print(f"완료 -> {out_path} (마스크: {mask_out_path})")

print("모든 fit_type 처리 완료")
