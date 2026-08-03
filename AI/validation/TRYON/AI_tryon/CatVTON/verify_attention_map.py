"""CatVTON self-attention의 어텐션 맵을 실제로 뽑아서, 발목(gap) 위치의 쿼리가 어디를
참조하는지 시각화한다.

CatVTON은 인물 latent와 레퍼런스 의류 latent를 세로로 이어붙인 하나의 캔버스
(`torch.cat([masked_latent, condition_latent], dim=-2)`, `model/pipeline.py:139`)로
UNet에 넣고, self-attention(`attn1`)이 그 안에서 자유롭게 서로를 참조한다. "발목 부위
쿼리가 인접한 원본(청바지) 쪽에 쏠리는지, 아니면 레퍼런스 의류 쪽을 보는지"를 직접
확인하면 오늘 계속 가설로만 얘기했던 "인접 원본 편향"을 실제 증거로 확인할 수 있다.

`F.scaled_dot_product_attention`은 fused 커널이라 중간 어텐션 가중치를 안 보여주므로,
진단 목적으로 self-attn 레이어 하나만 수동 계산(softmax(QK^T)V)으로 바꿔치기해서
가중치를 붙잡는다. 프로덕션 코드는 건드리지 않는다(이 검증 스크립트 안에서만 몽키패치).
"""

import math
import os

import numpy as np
import torch
import torch.nn.functional as F
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image, ImageDraw

from model.cloth_masker import AutoMasker
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding

OUT_DIR = "attention_map_result"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
FIT_TYPE = "regular"
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
CAPTURE_AT_STEP = 40  # 초반보다 후반부가 구조가 더 잡혀서 해석하기 쉬움

PERSON_PATH = os.path.join("..", "models_ai_generated", "younghee.png")
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

# --- self-attn(attn1) 레이어 이름 목록 확인 ---
self_attn_names = [n for n in pipeline.unet.attn_processors.keys() if n.endswith("attn1.processor")]
print(f"\nself-attn 레이어 수: {len(self_attn_names)}")
# up_blocks 중간 정도 해상도(디테일과 구조가 둘 다 살아있는 지점) 하나를 고른다.
TARGET_NAME = next((n for n in self_attn_names if n.startswith("up_blocks.1")), self_attn_names[len(self_attn_names) // 2])
print(f"캡처 대상 레이어: {TARGET_NAME}")

_capture = {"step": 0, "attn": None, "hw": None}


class CapturingAttnProcessor(torch.nn.Module):
    """AttnProcessor2_0과 동일하지만, 지정된 스텝에서 어텐션 가중치를 수동 계산해서 저장한다."""

    def __call__(self, attn, hidden_states, encoder_hidden_states=None, attention_mask=None, temb=None, *args, **kwargs):
        residual = hidden_states
        input_ndim = hidden_states.ndim
        if input_ndim == 4:
            batch_size, channel, height, width = hidden_states.shape
            hidden_states = hidden_states.view(batch_size, channel, height * width).transpose(1, 2)
        else:
            # transformer_blocks 내부의 attn1은 이미 3D(batch, seq_len, ch)로 들어온다 --
            # 4D->3D reshape는 이 지점 이전(Transformer2DModel)에서 이미 끝난 상태라
            # input_ndim==4 분기를 안 타므로, 캔버스 종횡비(세로로 person+garment concat)로
            # 역산해서 h, w를 구한다.
            seq_len = hidden_states.shape[1]
            canvas_aspect = (2 * HEIGHT) / WIDTH  # concat_dim=-2로 세로가 2배
            width = round(math.sqrt(seq_len / canvas_aspect))
            height = seq_len // width

        batch_size, sequence_length, _ = hidden_states.shape
        query = attn.to_q(hidden_states)
        encoder_hidden_states = hidden_states if encoder_hidden_states is None else encoder_hidden_states
        key = attn.to_k(encoder_hidden_states)
        value = attn.to_v(encoder_hidden_states)

        inner_dim = key.shape[-1]
        head_dim = inner_dim // attn.heads
        query = query.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
        key = key.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)
        value = value.view(batch_size, -1, attn.heads, head_dim).transpose(1, 2)

        _capture["step"] += 1
        if _capture["step"] == CAPTURE_AT_STEP:
            with torch.no_grad():
                scores = torch.matmul(query, key.transpose(-1, -2)) / math.sqrt(head_dim)
                probs = torch.softmax(scores.float(), dim=-1)  # (batch, heads, seq, seq)
                # 배치 순서는 [uncond(조건 zeroed), cond(실제 레퍼런스 포함)] -- 실제 레퍼런스가
                # 들어간 conditional 쪽(인덱스 1)을 봐야 "레퍼런스를 얼마나 참조하는지"가 의미있다.
                cond_index = 1 if probs.shape[0] > 1 else 0
                _capture["attn"] = probs.mean(dim=1)[cond_index].cpu()  # 헤드 평균
                _capture["hw"] = (height, width)

        hidden_states = F.scaled_dot_product_attention(query, key, value, attn_mask=None, dropout_p=0.0, is_causal=False)
        hidden_states = hidden_states.transpose(1, 2).reshape(batch_size, -1, attn.heads * head_dim).to(query.dtype)
        hidden_states = attn.to_out[0](hidden_states)
        hidden_states = attn.to_out[1](hidden_states)
        if input_ndim == 4:
            hidden_states = hidden_states.transpose(-1, -2).reshape(batch_size, channel, height, width)
        if attn.residual_connection:
            hidden_states = hidden_states + residual
        hidden_states = hidden_states / attn.rescale_output_factor
        return hidden_states


attn_procs = dict(pipeline.unet.attn_processors)
attn_procs[TARGET_NAME] = CapturingAttnProcessor()
pipeline.unet.set_attn_processor(attn_procs)

# --- 입력 준비: 철수 + 반바지, 하의 마스크(오늘 계속 실패했던 케이스) ---
print("\n=== 입력 준비 ===")
person_image = Image.open(PERSON_PATH).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))
pants_image = Image.open(PANTS_PATH).convert("RGB")
pants_image = resize_and_padding(pants_image, (WIDTH, HEIGHT))

