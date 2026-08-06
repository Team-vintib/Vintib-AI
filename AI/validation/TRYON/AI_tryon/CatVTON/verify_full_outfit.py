"""person.jpg에 상의/바지/모자/신발을 각각 입힌 결과와, 전부 입힌 결과를 만든다.

hat/shoes 마스킹(`_hat_mask`/`_shoes_mask`)은 아직 프로덕션(`worker/models/catvton`)에는
반영 안 된 상태라(`AI/docs/tryon-advancement-strategy.md` §7.3 참고), 이 검증 스냅샷
(`AI/validation/TRYON/AI_tryon/CatVTON/model/cloth_masker.py`)의 로컬 `model.` 코드를
그대로 쓴다 — 여기서만 4종(상의/하의/모자/신발) 마스킹이 다 갖춰져 있다.

사이즈는 "적당히 맞는다"고 가정한다 — 즉 적응형 마스킹(스키니/배기) 없이 fit_type="regular"
그대로 쓴다. 이 스냅샷엔 이번 세션에 새로 만든 `adaptive_fit.py`도 없다.

pytest 안 걸림 — `python verify_full_outfit.py`로 직접 실행 후 `result/`에 저장된 PNG를
육안 확인한다(기존 verify_*.py 관례).
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

OUT_DIR = os.path.join("result", "full_outfit_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
PERSON_PATH = "image/person.jpg"

ITEMS = [
    ("top", "upper", "image/cloth.jpg"),
    ("pants", "lower", "image/pants.jpg"),
    ("hat", "hat", "image/hat.jpg"),
    ("shoes", "shoes", "image/shoes.jpg"),
]

person_image = Image.open(PERSON_PATH).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

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


# --- 마스크는 포즈 기준이라 아이템별로 한 번만 계산해서 재사용한다 -------------------
print("=== 마스크 계산 ===")
masks = {}
cloth_images = {}
for label, mask_type, cloth_path in ITEMS:
    mask = automasker(person_image, mask_type=mask_type, fit_type="regular")["mask"]
    masks[label] = mask_processor.blur(mask, blur_factor=9)
    cloth_images[label] = resize_and_padding(Image.open(cloth_path).convert("RGB"), (WIDTH, HEIGHT))
    vis_mask(person_image, mask).save(os.path.join(OUT_DIR, f"mask_{label}.png"))

# --- 개별 착용(각각 원본 사진 기준) ---------------------------------------------
print("=== 개별 착용 ===")
for label, _mask_type, _cloth_path in ITEMS:
    print(f"  {label} 단독")
    result = generate(person_image, cloth_images[label], masks[label])
    result.save(os.path.join(OUT_DIR, f"only_{label}.png"))

# --- 전부 착용(순차 적용: 상의 -> 바지 -> 모자 -> 신발) --------------------------
print("=== 전부 착용(순차 적용) ===")
combined = person_image
for label, _mask_type, _cloth_path in ITEMS:
    print(f"  + {label}")
    combined = generate(combined, cloth_images[label], masks[label])
combined.save(os.path.join(OUT_DIR, "full_outfit.png"))

print(f"\n완료 -> {OUT_DIR}/ 안의 only_{{top,pants,hat,shoes}}.png / full_outfit.png 확인")
