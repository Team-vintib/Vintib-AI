"""체형-의류 스펙 차이 기반 적응형 마스킹(바지 허리 너비/스키니-배기 축)이 방향대로
동작하는지, 실제 옷을 입힌 결과에도 반영되는지 육안 확인한다.

**길이(기장) 축은 없다** — 마스크 하단을 잘라 기장을 줄이면 그 자리에 diffusion이 맨살을
새로 생성해야 하는데, AI 가드레일상 정책적으로 피해야 해서 뺐다(`adaptive_fit.py` docstring
참고). 그래서 이 스크립트는 상의(길이 축만 있었음)는 다루지 않고 바지(너비 축)만 본다.

마스크만 비교하는 걸로는 "diffusion이 그 마스크를 갖고 실제로 뭘 그리는지"까지는 못 본다 —
그래서 `CatVTONPipeline`까지 돌려서 진짜 합성 결과(옷을 입힌 사진)를 저장한다.
`verify_fit_tryon.py`와 같은 추론 파라미터(steps=50, guidance_scale=3.0 — §7.1에서 확정한 값)를
쓴다.

pytest 안 걸림 — `python verify_adaptive_masking.py`로 직접 실행 후 `result/`에 저장된
PNG(마스크 + 합성 결과)를 육안 확인한다(기존 verify_*.py 관례).

**이 파일이 있는 `AI/validation/TRYON/AI_tryon/CatVTON/`은 `worker/models/catvton`을 복제한
실험용 스냅샷이라 적응형 마스킹 코드(`adaptive_fit.py`, `cloth_masker.py`의 새 함수들)가 아직
없다.** 스냅샷에 따로 복사해두는 대신, 검증하려는 실제 프로덕션 코드(`worker/models/catvton`)를
sys.path 맨 앞에 꽂아서 이 스크립트가 실제 배포될 코드를 그대로 쓰게 한다 — 여기서 검증하는
대상은 "새로 실험 중인 코드"가 아니라 "이미 구현된 프로덕션 코드"이기 때문이다.
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

OUT_DIR = os.path.join("result", "adaptive_masking_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
PERSON_PATH = "image/person.jpg"
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

print("\n=== 바지(너비 축) ===")
for label, (body, garment) in LOWER_CASES.items():
    run_case(label, body, garment)

print(f"\n완료 -> {OUT_DIR}/ 안의 *_mask.png(마스크) / *_tryon.png(합성 결과) 비교")
print("확인 포인트: tight_for_body가 roomy_for_body보다 바지 폭이 더 좁게(스키니하게) 나와야 한다.")
