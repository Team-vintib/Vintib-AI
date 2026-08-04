"""아우터(오버셔츠形 재킷, `outer.jpg`) 실사용자 사이즈표 기반 fit-aware worn-reference를
희동이 1명 x 4사이즈(M/L/XL/XXL)로 생성한다. `generate_worn_reference_top_fitaware.py`와
동일한 원리 -- 가슴둘레/전체길이/어깨너비/소매길이를 각각 몸 치수와 비교해 핏 정도를
프롬프트에 반영한다.

아우터는 그래픽이 없는 민무늬 울 소재라(그래픽 정확도 문제와 무관), 이 실험의 목적은
"패턴이 있는 니트가 아니라 칼라/버튼/포켓이 있는 구조화된 재킷에서도 fit-aware
worn-reference + worn-reference-as-person 방식이 통하는지" 확인하는 것이다.

사이즈마다 독립적으로 처음부터(순수 txt2img) 생성했더니, 옷이 오버사이즈로 묘사될수록
카메라가 인물을 확대해서 찍는 프레이밍 버그가 있었다(SCHP로 머리 크기만 따로 재보니
M~XXL 사이에 38%나 벌어짐 -- 재킷 폭이 넓어지는 것과는 별개로 사람 자체가 커짐). 옷을
입은 worn-reference를 참조로 주고 "핏만 바꿔라"는 편집 프롬프트를 시도했더니 프레이밍은
고정됐지만 이미 그려진 재킷을 갈아치우는 걸 모델이 거부해서 핏 변화가 거의 안 먹혔다.
최종적으로는 재킷이 전혀 없는 원본 베이스 사진(`models_ai_generated/{person}.png`)을
FLUX2의 `image=` 참조로 주고 "이 사람에게 이런 핏의 재킷을 입혀라"는 새 생성 프롬프트를
쓰는 방식으로 두 문제를 동시에 해결했다 -- 기존 옷을 지우는 게 아니라 새로 입히는
것이므로 핏 반영도 잘 되고, 포즈/스케일/프레이밍(발이 보이는지 여부까지)은 참조 사진
그대로 상속된다.

사이즈표(cm): 어깨너비/소매길이/가슴둘레/전체길이. 소매길이가 상의 티셔츠표(23.5~27.5cm,
반팔 노출 길이)와 스케일이 다르다(60.5~64.5cm, 어깨점~손목 전체 소매기장) -- 재킷은
긴팔이라 별도의 신체 "전체 팔길이" 가정값을 쓴다(§ARM_FULL_CM).
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
from utils import resize_and_crop  # noqa: E402

OUT_DIR = "result/worn_references"
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
NUM_STEPS = 8  # 8/24스텝 비교 결과 품질/핏 반영 차이가 거의 없어 8로 유지
GARMENT_PATH = os.path.join("image", "alpha_3", "outer.jpg")
ORIGINAL_PHOTO_PATH = os.path.join("..", "models_ai_generated", "heedongi.png")

# 희동이 본인 AI 모델 생성 프롬프트와 동일한 몸 묘사 + 하의(청바지) + 가슴둘레/키/어깨너비는
# 상의 파이프라인과 동일값 재사용. ARM_FULL_CM만 이 스크립트 전용 -- 반팔 노출길이(28cm)가
# 아니라 어깨점부터 손목까지 전체 팔길이 가정값(175cm 남성 평균 근사치).
PERSON_NAME = "heedongi"
BODY_DESC = "a young Korean man"
BASE_LAYER_DESC = "a plain white t-shirt visible at the collar and cuffs, and plain jeans"
CHEST_CM = 92.0
SHOULDER_CM = 46.0
ARM_FULL_CM = 59.0

SIZE_TABLE_CHEST_CM = {"M": 114.0, "L": 118.0, "XL": 122.0, "XXL": 128.0}
LENGTH_TABLE_CM = {"M": 68.0, "L": 70.0, "XL": 72.0, "XXL": 73.0}
SHOULDER_TABLE_CM = {"M": 46.8, "L": 48.0, "XL": 49.2, "XXL": 51.0}
SLEEVE_TABLE_CM = {"M": 60.5, "L": 62.0, "XL": 63.5, "XXL": 64.5}
BASE_SIZE = "M"  # 이 사이즈표에서 가장 작은 사이즈(기장 델타 기준점)


# `generate_worn_reference_top_fitaware.py`와 동일한 테이블/로직 -- 재킷도 "가슴/어깨
# 둘레가 얼마나 남는가"로 핏을 표현하는 게 동일하게 적용된다.
_TIGHT_TABLE = [
    (0.65, "crushed impossibly tight, the fabric stretched to tearing point across the "
           "chest, belly, and shoulders, a second-skin silhouette with zero slack "
           "fabric anywhere, the shoulders and upper arms visibly compressed, unable to "
           "close the front buttons", True),
    (0.72, "stretched to its absolute limit, clinging tightly to the exact contour of "
           "the chest, belly, and shoulders with almost no slack fabric anywhere, a "
           "second-skin silhouette instead of the garment's normal relaxed cut, the "
           "front buttons straining", True),
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
    pct = abs(ratio - 1.0) * 100
    if 0.95 <= ratio <= 1.05:
        return "fitting comfortably in a regular fit", False
    table = _TIGHT_TABLE if ratio < 0.95 else _LOOSE_TABLE
    direction = "too small" if ratio < 0.95 else "too big"
    for upper, base, emphasize in table:
        if ratio <= upper:
            return f"{base}, about {pct:.0f}% {direction} at the chest", emphasize
    base, emphasize = table[-1][1], table[-1][2]
    return f"{base}, about {pct:.0f}% {direction} at the chest", emphasize


def length_descriptor(length_delta_cm: float) -> str:
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
    if ratio <= 0.90:
        return ", the shoulder seams pulled up tight onto the top of the shoulders"
    if ratio <= 1.10:
        return ", the shoulder seams sitting right at the natural shoulder points"
    return ", the shoulder seams drooping down off the shoulders onto the upper arms"


def sleeve_descriptor(ratio: float) -> str:
    if ratio <= 0.90:
        return ", the sleeves ending short of the wrist"
    if ratio <= 1.15:
        return ", the sleeves ending right at the wrist, a normal length"
    return ", the sleeves hanging long, covering the hands past the wrist"


CAPTION_PROMPT = (
    "Describe this jacket's color, fabric texture, and style (collar, buttons, "
    "pockets) in one short phrase for a fashion photo shoot brief, e.g. 'charcoal "
    "grey wool-blend collared overshirt jacket with a button front and chest "
    "pocket'. Do NOT mention the cut, fit, or silhouette (not 'loose', 'fitted', "
    "'oversized', etc.) -- that will be specified separately. Do not mention a "
    "person."
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

# 재킷이 전혀 없는 원본 베이스 사진을 참조로 준다 -- 포즈/스케일/카메라 프레이밍(발이
# 보이는지 여부까지)이 여기서 그대로 상속된다. txt2img로 매번 새로 그리면 사이즈마다
# 카메라 확대 정도가 달라지는 프레이밍 버그가 있었는데, 이 방식은 그 문제를 원천 차단한다.
ref_image = resize_and_crop(Image.open(ORIGINAL_PHOTO_PATH).convert("RGB"), (WIDTH, HEIGHT))

for size_label, garment_chest_cm in SIZE_TABLE_CHEST_CM.items():
    ratio = garment_chest_cm / CHEST_CM
    fit_phrase, needs_emphasis = fit_descriptor(ratio)
    length_delta_cm = LENGTH_TABLE_CM[size_label] - LENGTH_TABLE_CM[BASE_SIZE]
    length_phrase = length_descriptor(length_delta_cm)
    hem_phrase = length_phrase if length_phrase else ", the hem ending right at the hip"
    shoulder_phrase = shoulder_descriptor(SHOULDER_TABLE_CM[size_label] / SHOULDER_CM)
    sleeve_phrase = sleeve_descriptor(SLEEVE_TABLE_CM[size_label] / ARM_FULL_CM)
    hem_phrase = f"{hem_phrase}{shoulder_phrase}{sleeve_phrase}"

    if needs_emphasis:
        extremely = "skin-tight and compression-fit" if ratio < 1.0 else "oversized and baggy"
        emphasis_lead = f"IMPORTANT: the jacket must look extremely {extremely} -- NOT a fitted or regular cut. "
    else:
        emphasis_lead = ""

    prompt = (
        f"{emphasis_lead}dress the person in the reference photo in a "
        f"{garment_caption} that is {fit_phrase}{hem_phrase}, over "
        f"{BASE_LAYER_DESC}. Keep the same person, face, pose, camera angle, "
        "framing, and background as the reference photo -- change only the "
        "clothing."
    )
    print(f"\n=== 생성: {PERSON_NAME}_{size_label} (ratio={ratio:.3f}, length_delta={length_delta_cm:.1f}cm) ===")
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

    out_path = os.path.join(OUT_DIR, f"outer_worn_reference_{PERSON_NAME}_{size_label}.png")
    image.save(out_path)
    print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")

print("\n=== 전체 완료 ===")
