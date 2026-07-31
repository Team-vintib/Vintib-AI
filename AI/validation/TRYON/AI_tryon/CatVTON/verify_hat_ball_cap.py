"""수정된 `_hat_mask`가 볼캡(챙이 좁고 낮은 스타일)에서도 잘 동작하는지 확인한다.

앞서 `hat.jpg`(고깔형)로는 확인했으니, 형태가 많이 다른 `ball_cap.jpg`로 한 번 더 검증한다.
"""

import os
from datetime import datetime

import numpy as np
import torch
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image

from model.cloth_masker import AutoMasker, vis_mask
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding


def composite_with_original(original_image, generated_image, mask):
    original_np = np.array(original_image.resize(generated_image.size)).astype(np.float32)
    generated_np = np.array(generated_image).astype(np.float32)
    mask_np = np.array(mask.resize(generated_image.size).convert("L")).astype(np.float32) / 255.0
    mask_np = np.expand_dims(mask_np, axis=-1)
    composited = generated_np * mask_np + original_np * (1 - mask_np)
    return Image.fromarray(composited.astype(np.uint8))


def _bypass_safety_checker(self, image):
    has_nsfw_concept = [False] * len(image) if isinstance(image, list) else [False]
    return image, has_nsfw_concept


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
pipeline.run_safety_checker = _bypass_safety_checker.__get__(pipeline)

mask_processor = VaeImageProcessor(
    vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True
)
automasker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device="cuda",
)
print("초기화 완료")

OUT_DIR = os.path.join("result", "hat_ball_cap_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
PERSON_PATH = "image/person.jpg"
CAP_PATH = "image/ball_cap.jpg"

person_image = Image.open(PERSON_PATH).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))
cap_image = resize_and_padding(Image.open(CAP_PATH).convert("RGB"), (WIDTH, HEIGHT))

generator = torch.Generator(device="cuda").manual_seed(42)

mask = automasker(person_image, mask_type="hat", fit_type="regular")["mask"]
mask_blurred = mask_processor.blur(mask, blur_factor=9)
vis_mask(person_image, mask).save(os.path.join(OUT_DIR, "ball_cap_mask.png"))

result_image = pipeline(
    image=person_image,
    condition_image=cap_image,
    mask=mask_blurred,
    num_inference_steps=NUM_INFERENCE_STEPS,
    guidance_scale=GUIDANCE_SCALE,
    generator=generator,
)[0]
result = composite_with_original(person_image, result_image, mask_blurred)
result.save(os.path.join(OUT_DIR, "ball_cap_tryon.png"))

print(f"완료 -> {OUT_DIR}/ball_cap_tryon.png 확인")
