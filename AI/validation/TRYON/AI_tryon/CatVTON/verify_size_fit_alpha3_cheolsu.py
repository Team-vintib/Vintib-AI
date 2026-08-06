"""철수에게 알파테스트3 의상(상의+버뮤다 반바지)을 입힌다. 상의는 레귤러 고정, 하의는
실제 사이즈표(M/L/XL/4XL)의 실측값으로 §7.5 폭 조절 경로를 그대로 태운다.

**1차 시도(scale_px=20, 이 표 그대로)는 스윙이 -1.9px~+2.4px로 육안상 거의 안 보였다.**
(허리단면 표로 된 다른 사이즈표는 실제로는 청바지용이라 이 스크립트에서는 쓰지 않는다 --
별도 청바지 테스트에서 사용 예정.) 원인이 표가 아니라 `ratio_to_dilation_px`의
`scale_px` 상수라고 보고, `model/adaptive_fit.py`에서 이번 세션에 20 -> 60으로
실험적으로 올려서(§9 캘리브레이션 메모 참고, production에는 아직 미반영) 같은 표로
재검증한다.

사이즈표(허리둘레, cm): M=68 L=72 XL=76 4XL=84. `WAIST_WIDTH`는 평평하게 편 원단의 좌우
폭(허리둘레의 절반)이므로 표의 허리둘레를 2로 나눠서 넘긴다. 철수의 허리둘레는 지금까지의
다른 검증(`verify_size_fit_combined.py`)과 동일하게 75cm로 가정한다.

하의 길이는 §8/§9에서 확립한 worn-reference(`generate_worn_reference_alpha3_cheolsu.py`가
생성) + self-attention 부스팅 + blur_factor=2(고스트 방지)를 그대로 쓴다. 상의는 원래
alpha 테스트에서 문제없이 동작했던 flat-lay 그대로 조건 이미지로 쓴다(별도 기법 불필요).
"""

import math
import os
from datetime import datetime

import numpy as np
import torch
import torch.nn.functional as F
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image

from model.cloth_masker import AutoMasker
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding

OUT_DIR = os.path.join("result", "size_fit_alpha3_cheolsu_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
BOOST_ROW_FRAC = 0.70
BOOST_LOGIT = 6.0

CHEOLSU_WAIST_CM = 75.0  # verify_size_fit_combined.py와 동일한 가정값
# 사이즈표(허리둘레 cm) -> WAIST_WIDTH(평평하게 편 좌우 폭 = 허리둘레/2)
SIZE_TABLE_WAIST_WIDTH_CM = {"M": 68.0 / 2, "L": 72.0 / 2, "XL": 76.0 / 2, "4XL": 84.0 / 2}

UPPER_PATH = os.path.join("image", "alpha_3", "top.jpg")
LOWER_PATH = os.path.join("image", "alpha_3", "pants_cropped.png")
LOWER_WORN_REF_PATH = os.path.join("result", "worn_references", "pants_worn_reference_alpha3_cheolsu.png")
PERSON_PATH = os.path.join("..", "models_ai_generated", "cheolsu.png")

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


class BoostedAttnProcessor(torch.nn.Module):
    """다리 하단 쿼리 -> 레퍼런스(garment half) 키 로짓에 보너스를 더해 형태 편향을 교정한다."""

    def __call__(self, attn, hidden_states, encoder_hidden_states=None, attention_mask=None, temb=None, *args, **kwargs):
        residual = hidden_states
        input_ndim = hidden_states.ndim
        if input_ndim == 4:
            batch_size, channel, height, width = hidden_states.shape
            hidden_states = hidden_states.view(batch_size, channel, height * width).transpose(1, 2)
        else:
            seq_len = hidden_states.shape[1]
            canvas_aspect = (2 * HEIGHT) / WIDTH
            width = round(math.sqrt(seq_len / canvas_aspect))
            height = seq_len // width

        batch_size, sequence_length, _ = hidden_states.shape
        query = attn.to_q(hidden_states)
        encoder_hidden_states = hidden_states if encoder_hidden_states is None else encoder_hidden_states
        key = attn.to_k(encoder_hidden_states)
        value = attn.to_v(encoder_hidden_states)

        inner_dim = key.shape[-1]
        head_dim = inner_dim // attn.heads
        query_h = query.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
        key_h = key.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
        value_h = value.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)

        half_h = height // 2
        boost_row_start = int(BOOST_ROW_FRAC * half_h)
        row_of_token = torch.arange(height * width, device=query.device) // width
        is_person_query = row_of_token < half_h
        is_lower_leg_query = is_person_query & (row_of_token >= boost_row_start)
        is_garment_key = row_of_token >= half_h

        SAFE_SEQ_LEN = 4096
        if sequence_length <= SAFE_SEQ_LEN and is_lower_leg_query.any():
            scores = torch.matmul(query_h, key_h.transpose(-1, -2)) / math.sqrt(head_dim)
            bias = torch.zeros(sequence_length, sequence_length, device=scores.device, dtype=scores.dtype)
            bias[is_lower_leg_query.unsqueeze(1) & is_garment_key.unsqueeze(0)] = BOOST_LOGIT
            scores = scores + bias
            probs = torch.softmax(scores, dim=-1)
            hidden_states = torch.matmul(probs.to(value_h.dtype), value_h)
        else:
            hidden_states = F.scaled_dot_product_attention(query_h, key_h, value_h, attn_mask=None, dropout_p=0.0, is_causal=False)

        hidden_states = hidden_states.transpose(1, 2).reshape(batch_size, -1, attn.heads * head_dim).to(query.dtype)
        hidden_states = attn.to_out[0](hidden_states)
        hidden_states = attn.to_out[1](hidden_states)
        if input_ndim == 4:
            hidden_states = hidden_states.transpose(-1, -2).reshape(batch_size, channel, height, width)
        if attn.residual_connection:
            hidden_states = hidden_states + residual
        hidden_states = hidden_states / attn.rescale_output_factor
        return hidden_states


