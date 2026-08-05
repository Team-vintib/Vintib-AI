"""모자(`hat.jpg`)/신발(`shoes.jpg`)은 CatVTON으로 시도했을 때 둘 다 실패했다 -- 모자는
마스크를 수동으로 그려도 엉뚱한 상자 모양+색으로 나왔고, 신발은 마스크가 원본 운동화
실루엣에 묶여서 샌들의 오픈토/스트랩 형태 자체가 나올 수 없었다. CatVTON은 상의/하의
의류 try-on 전용으로 학습된 모델이라 액세서리는 학습 분포 밖이다.

모자/신발은 (아우터나 상의/하의와 달리) 사이즈 조절이 필요 없으므로, 아우터에서 검증한
FLUX2 참조 편집 방식(`image=` 원본 사진 + "이 사람에게 이걸 입혀라" 프롬프트)을 그대로
쓴다 -- 마스크/인페인팅 없이 통짜로 다시 그리는 방식이라 신발 형태가 원본 실루엣에
묶이는 문제 자체가 없고, VLM 캡션으로 뽑은 색상/스타일 설명을 프롬프트에 직접 반영하니
색상 정확도도 CatVTON보다 나을 것으로 기대한다. CatVTON 패스 없이 이 결과를 그대로 최종
결과로 쓴다.
"""

import os
import time

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from PIL import Image
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

from quality_vlm_loader import generate_from_image, load_qwen_vl
from utils import resize_and_crop

OUT_DIR = "result/alpha3_hat_shoes"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
NUM_STEPS = 8
PERSON_NAME = "heedongi"
ORIGINAL_PHOTO_PATH = os.path.join("..", "models_ai_generated", f"{PERSON_NAME}.png")
HAT_PATH = os.path.join("image", "alpha_3", "hat.jpg")
SHOES_PATH = os.path.join("image", "alpha_3", "shoes.jpg")

CAPTION_PROMPT = (
    "Describe this product's color, material, and style in one short phrase for a "
    "fashion photo shoot brief, e.g. 'a black wide-brim nylon bucket hat' or 'black "
    "leather cross-strap sandals'. Do not mention a person."
)

print("=== Step 0: VLM로 모자/신발 캡션 (Qwen3-VL-4B, 4bit) ===")
t0 = time.time()
vlm_bundle = load_qwen_vl("Qwen/Qwen3-VL-4B-Instruct", quantization="4bit")
hat_caption = generate_from_image(vlm_bundle, Image.open(HAT_PATH).convert("RGB"), CAPTION_PROMPT, max_new_tokens=60)
shoes_caption = generate_from_image(vlm_bundle, Image.open(SHOES_PATH).convert("RGB"), CAPTION_PROMPT, max_new_tokens=60)
print(f"모자 캡션: {hat_caption!r}")
print(f"신발 캡션: {shoes_caption!r} ({time.time() - t0:.1f}s)")

del vlm_bundle
torch.cuda.empty_cache()

print("\n=== Step 1: 텍스트 인코더 로드 ===")
t0 = time.time()
quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
text_encoder = AutoModelForCausalLM.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    subfolder="text_encoder",
    quantization_config=quant_config,
    torch_dtype=torch.bfloat16,
)
print(f"완료 ({time.time() - t0:.1f}s)")

print("\n=== Step 2: 트랜스포머 로드 ===")
t0 = time.time()
transformer = Flux2Transformer2DModel.from_single_file(
    "https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF/blob/main/flux-2-klein-4b-Q4_0.gguf",
    config="black-forest-labs/FLUX.2-klein-4B",
    subfolder="transformer",
    quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
    torch_dtype=torch.bfloat16,
)
print(f"완료 ({time.time() - t0:.1f}s)")

print("\n=== Step 3: 파이프라인 조립 ===")
pipe = Flux2KleinPipeline.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    transformer=transformer,
    text_encoder=text_encoder,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()

ref_image = resize_and_crop(Image.open(ORIGINAL_PHOTO_PATH).convert("RGB"), (WIDTH, HEIGHT))

cases = {
    "hat_only": (
        f"IMPORTANT: dress the person in the reference photo in {hat_caption}. Keep "
        "the same person, face, pose, camera angle, framing, and background as the "
        "reference photo, and keep the existing shirt, pants, and shoes unchanged "
        "-- change only by adding the hat."
    ),
    "shoes_only": (
        f"IMPORTANT: change the person's shoes in the reference photo to {shoes_caption}. "
        "Keep the same person, face, pose, camera angle, framing, and background as "
        "the reference photo, and keep the existing shirt and pants unchanged -- "
        "change only the shoes."
    ),
    "hat_and_shoes": (
        f"IMPORTANT: dress the person in the reference photo in {hat_caption}, and "
        f"change their shoes to {shoes_caption}. Keep the same person, face, pose, "
        "camera angle, framing, and background as the reference photo, and keep the "
        "existing shirt and pants unchanged -- change only the hat and shoes."
    ),
}

for name, prompt in cases.items():
    print(f"\n=== 생성: {PERSON_NAME}_{name} ===")
    print(f"프롬프트: {prompt!r}")

    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    image = pipe(
        image=[ref_image],
        prompt=prompt,
        height=HEIGHT,
        width=WIDTH,
        num_inference_steps=NUM_STEPS,
        guidance_scale=4.0,
        generator=torch.Generator(device="cpu").manual_seed(1),
    ).images[0]
    elapsed = time.time() - t0
    peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9

    out_path = os.path.join(OUT_DIR, f"flux_{PERSON_NAME}_{name}.png")
    image.save(out_path)
    print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")

print("\n=== 전체 완료 ===")
