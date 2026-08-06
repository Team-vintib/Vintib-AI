"""CatVTON 표준 입력(image=사람, condition_image=옷) 구조를 그대로 쓰되, `image` 자리에
원본 사람 사진 대신 worn-reference(FLUX가 그린 "이 사이즈를 입은 모습")를 넣고,
`condition_image`엔 실제 상품 사진(`top.jpg`, 정확한 그래픽)을 넣는다.

핵심 아이디어: AutoMasker는 DensePose(신체 부위)뿐 아니라 SCHP(의류 파싱)도 같이 써서
마스크를 잡는다(`model/cloth_masker.py`) -- worn-reference 사진에 이미 타이트/루즈한
실루엣이 그려져 있으면, SCHP가 그 실제 옷 윤곽을 그대로 마스크로 잡아줄 것이다. 그러면
"마스크 모양 자체가 핏을 반영"하게 되고, 그 안을 실제 상품 사진으로 채우면 그래픽도
정확해진다 -- 파이프라인 구조 변경이 전혀 필요 없다.

한 사이즈(XXL, 가장 루즈한 케이스라 마스크 모양 차이가 가장 잘 보일 것)로 빠르게
확인한다.
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

OUT_DIR = "result/top_worn_ref_as_person"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

PERSON_NAME = "heedongi"
SIZE_LABEL = "XXL"  # 가장 루즈한 케이스 -- 마스크 모양 차이가 제일 잘 보일 것
WORN_REF_PATH = os.path.join("result", "worn_references", f"top_worn_reference_{PERSON_NAME}_{SIZE_LABEL}.png")
REAL_GARMENT_PATH = os.path.join("image", "alpha_3", "top.jpg")

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


worn_ref_image = Image.open(WORN_REF_PATH).convert("RGB")
worn_ref_image = resize_and_crop(worn_ref_image, (WIDTH, HEIGHT))  # 이번엔 "사람" 역할이라 crop

real_garment_image = Image.open(REAL_GARMENT_PATH).convert("RGB")
real_garment_image = resize_and_padding(real_garment_image, (WIDTH, HEIGHT))

# worn-reference 자체를 "사람"으로 놓고 마스크를 새로 계산한다 -- 여기서 헐렁한 실루엣이
# 마스크에 반영되는지가 이 실험의 핵심 확인 포인트다.
upper_mask = automasker(worn_ref_image, mask_type="upper", fit_type="regular")["mask"]
vis_mask(worn_ref_image, upper_mask).save(os.path.join(OUT_DIR, f"mask_on_worn_ref_{PERSON_NAME}_{SIZE_LABEL}.png"))
upper_mask_blurred = mask_processor.blur(upper_mask, blur_factor=2)

generator = torch.Generator(device="cuda").manual_seed(42)

print(f"\n=== 생성: {PERSON_NAME}_{SIZE_LABEL} (image=worn-reference, condition=실제 상품 사진) ===")
result_image = pipeline(
    image=worn_ref_image,
    condition_image=real_garment_image,
    mask=upper_mask_blurred,
    num_inference_steps=NUM_INFERENCE_STEPS,
    guidance_scale=GUIDANCE_SCALE,
    generator=generator,
)[0]
final = composite_with_original(worn_ref_image, result_image, upper_mask_blurred)

out_path = os.path.join(OUT_DIR, f"tryon_{PERSON_NAME}_{SIZE_LABEL}_wornrefasperson.png")
final.save(out_path)
print(f"완료 -> {out_path}")
