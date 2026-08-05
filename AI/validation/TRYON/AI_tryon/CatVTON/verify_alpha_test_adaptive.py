"""알파테스트2(image/alpha_2, 인물 1명 + 반바지 1개)에 실제 체형/의류 실측값을 데모로 넣어
적응형 마스킹(허리 폭 축)이 타는 경로를 확인한다.

알파테스트1(상의)은 대상이 아니다 — 적응형 마스킹은 하의(바지) 허리 폭 축만 구현돼 있고
상의는 가슴 실측/랜드마크가 없어 애초에 적응형 마스킹 대상이 아니다(`adaptive_fit.py`
docstring 참고). 그래서 이 스크립트는 알파테스트2만, 실제 실측값 대신
`verify_adaptive_masking.py`와 같은 데모용 body/garment 조합(waist_cm / WAIST_WIDTH)으로
baseline(실측 없음)·snug·tight·roomy 네 케이스를 만든다.

이전 `verify_alpha_test.py` 실행(fit_type="regular" 고정)과 비교하면, 같은 인물·같은
반바지인데 실측값이 있을 때 마스크 폭이 실제로 달라지는지가 이번 확인 포인트다.

프로덕션 코드(`worker/models/catvton`)를 그대로 쓴다 — 검증 대상이 실제 배포될 코드이기
때문이다(기존 verify_*.py 관례).
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

OUT_DIR = os.path.join("result", "alpha_test_adaptive_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
PERSON_PATH = "image/alpha_2/person.png"
LOWER_CLOTH_PATH = "image/alpha_2/pants.png"

person_image = resize_and_crop(Image.open(PERSON_PATH).convert("RGB"), (WIDTH, HEIGHT))
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

    vis_mask(person_image, mask).save(os.path.join(OUT_DIR, f"alpha2_{label}_mask.png"))
    result = generate(person_image, lower_cloth_image, mask_blurred)
    result.save(os.path.join(OUT_DIR, f"alpha2_{label}_tryon.png"))


# --- 데모 실측값(waist_cm / WAIST_WIDTH) 조합 -----------------------------------
LOWER_CASES = {
    "baseline_no_measurements": (None, None),
    "snug_fit": ({"waist_cm": 70.0}, {"WAIST_WIDTH": 35.0}),
    "tight_for_body": ({"waist_cm": 90.0}, {"WAIST_WIDTH": 35.0}),
    "roomy_for_body": ({"waist_cm": 60.0}, {"WAIST_WIDTH": 50.0}),
}

print("\n=== 알파테스트2 + 적응형 마스킹(데모 실측값) ===")
for label, (body, garment) in LOWER_CASES.items():
    run_case(label, body, garment)

print(f"\n완료 -> {OUT_DIR}/ 안의 *_mask.png(마스크) / *_tryon.png(합성 결과) 비교")
print("확인 포인트: tight_for_body가 roomy_for_body보다 바지 폭이 더 좁게 나와야 한다.")
