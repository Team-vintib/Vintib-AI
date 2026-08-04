"""4명(철수/영희/둘리/마이콜) x 5사이즈(S/M/L/XL/XXL) 조합마다 실제 치수 비율(chest_ratio)로
"얼마나 타이트/루즈한지"를 계산해서, 그 정도에 맞는 알파테스트3 그래픽 티셔츠(`top.jpg`)
worn-reference를 FLUX로 생성한다. `generate_worn_reference_jeans_fitaware.py`(하의)와 같은
원리를 상의에 적용한다 -- 가슴둘레가 허리둘레 역할, 전체길이가 총장 역할을 한다.

사이즈표(가슴둘레 cm): S=107 M=112 L=117 XL=122 XXL=127. `가슴둘레`는 청바지 첫 표와
마찬가지로 "둘레"라서, ratio = 가슴둘레 / body_chest_cm로 그대로 계산한다(양쪽 다
평평하게 편 폭으로 나누면 상쇄되므로 §9와 동일한 식).

이 상품은 그래픽 프린트가 제품 정체성의 핵심이라(캡션에서 색상/원단만 뽑으면 프린트가
날아가서 다른 옷처럼 보인다), 이번 VLM 캡션 프롬프트는 색상과 함께 그래픽/텍스트 디자인도
같이 뽑는다.
"""

import os
import sys
import time
from pathlib import Path

import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
from PIL import Image
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

_REPO_ROOT = Path(__file__).resolve().parents[5]
_WORKER_MODELS_PATH = _REPO_ROOT / "worker" / "models"
if str(_WORKER_MODELS_PATH) not in sys.path:
    sys.path.insert(0, str(_WORKER_MODELS_PATH))

from quality_vlm.loader import generate_from_image, load_qwen_vl  # noqa: E402

OUT_DIR = "result/worn_references"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
NUM_STEPS = 8
GARMENT_PATH = os.path.join("image", "alpha_3", "top.jpg")

# 사람마다 본인 AI 모델 생성 프롬프트와 동일한 몸 묘사 + 하의 색(전부 청바지라 안전) +
# 가슴둘레/키/어깨너비/팔길이 가정값. 둘리는 XXL(127cm)보다도 큰 130cm로 잡아서 전
# 사이즈에서 타이트하게 나오도록 한다(§9의 둘리 허리 110cm와 같은 설계). 어깨/팔은
# 체격에 비례해서 대략적으로 잡았다(실측 데이터 없음, §9.4 신장 가정값과 같은 성격의
# 근사치).
PEOPLE = {
    # (body_desc, pants_desc, chest_cm, height_cm, shoulder_cm, arm_cm)
    # NOTE: cheolsu -> heedongi(희동이), younghee -> dooner(도우너)로 개명(둘리 세계관
    # 캐릭터 이름으로 통일). 체격 가정값은 그대로 유지.
    "heedongi": ("a young Korean man", "jeans", 92.0, 175.0, 46.0, 28.0),
    "dooner": ("a young Korean woman", "jeans", 84.0, 162.0, 38.0, 24.0),
    "dooly": ("a heavyset plus-size Korean man with a bigger, larger build", "jeans", 130.0, 172.0, 54.0, 27.0),
    "maikol": ("a tall, slim young Black man", "jeans", 96.0, 188.0, 48.0, 31.0),
}
SIZE_TABLE_CHEST_CM = {"S": 107.0, "M": 112.0, "L": 117.0, "XL": 122.0, "XXL": 127.0}
# 전체길이(cm, 실제 사이즈표 값) -- 사이즈가 커질수록 기장도 길어진다.
LENGTH_TABLE_CM = {"S": 68.0, "M": 70.0, "L": 72.0, "XL": 74.0, "XXL": 75.0}
# 어깨너비(cm, 실제 사이즈표 값)
SHOULDER_TABLE_CM = {"S": 53.5, "M": 55.0, "L": 56.5, "XL": 58.0, "XXL": 59.5}
# 소매길이(cm, 실제 사이즈표 값)
SLEEVE_TABLE_CM = {"S": 23.5, "M": 24.5, "L": 25.5, "XL": 26.5, "XXL": 27.5}


