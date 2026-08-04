"""CatVTON이 조건 이미지를 하나만 받는 구조라, worn-reference(핏 정보) 아니면 실제 상품
사진(정확한 그래픽) 둘 중 하나만 고를 수 있었다 -- 사람 캔버스 + 레퍼런스 캔버스를 세로로
이어붙여(2배 높이) self-attention이 그 안에서 서로 참조하게 하는 구조(`model/pipeline.py`
`concat_dim=-2`)이므로, 여기에 실제 상품 사진 블록을 하나 더 이어붙여서(3배 높이) 두
레퍼런스를 동시에 주는 실험을 한다.

`CatVTONPipeline.__call__`을 직접 고치지 않고, 그 구성요소(vae/unet/scheduler)를 그대로
재사용하는 별도 함수로 구현한다 -- 원본 모델이 "사람+레퍼런스 1개"(2배 높이) 비율로
학습됐어서 3배로 늘리면 예상 못한 결과가 나올 수 있다는 걸 감안하고, 우선 한 케이스만
빠르게 테스트한다.
"""

import os

import numpy as np
import torch
import tqdm
from diffusers.image_processor import VaeImageProcessor
from diffusers.utils.torch_utils import randn_tensor
from huggingface_hub import snapshot_download
from PIL import Image

from model.cloth_masker import AutoMasker
from model.pipeline import CatVTONPipeline
from utils import (compute_vae_encodings, init_weight_dtype, numpy_to_pil,
                    prepare_image, prepare_mask_image, resize_and_crop,
                    resize_and_padding)

OUT_DIR = "result/top_dual_reference"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

PERSON_NAME = "heedongi"
SIZE_LABEL = "S"  # 우선 1케이스만 빠르게 확인

_MODELS_DIR = os.path.join("..", "models_ai_generated")
WORN_REF_PATH = os.path.join("result", "worn_references", f"top_worn_reference_{PERSON_NAME}_{SIZE_LABEL}.png")
REAL_GARMENT_PATH = os.path.join("image", "alpha_3", "top.jpg")


