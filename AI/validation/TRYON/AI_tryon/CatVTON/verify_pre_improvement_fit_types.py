"""개선 전(프로덕션, `worker/models/catvton`) 코드의 `fit_type` 3종(regular/oversized/
cropped)으로 상의를 입힌 결과를 만든다 — 적응형 마스킹(스키니/배기) 이전부터 있던 고정 3단계
로직이 실제로 어떻게 보이는지 기록용으로 남긴다.

**주의**: `cropped`는 마스크 하단을 잘라 기장을 줄이는 방식이라 그 자리에 맨살이 새로 생성될
수 있다 — 이번 세션에 적응형 마스킹에서 길이 축을 뺀 이유와 같은 문제다. 이 스크립트는 기존에
이미 있던 `fit_type` 옵션이 실제로 뭘 만들어내는지 기록하기 위한 것으로, 이 옵션 자체를
유지할지는 별도 판단 사항이다.

`worker/models/catvton`(프로덕션)을 그대로 쓴다 — hat/shoes 지원은 없고 upper/lower/overall/
inner/outer + fit_type만 있다.

pytest 안 걸림 — `python verify_pre_improvement_fit_types.py`로 직접 실행 후 `result/`에
저장된 PNG를 육안 확인한다.
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

from model.cloth_masker import AutoMasker, vis_mask  # noqa: E402
from model.pipeline import CatVTONPipeline  # noqa: E402
from utils import init_weight_dtype, resize_and_crop, resize_and_padding  # noqa: E402


def composite_with_original(original_image, generated_image, mask):
    original_np = np.array(original_image.resize(generated_image.size)).astype(np.float32)
    generated_np = np.array(generated_image).astype(np.float32)
    mask_np = np.array(mask.resize(generated_image.size).convert("L")).astype(np.float32) / 255.0
    mask_np = np.expand_dims(mask_np, axis=-1)
    composited = generated_np * mask_np + original_np * (1 - mask_np)
    return Image.fromarray(composited.astype(np.uint8))


def _bypass_safety_checker(self, image):
    has_nsfw_concept = [False] * len(image) if isinstance(image, list) else [False]
    return image, has_nsfw_concept


print("=== 파이프라인 초기화(개선 전 프로덕션 코드) ===")
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

OUT_DIR = os.path.join(
    "result", "pre_improvement_fit_types_" + datetime.now().strftime("%Y%m%d_%H%M%S")
)
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50
PERSON_PATH = "image/person.jpg"
CLOTH_PATH = "image/cloth.jpg"

person_image = Image.open(PERSON_PATH).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))
cloth_image = resize_and_padding(Image.open(CLOTH_PATH).convert("RGB"), (WIDTH, HEIGHT))

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


for fit_type in ["regular", "oversized", "cropped"]:
    print(f"=== fit_type={fit_type} ===")
    mask = automasker(person_image, mask_type="upper", fit_type=fit_type)["mask"]
    mask_blurred = mask_processor.blur(mask, blur_factor=9)

    vis_mask(person_image, mask).save(os.path.join(OUT_DIR, f"upper_{fit_type}_mask.png"))
    result = generate(person_image, cloth_image, mask_blurred)
    result.save(os.path.join(OUT_DIR, f"upper_{fit_type}_tryon.png"))

print(f"\n완료 -> {OUT_DIR}/ 안의 upper_{{regular,oversized,cropped}}_tryon.png 확인")
