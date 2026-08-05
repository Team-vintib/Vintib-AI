"""self-attention의 "형태 기반 편향"을 추론 시점에 직접 교정한다.

확인된 메커니즘: 마스크 영역은 VAE 인코딩 전에 이미 0으로 지워진다(`masked_image = image
* (mask < 0.5)`, `model/pipeline.py:132`) — 그러니 모델이 "청바지 픽셀을 보고 이어그리는"
게 아니라, "다리 모양으로 뚫린 빈 영역 = 옷 한 벌로 채워야 한다"는 형태 기반 사전지식으로
기본 판단한다. 레퍼런스 의류(어텐션의 10% 내외)가 이 기본 판단을 못 뒤집는 게 문제였다.

이 스크립트는 self-attn(attn1) 전 레이어에서, **다리 하단(무릎 아래) 위치의 쿼리에 한해서
레퍼런스 의류 쪽(key) 로짓에 인위적으로 보너스를 더해서** softmax 이후 그쪽 가중치가
커지도록 만든다 — 재학습 없이 추론 중 어텐션을 직접 교정하는 방식이다.

체형 매칭 worn-reference로도 계속 실패하던 둘리 케이스로 테스트한다.
"""

import math
import os

import numpy as np
import torch
import torch.nn.functional as F
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image

from model.cloth_masker import AutoMasker
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding

OUT_DIR = "result/attention_boost_result"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
FIT_TYPE = "regular"
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

BOOST_ROW_FRAC = 0.70  # person 절반 높이 중 이 비율보다 아래(다리 하단)만 부스팅
BOOST_LOGIT = 6.0  # softmax 전 로짓 가산치(클수록 강하게 레퍼런스 쪽을 봄)

PEOPLE = {
    "cheolsu": os.path.join("..", "models_ai_generated", "cheolsu.png"),
    "younghee": os.path.join("..", "models_ai_generated", "younghee.png"),
    "dooly": os.path.join("..", "models_ai_generated", "dooly.png"),
}
WORN_REF_DIR = "result/worn_references"

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
    """AttnProcessor2_0과 동일하되, 다리 하단 쿼리 -> 레퍼런스(garment half) 키 로짓에
    보너스를 더해서 그쪽을 더 강하게 참조하도록 만든다."""

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

        half_h = height // 2  # concat_dim=-2로 person(위)/garment(아래) 절반씩
        boost_row_start = int(BOOST_ROW_FRAC * half_h)

        # 부스팅 대상 쿼리 인덱스(= person 절반의 하단부, 다리 아래쪽) 마스크
        row_of_token = torch.arange(height * width, device=query.device) // width  # 각 캔버스 토큰의 y좌표
        is_person_query = row_of_token < half_h
        is_lower_leg_query = is_person_query & (row_of_token >= boost_row_start)
        is_garment_key = row_of_token >= half_h  # 캔버스 아래 절반 = 레퍼런스 의류

        # seq_len^2 풀 어텐션 행렬은 고해상도 레이어에서 메모리 폭증 -- 작은 해상도 레이어만
        # 수동 계산(부스팅)하고, 큰 레이어는 안전하게 fused kernel 경로로 폴백한다.
        SAFE_SEQ_LEN = 4096
        if sequence_length <= SAFE_SEQ_LEN and is_lower_leg_query.any():
            scores = torch.matmul(query_h, key_h.transpose(-1, -2)) / math.sqrt(head_dim)
            bias = torch.zeros(sequence_length, sequence_length, device=scores.device, dtype=scores.dtype)
            bias[is_lower_leg_query.unsqueeze(1) & is_garment_key.unsqueeze(0)] = BOOST_LOGIT
            scores = scores + bias  # (batch, heads, seq, seq)에 브로드캐스트
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


generator = torch.Generator(device="cuda").manual_seed(42)

for person_name, person_path in PEOPLE.items():
    person_image = Image.open(person_path).convert("RGB")
    person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

    worn_ref_path = os.path.join(WORN_REF_DIR, f"pants_worn_reference_{person_name}.png")
    worn_ref_image = Image.open(worn_ref_path).convert("RGB")
    worn_ref_image = resize_and_padding(worn_ref_image, (WIDTH, HEIGHT))

    lower_mask = automasker(person_image, mask_type="lower", fit_type=FIT_TYPE)["mask"]
    lower_mask = mask_processor.blur(lower_mask, blur_factor=9)

    print(f"=== 생성: {person_name} + 체형매칭 레퍼런스 + 어텐션 부스팅 ===")
    result_image = pipeline(
        image=person_image,
        condition_image=worn_ref_image,
        mask=lower_mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]

    final = composite_with_original(person_image, result_image, lower_mask)
    out_path = os.path.join(OUT_DIR, f"tryon_{person_name}_lower_boosted.png")
    final.save(out_path)
    print(f"완료 -> {out_path}")

print("모든 인물 처리 완료")
