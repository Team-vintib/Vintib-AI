"""영희/둘리/마이콜에게도 알파테스트3 청바지를 사이즈표(M/L/XL/2XL)대로 입혀서
`verify_size_fit_alpha3_jeans_cheolsu.py`(철수)와 같은 검증을 나머지 체형으로 확장한다.

세 사람 다 원본 사진이 이미 긴 청바지를 입고 있어서(§9.2에서 통일한 768x1024 AI 모델
사진들, 공통 프롬프트에 jeans 포함) 철수 때와 마찬가지로 worn-reference/attention
부스팅 없이 flat-lay 그대로 condition_image로 쓴다 -- 길이 미스매치가 없다.

허리둘레 가정값은 기존 검증(`verify_size_fit_combined.py`)과 동일하게 영희=65cm,
둘리=110cm를 그대로 쓰고, 마이콜(키 크고 마른 남성)은 철수(75cm)보다 살짝 슬림하게
72cm로 가정한다.
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

OUT_DIR = os.path.join("result", "size_fit_alpha3_jeans_all_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

# (person_image, 가정 허리둘레cm) -- 철수(75cm)는 verify_size_fit_alpha3_jeans_cheolsu.py에서
# 이미 검증했으므로 나머지 세 체형만 돈다.
PEOPLE = {
    "younghee": ("younghee.png", 65.0),
    "dooly": ("dooly.png", 110.0),
    "maikol": ("maikol.png", 72.0),
}
# "허리단면" 표 -> WAIST_WIDTH에 그대로 사용(이미 평평하게 잰 폭)
SIZE_TABLE_WAIST_WIDTH_CM = {"M": 40.0, "L": 42.5, "XL": 45.0, "2XL": 47.5}

LOWER_PATH = os.path.join("image", "alpha_3", "jeans_cropped.png")
_MODELS_DIR = os.path.join("..", "models_ai_generated")

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


jeans_image = Image.open(LOWER_PATH).convert("RGB")
jeans_image = resize_and_padding(jeans_image, (WIDTH, HEIGHT))

for person_name, (person_file, waist_cm) in PEOPLE.items():
    person_image = Image.open(os.path.join(_MODELS_DIR, person_file)).convert("RGB")
    person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

    for size_label, garment_waist_width_cm in SIZE_TABLE_WAIST_WIDTH_CM.items():
        generator = torch.Generator(device="cuda").manual_seed(42)

        print(f"\n=== {person_name} {size_label} (WAIST_WIDTH {garment_waist_width_cm}cm, 허리 {waist_cm}cm) ===")
        lower_mask = automasker(
            person_image,
            mask_type="lower",
            fit_type="regular",
            body_measurements={"waist_cm": waist_cm},
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

        out_path = os.path.join(OUT_DIR, f"tryon_{person_name}_{size_label}.png")
        final.save(out_path)
        print(f"완료 -> {out_path}")

print(f"\n모든 인물 x 사이즈 처리 완료 -> {OUT_DIR}")