lower_mask = automasker(person_image, mask_type="lower", fit_type=FIT_TYPE)["mask"]
lower_mask = mask_processor.blur(lower_mask, blur_factor=9)

generator = torch.Generator(device="cuda").manual_seed(42)

print("\n=== 생성(어텐션 캡처 포함) ===")
result_image = pipeline(
    image=person_image,
    condition_image=pants_image,
    mask=lower_mask,
    num_inference_steps=NUM_INFERENCE_STEPS,
    guidance_scale=GUIDANCE_SCALE,
    generator=generator,
)[0]
result_image.save(os.path.join(OUT_DIR, "generation_result.png"))

if _capture["attn"] is None:
    raise RuntimeError("어텐션을 캡처하지 못했습니다 (CAPTURE_AT_STEP이 총 스텝 수보다 클 수 있음)")

# --- 어텐션 맵 시각화 ---
print("\n=== 어텐션 맵 시각화 ===")
attn = _capture["attn"]  # (seq_len, seq_len)
h, w = _capture["hw"]  # 캔버스 전체 latent 해상도 (person 위 절반 + garment 아래 절반, concat_dim=-2)
half_h = h // 2
print(f"레이어 latent 해상도: {h}x{w} (person 절반: {half_h}x{w}, garment 절반: {half_h}x{w})")

# 발목 위치(person 사진 기준 y=92%, x=50%)에 해당하는 person 절반의 latent 좌표
ankle_y_frac, ankle_x_frac = 0.92, 0.5
query_y = int(ankle_y_frac * half_h)
query_x = int(ankle_x_frac * w)
query_idx = query_y * w + query_x

attn_row = attn[query_idx]  # (seq_len,) -- 이 쿼리가 전체 캔버스의 각 위치를 보는 가중치
attn_person_half = attn_row[: half_h * w].reshape(half_h, w).numpy()
attn_garment_half = attn_row[half_h * w :].reshape(half_h, w).numpy()

person_weight_sum = float(attn_person_half.sum())
garment_weight_sum = float(attn_garment_half.sum())
print(f"발목 쿼리 어텐션 비중 -- person(원본) 절반: {person_weight_sum:.3f} / garment(레퍼런스) 절반: {garment_weight_sum:.3f}")


def heatmap_overlay(base_image: Image.Image, attn_map: np.ndarray, query_px=None) -> Image.Image:
    attn_map = attn_map / (attn_map.max() + 1e-8)
    heat = Image.fromarray((attn_map * 255).astype(np.uint8)).resize(base_image.size, Image.BILINEAR)
    heat_np = np.array(heat).astype(np.float32) / 255.0
    base_np = np.array(base_image).astype(np.float32)
    red = np.zeros_like(base_np)
    red[..., 0] = 255
    alpha = (heat_np[..., None] ** 0.6) * 0.75
    blended = base_np * (1 - alpha) + red * alpha
    out = Image.fromarray(blended.astype(np.uint8))
    if query_px is not None:
        draw = ImageDraw.Draw(out)
        x, y = query_px
        r = 8
        draw.ellipse([x - r, y - r, x + r, y + r], outline=(0, 255, 0), width=3)
    return out


query_px = (int(ankle_x_frac * WIDTH), int(ankle_y_frac * HEIGHT))
person_overlay = heatmap_overlay(person_image, attn_person_half, query_px=query_px)
garment_overlay = heatmap_overlay(pants_image, attn_garment_half)

person_overlay.save(os.path.join(OUT_DIR, "attn_on_person.png"))
garment_overlay.save(os.path.join(OUT_DIR, "attn_on_garment.png"))

with open(os.path.join(OUT_DIR, "summary.txt"), "w", encoding="utf-8") as f:
    f.write(f"layer: {TARGET_NAME}\nstep: {CAPTURE_AT_STEP}/{NUM_INFERENCE_STEPS}\n")
    f.write(f"query(ankle) pixel: {query_px}\n")
    f.write(f"attention weight sum -- person(original) half: {person_weight_sum:.4f}\n")
    f.write(f"attention weight sum -- garment(reference) half: {garment_weight_sum:.4f}\n")

print(f"\n완료 -> {OUT_DIR}/ (generation_result.png, attn_on_person.png, attn_on_garment.png, summary.txt)")
