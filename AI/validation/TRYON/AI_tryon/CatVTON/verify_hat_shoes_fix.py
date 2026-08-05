"""`_hat_mask`/`_shoes_mask` 수정 후 결과를 검증한다.

- 모자: 얼굴 영역을 "피해서" 그리는 대신, 얼굴이 시작되는 행 위쪽만 깨끗하게 잘라 쓰도록
  바꿨다 — 마스크 경계가 얼굴 윤곽을 따라 울퉁불퉁해지지 않고 수평선 하나로 단순해진다.
- 신발: bbox를 사각형으로 채우던 방식 대신, 실제 발/신발 윤곽을 세로 방향 커널로 dilate해서
  위쪽(발목)으로만 자연스럽게 늘어나게 바꿨다 — 뻣뻣한 사각 블록 대신 발 모양이 유지된다.

이 스냅샷(`AI/validation/TRYON/AI_tryon/CatVTON/`)의 로컬 `model.` 코드를 그대로 쓴다.

pytest 안 걸림 — `python verify_hat_shoes_fix.py`로 직접 실행 후 `result/`에 저장된 PNG를
육안 확인한다.
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

OUT_DIR = os.path.join("result", "hat_shoes_fix_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
PERSON_PATH = "image/person.jpg"

ITEMS = [
    ("hat", "hat", "image/hat.jpg"),
    ("shoes", "shoes", "image/shoes.jpg"),
]

person_image = Image.open(PERSON_PATH).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

generator = torch.Generator(device="cuda").manual_seed(42)


def generate(base_image, condition_image, mask):
    result_image = pipeline(
        image=base_image,
        condition_image=condition_image,
        mask=mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]
    return composite_with_original(base_image, result_image, mask)


for label, mask_type, cloth_path in ITEMS:
    print(f"=== {label} ===")
    mask = automasker(person_image, mask_type=mask_type, fit_type="regular")["mask"]
    mask_blurred = mask_processor.blur(mask, blur_factor=9)
    cloth_image = resize_and_padding(Image.open(cloth_path).convert("RGB"), (WIDTH, HEIGHT))

    vis_mask(person_image, mask).save(os.path.join(OUT_DIR, f"{label}_mask.png"))
    result = generate(person_image, cloth_image, mask_blurred)
    result.save(os.path.join(OUT_DIR, f"{label}_tryon.png"))

print(f"\n완료 -> {OUT_DIR}/ 안의 hat_*.png / shoes_*.png 확인")