self_attn_names = [n for n in pipeline.unet.attn_processors.keys() if n.endswith("attn1.processor")]
attn_procs = dict(pipeline.unet.attn_processors)
for name in self_attn_names:
    attn_procs[name] = BoostedAttnProcessor()
pipeline.unet.set_attn_processor(attn_procs)
print(f"어텐션 부스팅 적용된 self-attn 레이어 수: {len(self_attn_names)}")


def composite_with_original(original_image, generated_image, mask):
    original_np = np.array(original_image.resize(generated_image.size)).astype(np.float32)
    generated_np = np.array(generated_image).astype(np.float32)
    mask_np = np.array(mask.resize(generated_image.size).convert("L")).astype(np.float32) / 255.0
    mask_np = np.expand_dims(mask_np, axis=-1)
    composited = generated_np * mask_np + original_np * (1 - mask_np)
    return Image.fromarray(composited.astype(np.uint8))


def generate(base_image, condition_image, mask, generator):
    result_image = pipeline(
        image=base_image,
        condition_image=condition_image,
        mask=mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]
    return composite_with_original(base_image, result_image, mask)


person_image = Image.open(PERSON_PATH).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

upper_image = Image.open(UPPER_PATH).convert("RGB")
upper_image = resize_and_padding(upper_image, (WIDTH, HEIGHT))
lower_worn_ref_image = Image.open(LOWER_WORN_REF_PATH).convert("RGB")
lower_worn_ref_image = resize_and_padding(lower_worn_ref_image, (WIDTH, HEIGHT))

upper_mask = automasker(person_image, mask_type="upper", fit_type="regular")["mask"]
upper_mask = mask_processor.blur(upper_mask, blur_factor=9)

for size_label, garment_waist_width_cm in SIZE_TABLE_WAIST_WIDTH_CM.items():
    generator = torch.Generator(device="cuda").manual_seed(42)

    print(f"\n=== {size_label} (WAIST_WIDTH {garment_waist_width_cm}cm, 철수 허리 {CHEOLSU_WAIST_CM}cm) ===")
    print(f"  상의: 레귤러 고정")
    upper_only = generate(person_image, upper_image, upper_mask, generator)

    lower_mask = automasker(
        person_image,
        mask_type="lower",
        fit_type="regular",
        body_measurements={"waist_cm": CHEOLSU_WAIST_CM},
        garment_measurements={"WAIST_WIDTH": garment_waist_width_cm},
    )["mask"]
    lower_mask = mask_processor.blur(lower_mask, blur_factor=2)  # §9.3 고스트 방지

    both = generate(upper_only, lower_worn_ref_image, lower_mask, generator)
    out_path = os.path.join(OUT_DIR, f"tryon_cheolsu_{size_label}.png")
    both.save(out_path)
    print(f"완료 -> {out_path}")

print(f"\n모든 사이즈 처리 완료 -> {OUT_DIR}")
