"""4명(철수/영희/둘리/마이콜) x 4사이즈(M/L/XL/2XL) 전체에 fit-aware worn-reference
(`generate_worn_reference_jeans_fitaware.py`가 생성)를 condition_image로 써서 청바지를
입힌다.

**이번엔 AutoMasker에 body_measurements/garment_measurements를 안 넘긴다** -- §9에서
마스크 침식/팽창(width_ratio 경로)만으로 타이트/루즈를 표현하려 했더니, (1) 조정량이
작으면 육안상 차이가 안 보이고, (2) 조정량이 커도 "침식이 클수록 마스크 밖의(이미
편안하게 맞는) 원본이 더 많이 남아서 오히려 루즈해 보이는" 역설적인 효과가 확인됐다.
두 신호(마스크 지오메트리 + 레퍼런스 이미지)를 같이 켜두면 서로 반대 방향으로 작용해
결과가 더 헷갈릴 수 있어서, 이번 테스트는 레퍼런스 이미지 하나로만 타이트/루즈 신호를
주고 마스크는 `fit_type="regular"` 고정값으로 둔다.

원본 사진들이 이미 긴 청바지를 입고 있어서 worn-reference/attention 부스팅(§8, 길이
불일치 픽스)도 이번엔 불필요하다.
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

OUT_DIR = os.path.join("result", "size_fit_alpha3_jeans_fitaware_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

PEOPLE = ["cheolsu", "younghee", "dooly", "maikol"]
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


for person_name in PEOPLE:
    person_image = Image.open(os.path.join(_MODELS_DIR, f"{person_name}.png")).convert("RGB")
    person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

    lower_mask = automasker(person_image, mask_type="lower", fit_type="regular")["mask"]
    lower_mask = mask_processor.blur(lower_mask, blur_factor=2)  # §9.3 -- 9면 마스크 경계에 고스트/틈이 생긴다

    for size_label in SIZES:
        generator = torch.Generator(device="cuda").manual_seed(42)

        worn_ref_path = os.path.join(_WORN_REF_DIR, f"jeans_worn_reference_{person_name}_{size_label}.png")
        worn_ref_image = Image.open(worn_ref_path).convert("RGB")
        worn_ref_image = resize_and_padding(worn_ref_image, (WIDTH, HEIGHT))

        print(f"\n=== {person_name} {size_label} ===")
        result_image = pipeline(
            image=person_image,
            condition_image=worn_ref_image,
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
