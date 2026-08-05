"""옵션 B: CatVTON을 2단계로 순차 실행한다.

1단계: worn-reference(핏 정보)로 CatVTON을 돌려서 사람이 타이트/루즈가 반영된 옷을 입은
결과를 만든다(이미 생성된 결과를 재사용).
2단계: 1단계 결과를 새 "사람" 입력으로 삼아, 실제 상품 사진(`top.jpg`, 정확한 그래픽)을
condition_image로 다시 CatVTON을 돌린다 -- 같은 마스크를 다시 쓰면 CatVTON이 1단계의
핏(실루엣)을 유지한 채 그래픽만 정확하게 바꿔줄지, 아니면 마스크 안을 완전히 새로
그려서 1단계 효과가 사라질지 확인한다.
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

OUT_DIR = "result/top_two_stage"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

PERSON_NAME = "heedongi"
SIZE_LABEL = "S"
STAGE1_RESULT_PATH = os.path.join(
    "result", "size_fit_alpha3_top_fitaware_20260804_160815", f"tryon_{PERSON_NAME}_{SIZE_LABEL}.png"
)
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


# 2단계 입력 = 1단계 결과(이미 핏이 반영된 이미지)
stage1_image = Image.open(STAGE1_RESULT_PATH).convert("RGB")
stage1_image = resize_and_crop(stage1_image, (WIDTH, HEIGHT))

real_garment_image = Image.open(REAL_GARMENT_PATH).convert("RGB")
real_garment_image = resize_and_padding(real_garment_image, (WIDTH, HEIGHT))

# 마스크는 1단계와 동일한 조건(같은 사람, 같은 mask_type)으로 새로 계산 -- 1단계 결과
# 이미지 기준으로 다시 계산해도 실질적으로 같은 마스크가 나온다(옷 입은 채로도 상체
# 영역은 DensePose로 잡히므로).
upper_mask = automasker(stage1_image, mask_type="upper", fit_type="regular")["mask"]
upper_mask = mask_processor.blur(upper_mask, blur_factor=2)

generator = torch.Generator(device="cuda").manual_seed(42)

print(f"\n=== 2단계: {PERSON_NAME}_{SIZE_LABEL} (1단계 결과 + 실제 상품 사진) ===")
result_image = pipeline(
    image=stage1_image,
    condition_image=real_garment_image,
    mask=upper_mask,
    num_inference_steps=NUM_INFERENCE_STEPS,
    guidance_scale=GUIDANCE_SCALE,
    generator=generator,
)[0]
final = composite_with_original(stage1_image, result_image, upper_mask)

out_path = os.path.join(OUT_DIR, f"tryon_{PERSON_NAME}_{SIZE_LABEL}_stage2.png")
final.save(out_path)
print(f"완료 -> {out_path}")
