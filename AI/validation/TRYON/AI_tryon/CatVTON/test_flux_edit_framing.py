"""FLUX2 Klein이 `image=` 참조 이미지를 앵커로 삼아 편집하는 모드를 지원하는지 빠르게
확인한다.

1차 시도: M 사이즈 worn-reference(이미 재킷을 입은 이미지)를 참조로 주고 "재킷 핏만
바꿔라"고 지시했더니, 프레이밍은 완벽히 고정됐지만 핏 변화 자체가 거의 반영 안 됐다 --
이미 그려진 재킷을 갈아치우는 걸 모델이 강하게 거부하는 것으로 보인다.

2차 시도(이 버전): 재킷이 전혀 없는 진짜 원본(맨몸/베이스 사진, `models_ai_generated/
heedongi.png`)을 참조로 주고 "이 사람에게 이런 핏의 재킷을 입혀라"는 새 생성 프롬프트를
쓴다 -- 기존 옷을 지우는 게 아니라 새로 입히는 것이므로 핏 반영이 더 잘 될 수 있다.
프레이밍(포즈/스케일/카메라/발 보이는지 여부까지)은 원본 사진 그대로를 정답 기준으로
삼는다 -- 원본에 발이 없으면 없는 대로, 있으면 있는 대로 따라가면 된다.
"""

import time

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from PIL import Image
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

from utils import resize_and_crop

REF_PATH = "../models_ai_generated/heedongi.png"
OUT_PATH = "result/worn_references/_test_edit_xxl_from_original_8steps.png"

print("=== 로드 ===")
t0 = time.time()
quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
text_encoder = AutoModelForCausalLM.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    subfolder="text_encoder",
    quantization_config=quant_config,
    torch_dtype=torch.bfloat16,
)
transformer = Flux2Transformer2DModel.from_single_file(
    "https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF/blob/main/flux-2-klein-4b-Q4_0.gguf",
    config="black-forest-labs/FLUX.2-klein-4B",
    subfolder="transformer",
    quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
    torch_dtype=torch.bfloat16,
)
pipe = Flux2KleinPipeline.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    transformer=transformer,
    text_encoder=text_encoder,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()
print(f"완료 ({time.time() - t0:.1f}s)")

ref_image = resize_and_crop(Image.open(REF_PATH).convert("RGB"), (768, 1024))

prompt = (
    "IMPORTANT: dress the person in the reference photo in a charcoal grey "
    "wool-blend collared overshirt jacket with a button front and chest pocket "
    "that looks extremely oversized and baggy -- NOT a fitted or regular cut. The "
    "jacket must be worn in an obviously very baggy fit that visibly drapes far "
    "away from the body through the chest, shoulders, and body, about 39% too big "
    "at the chest, the shoulder seams drooping down off the shoulders onto the "
    "upper arms, over a plain white t-shirt visible at the collar and cuffs, and "
    "plain jeans. Keep the same person, face, pose, camera angle, framing, and "
    "background as the reference photo -- change only the clothing."
)
print(f"프롬프트: {prompt!r}")

t0 = time.time()
image = pipe(
    image=[ref_image],
    prompt=prompt,
    height=1024,
    width=768,
    num_inference_steps=8,
    guidance_scale=4.0,
    generator=torch.Generator(device="cpu").manual_seed(1),
).images[0]
print(f"생성 완료 ({time.time() - t0:.1f}s)")
image.save(OUT_PATH)
print(f"저장 -> {OUT_PATH}")
