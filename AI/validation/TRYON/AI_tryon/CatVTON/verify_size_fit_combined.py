"""사이즈(체형-의류 치수) 기반 폭 조절 + 오늘 확보한 정확한 길이 렌더링(worn-reference +
attention 부스팅)을 결합한다.

`adaptive_fit.py`의 `compute_mask_adjustment()`는 `body_measurements`(허리둘레)와
`garment_measurements`(WAIST_WIDTH)가 둘 다 있으면 실제 치수 차이로 마스크 폭을
연속적으로 조절한다(§7.5) — 지금까지는 이 축을 fit_type 고정값으로만 테스트했는데, 이번엔
진짜 치수 딕셔너리를 넘겨서 실제 프로덕션 경로(`AutoMasker(..., body_measurements=...,
garment_measurements=...)`)를 그대로 탄다.

같은 반바지(WAIST_WIDTH=38cm로 가정 — 평평하게 편 원단 폭)를 허리둘레가 다른 세 체형에게
입혀서, 같은 옷이라도 체형에 따라 자동으로 타이트/레귤러/루즈하게 나오는지 확인한다:
  - 영희(허리 65cm 가정): 옷이 상대적으로 커서 루즈
  - 철수(허리 75cm 가정): 거의 딱 맞음(레귤러)
  - 둘리(허리 110cm 가정): 옷이 상대적으로 작아서 타이트

마스크(폭)는 손대되, 길이(기장)는 오늘 확립한 방식(worn-reference condition_image +
체형 매칭 + self-attention 부스팅)을 그대로 유지해서 반바지 길이 자체는 항상 정확하게
나오게 한다.
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

OUT_DIR = os.path.join("result", "size_fit_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
BOOST_ROW_FRAC = 0.70
BOOST_LOGIT = 6.0
GARMENT_WAIST_WIDTH_CM = 38.0  # 반바지 레퍼런스의 평편 원단 폭(가정값)

PEOPLE = {
    # (person_image, worn_reference, 가정 허리둘레cm) -- 허리둘레만 다르고 옷은 동일
    "younghee_loose": ("younghee.png", "pants_worn_reference_younghee.png", 65.0),
    "cheolsu_regular": ("cheolsu.png", "pants_worn_reference_cheolsu.png", 75.0),
    "dooly_tight": ("dooly.png", "pants_worn_reference_dooly.png", 110.0),
}
PANTS_PATH = os.path.join("image", "alpha_2", "pants.png")

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


pants_image = Image.open(PANTS_PATH).convert("RGB")
pants_image = resize_and_padding(pants_image, (WIDTH, HEIGHT))

for case_name, (person_file, worn_ref_file, waist_cm) in PEOPLE.items():
    # 케이스마다 매번 새로 시드를 고정한다 -- generator를 루프 밖에서 하나만 만들어 재사용하면
    # 매 pipeline() 호출(랜덤 초기 노이즈 샘플링)마다 내부 상태가 전진해서, 두 번째/세 번째
    # 케이스는 seed=42가 아닌 사실상 재현 불가능한 상태를 쓰게 된다.
    generator = torch.Generator(device="cuda").manual_seed(42)
    person_image = Image.open(os.path.join("..", "models_ai_generated", person_file)).convert("RGB")
    person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))
    worn_ref_image = Image.open(os.path.join("result", "worn_references", worn_ref_file)).convert("RGB")
    worn_ref_image = resize_and_padding(worn_ref_image, (WIDTH, HEIGHT))

    lower_mask = automasker(
        person_image,
        mask_type="lower",
        fit_type="regular",
        body_measurements={"waist_cm": waist_cm},
        garment_measurements={"WAIST_WIDTH": GARMENT_WAIST_WIDTH_CM},
    )["mask"]
    lower_mask = mask_processor.blur(lower_mask, blur_factor=9)

    print(f"\n=== 생성: {case_name} (허리 {waist_cm}cm, 옷 폭 {GARMENT_WAIST_WIDTH_CM}cm) ===")
    result_image = pipeline(
        image=person_image,
        condition_image=worn_ref_image,
        mask=lower_mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]

    final = composite_with_original(person_image, result_image, lower_mask)
    out_path = os.path.join(OUT_DIR, f"tryon_{case_name}.png")
    final.save(out_path)
    print(f"완료 -> {out_path}")

print("\n모든 케이스 처리 완료")
