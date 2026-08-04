"""4명(철수/영희/둘리/마이콜) x 4사이즈(M/L/XL/2XL) 조합마다 실제 치수 비율(width_ratio)로
"얼마나 타이트/루즈한지"를 계산해서, 그 정도에 맞는 청바지 worn-reference를 FLUX로 생성한다.

마스크 폭(dilation/erosion)만 조절하는 기존 방식은 두 가지 문제가 확인됐다(§9):
1. 조정량이 작으면(느슨한 핏 옷) 육안상 차이가 거의 안 보인다.
2. 조정량이 커도, "침식이 클수록(옷이 작을수록) 마스크 바깥의 원본이 더 많이 남고, 그
   원본은 이미 편안하게 맞는 모습으로 생성돼 있어서 오히려 루즈해 보이는" 역설적인 효과가
   있다 -- 침식량과 시각적 타이트함의 관계가 의도와 반대로 나타날 수 있다.

그래서 이번엔 레퍼런스 이미지 자체에 타이트/루즈 정도를 명시해서 diffusion에 직접 신호를
준다. `ratio = WAIST_WIDTH / (body_waist_cm / 2)`(§7.5 정의)를 7단계로 나눠 문구를 고른다.
옷 캡션은 VLM(quality_vlm의 Qwen3-VL 로더)로 한 번만 뽑아 4명 x 4사이즈에 재사용한다.
"""

import os
import time

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from PIL import Image
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

from quality_vlm_loader import generate_from_image, load_qwen_vl

OUT_DIR = "result/worn_references"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
NUM_STEPS = 8
GARMENT_PATH = os.path.join("image", "alpha_3", "jeans_cropped.png")

# 사람마다 본인 AI 모델 생성 프롬프트와 동일한 몸 묘사 + 셔츠 색 + 허리둘레/키 가정값
# (§9에서 확립). 셔츠 색을 본인 베이스 사진과 다르게 주면(예: 영희는 실제로 흰 티인데
# 회색으로 생성) 마스크 경계에서 그 색이 새어나오는 아티팩트가 생긴다 -- 반드시 맞춰야
# 한다. 키는 총장(길이) 차이를 "그 사람 기준 %"로 정규화하는 데 쓴다 -- 폭 축이
# body_waist_cm로 정규화하는 것과 같은 원리(§7.5).
PEOPLE = {
    # NOTE: 둘리 M(ratio=0.727, 물리적으로 30cm나 작은 사이즈)이 여전히 안 타이트해
    # 보여서 "extremely tight" 문구를 더 극단적으로 강화하고 둘리만 다시 만든다.
    # "cheolsu": ("a young Korean man", "grey", 75.0, 175.0),
    # "younghee": ("a young Korean woman", "white", 65.0, 162.0),
    "dooly": ("a heavyset plus-size Korean man with a bigger, larger build", "grey", 110.0, 172.0),
    # "maikol": ("a tall, slim young Black man", "grey", 72.0, 188.0),
}
SIZE_TABLE_WAIST_WIDTH_CM = {"M": 40.0, "L": 42.5, "XL": 45.0, "2XL": 47.5}
# 총장(cm, 실제 사이즈표 값) -- 사이즈가 커질수록 기장도 길어진다.
LENGTH_TABLE_CM = {"M": 106.5, "L": 108.0, "XL": 109.5, "2XL": 111.0}


def fit_descriptor(ratio: float) -> str:
    """width_ratio(1.0 근처가 중립) -> FLUX 프롬프트용 핏 묘사 절(clause).

    "jeans" 명사 뒤에 별도 절로 붙는다(예: "... jeans, {phrase}, bare ankles...") --
    캡션의 색상/원단 설명과 문법적으로 겹치지 않게 분리해서 핏 신호가 캡션에 묻히지
    않도록 한다.

    질적 구간(7단계)만 쓰면 같은 구간에 여러 사이즈가 몰릴 때(예: 영희의 L/XL/2XL이
    전부 ratio>1.30) 문구가 완전히 같아져서 같은 시드로는 동일한 이미지가 나온다 --
    정확한 %편차를 문구에 같이 넣어서 사이즈마다 항상 다른 프롬프트가 되게 한다.
    """
    pct = abs(ratio - 1.0) * 100
    if ratio < 1.0:
        if ratio <= 0.75:
            base = (
                "stretched to its absolute limit, clinging tightly to the exact contour "
                "of the belly, hips, thighs, and calves like a pair of skinny jeans "
                "with almost no slack fabric anywhere, a second-skin silhouette instead "
                "of the garment's normal straight-leg cut, a muffin-top bulge visible "
                "just above the waistband, the button straining hard to stay closed"
            )
        elif ratio <= 0.85:
            base = (
                "clinging closely to the contour of the hips, thighs, and calves with "
                "very little slack fabric, a noticeably narrower, more skinny-fit "
                "silhouette than the garment's normal straight-leg cut, the waistband "
                "snug against the skin with a slight bulge above it"
            )
        else:
            base = "worn snugly, fitting close and slightly tight against the hips, thighs, and calves"
        return f"{base}, about {pct:.0f}% too small at the waist"
    if ratio <= 1.05:
        return "fitting comfortably in a regular fit"
    if ratio <= 1.15:
        base = "worn in a relaxed, slightly loose fit through the hips, thighs, and calves"
    elif ratio <= 1.30:
        base = "worn in a loose, baggy fit with extra room through the hips, thighs, and calves"
    else:
        base = "worn in an extremely loose, oversized fit with excess room through the hips, thighs, and calves"
    return f"{base}, about {pct:.0f}% too big at the waist"