# (상한 ratio, 문구, 강조 재배치 필요 여부) -- ratio 오름차순. 0.05 단위로 촘촘하게
# 나눠서 5사이즈가 사람마다 서로 다른 단계에 떨어지게 한다(§9 청바지보다 더 세분화).
# 강조 재배치(True)는 극단(아주 타이트/아주 루즈)에서만 켠다 -- LLM 텍스트 인코더가
# 문장 앞쪽에 더 강하게 반응해서, "체격 큰/작은 사람"이 먼저 나오면 학습된 편향(평범한
# 핏)으로 되돌아간다는 게 §9 청바지에서 확립됐다.
_TIGHT_TABLE = [
    (0.65, "crushed impossibly tight, the fabric stretched to tearing point across the "
           "chest, belly, and shoulders, a second-skin silhouette with zero slack "
           "fabric anywhere, the shoulders and upper arms visibly compressed", True),
    (0.72, "stretched to its absolute limit, clinging tightly to the exact contour of "
           "the chest, belly, and shoulders like a compression shirt or muscle tee "
           "with almost no slack fabric anywhere, a second-skin silhouette instead of "
           "the garment's normal relaxed cut", True),
    (0.79, "clinging tightly to the contour of the chest, belly, and shoulders with "
           "very little slack fabric, a noticeably fitted, skin-tight silhouette "
           "instead of the garment's normal relaxed cut", True),
    (0.85, "clinging closely to the contour of the chest, belly, and shoulders with "
           "little slack fabric, a noticeably more fitted silhouette than the "
           "garment's normal relaxed cut", False),
    (0.90, "fitting close through the chest and shoulders with only a little slack "
           "fabric, slightly more fitted than the garment's normal relaxed cut", False),
    (0.95, "worn snugly, fitting close and slightly tight across the chest and "
           "shoulders", False),
]
_LOOSE_TABLE = [
    (1.10, "worn in a relaxed, very slightly loose fit through the chest and "
           "shoulders", False),
    (1.16, "worn in a noticeably loose fit with visible extra room through the chest "
           "and shoulders", False),
    (1.23, "worn in a loose, roomy fit with clearly visible extra fabric through the "
           "chest, shoulders, and body", False),
    (1.30, "worn in a baggy fit with excess room through the chest, shoulders, and "
           "body", False),
    (1.40, "worn in a very baggy fit that visibly drapes away from the body through "
           "the chest, shoulders, and body", True),
    (1.55, "worn in an oversized fit, swimming in excess fabric that drapes far away "
           "from the body through the chest, shoulders, and body", True),
    (float("inf"), "worn in an extremely oversized fit, engulfed in excess fabric that "
                   "drapes far away from the body through the chest, shoulders, and "
                   "body, like wearing a garment several sizes too large", True),
]


def fit_descriptor(ratio: float) -> tuple[str, bool]:
    """chest_ratio(1.0 근처가 중립) -> (FLUX 프롬프트용 핏 묘사 절, 강조 재배치 필요 여부).

    레귤러 구간(0.95~1.05)은 대칭 처리한다 -- ratio<1.0이면 무조건 타이트로 빠지던
    버그(둘리 XXL=0.977이 "약간 타이트"로 잘못 나온 원인)를 고쳤다.
    """
    pct = abs(ratio - 1.0) * 100
    if 0.95 <= ratio <= 1.05:
        return "fitting comfortably in a regular fit", False
    table = _TIGHT_TABLE if ratio < 0.95 else _LOOSE_TABLE
    direction = "too small" if ratio < 0.95 else "too big"
    for upper, base, emphasize in table:
        if ratio <= upper:
            return f"{base}, about {pct:.0f}% {direction} at the chest", emphasize
    # 도달하지 않음(테이블 마지막 항목이 inf) -- 방어적으로만 남겨둠
    base, emphasize = table[-1][1], table[-1][2]
    return f"{base}, about {pct:.0f}% {direction} at the chest", emphasize


def length_descriptor(length_delta_cm: float) -> str:
    """S(가장 짧은 사이즈) 대비 전체길이 차이를 밑단 묘사 절로 바꾼다. 0이면(S 자신)
    문구 없음.

    실제 사이즈표 범위(S~XXL 전체길이 68~75cm)는 절대 편차가 최대 7cm뿐이다(키
    대비로도 3.5~4.3% 수준). 이전 버전은 %만 보고 상위 구간에서 "엉덩이를 훌쩍
    지나 내려온다"는 식으로 표현했는데, 사람마다 이 pct가 다 XXL에서 3.7~4.3%로
    비슷하게 몰려서 사실상 전원 최상위(가장 센) 문구를 받았고, 그 문구 자체도
    "well past the hips"라 실제 7cm보다 과장돼 보였다. cm 절대값을 그대로 문구에
    박아서 항상 "몇 cm 차이일 뿐"이라는 걸 명시하고, 표현 강도도 전체적으로
    낮춘다(최상위도 "엉덩이선 바로 아래" 정도로만).
    """
    if length_delta_cm <= 0:
        return ""
    if length_delta_cm <= 2.0:
        return f", the hem sitting just barely lower, only about {length_delta_cm:.1f}cm longer than the shortest size -- a subtle difference"
    if length_delta_cm <= 4.5:
        return f", the hem sitting a little lower at the hip line, about {length_delta_cm:.1f}cm longer than the shortest size -- still a modest difference"
    return (
        f", the hem sitting right at or just barely below the hip line, about "
        f"{length_delta_cm:.1f}cm longer than the shortest size -- a modest, "
        "realistic difference, not dramatically longer"
    )


