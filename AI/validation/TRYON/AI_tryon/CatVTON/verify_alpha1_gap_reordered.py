"""person1(긴팔 원본) + 반팔 셔츠 케이스를 "의류 패스 먼저, 스킨 패스 나중" 순서로 다시
만들어서, 기존 순서(스킨 먼저 -> 의류 나중)와 비교한다.

진단 이미지(`analysis_alpha1_person1_shirt/`)로 확인한 문제: 스킨 패스를 먼저 하면, 그
시점엔 갭(팔뚝) 바로 옆에 아직 원래 재킷이 그대로 남아있어서 diffusion이 스킨 패치보다
그 재킷 색을 더 강하게 이어 그린다. 순서를 바꾸면 스킨 패스를 할 시점엔 옆이 이미 새
셔츠(반팔)로 바뀌어 있으니 다를 수 있다 — 가설을 실제로 돌려서 확인한다.

이 스크립트는 프로덕션 코드(`worker/models/catvton`)를 바꾸지 않는다 — 순서를 실제로
바꿔야 할지부터 먼저 결과로 확인하기 위한 실험용 스크립트다(기존 verify_*.py 관례).
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
from model.cloth_masker import AutoMasker, extract_skin_patch, split_mask_by_gap, vis_mask  # noqa: E402
from model.pipeline import CatVTONPipeline  # noqa: E402
from utils import init_weight_dtype, resize_and_crop, resize_and_padding  # noqa: E402


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

OUT_DIR = os.path.join("result", "alpha1_gap_reordered_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

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


person_image = resize_and_crop(Image.open("image/alpha_1/person.png").convert("RGB"), (WIDTH, HEIGHT))
cloth_image = resize_and_padding(Image.open("image/alpha_1/shirt.png").convert("RGB"), (WIDTH, HEIGHT))

mask_result = automasker(person_image, mask_type="upper", fit_type="regular")
raw_mask = mask_result["mask"]
densepose_np = np.array(mask_result["densepose"])

length_class = classify_garment_length("upper", {"SLEEVE_LENGTH": 22.0})
garment_mask_np, gap_mask_np = split_mask_by_gap(np.array(raw_mask) // 255, densepose_np, "forearms")
print(f"classify_garment_length -> {length_class}, gap pixel 수 -> {int(gap_mask_np.sum())}")

garment_mask = mask_processor.blur(Image.fromarray(garment_mask_np * 255), blur_factor=9)
gap_mask = mask_processor.blur(Image.fromarray(gap_mask_np * 255), blur_factor=9)
skin_patch = extract_skin_patch(person_image, densepose_np, np.array(mask_result["schp_lip"]))
skin_patch.resize((100, 100)).save(os.path.join(OUT_DIR, "skin_patch.png"))
vis_mask(person_image, Image.fromarray(garment_mask_np * 255)).save(os.path.join(OUT_DIR, "garment_mask.png"))
vis_mask(person_image, Image.fromarray(gap_mask_np * 255)).save(os.path.join(OUT_DIR, "gap_mask.png"))

# --- 순서 A(기존): 스킨 먼저 -> 의류 나중 -----------------------------------------
print("\n=== 순서 A: 스킨 패스 먼저 -> 의류 패스 나중(기존 순서) ===")
a_after_skin = generate(person_image, skin_patch, gap_mask)
a_after_skin.save(os.path.join(OUT_DIR, "orderA_1_after_skin.png"))
a_final = generate(a_after_skin, cloth_image, garment_mask)
a_final.save(os.path.join(OUT_DIR, "orderA_2_final.png"))

# --- 순서 B(제안): 의류 먼저 -> 스킨 나중 -----------------------------------------
print("\n=== 순서 B: 의류 패스 먼저 -> 스킨 패스 나중(제안 순서) ===")
b_after_garment = generate(person_image, cloth_image, garment_mask)
b_after_garment.save(os.path.join(OUT_DIR, "orderB_1_after_garment.png"))
b_final = generate(b_after_garment, skin_patch, gap_mask)
b_final.save(os.path.join(OUT_DIR, "orderB_2_final.png"))

print(f"\n완료 -> {OUT_DIR}/ 안의 orderA_2_final.png(기존) vs orderB_2_final.png(제안) 비교")
