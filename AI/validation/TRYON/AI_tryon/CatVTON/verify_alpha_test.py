"""알파 테스트로 모은 실제 팀원 이미지(image/alpha_1, image/alpha_2)로 현재 프로덕션 코드
(`worker/models/catvton`)가 얼마나 잘 동작하는지 육안 확인한다.

- 알파테스트1(`image/alpha_1/`): person2.png(반팔 원본) + 상의 1개(shirt.png, 반팔).
  person.png(레드카펫, 긴팔 원본)는 뺐다 — 긴팔 원본에 반팔 레퍼런스를 입히면 마스크가
  덮는 팔뚝 범위를 반팔 레퍼런스가 채워주지 못해 diffusion이 그 구간을 애매하게 메꾸는
  문제(§ 알파테스트 진단 기록)가 있다.
- 알파테스트2(`image/alpha_2/pants.png`, 반바지)도 같은 이유로 뺐다 — `alpha_2/person.png`가
  긴 청바지 원본이라 반바지 레퍼런스를 입히면 밑단 아래가 반투명/얼룩 패턴으로 깨진다.
  기장이 맞는 레퍼런스가 생기기 전까지는 반바지/반팔처럼 원본보다 짧은 레퍼런스는 정기
  알파테스트 범위에서 전부 제외한다 — 이 조합들은 알려진 한계로만 기록해둔다.

체형/의류 실측값은 이 알파테스트 이미지들에 없으므로 적응형 마스킹(폭 축)은 타지 않는다 —
`fit_type="regular"` 고정, 즉 이번 실행은 적응형 마스킹이 아니라 **기존 마스킹 파이프라인
자체가 실제 사용자 사진에 얼마나 강건한지**를 보는 게 목적이다.

pytest 안 걸림 — `python verify_alpha_test.py`로 직접 실행 후 `result/`에 저장된 PNG를
육안 확인한다(기존 verify_*.py 관례).
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

OUT_DIR = os.path.join("result", "alpha_test_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
GUIDANCE_SCALE = 3.0
NUM_INFERENCE_STEPS = 50

generator = torch.Generator(device="cuda").manual_seed(42)


def load_person(path):
    return resize_and_crop(Image.open(path).convert("RGB"), (WIDTH, HEIGHT))


def load_cloth(path):
    return resize_and_padding(Image.open(path).convert("RGB"), (WIDTH, HEIGHT))


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


def run_single(label, person_path, mask_type, cloth_path):
    print(f"--- {label} ---")
    person_image = load_person(person_path)
    cloth_image = load_cloth(cloth_path)
    mask = automasker(person_image, mask_type=mask_type, fit_type="regular")["mask"]
    mask_blurred = mask_processor.blur(mask, blur_factor=9)
    vis_mask(person_image, mask).save(os.path.join(OUT_DIR, f"{label}_mask.png"))
    result = generate(person_image, cloth_image, mask_blurred)
    result.save(os.path.join(OUT_DIR, f"{label}_tryon.png"))


# --- 알파테스트1: 상의(반팔 원본 x 반팔 레퍼런스만) --------------------------------
print("\n=== 알파테스트1: 상의 ===")
run_single("alpha1_person2_shirt", "image/alpha_1/person2.png", "upper", "image/alpha_1/shirt.png")

# --- 체형 교차: 알파2 인물(반팔 원본)에 알파1 상의를 입힌다 -------------------------
# pants.png는 알파2 인물(긴 청바지 원본)과 기장이 안 맞는 레퍼런스라 뺐다(위 docstring).
print("\n=== 체형 교차: 알파2 인물 + 알파1 상의 ===")
cross_person = load_person("image/alpha_2/person.png")
shirt_cloth = load_cloth("image/alpha_1/shirt.png")

cross_mask = automasker(cross_person, mask_type="upper", fit_type="regular")["mask"]
cross_mask_blurred = mask_processor.blur(cross_mask, blur_factor=9)
vis_mask(cross_person, cross_mask).save(os.path.join(OUT_DIR, "cross_alpha2_person_alpha1_shirt_mask.png"))
cross_result = generate(cross_person, shirt_cloth, cross_mask_blurred)
cross_result.save(os.path.join(OUT_DIR, "cross_alpha2_person_alpha1_shirt_tryon.png"))

print(f"\n완료 -> {OUT_DIR}/ 안의 결과 PNG 확인")
