"""알파테스트3에 새로 추가된 모자(`hat.jpg`, 버킷햇)와 신발(`shoes.jpg`, 샌들)을 희동이
(heedongi) 원본 사진에 입혀본다.

CatVTON의 AutoMasker는 `mask_type`으로 upper/lower/overall/inner/outer만 지원한다
(`model/cloth_masker.py`) -- 모자/신발은 지원 카테고리가 아니라서 SCHP 인체 파싱 결과에서
직접 마스크를 만든다.

- 신발: 원본 사진에 이미 신발을 신고 있어서(SCHP ATR의 Left-shoe=9/Right-shoe=10 클래스가
  존재) 그 픽셀을 그대로 마스크로 쓴다 -- 기존 upper/lower 마스킹과 원리가 같다.
- 모자: 원본 사진엔 모자가 없어서 SCHP에 'Hat' 클래스 픽셀이 아예 없다. 대신 Hair|Face
  bbox를 이용해 머리 위쪽(정수리~눈썹 라인)과 챙이 걸쳐질 좌우 여유를 더한 사각형을
  수동으로 마스크로 쓴다 -- 근사치다.

CatVTON은 애초에 상의/하의 의류 try-on으로 학습된 모델이라 모자/신발 같은 액세서리는
학습 분포 밖이다. 결과 품질은 보장할 수 없는 PoC 테스트다.
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

OUT_DIR = "result/alpha3_hat_shoes"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 2.5
NUM_INFERENCE_STEPS = 50

PERSON_NAME = "heedongi"
PERSON_PATH = os.path.join("..", "models_ai_generated", f"{PERSON_NAME}.png")
HAT_PATH = os.path.join("image", "alpha_3", "hat.jpg")
SHOES_PATH = os.path.join("image", "alpha_3", "shoes.jpg")

ATR_HAT = 1
ATR_LEFT_SHOE = 9
ATR_RIGHT_SHOE = 10
ATR_HAIR = 2
ATR_FACE = 11

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


def mask_from_array(mask_bool: np.ndarray) -> Image.Image:
    return Image.fromarray((mask_bool * 255).astype(np.uint8)).convert("L")


person_image = Image.open(PERSON_PATH).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

parse = np.array(automasker.process_schp_atr(person_image))

# --- 신발: 기존 신발 픽셀을 그대로 마스크로 사용 ---
shoe_mask_bool = (parse == ATR_LEFT_SHOE) | (parse == ATR_RIGHT_SHOE)
shoe_mask = mask_from_array(shoe_mask_bool)
shoe_mask_blurred = mask_processor.blur(shoe_mask, blur_factor=6)  # 신발처럼 작은 영역은 더 넓게 블러

# --- 모자: Hair|Face bbox 기반으로 정수리~눈썹 라인 + 챙 여유를 수동으로 마스크 ---
head_mask_bool = (parse == ATR_HAIR) | (parse == ATR_FACE)
rows = np.where(head_mask_bool.any(axis=1))[0]
cols = np.where(head_mask_bool.any(axis=0))[0]
head_top, head_bottom, head_left, head_right = rows[0], rows[-1], cols[0], cols[-1]
head_height = head_bottom - head_top

hat_top = max(0, head_top - 25)
hat_bottom = head_top + int(head_height * 0.45)  # 눈썹 라인 근처까지만(눈 가리지 않도록)
hat_left = max(0, head_left - 45)  # 버킷햇 챙 여유
hat_right = min(WIDTH, head_right + 45)

hat_mask_bool = np.zeros_like(head_mask_bool)
hat_mask_bool[hat_top:hat_bottom, hat_left:hat_right] = True
hat_mask = mask_from_array(hat_mask_bool)
hat_mask_blurred = mask_processor.blur(hat_mask, blur_factor=6)

for name, condition_path, mask_blurred in [
    ("hat", HAT_PATH, hat_mask_blurred),
    ("shoes", SHOES_PATH, shoe_mask_blurred),
]:
    condition_image = Image.open(condition_path).convert("RGB")
    condition_image = resize_and_padding(condition_image, (WIDTH, HEIGHT))

    from model.cloth_masker import vis_mask
    vis_mask(person_image, mask_blurred).save(os.path.join(OUT_DIR, f"mask_{name}_{PERSON_NAME}.png"))

    generator = torch.Generator(device="cuda").manual_seed(42)
    print(f"\n=== 생성: {PERSON_NAME} + {name} ===")
    result_image = pipeline(
        image=person_image,
        condition_image=condition_image,
        mask=mask_blurred,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]
    final = composite_with_original(person_image, result_image, mask_blurred)

    out_path = os.path.join(OUT_DIR, f"tryon_{PERSON_NAME}_{name}.png")
    final.save(out_path)
    print(f"완료 -> {out_path}")

print("\n=== 전체 완료 ===")
