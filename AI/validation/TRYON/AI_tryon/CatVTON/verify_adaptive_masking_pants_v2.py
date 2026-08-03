"""바지(너비 축) 적응형 마스킹 재검증 — `person.jpg`로 찍은 기존 결과가 전부 무릎 아래가
잘려 나온 원인을 찾다가, 원본 인물 사진(person.jpg)이 상의·바지·신발이 전부 짙은 색이라
SCHP 인물 파싱이 하의 영역을 허벅지까지밖에 못 잡는 것으로 확인했다(마스크 자체가 이미
그 지점에서 끊겨 있었다 — diffusion 품질 문제가 아니었다).

그래서 이 스크립트는 `person.jpg` 대신, 색 대비가 뚜렷한 평면 스튜디오 컷
`person2.jpg`(연노랑 티셔츠 + 청바지 + 흰 운동화, 균일 조명)로 같은 케이스를 다시 돌린다.
나머지 로직(케이스 구성, 실측값)은 `verify_adaptive_masking.py`와 동일 — 다만 빠른 확인을
위해 스텝을 50 대신 20으로 낮췄다(§7.1의 50은 최종 품질 기준값이고, 이 스크립트는 마스크
커버리지 자체를 눈으로 확인하는 게 목적이라 속도를 우선한다).
"""

import os
import sys
from datetime import datetime

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_PRODUCTION_CATVTON_PATH = os.path.join(_REPO_ROOT, "worker", "models", "catvton")
sys.path.insert(0, _PRODUCTION_CATVTON_PATH)

import numpy as np  # noqa: E402
import torch  # noqa: E402
from diffusers.image_processor import VaeImageProcessor  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from PIL import Image  # noqa: E402

from model.adaptive_fit import compute_mask_adjustment  # noqa: E402
from model.cloth_masker import AutoMasker, vis_mask  # noqa: E402
from model.pipeline import CatVTONPipeline  # noqa: E402
from utils import init_weight_dtype, resize_and_crop, resize_and_padding  # noqa: E402


def composite_with_original(original_image, generated_image, mask):
    """마스크 안쪽은 생성된 이미지, 바깥쪽은 원본 이미지를 사용해 합성한다."""
    original_np = np.array(original_image.resize(generated_image.size)).astype(np.float32)
    generated_np = np.array(generated_image).astype(np.float32)
    mask_np = np.array(mask.resize(generated_image.size).convert("L")).astype(np.float32) / 255.0
    mask_np = np.expand_dims(mask_np, axis=-1)
    composited = generated_np * mask_np + original_np * (1 - mask_np)
    return Image.fromarray(composited.astype(np.uint8))


def _bypass_safety_checker(self, image):
    has_nsfw_concept = [False] * len(image) if isinstance(image, list) else [False]
    return image, has_nsfw_concept


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
pipeline.run_safety_checker = _bypass_safety_checker.__get__(pipeline)

mask_processor = VaeImageProcessor(
    vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True
)
automasker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device="cuda",
)
print("초기화 완료")

OUT_DIR = os.path.join("result", "adaptive_masking_pants_v2_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 20
PERSON_PATH = "image/person2.jpg"
LOWER_CLOTH_PATH = "image/pants.jpg"

person_image = Image.open(PERSON_PATH).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))
lower_cloth_image = resize_and_padding(Image.open(LOWER_CLOTH_PATH).convert("RGB"), (WIDTH, HEIGHT))

generator = torch.Generator(device="cuda").manual_seed(42)


def generate(base_image, condition_image, mask):
    result_image = pipeline(
        image=base_image,
        condition_image=condition_image,
        mask=mask,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        generator=generator,
    )[0]
    return composite_with_original(base_image, result_image, mask)


def run_case(label, body, garment):
    dilation_px = compute_mask_adjustment("lower", body, garment)
    print(f"{label}: body={body} garment={garment} -> dilation_px={dilation_px}")

    mask = automasker(
        person_image,
        mask_type="lower",
        fit_type="regular",  # body/garment 둘 다 있으면 무시되고 적응형 계산이 대신 쓰인다
        body_measurements=body,
        garment_measurements=garment,
    )["mask"]
    mask_blurred = mask_processor.blur(mask, blur_factor=9)

    vis_mask(person_image, mask).save(os.path.join(OUT_DIR, f"lower_{label}_mask.png"))
    result = generate(person_image, lower_cloth_image, mask_blurred)
    result.save(os.path.join(OUT_DIR, f"lower_{label}_tryon.png"))


# --- 너비 축(바지 허리): 몸 대비 타이트/루즈(스키니/배기) 비교 --------------------
LOWER_CASES = {
    "baseline_no_measurements": (None, None),
    "snug_fit": ({"waist_cm": 70.0}, {"WAIST_WIDTH": 35.0}),
    "tight_for_body": ({"waist_cm": 90.0}, {"WAIST_WIDTH": 35.0}),
    "roomy_for_body": ({"waist_cm": 60.0}, {"WAIST_WIDTH": 50.0}),
}

print("\n=== 바지(너비 축) - person2.jpg, steps=20 ===")
for label, (body, garment) in LOWER_CASES.items():
    run_case(label, body, garment)

print(f"\n완료 -> {OUT_DIR}/ 안의 *_mask.png(마스크) / *_tryon.png(합성 결과) 비교")
print("확인 포인트: tight_for_body가 roomy_for_body보다 바지 폭이 더 좁게(스키니하게) 나와야 한다.")
