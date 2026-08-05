"""아우터(재킷) 4사이즈(M/L/XL/XXL) x 희동이 1명에 대해, 방금 상의(그래픽 티셔츠)에서
검증된 "worn-reference-as-person" 방식(`verify_top_worn_ref_as_person.py`)을 그대로
재사용한다: `image` 자리에 FLUX가 그린 fit-aware worn-reference를, `condition_image`
자리에 실제 상품 사진(`outer.jpg`)을 넣고, 마스크는 worn-reference 위에서 새로
계산한다(SCHP가 이미 그려진 핏 실루엣을 그대로 마스크 모양으로 잡아준다).

아우터는 그래픽이 없는 민무늬 재킷이라 이 실험의 핵심 확인 포인트는 그래픽 정확도가
아니라, 칼라/버튼/포켓 등 구조가 있는 재킷에서도 마스크가 핏(품)을 제대로 반영하고
CatVTON이 그 구조를 자연스럽게 유지하는지다.
"""

import os

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
SIZE_LABELS = ["M", "L", "XL", "XXL"]
REAL_GARMENT_PATH = os.path.join("image", "alpha_3", "outer.jpg")

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

for size_label in SIZE_LABELS:
    worn_ref_path = os.path.join("result", "worn_references", f"outer_worn_reference_{PERSON_NAME}_{size_label}.png")
    worn_ref_image = Image.open(worn_ref_path).convert("RGB")
    worn_ref_image = resize_and_crop(worn_ref_image, (WIDTH, HEIGHT))

    upper_mask = automasker(worn_ref_image, mask_type="upper", fit_type="regular")["mask"]
    vis_mask(worn_ref_image, upper_mask).save(os.path.join(OUT_DIR, f"mask_on_worn_ref_{PERSON_NAME}_{size_label}.png"))
    upper_mask_blurred = mask_processor.blur(upper_mask, blur_factor=2)

    generator = torch.Generator(device="cuda").manual_seed(42)

    print(f"\n=== 생성: {PERSON_NAME}_{size_label} (image=worn-reference, condition=실제 상품 사진) ===")
    result_image = pipeline(
        image=worn_ref_image,
        condition_image=real_garment_image,
        mask=upper_mask_blurred,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]
    final = composite_with_original(worn_ref_image, result_image, upper_mask_blurred)

    out_path = os.path.join(OUT_DIR, f"tryon_{PERSON_NAME}_{size_label}_wornrefasperson.png")
    final.save(out_path)
    print(f"완료 -> {out_path}")

print("\n=== 전체 완료 ===")
