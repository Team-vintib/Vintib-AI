"""반팔/반바지 갭 채우기를 "본인 피부 패치" 대신 "텍스트 프롬프트"(cross-attention 되살리기,
`CatVTONPipeline.generate_from_text`)로 채운 person1/person2 결과를 만든다.

Before(Option A, 본인 피부 패치): `result/alpha_test_gap_20260731_124316/`
After(Option B, 텍스트 프롬프트): 이 스크립트의 출력 폴더

프로덕션 코드(`worker/models/catvton`)를 그대로 쓴다.
"""

import os
import sys
from datetime import datetime

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_PRODUCTION_CATVTON_PATH = os.path.join(_REPO_ROOT, "worker", "models", "catvton")
sys.path.insert(0, _PRODUCTION_CATVTON_PATH)

import numpy as np  # noqa: E402
import torch  # noqa: E402
from diffusers.image_processor import VaeImageProcessor  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from PIL import Image  # noqa: E402

from model.adaptive_fit import classify_garment_length  # noqa: E402
from model.cloth_masker import AutoMasker, split_mask_by_gap, vis_mask  # noqa: E402
from model.pipeline import CatVTONPipeline  # noqa: E402
from utils import init_weight_dtype, resize_and_crop, resize_and_padding  # noqa: E402

_GAP_FILL_PROMPTS = {
    "forearms": "bare skin, forearm, natural skin texture, photorealistic",
    "legs": "bare skin, lower leg, natural skin texture, photorealistic",
}
_GAP_FILL_NEGATIVE_PROMPT = "clothing, fabric, sleeve, sock, pants, jacket, pattern, seam"


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

OUT_DIR = os.path.join("result", "alpha_test_gap_textprompt_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 15  # 빠른 검증 우선(사용자 지시)

generator = torch.Generator(device="cuda").manual_seed(42)


def generate_garment(base_image, condition_image, mask):
    result_image = pipeline(
        image=base_image,
        condition_image=condition_image,
        mask=mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]
    return composite_with_original(base_image, result_image, mask)


def generate_skin(base_image, mask, prompt):
    result_image = pipeline.generate_from_text(
        image=base_image,
        mask=mask,
        prompt=prompt,
        negative_prompt=_GAP_FILL_NEGATIVE_PROMPT,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=7.5,
        generator=generator,
    )
    return composite_with_original(base_image, result_image, mask)


def run_case(label, person_path, mask_type, cloth_path, garment_measurements, gap_part):
    print(f"--- {label} ---")
    person_image = resize_and_crop(Image.open(person_path).convert("RGB"), (WIDTH, HEIGHT))
    cloth_image = resize_and_padding(Image.open(cloth_path).convert("RGB"), (WIDTH, HEIGHT))

    mask_result = automasker(person_image, mask_type=mask_type, fit_type="regular")
    raw_mask = mask_result["mask"]
    densepose_np = np.array(mask_result["densepose"])

    length_class = classify_garment_length(mask_type, garment_measurements)
    print(f"    classify_garment_length -> {length_class}")
    garment_mask_np, gap_mask_np = split_mask_by_gap(np.array(raw_mask) // 255, densepose_np, gap_part)
    print(f"    gap pixel count -> {int(gap_mask_np.sum())}")

    garment_mask = mask_processor.blur(Image.fromarray(garment_mask_np * 255), blur_factor=9)
    gap_mask = mask_processor.blur(Image.fromarray(gap_mask_np * 255), blur_factor=9)
    vis_mask(person_image, Image.fromarray(gap_mask_np * 255)).save(os.path.join(OUT_DIR, f"{label}_gap_mask.png"))

    after_skin = generate_skin(person_image, gap_mask, _GAP_FILL_PROMPTS[gap_part])
    after_skin.save(os.path.join(OUT_DIR, f"{label}_after_skin.png"))

    final_result = generate_garment(after_skin, cloth_image, garment_mask)
    final_result.save(os.path.join(OUT_DIR, f"{label}_tryon.png"))


print("\n=== person1: 긴팔 원본 + 반팔 셔츠(텍스트 프롬프트 갭 채우기) ===")
run_case(
    "alpha1_person1_shirt",
    "image/alpha_1/person.png",
    "upper",
    "image/alpha_1/shirt.png",
    {"SLEEVE_LENGTH": 22.0},
    "forearms",
)

print("\n=== person2: 긴바지 원본 + 반바지(텍스트 프롬프트 갭 채우기) ===")
run_case(
    "alpha2_person_pants",
    "image/alpha_2/person.png",
    "lower",
    "image/alpha_2/pants.png",
    {"OUTSEAM_LENGTH": 40.0},
    "legs",
)

print(f"\n완료 -> {OUT_DIR}/ vs result/alpha_test_gap_20260731_124316/(Before, 피부 패치) 비교")