def length_descriptor(length_delta_cm: float, height_cm: float) -> str:
    """M(가장 짧은 사이즈) 대비 총장 차이를 그 사람 키 대비 %로 정규화해서 기장 묘사 절을
    고른다 -- 같은 절대 cm라도 키가 작으면 더 크게, 크면 더 작게 체감된다는 걸 반영한다
    (폭 축이 body_waist_cm로 정규화하는 것과 동일한 원리).

    0이면(M 자신) 문구 없음.
    """
    if length_delta_cm <= 0:
        return ""
    pct = length_delta_cm / height_cm * 100
    if pct <= 1.2:
        return f", the hem breaking gently right at the shoes (about {pct:.1f}% of their height longer than the shortest size)"
    return (
        f", the extra length (about {pct:.1f}% of their height more than the shortest "
        "size) pooling and bunching noticeably over the shoes"
    )


CAPTION_PROMPT = (
    "Describe this clothing item's color and fabric texture only, in a few words, e.g. "
    "'mid-wash blue denim with subtle whiskering'. Do NOT mention the cut, fit, or "
    "silhouette (not 'wide-leg', 'relaxed', 'skinny', 'baggy', etc.) -- that will be "
    "specified separately. Do not mention a person."
)

print("=== Step 0: VLM로 실제 상품 사진 캡션 (Qwen3-VL-4B, 4bit) ===")
t0 = time.time()
vlm_bundle = load_qwen_vl("Qwen/Qwen3-VL-4B-Instruct", quantization="4bit")
garment_image = Image.open(GARMENT_PATH).convert("RGB")
garment_caption = generate_from_image(vlm_bundle, garment_image, CAPTION_PROMPT, max_new_tokens=60)
print(f"캡션: {garment_caption!r} ({time.time() - t0:.1f}s)")

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

for person_name, (body_desc, shirt_color, waist_cm, height_cm) in PEOPLE.items():
    for size_label, garment_waist_width_cm in SIZE_TABLE_WAIST_WIDTH_CM.items():
        ratio = garment_waist_width_cm / (waist_cm / 2.0)
        fit_phrase = fit_descriptor(ratio)
        length_delta_cm = LENGTH_TABLE_CM[size_label] - LENGTH_TABLE_CM["M"]
        length_phrase = length_descriptor(length_delta_cm, height_cm)
        hem_phrase = length_phrase if length_phrase else ", ending cleanly right at the ankles above the shoes"

        if ratio <= 0.85:
            # LLM 텍스트 인코더는 문장 앞쪽 내용에 더 강하게 반응하는 것으로 보인다 --
            # "체격이 큰 사람"을 먼저 말하면 모델이 "그럼 루즈핏"이라는 학습된 편향으로
            # 돌아가버린다. 타이트한 실루엣을 문장 맨 앞으로 옮기고, 무엇이 "아닌지"도
            # 명시해서 편향을 상쇄한다.
            prompt = (
                f"IMPORTANT: the {garment_caption} jeans must look extremely "
                f"skin-tight and skinny-fit -- NOT a loose, straight-leg, or relaxed "
                f"cut. full body studio photo of {body_desc} standing straight, facing "
                f"camera, wearing a fitted plain {shirt_color} t-shirt and jeans that "
                f"are {fit_phrase}{hem_phrase}, plain solid white background, soft even "
                "studio lighting, photorealistic, sharp focus, e-commerce fashion "
                "model photo"
            )
        else:
            prompt = (
                f"full body studio photo of {body_desc} standing straight, facing camera, "
                f"wearing a fitted plain {shirt_color} t-shirt and "
                f"{garment_caption} jeans, {fit_phrase}{hem_phrase}, plain solid white "
                "background, soft even studio lighting, photorealistic, sharp focus, "
                "e-commerce fashion model photo"
            )
        print(f"\n=== 생성: {person_name}_{size_label} (ratio={ratio:.3f}, length_delta={length_delta_cm:.1f}cm) ===")
        print(f"프롬프트: {prompt!r}")

        torch.cuda.reset_peak_memory_stats()
        t0 = time.time()
        image = pipe(
            prompt=prompt,
            height=HEIGHT,
            width=WIDTH,
            num_inference_steps=NUM_STEPS,
            guidance_scale=4.0,
            generator=torch.Generator(device="cpu").manual_seed(1),
        ).images[0]
        elapsed = time.time() - t0
        peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9

        out_path = os.path.join(OUT_DIR, f"jeans_worn_reference_{person_name}_{size_label}.png")
        image.save(out_path)
        print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")

print("\n=== 전체 완료 ===")