@torch.no_grad()
def generate_dual_reference(
    pipeline: CatVTONPipeline,
    image,
    condition_image_fit,
    condition_image_real,
    mask,
    num_inference_steps=50,
    guidance_scale=2.5,
    height=1024,
    width=768,
    generator=None,
    eta=1.0,
):
    """사람 + (핏 정보용) worn-reference + (그래픽 정확도용) 실제 상품 사진, 3블록을
    세로로 이어붙인 캔버스로 생성한다. `CatVTONPipeline.__call__`(model/pipeline.py)의
    2블록 버전을 그대로 3블록으로 확장한 것 -- 로직은 동일하고 concat 블록 수만 다르다.
    """
    concat_dim = -2
    image = resize_and_crop(image, (width, height))
    mask = resize_and_crop(mask, (width, height))
    condition_image_fit = resize_and_padding(condition_image_fit, (width, height))
    condition_image_real = resize_and_padding(condition_image_real, (width, height))

    image = prepare_image(image).to(pipeline.device, dtype=pipeline.weight_dtype)
    condition_image_fit = prepare_image(condition_image_fit).to(pipeline.device, dtype=pipeline.weight_dtype)
    condition_image_real = prepare_image(condition_image_real).to(pipeline.device, dtype=pipeline.weight_dtype)
    mask = prepare_mask_image(mask).to(pipeline.device, dtype=pipeline.weight_dtype)

    masked_image = image * (mask < 0.5)
    masked_latent = compute_vae_encodings(masked_image, pipeline.vae)
    fit_latent = compute_vae_encodings(condition_image_fit, pipeline.vae)
    real_latent = compute_vae_encodings(condition_image_real, pipeline.vae)
    mask_latent = torch.nn.functional.interpolate(mask, size=masked_latent.shape[-2:], mode="nearest")
    del image, mask, condition_image_fit, condition_image_real

    # 3블록: [사람, worn-reference(핏), 실제 상품 사진(그래픽)]
    masked_latent_concat = torch.cat([masked_latent, fit_latent, real_latent], dim=concat_dim)
    zeros = torch.zeros_like(mask_latent)
    mask_latent_concat = torch.cat([mask_latent, zeros, zeros], dim=concat_dim)

    latents = randn_tensor(
        masked_latent_concat.shape,
        generator=generator,
        device=masked_latent_concat.device,
        dtype=pipeline.weight_dtype,
    )
    pipeline.noise_scheduler.set_timesteps(num_inference_steps, device=pipeline.device)
    timesteps = pipeline.noise_scheduler.timesteps
    latents = latents * pipeline.noise_scheduler.init_noise_sigma

    if do_cfg := (guidance_scale > 1.0):
        masked_latent_concat = torch.cat([
            torch.cat([masked_latent, torch.zeros_like(fit_latent), torch.zeros_like(real_latent)], dim=concat_dim),
            masked_latent_concat,
        ])
        mask_latent_concat = torch.cat([mask_latent_concat] * 2)

    extra_step_kwargs = pipeline.prepare_extra_step_kwargs(generator, eta)
    num_warmup_steps = len(timesteps) - num_inference_steps * pipeline.noise_scheduler.order
    with tqdm.tqdm(total=num_inference_steps) as progress_bar:
        for i, t in enumerate(timesteps):
            latent_model_input = torch.cat([latents] * 2) if do_cfg else latents
            latent_model_input = pipeline.noise_scheduler.scale_model_input(latent_model_input, t)
            inpainting_latent_model_input = torch.cat([latent_model_input, mask_latent_concat, masked_latent_concat], dim=1)
            noise_pred = pipeline.unet(inpainting_latent_model_input, t.to(pipeline.device), encoder_hidden_states=None, return_dict=False)[0]
            if do_cfg:
                noise_pred_uncond, noise_pred_text = noise_pred.chunk(2)
                noise_pred = noise_pred_uncond + guidance_scale * (noise_pred_text - noise_pred_uncond)
            latents = pipeline.noise_scheduler.step(noise_pred, t, latents, **extra_step_kwargs).prev_sample
            if i == len(timesteps) - 1 or ((i + 1) > num_warmup_steps and (i + 1) % pipeline.noise_scheduler.order == 0):
                progress_bar.update()

    # 3블록 중 맨 위(사람) 블록만 잘라낸다
    latents = latents.split(latents.shape[concat_dim] // 3, dim=concat_dim)[0]
    latents = 1 / pipeline.vae.config.scaling_factor * latents
    image = pipeline.vae.decode(latents.to(pipeline.device, dtype=pipeline.weight_dtype)).sample
    image = (image / 2 + 0.5).clamp(0, 1)
    image = image.cpu().permute(0, 2, 3, 1).float().numpy()
    return numpy_to_pil(image)


def composite_with_original(original_image, generated_image, mask):
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

person_image = Image.open(os.path.join(_MODELS_DIR, f"{PERSON_NAME}.png")).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

worn_ref_image = Image.open(WORN_REF_PATH).convert("RGB")
real_garment_image = Image.open(REAL_GARMENT_PATH).convert("RGB")

upper_mask = automasker(person_image, mask_type="upper", fit_type="regular")["mask"]
upper_mask = mask_processor.blur(upper_mask, blur_factor=2)

generator = torch.Generator(device="cuda").manual_seed(42)

print(f"\n=== 생성: {PERSON_NAME}_{SIZE_LABEL} (3블록: 사람+worn-ref+실제사진) ===")
result_image = generate_dual_reference(
    pipeline,
    image=person_image,
    condition_image_fit=worn_ref_image,
    condition_image_real=real_garment_image,
    mask=upper_mask,
    num_inference_steps=NUM_INFERENCE_STEPS,
    guidance_scale=GUIDANCE_SCALE,
    height=HEIGHT,
    width=WIDTH,
    generator=generator,
)[0]
final = composite_with_original(person_image, result_image, upper_mask)

out_path = os.path.join(OUT_DIR, f"tryon_{PERSON_NAME}_{SIZE_LABEL}_dualref.png")
final.save(out_path)
print(f"완료 -> {out_path}")