def shoulder_descriptor(ratio: float) -> str:
    """garment_shoulder_width / body_shoulder_cm(1.0 근처가 중립) -> 어깨선 묘사 절."""
    if ratio <= 0.90:
        return ", the shoulder seams pulled up tight onto the top of the shoulders"
    if ratio <= 1.10:
        return ", the shoulder seams sitting right at the natural shoulder points"
    return ", the shoulder seams drooping down off the shoulders onto the upper arms"


def sleeve_descriptor(ratio: float) -> str:
    """garment_sleeve_length / body_arm_cm(1.0 근처가 중립) -> 소매 길이 묘사 절."""
    if ratio <= 0.90:
        return ", the short sleeves riding up above the bicep"
    if ratio <= 1.15:
        return ", the sleeves ending at a normal length around the mid-bicep"
    return ", the sleeves hanging long, extending down past the elbow"


CAPTION_PROMPT = (
    "Describe this t-shirt's color and any graphic print or text design on it, in one "
    "short phrase for a fashion photo shoot brief, e.g. 'dark navy t-shirt with a "
    "colorful graphic print and text on the front'. Do NOT mention the cut, fit, or "
    "silhouette (not 'loose', 'fitted', 'oversized', etc.) -- that will be specified "
    "separately. Do not mention a person."
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

for person_name, (body_desc, pants_desc, chest_cm, height_cm, shoulder_cm, arm_cm) in PEOPLE.items():
    for size_label, garment_chest_cm in SIZE_TABLE_CHEST_CM.items():
        ratio = garment_chest_cm / chest_cm
        fit_phrase, needs_emphasis = fit_descriptor(ratio)
        length_delta_cm = LENGTH_TABLE_CM[size_label] - LENGTH_TABLE_CM["S"]
        length_phrase = length_descriptor(length_delta_cm)
        hem_phrase = length_phrase if length_phrase else ", the hem ending right at the waist"
        shoulder_phrase = shoulder_descriptor(SHOULDER_TABLE_CM[size_label] / shoulder_cm)
        sleeve_phrase = sleeve_descriptor(SLEEVE_TABLE_CM[size_label] / arm_cm)
        hem_phrase = f"{hem_phrase}{shoulder_phrase}{sleeve_phrase}"

        if needs_emphasis:
            # §9(청바지)에서 확립: LLM 텍스트 인코더는 문장 앞쪽 내용에 더 강하게
            # 반응한다 -- "체격이 큰/작은 사람"을 먼저 말하면 학습된 편향(평범한 핏)으로
            # 돌아가버린다. 실루엣을 문장 맨 앞으로 옮기고, 무엇이 "아닌지"도 명시해서
            # 편향을 상쇄한다. 타이트/루즈 양쪽 다 극단 구간에서 적용한다.
            if ratio < 1.0:
                emphasis_lead = (
                    f"IMPORTANT: the {garment_caption} t-shirt must look extremely "
                    "skin-tight and compression-fit -- NOT a loose or regular cut. "
                )
            else:
                emphasis_lead = (
                    f"IMPORTANT: the {garment_caption} t-shirt must look extremely "
                    "oversized and baggy -- NOT a fitted or regular cut. "
                )
            prompt = (
                f"{emphasis_lead}full "
                f"body studio photo of {body_desc} standing straight, facing camera, "
                f"wearing a t-shirt that is {fit_phrase}{hem_phrase}, and plain "
                f"{pants_desc} down to the ankles and shoes, the entire body from head "
                "to feet clearly visible in frame, plain solid white background, soft "
                "even studio lighting, photorealistic, sharp focus, e-commerce fashion "
                "model photo"
            )
        else:
            prompt = (
                f"full body studio photo of {body_desc} standing straight, facing camera, "
                f"wearing a {garment_caption} t-shirt, {fit_phrase}{hem_phrase}, and "
                f"plain {pants_desc} down to the ankles and shoes, the entire body from "
                "head to feet clearly visible in frame, plain solid white background, "
                "soft even studio lighting, photorealistic, sharp focus, e-commerce "
                "fashion model photo"
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

        out_path = os.path.join(OUT_DIR, f"top_worn_reference_{person_name}_{size_label}.png")
        image.save(out_path)
        print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")

print("\n=== 전체 완료 ===")
