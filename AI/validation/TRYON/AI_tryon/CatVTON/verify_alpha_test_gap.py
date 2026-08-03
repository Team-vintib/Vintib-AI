"""반팔/반바지 갭 채우기(`split_mask_by_gap`/`extract_skin_patch`)가 실제로 문제를 고치는지,
방금 문제를 발견한 바로 그 알파테스트 이미지로 확인한다.

- alpha1_person1_shirt: 긴팔 재킷 원본(`image/alpha_1/person.png`) + 반팔 셔츠 레퍼런스
  (`image/alpha_1/shirt.png`). 갭 채우기 없이 돌렸을 때 팔뚝이 원래 재킷과 비슷한 애매한
  톤으로 채워졌던 케이스(`result/alpha_test_20260731_103156/alpha1_person1_shirt_tryon.png`).
- alpha2_person_pants: 긴바지 원본(`image/alpha_2/person.png`) + 반바지 레퍼런스
  (`image/alpha_2/pants.png`). 갭 채우기 없이 돌렸을 때 반바지 원단이 발목까지 억지로
  늘어나거나 시스루로 채워졌던 케이스
  (`result/alpha_test_20260731_103156/alpha2_person_pants_tryon.png`).

실제 실측값이 없어서 `SLEEVE_LENGTH`/`OUTSEAM_LENGTH`는 데모값을 쓴다(레퍼런스 의류가
반팔/반바지라는 걸 분명히 판정시키기 위한 값 — 정확한 cm보다 "짧다고 판정되는지"가 중요).

프로덕션 코드(`worker/models/catvton`)를 그대로 쓴다 — 검증 대상이 실제 배포될 코드이기
때문이다. steps=50으로 이전 알파테스트 결과와 나란히 비교할 수 있게 맞춘다(기존 verify_*.py
관례).
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
from model.cloth_masker import (  # noqa: E402
    AutoMasker,
    extract_skin_patch,
    split_mask_by_gap,
    vis_mask,
)
from model.pipeline import CatVTONPipeline  # noqa: E402
from utils import init_weight_dtype, resize_and_crop, resize_and_padding  # noqa: E402

_GAP_DENSEPOSE_PART = {"upper": "forearms", "lower": "legs"}


def composite_with_original(original_image, generated_image, mask):
    """마스크 안쪽은 생성된 이미지, 바깥쪽은 원본 이미지를 사용해 합성한다."""
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

OUT_DIR = os.path.join("result", "alpha_test_gap_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

generator = torch.Generator(device="cuda").manual_seed(42)


def load_person(path):
    return resize_and_crop(Image.open(path).convert("RGB"), (WIDTH, HEIGHT))


def load_cloth(path):
    return resize_and_padding(Image.open(path).convert("RGB"), (WIDTH, HEIGHT))


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


def run_case(label, person_path, mask_type, cloth_path, garment_measurements):
    print(f"--- {label} ---")
    person_image = load_person(person_path)
    cloth_image = load_cloth(cloth_path)

    mask_result = automasker(person_image, mask_type=mask_type, fit_type="regular")
    raw_mask = mask_result["mask"]
    densepose_np = np.array(mask_result["densepose"])

    length_class = classify_garment_length(mask_type, garment_measurements)
    gap_part = _GAP_DENSEPOSE_PART.get(mask_type)
    print(f"    classify_garment_length -> {length_class}")

    gap_mask_np = None
    if length_class == "short" and gap_part is not None:
        garment_mask_np, gap_mask_np = split_mask_by_gap(
            np.array(raw_mask) // 255, densepose_np, gap_part
        )
        if not gap_mask_np.any():
            gap_mask_np = None
    print(f"    gap_fill_used -> {gap_mask_np is not None}")

    if gap_mask_np is None:
        # 갭 없음 — 기존 단일 패스(비교 기준선으로만 씀, 이 스크립트의 핵심 케이스는 전부 갭이 있음)
        mask = mask_processor.blur(raw_mask, blur_factor=9)
        vis_mask(person_image, raw_mask).save(os.path.join(OUT_DIR, f"{label}_mask.png"))
        result = generate(person_image, cloth_image, mask)
        result.save(os.path.join(OUT_DIR, f"{label}_tryon.png"))
        return

    skin_patch = extract_skin_patch(person_image, densepose_np, np.array(mask_result["schp_lip"]))
    gap_mask = mask_processor.blur(Image.fromarray(gap_mask_np * 255), blur_factor=9)
    garment_mask = mask_processor.blur(Image.fromarray(garment_mask_np * 255), blur_factor=9)

    vis_mask(person_image, Image.fromarray(gap_mask_np * 255)).save(
        os.path.join(OUT_DIR, f"{label}_gap_mask.png")
    )
    vis_mask(person_image, Image.fromarray(garment_mask_np * 255)).save(
        os.path.join(OUT_DIR, f"{label}_garment_mask.png")
    )
    skin_patch.resize((100, 100)).save(os.path.join(OUT_DIR, f"{label}_skin_patch.png"))

    skin_filled = generate(person_image, skin_patch, gap_mask)
    skin_filled.save(os.path.join(OUT_DIR, f"{label}_after_skin.png"))

    final_result = generate(skin_filled, cloth_image, garment_mask)
    final_result.save(os.path.join(OUT_DIR, f"{label}_tryon.png"))


print("\n=== 알파테스트1: 긴팔 원본 + 반팔 셔츠(갭 채우기) ===")
run_case(
    "alpha1_person1_shirt",
    "image/alpha_1/person.png",
    "upper",
    "image/alpha_1/shirt.png",
    {"SLEEVE_LENGTH": 22.0},
)

print("\n=== 알파테스트2: 긴바지 원본 + 반바지(갭 채우기) ===")
run_case(
    "alpha2_person_pants",
    "image/alpha_2/person.png",
    "lower",
    "image/alpha_2/pants.png",
    {"OUTSEAM_LENGTH": 40.0},
)

# --- 체형 교차 비교: 알파테스트2 인물(다른 체형)에 알파테스트1 상의를 입힌다 ------------------
# 원본이 이미 반팔(alpha_2/person.png)이라 갭 채우기는 안 탄다(단일 패스) — 순수하게 "같은
# 의류가 체형에 따라 어떻게 다르게 걸쳐지는지"만 보는 케이스다. alpha1_person1_shirt/
# alpha1_person2_shirt와 나란히 놓고 비교한다.
print("\n=== 체형 교차: 알파테스트2 인물 + 알파테스트1 상의 ===")
run_case(
    "cross_alpha2_person_alpha1_shirt",
    "image/alpha_2/person.png",
    "upper",
    "image/alpha_1/shirt.png",
    {"SLEEVE_LENGTH": 22.0},
)

print(f"\n완료 -> {OUT_DIR}/ 비교 대상: result/alpha_test_20260731_103156/ (갭 채우기 이전)")
