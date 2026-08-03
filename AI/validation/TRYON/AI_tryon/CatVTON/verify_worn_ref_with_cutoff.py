"""worn-reference condition_image + 마스크 길이 컷오프를 결합해서, 체형과 무관하게
일관되게 반바지 길이만큼만 마스킹되도록 한다.

지금까지 확인한 것:
- 플랫레이 레퍼런스 -> 마스크(다리 전체)를 원단으로 다 채움 (모두 실패)
- worn-reference(사람이 입은 형태) -> 철수(작은 마스크)는 완벽 성공, 영희는 부분 성공,
  둘리(큰 마스크)는 거의 실패 -- 마스크 면적이 클수록 "인접 원본을 이어가려는 편향"을
  이기지 못하는 것으로 보임.

이번엔 모델의 판단에만 맡기지 않고, AutoMasker가 만든 "하의(다리 전체)" 마스크의
바운딩박스에서 위쪽 CUTOFF_FRAC 비율까지만 마스크로 남기고 나머지는 원천적으로
마스크에서 제외한다(부드러운 테이퍼 포함). 체형이 커도 그 사람 마스크의 상대적 비율로
자르므로 일관성이 생긴다.

CUTOFF_FRAC=0.4는 `pants_worn_reference.png`(FLUX 생성 워런 레퍼런스)에서 반바지
밑단이 허리~발목 구간의 대략 36~40% 지점에서 끝나는 걸 눈대중으로 잰 값이다.
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

OUT_DIR = "worn_ref_cutoff_result"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
FIT_TYPE = "regular"
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
CUTOFF_FRAC = 0.40  # 마스크 바운딩박스 상단부터 이 비율까지만 남김
TAPER_PX = 40  # 컷오프 경계를 부드럽게

PEOPLE = {
    "cheolsu": os.path.join("..", "models_ai_generated", "cheolsu.png"),
    "younghee": os.path.join("..", "models_ai_generated", "younghee.png"),
    "dooly": os.path.join("..", "models_ai_generated", "dooly.png"),
}
WORN_REF_PATH = os.path.join("..", "fashn-vton-1.5", "pants_worn_reference.png")

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


def apply_length_cutoff(mask: Image.Image, cutoff_frac: float, taper_px: int) -> Image.Image:
    """마스크의 바운딩박스 상단부터 cutoff_frac 비율까지만 남기고 나머지는 지운다."""
    mask_np = np.array(mask.convert("L")).astype(np.float32)
    rows = np.where(mask_np.max(axis=1) > 10)[0]
    if len(rows) == 0:
        return mask
    top_y, bottom_y = rows[0], rows[-1]
    cutoff_y = top_y + cutoff_frac * (bottom_y - top_y)

    h = mask_np.shape[0]
    ys = np.arange(h, dtype=np.float32)
    weight = np.ones(h, dtype=np.float32)
    weight[ys > cutoff_y + taper_px] = 0.0
    taper_zone = (ys >= cutoff_y) & (ys <= cutoff_y + taper_px)
    weight[taper_zone] = 1.0 - (ys[taper_zone] - cutoff_y) / taper_px

    new_mask_np = (mask_np * weight[:, None]).astype(np.uint8)
    return Image.fromarray(new_mask_np, mode="L").convert(mask.mode)


worn_ref_image = Image.open(WORN_REF_PATH).convert("RGB")
worn_ref_image = resize_and_padding(worn_ref_image, (WIDTH, HEIGHT))
generator = torch.Generator(device="cuda").manual_seed(42)

for person_name, person_path in PEOPLE.items():
    person_image = Image.open(person_path).convert("RGB")
    person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

    lower_mask = automasker(person_image, mask_type="lower", fit_type=FIT_TYPE)["mask"]
    lower_mask = apply_length_cutoff(lower_mask, CUTOFF_FRAC, TAPER_PX)
    lower_mask = mask_processor.blur(lower_mask, blur_factor=9)
    lower_mask.save(os.path.join(OUT_DIR, f"mask_{person_name}_cutoff.png"))

    print(f"=== 생성: {person_name} + worn-reference + 마스크 컷오프(40%) ===")
    result_image = pipeline(
        image=person_image,
        condition_image=worn_ref_image,
        mask=lower_mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]

    final = composite_with_original(person_image, result_image, lower_mask)
    out_path = os.path.join(OUT_DIR, f"tryon_{person_name}_lower_cutoff.png")
    final.save(out_path)
    print(f"완료 -> {out_path}")

print("모든 인물 처리 완료")
