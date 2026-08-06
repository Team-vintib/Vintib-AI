import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from PIL import Image
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

print("=== Step 1: 텍스트 인코더 로드 (4bit 양자화) ===")
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

text_encoder = AutoModelForCausalLM.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    subfolder="text_encoder",
    quantization_config=quant_config,
    torch_dtype=torch.bfloat16,
)
print("텍스트 인코더 로드 완료")

print("=== Step 2: Diffusion 트랜스포머 로드 (GGUF Q4_0) ===")
transformer = Flux2Transformer2DModel.from_single_file(
    "https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF/blob/main/flux-2-klein-4b-Q4_0.gguf",
    config="black-forest-labs/FLUX.2-klein-4B",
    subfolder="transformer",
    quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
    torch_dtype=torch.bfloat16,
)
print("트랜스포머 로드 완료")

print("=== Step 3: 파이프라인 조립 ===")
pipe = Flux2KleinPipeline.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    transformer=transformer,
    text_encoder=text_encoder,
    torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()
print("파이프라인 조립 완료")

print("=== Step 4: 레퍼런스 이미지 로드 ===")
person_img = Image.open("image/person.jpg").convert("RGB").resize((1024, 1024))
cloth_img = Image.open("image/cloth.jpg").convert("RGB").resize((1024, 1024))

# ---- 신체 스펙 (실제 서비스에선 사용자 입력값으로 대체) ----
body_specs = {
    "height_cm": 150,
    "build": "athletic",
    "shoulder_width": "broad",  # narrow / average / broad
    "waist": "wide",  # slim / average / wide
}

print("=== 프롬프트 구성 ===")
prompt = (
    "The person from the first reference image, keeping their exact face, "
    "hairstyle, skin tone, and identity unchanged. "
    f"The person's body proportions: approximately {body_specs['height_cm']}cm tall, "
    f"{body_specs['build']} build, {body_specs['shoulder_width']} shoulders, "
    f"{body_specs['waist']} waist. "
    "Adjust the body shape in the image to match these proportions if different "
    "from the original photo. "
    "The person is now wearing the exact garment shown in the second reference image — "
    "same color, pattern, fabric texture, and silhouette. Do not alter the garment design. "
    "Photorealistic, natural studio lighting, full body visible."
)

print("=== 이미지 생성 ===")
image = pipe(
    prompt=prompt,
    image=[person_img, cloth_img],
    height=1024,
    width=1024,
    num_inference_steps=20,
    guidance_scale=7.0,
    generator=torch.Generator(device="cpu").manual_seed(0),
).images[0]

image.save("bodyspec_tryon_output2.png")
print("완료!")
