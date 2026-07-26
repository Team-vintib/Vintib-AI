import os
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

# ---- 입력 준비 ----
WIDTH, HEIGHT = 768, 1024  # app.py 기본값과 동일

print("=== 입력 이미지 로드 ===")
person_image = Image.open("image/person.jpg").convert("RGB")
cloth_image = Image.open("image/cloth.jpg").convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))
cloth_image = resize_and_padding(cloth_image, (WIDTH, HEIGHT))

generator = torch.Generator(device='cuda').manual_seed(42)

# ---- 핏별로 반복 실행 ----
for fit_type in ["regular", "oversized", "cropped"]:
    print(f"=== {fit_type} 처리 중 ===")
    mask_result = automasker(person_image, mask_type="upper", fit_type=fit_type)
    mask = mask_result["mask"]
    mask = mask_processor.blur(mask, blur_factor=9)

    result_image = pipeline(
        image=person_image,
        condition_image=cloth_image,
        mask=mask,
        num_inference_steps=20,
        guidance_scale=2.5,
        generator=generator
    )[0]
    result_image = composite_with_original(person_image, result_image, mask)
    result_image.save(f"tryon_{fit_type}.png")

    # 참고용: 마스크가 어디 씌워졌는지 시각화도 같이 저장
    masked_person = vis_mask(person_image, mask)
    masked_person.save(f"masked_{fit_type}.png")

    print(f"{fit_type} 완료 -> tryon_{fit_type}.png")

print("모든 핏 타입 처리 완료")