import os
from datetime import datetime

import torch
from huggingface_hub import snapshot_download
from PIL import Image
from diffusers.image_processor import VaeImageProcessor

from model.cloth_masker import AutoMasker, vis_mask
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding

import numpy as np

def composite_with_original(
    original_image: Image.Image,
    generated_image: Image.Image,
    mask: Image.Image,
) -> Image.Image:
    """
    마스크 안쪽은 생성된 이미지, 마스크 바깥쪽은 원본 이미지를 사용해 합성한다.
    """
    original_np = np.array(original_image.resize(generated_image.size)).astype(np.float32)
    generated_np = np.array(generated_image).astype(np.float32)

    mask_np = np.array(mask.resize(generated_image.size).convert("L")).astype(np.float32) / 255.0
    mask_np = np.expand_dims(mask_np, axis=-1)

    composited = generated_np * mask_np + original_np * (1 - mask_np)
    return Image.fromarray(composited.astype(np.uint8))

# ---- 초기화 (app.py와 동일한 방식) ----
print("=== 파이프라인 초기화 ===")
repo_path = snapshot_download(repo_id="zhengchong/CatVTON")

pipeline = CatVTONPipeline(
    base_ckpt="booksforcharlie/stable-diffusion-inpainting",
    attn_ckpt=repo_path,
    attn_ckpt_version="mix",
    weight_dtype=init_weight_dtype("bf16"),
    use_tf32=True,
    device='cuda'
)
pipeline.safety_checker = None   # ← 이 줄 추가
# safety checker 우회 (디버깅 목적)
def _bypass_safety_checker(self, image):
    has_nsfw_concept = [False] * len(image) if isinstance(image, list) else [False]
    return image, has_nsfw_concept

pipeline.run_safety_checker = _bypass_safety_checker.__get__(pipeline)


mask_processor = VaeImageProcessor(vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True)

automasker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device='cuda',
)
print("초기화 완료")

# ---- 결과 저장 폴더 (테스트 실행 시각별로 구분) ----
OUT_DIR = os.path.join("result", datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

# ---- 입력 준비 ----
WIDTH, HEIGHT = 768, 1024  # app.py 기본값과 동일
FIT_TYPE = "regular"
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

PERSONS = ["image/person.jpg", "image/person2.jpg"]
UPPER_CLOTH_PATH = "image/cloth.jpg"
LOWER_CLOTH_PATH = "image/pants.jpg"

print("=== 입력 이미지 로드 ===")
upper_cloth_image = Image.open(UPPER_CLOTH_PATH).convert("RGB")
upper_cloth_image = resize_and_padding(upper_cloth_image, (WIDTH, HEIGHT))
lower_cloth_image = Image.open(LOWER_CLOTH_PATH).convert("RGB")
lower_cloth_image = resize_and_padding(lower_cloth_image, (WIDTH, HEIGHT))

generator = torch.Generator(device='cuda').manual_seed(42)


def generate(base_image, condition_image, mask):
    """base_image의 mask 영역에 condition_image를 입힌 합성 결과를 돌려준다."""
    result_image = pipeline(
        image=base_image,
        condition_image=condition_image,
        mask=mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]
    return composite_with_original(base_image, result_image, mask)


# ---- 인물 x (상의만/하의만/둘다) 반복 실행 ----
for person_path in PERSONS:
    person_tag = os.path.splitext(os.path.basename(person_path))[0]
    person_image = Image.open(person_path).convert("RGB")
    person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

    # 마스크는 몸 포즈 기준이라 상의/하의 각각 한 번만 계산해서 재사용한다.
    upper_mask = automasker(person_image, mask_type="upper", fit_type=FIT_TYPE)["mask"]
    upper_mask = mask_processor.blur(upper_mask, blur_factor=9)
    lower_mask = automasker(person_image, mask_type="lower", fit_type=FIT_TYPE)["mask"]
    lower_mask = mask_processor.blur(lower_mask, blur_factor=9)

    vis_mask(person_image, upper_mask).save(os.path.join(OUT_DIR, f"masked_{person_tag}_upper.png"))
    vis_mask(person_image, lower_mask).save(os.path.join(OUT_DIR, f"masked_{person_tag}_lower.png"))

    print(f"=== {person_tag}: 상의만 ===")
    upper_only = generate(person_image, upper_cloth_image, upper_mask)
    upper_only.save(os.path.join(OUT_DIR, f"tryon_{person_tag}_upper.png"))

    print(f"=== {person_tag}: 하의만 ===")
    lower_only = generate(person_image, lower_cloth_image, lower_mask)
    lower_only.save(os.path.join(OUT_DIR, f"tryon_{person_tag}_lower.png"))

    print(f"=== {person_tag}: 상의+하의 ===")
    # 상의를 먼저 입힌 결과(위에서 만든 upper_only) 위에 하의를 이어서 입힌다 — 한 번에
    # 두 부위를 처리하는 조건 이미지가 없어서(파이프라인은 condition_image를 1장만 받음)
    # 순차 적용 방식으로 구성한다.
    both = generate(upper_only, lower_cloth_image, lower_mask)
    both.save(os.path.join(OUT_DIR, f"tryon_{person_tag}_both.png"))

    print(f"{person_tag} 완료 -> {OUT_DIR}/tryon_{person_tag}_{{upper,lower,both}}.png")

print("모든 인물 x 조합 처리 완료")