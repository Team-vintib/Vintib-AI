import torch
from PIL import Image
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel
from diffusers import GGUFQuantizationConfig
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

# =========================================================
# 0. 핏(Fit) 계산 엔진 — 규칙 기반
#    사람 사이즈 vs 옷 사이즈를 비교해서
#    "핏 카테고리"와 "구체적 시각 묘사 문구"를 산출한다.
# =========================================================

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

FIT_DESCRIPTIONS = {
    "tight": (
        "the garment fits tightly and snugly against the body, "
        "fabric slightly stretched across the shoulders and torso, "
        "sleeves ending right at the wrist, no excess fabric"
    ),
    "fitted": (
        "the garment fits well and follows the body's natural silhouette, "
        "shoulder seams aligning with the natural shoulder line, "
        "sleeves reaching the wrist naturally"
    ),
    "relaxed": (
        "the garment fits loosely with a relaxed drape, "
        "slight excess fabric at the waist and torso, "
        "sleeves slightly longer than the wrist, "
        "shoulder seams sitting slightly below the natural shoulder line"
    ),
    "oversized": (
        "the garment is noticeably oversized for the body, "
        "sleeves extending past the wrists and partially covering the hands, "
        "shoulder seams drooping well past the natural shoulder line, "
        "excess loose fabric bunching and folding at the torso and waist, "
        "the overall silhouette appearing baggy and boxy rather than fitted"
    ),
}


def determine_fit_category(body_size: str, cloth_size: str) -> str:
    """사람 사이즈와 옷 사이즈의 순번 차이를 계산해 핏 카테고리를 반환."""
    diff = SIZE_ORDER.index(cloth_size) - SIZE_ORDER.index(body_size)
    if diff <= 0:
        return "tight"
    elif diff == 1:
        return "fitted"
    elif diff == 2:
        return "relaxed"
    else:
        return "oversized"


def build_fit_prompt_segment(body_size: str, cloth_size: str) -> str:
    category = determine_fit_category(body_size, cloth_size)
    description = FIT_DESCRIPTIONS[category]
    return category, description


# =========================================================
# 1. 파이프라인 로드
# =========================================================

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


# =========================================================
# 2. 레퍼런스 이미지 + 스펙 입력
#    (실제 서비스에선 이 블록 전체가 사용자 입력값으로 대체됨)
# =========================================================

print("=== Step 4: 레퍼런스 이미지 로드 ===")
person_img = Image.open("image/person.jpg").convert("RGB").resize((1024, 1024))
cloth_img = Image.open("image/cloth.jpg").convert("RGB").resize((1024, 1024))

# ---- 사람 신체 스펙 ----
body_specs = {
    "height_cm": 190,
    "build": "athletic",
    "shoulder_width": "broad",  # narrow / average / broad
    "waist": "wide",  # slim / average / wide
    "size_label": "XL",  # 사람의 체형에 맞는 옷 사이즈 (예: 평소 입는 사이즈)
}

# ---- 옷 스펙 (상품 정보에서 가져온다고 가정) ----
cloth_specs = {
    "size_label": "XS",
    "category": "t-shirt",
}

# ---- 핏 계산 ----
fit_category, fit_description = build_fit_prompt_segment(
    body_specs["size_label"], cloth_specs["size_label"]
)
print(f"계산된 핏 카테고리: {fit_category}")


# =========================================================
# 3. 프롬프트 구성
# =========================================================

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
    "same color, pattern, and fabric texture as the reference. "
    f"Because the garment is size {cloth_specs['size_label']} and the person's usual size "
    f"is {body_specs['size_label']}, the fit must clearly show this size difference: "
    f"{fit_description}. "
    "Photorealistic clothing drape, natural fabric folds and shadows consistent with "
    "the described fit, studio lighting, full body visible from head to feet."
)

print("---- 최종 프롬프트 ----")
print(prompt)

# =========================================================
# 4. 이미지 생성
#    * klein(distilled)은 guidance_scale이 무시되므로 전달하지 않는다.
# =========================================================

print("=== 이미지 생성 ===")
image = pipe(
    prompt=prompt,
    image=[person_img, cloth_img],
    height=1024,
    width=1024,
    num_inference_steps=10,
    generator=torch.Generator(device="cpu").manual_seed(0),
).images[0]

output_name = f"tryon_fit_{fit_category}.png"
image.save(output_name)
print(f"완료! {output_name} 저장됨")
