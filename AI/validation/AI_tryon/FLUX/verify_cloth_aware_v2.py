import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from PIL import Image
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

# =========================================================
# 0. 핏(Fit) 계산 엔진 — 규칙 기반
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
    diff = SIZE_ORDER.index(cloth_size) - SIZE_ORDER.index(body_size)
    if diff <= 0:
        return "tight"
    elif diff == 1:
        return "fitted"
    elif diff == 2:
        return "relaxed"
    else:
        return "oversized"


def build_fit_prompt_segment(body_size: str, cloth_size: str):
    category = determine_fit_category(body_size, cloth_size)
    description = FIT_DESCRIPTIONS[category]
    return category, description


# =========================================================
# 0-1. 체형 사전 워핑(pre-warp) 함수
#    person_img 레퍼런스가 체형 지시를 덮어버리는 문제를 완화하기 위해,
#    목표 체형 방향으로 이미지를 미리 살짝 왜곡시켜 놓는다.
#    (참고용 근사치이며, 정밀한 신체 비율 계산이 아님)
# =========================================================


def pre_warp_body(
    img: Image.Image, height_scale: float = 1.0, width_scale: float = 1.0
) -> Image.Image:
    w, h = img.size
    new_w, new_h = int(w * width_scale), int(h * height_scale)
    resized = img.resize((new_w, new_h))
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    offset = ((w - new_w) // 2, (h - new_h) // 2)
    canvas.paste(resized, offset)
    return canvas


def estimate_warp_scale(body_specs: dict, reference_height_cm: float = 170.0):
    """reference_height_cm: 원본 person_img 속 인물의 대략적인 기준 키(추정치).
    실제 서비스에서는 원본 사진의 실제 키 추정치를 넣어야 정확도가 올라간다."""
    height_scale = body_specs["height_cm"] / reference_height_cm

    shoulder_map = {"narrow": 0.92, "average": 1.0, "broad": 1.1}
    waist_map = {"slim": 0.92, "average": 1.0, "wide": 1.1}

    width_scale = shoulder_map.get(body_specs["shoulder_width"], 1.0) * waist_map.get(
        body_specs["waist"], 1.0
    )
    height_scale = max(0.85, min(1.15, height_scale))
    width_scale = max(0.85, min(1.2, width_scale))
    return height_scale, width_scale


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
# =========================================================

print("=== Step 4: 레퍼런스 이미지 로드 ===")
person_img = Image.open("image/person2.jpg").convert("RGB").resize((1024, 1024))
cloth_img = Image.open("image/cloth3.jpg").convert("RGB").resize((1024, 1024))

body_specs = {
    "height_cm": 190,
    "build": "athletic",
    "shoulder_width": "broad",
    "waist": "wide",
    "size_label": "XXL",
}

cloth_specs = {
    "size_label": "XS",
    "category": "t-shirt",
}

fit_category, fit_description = build_fit_prompt_segment(
    body_specs["size_label"], cloth_specs["size_label"]
)
print(f"계산된 핏 카테고리: {fit_category}")

height_scale, width_scale = estimate_warp_scale(body_specs, reference_height_cm=170.0)
print(f"적용할 warp scale: height={height_scale:.3f}, width={width_scale:.3f}")
person_img_warped = pre_warp_body(person_img, height_scale=height_scale, width_scale=width_scale)


# =========================================================
# 3. 프롬프트 구성
# =========================================================

print("=== 프롬프트 구성 ===")
prompt = (
    "Take the face, hairstyle, and skin tone from the first reference image, but "
    "generate a COMPLETELY DIFFERENT body build: "
    f"approximately {body_specs['height_cm']}cm tall, {body_specs['build']} build, "
    f"{body_specs['shoulder_width']} shoulders, {body_specs['waist']} waist. "
    "This body's proportions must look visibly different from the body shown in the "
    "reference photo — do not copy the reference body shape or proportions. "
    "Only the face, hairstyle, and skin tone should match the reference. "
    "The person is now wearing the exact garment shown in the second reference image — "
    "same color, pattern, and fabric texture as the reference. "
    f"Because the garment is size {cloth_specs['size_label']} and the person's body "
    f"requires size {body_specs['size_label']}, the fit must clearly show this size "
    f"difference: {fit_description}. "
    "Photorealistic, natural studio lighting, full body visible from head to feet."
)

print("---- 최종 프롬프트 ----")
print(prompt)


# =========================================================
# 4. 이미지 생성
# =========================================================

print("=== 이미지 생성 ===")
image = pipe(
    prompt=prompt,
    image=[person_img_warped, cloth_img],
    height=1024,
    width=1024,
    num_inference_steps=10,
    generator=torch.Generator(device="cpu").manual_seed(0),
).images[0]

output_name = f"tryon_fit_{fit_category}.png"
image.save(output_name)
print(f"완료! {output_name} 저장됨")
