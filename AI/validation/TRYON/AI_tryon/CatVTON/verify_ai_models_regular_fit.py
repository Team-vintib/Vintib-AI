"""CatVTON(레귤러 핏)으로 AI 생성 모델(철수/영희/둘리)에게 알파테스트 의류를 입혀본다.

FASHN VTON은 "모델이 알아서 예쁘게 맞춰 입히는" 방식이라, 실제 의류 실측 치수와 무관하게
옷이 사람 체형에 맞춰 늘었다 줄었다 하는 문제가 있었다(둘리 케이스에서 확인) — 중고 거래
플랫폼에서는 "이 실제 옷이 이 사람 몸에 어떻게 보이는지"가 중요하므로, 옷 크기 자체는
고정하고 체형에 맞춰 핏이 달라지는(타이트/루즈해 보이는) CatVTON 쪽이 목적에 더 맞는다는
판단으로 되돌아왔다. `verify_fit_tryon.py`(레귤러 핏 검증)와 같은 구조를 재사용한다.

FASHN VTON 테스트와 같은 조건(같은 의류: alpha_1/shirt.png, alpha_2/pants.png)으로 비교
가능하게 맞춘다.
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


def composite_with_original(
    original_image: Image.Image,
    generated_image: Image.Image,
    mask: Image.Image,
) -> Image.Image:
    original_np = np.array(original_image.resize(generated_image.size)).astype(np.float32)
    generated_np = np.array(generated_image).astype(np.float32)

    mask_np = np.array(mask.resize(generated_image.size).convert("L")).astype(np.float32) / 255.0
    mask_np = np.expand_dims(mask_np, axis=-1)

    composited = generated_np * mask_np + original_np * (1 - mask_np)
    return Image.fromarray(composited.astype(np.uint8))


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

OUT_DIR = os.path.join("result", "ai_models_regular_fit_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
FIT_TYPE = "regular"
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

_MODELS_DIR = os.path.join("..", "models_ai_generated")
PERSONS = {
    "cheolsu": os.path.join(_MODELS_DIR, "cheolsu.png"),
    "younghee": os.path.join(_MODELS_DIR, "younghee.png"),
    "dooly": os.path.join(_MODELS_DIR, "dooly.png"),
}
UPPER_CLOTH_PATH = os.path.join("image", "alpha_1", "shirt.png")
LOWER_CLOTH_PATH = os.path.join("image", "alpha_2", "pants.png")

print("=== 입력 이미지 로드 ===")
upper_cloth_image = Image.open(UPPER_CLOTH_PATH).convert("RGB")
upper_cloth_image = resize_and_padding(upper_cloth_image, (WIDTH, HEIGHT))
lower_cloth_image = Image.open(LOWER_CLOTH_PATH).convert("RGB")
lower_cloth_image = resize_and_padding(lower_cloth_image, (WIDTH, HEIGHT))

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


for person_name, person_path in PERSONS.items():
    person_image = Image.open(person_path).convert("RGB")
    person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

    upper_mask = automasker(person_image, mask_type="upper", fit_type=FIT_TYPE)["mask"]
    upper_mask = mask_processor.blur(upper_mask, blur_factor=9)
    lower_mask = automasker(person_image, mask_type="lower", fit_type=FIT_TYPE)["mask"]
    lower_mask = mask_processor.blur(lower_mask, blur_factor=9)

    print(f"=== {person_name}: 상의만 ===")
    upper_only = generate(person_image, upper_cloth_image, upper_mask)
    upper_only.save(os.path.join(OUT_DIR, f"tryon_{person_name}_upper.png"))

    print(f"=== {person_name}: 하의만 ===")
    lower_only = generate(person_image, lower_cloth_image, lower_mask)
    lower_only.save(os.path.join(OUT_DIR, f"tryon_{person_name}_lower.png"))

    print(f"=== {person_name}: 상의+하의 ===")
    both = generate(upper_only, lower_cloth_image, lower_mask)
    both.save(os.path.join(OUT_DIR, f"tryon_{person_name}_both.png"))

    print(f"{person_name} 완료 -> {OUT_DIR}/tryon_{person_name}_{{upper,lower,both}}.png")

print(f"모든 인물 x 조합 처리 완료 -> {OUT_DIR}")
