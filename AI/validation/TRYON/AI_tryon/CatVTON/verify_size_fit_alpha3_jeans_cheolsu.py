"""철수에게 알파테스트3 청바지(`jeans_cropped.png`)를 사이즈표(M/L/XL/2XL)대로 입혀서,
버뮤다 반바지(`verify_size_fit_alpha3_cheolsu.py`, scale_px=60)에서 사이즈 간 차이가
잘 안 보였던 게 "옷의 특성"(와이드핏+드로스트링이라 폭 차이가 원래 덜 도드라짐) 때문인지
확인한다. 청바지는 스트레이트핏이라 몸에 더 붙는 편이라 같은 scale_px에서도 차이가 더
잘 보일 거라는 가설이다.

사이즈표는 "허리**단면**"(이미 평평하게 잰 폭, `WAIST_WIDTH`와 동일 정의)이라 2로 안 나누고
그대로 쓴다: M=40 L=42.5 XL=45 2XL=47.5cm.

철수의 원본 사진(`models_ai_generated/cheolsu.png`)이 이미 긴바지를 입고 있어서, 이번엔
레퍼런스(청바지)도 원본과 길이가 비슷하다 -- §8의 worn-reference/attention 부스팅은
"짧은 레퍼런스 vs 긴 원본" 길이 불일치를 고치는 기법이라 여기선 불필요하다. flat-lay
그대로 condition_image로 써서 폭 축만 순수하게 테스트한다(하의만, 상의 없음).
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

OUT_DIR = os.path.join("result", "size_fit_alpha3_jeans_cheolsu_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

CHEOLSU_WAIST_CM = 75.0  # 다른 검증들과 동일한 가정값
# "허리단면" 표 -> WAIST_WIDTH에 그대로 사용(이미 평평하게 잰 폭)
SIZE_TABLE_WAIST_WIDTH_CM = {"M": 40.0, "L": 42.5, "XL": 45.0, "2XL": 47.5}

LOWER_PATH = os.path.join("image", "alpha_3", "jeans_cropped.png")
PERSON_PATH = os.path.join("..", "models_ai_generated", "cheolsu.png")

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

jeans_image = Image.open(LOWER_PATH).convert("RGB")
jeans_image = resize_and_padding(jeans_image, (WIDTH, HEIGHT))

for size_label, garment_waist_width_cm in SIZE_TABLE_WAIST_WIDTH_CM.items():
    generator = torch.Generator(device="cuda").manual_seed(42)

    print(f"\n=== {size_label} (WAIST_WIDTH {garment_waist_width_cm}cm, 철수 허리 {CHEOLSU_WAIST_CM}cm) ===")
    lower_mask = automasker(
        person_image,
        mask_type="lower",
        fit_type="regular",
        body_measurements={"waist_cm": CHEOLSU_WAIST_CM},
        garment_measurements={"WAIST_WIDTH": garment_waist_width_cm},
    )["mask"]
    lower_mask = mask_processor.blur(lower_mask, blur_factor=2)

    result_image = pipeline(
        image=person_image,
        condition_image=jeans_image,
        mask=lower_mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]
    final = composite_with_original(person_image, result_image, lower_mask)

    out_path = os.path.join(OUT_DIR, f"tryon_cheolsu_{size_label}.png")
    final.save(out_path)
    print(f"완료 -> {out_path}")

print(f"\n모든 사이즈 처리 완료 -> {OUT_DIR}")
