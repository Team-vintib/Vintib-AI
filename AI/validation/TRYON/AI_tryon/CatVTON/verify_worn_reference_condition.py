"""체형별로 따로 만든 "실제로 입은 사람" 레퍼런스(FLUX 생성)를 condition_image로 써서
CatVTON 하의 시착을 재시도한다.

1차 시도(같은 마른 체형 레퍼런스를 셋 다에게 재사용)는 철수는 완벽, 영희는 부분 성공,
둘리는 거의 실패였다 -- 체형이 안 맞아서 신호가 약해졌을 가능성. 이번엔 각자 자기 체형에
맞는 레퍼런스(`worn_references/pants_worn_reference_{name}.png`)를 쓴다. 마스크는 그대로
(체형 자체·마스크 크기는 안 건드림) -- 오직 레퍼런스 이미지만 바꾼다.
"""

import os

import torch
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image

from model.cloth_masker import AutoMasker
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding

OUT_DIR = "result/worn_reference_matched_result"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
FIT_TYPE = "regular"
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

PEOPLE = {
    "cheolsu": os.path.join("..", "models_ai_generated", "cheolsu.png"),
    "younghee": os.path.join("..", "models_ai_generated", "younghee.png"),
    "dooly": os.path.join("..", "models_ai_generated", "dooly.png"),
}
WORN_REF_DIR = "result/worn_references"

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

import numpy as np


def composite_with_original(original_image, generated_image, mask):
    original_np = np.array(original_image.resize(generated_image.size)).astype(np.float32)
    generated_np = np.array(generated_image).astype(np.float32)
    mask_np = np.array(mask.resize(generated_image.size).convert("L")).astype(np.float32) / 255.0
    mask_np = np.expand_dims(mask_np, axis=-1)
    composited = generated_np * mask_np + original_np * (1 - mask_np)
    return Image.fromarray(composited.astype(np.uint8))


generator = torch.Generator(device="cuda").manual_seed(42)

for person_name, person_path in PEOPLE.items():
    person_image = Image.open(person_path).convert("RGB")
    person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

    worn_ref_path = os.path.join(WORN_REF_DIR, f"pants_worn_reference_{person_name}.png")
    worn_ref_image = Image.open(worn_ref_path).convert("RGB")
    worn_ref_image = resize_and_padding(worn_ref_image, (WIDTH, HEIGHT))

    lower_mask = automasker(person_image, mask_type="lower", fit_type=FIT_TYPE)["mask"]
    lower_mask = mask_processor.blur(lower_mask, blur_factor=9)

    print(f"=== 생성: {person_name} + 체형매칭 worn-reference 반바지(하의) ===")
    result_image = pipeline(
        image=person_image,
        condition_image=worn_ref_image,
        mask=lower_mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]

    final = composite_with_original(person_image, result_image, lower_mask)
    out_path = os.path.join(OUT_DIR, f"tryon_{person_name}_lower_matched_ref.png")
    final.save(out_path)
    print(f"완료 -> {out_path}")

print("모든 인물 처리 완료")
