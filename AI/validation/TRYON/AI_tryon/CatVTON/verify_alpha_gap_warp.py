""""본인 피부" 갭 채우기 대신, 의류 랜드마크를 인물의 대응 신체 포인트로 워핑해서 그
워핑 결과를 조건 이미지로 주는 방식을 빠르게 검증한다(15 steps, 속도 우선).

**중요한 제약**: 실제 랜드마크 검출기(`worker/models/garment_measurement/`의
HRNetLandmarkDetector)는 체크포인트 파일(OneDrive 수동 다운로드 필요)이 이 환경에 없어서
쓸 수 없다. 그래서 이 스크립트는 `image/alpha_1/shirt.png`, `image/alpha_2/pants.png`
두 장에 대해 사람이 눈으로 본 근사 좌표(상대 비율)를 하드코딩했다 — 실제 검출기 정확도가
아니라 "워핑 자체가 방향성 있게 도움이 되는가"만 빠르게 확인하는 게 목적이다. 실측
파이프라인이 실제로 뽑는 랜드마크(`LandmarkType`: SHOULDER_LEFT/RIGHT, SLEEVE_END_LEFT/RIGHT,
WAIST_LEFT/RIGHT, HEM_LEFT/RIGHT_OUTER 등)와 이름을 맞춰서, 나중에 실제 검출기가 준비되면
좌표만 갈아끼우면 되게 해뒀다.

신체 쪽 대응점은 새 모델 없이 이미 있는 DensePose 부위 경계(어깨=big arm 상단,
팔꿈치=big arm/forearm 경계, 엉덩이=thigh 상단, 무릎=thigh/leg 경계)로 근사한다 —
`classify_garment_length`가 "short"로 판단한 케이스라 소매/밑단이 팔꿈치/무릎까지만
오도록 타깃을 잡는다.

갭 분리(`split_mask_by_gap`)나 텍스트 프롬프트 스킨 패스는 전혀 안 쓴다 — 워핑된 조건
이미지를 기존 단일 패스(`mask_type` 그대로, `fit_type="regular"`)에 그냥 흘려보낸다.
"""

import os
import sys
from datetime import datetime

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_PRODUCTION_CATVTON_PATH = os.path.join(_REPO_ROOT, "worker", "models", "catvton")
sys.path.insert(0, _PRODUCTION_CATVTON_PATH)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from diffusers.image_processor import VaeImageProcessor  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from PIL import Image  # noqa: E402

from model.cloth_masker import AutoMasker, DENSE_INDEX_MAP, part_mask_of, vis_mask  # noqa: E402
from model.pipeline import CatVTONPipeline  # noqa: E402
from utils import init_weight_dtype, resize_and_crop  # noqa: E402

WIDTH, HEIGHT = 768, 1024
NUM_INFERENCE_STEPS = 15  # 빠른 검증 우선(사용자 지시)
GUIDANCE_SCALE = 3.0


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


def _bbox(area: np.ndarray):
    rows = np.where(area.any(axis=1))[0]
    cols = np.where(area.any(axis=0))[0]
    return int(rows.min()), int(rows.max()), int(cols.min()), int(cols.max())


def warp_garment(garment_image: Image.Image, src_points_frac, dst_points_xy, canvas_size):
    """`garment_image` 위의 상대좌표(0~1) 3점을 인물 캔버스 위의 절대좌표(px) 3점으로
    보내는 아핀 변환을 구해서 워핑한다. 워핑 밖 영역은 흰 배경(기존 flat 제품컷과 동일한
    배경색)으로 채운다."""
    gw, gh = garment_image.size
    src = np.float32([[fx * gw, fy * gh] for fx, fy in src_points_frac])
    dst = np.float32(dst_points_xy)
    matrix = cv2.getAffineTransform(src, dst)
    garment_np = np.array(garment_image)
    warped = cv2.warpAffine(
        garment_np,
        matrix,
        canvas_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    return Image.fromarray(warped)


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

OUT_DIR = os.path.join("result", "alpha_gap_warp_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

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


# =========================================================
# person1: 긴팔 원본 + 반팔 셔츠 -> 어깨/팔꿈치로 워핑
# =========================================================
print("\n=== person1 + 반팔 셔츠(랜드마크 워핑 조건 이미지) ===")
person_image = resize_and_crop(
    Image.open("image/alpha_1/person.png").convert("RGB"), (WIDTH, HEIGHT)
)
shirt_image = Image.open("image/alpha_1/shirt.png").convert("RGB")

mask_result = automasker(person_image, mask_type="upper", fit_type="regular")
mask = mask_processor.blur(mask_result["mask"], blur_factor=9)
densepose_np = np.array(mask_result["densepose"])

left_arm_top, left_arm_bottom, left_arm_l, left_arm_r = _bbox(
    part_mask_of(["left big arm"], densepose_np, DENSE_INDEX_MAP)
)
right_arm_top, right_arm_bottom, right_arm_l, right_arm_r = _bbox(
    part_mask_of(["right big arm"], densepose_np, DENSE_INDEX_MAP)
)
torso_top, _, torso_l, torso_r = _bbox(part_mask_of(["torso"], densepose_np, DENSE_INDEX_MAP))

# 어깨 = 팔(big arm) 상단 안쪽 끝, 팔꿈치 = big arm 하단(=forearm과의 경계, "짧은 소매"의
# 목표 지점). 사람 이미지 기준 왼쪽(화면상 오른쪽 어깨)/오른쪽을 DensePose 라벨명 그대로 쓴다.
shoulder_left_xy = (left_arm_r, torso_top)  # 오른팔(화면 왼쪽)이 'right big arm'일 수도 있으니 아래서 스왑 처리
shoulder_right_xy = (right_arm_l, torso_top)
elbow_left_xy = ((left_arm_l + left_arm_r) // 2, left_arm_bottom)
elbow_right_xy = ((right_arm_l + right_arm_r) // 2, right_arm_bottom)

# shirt.png 상의 상대좌표(사람이 눈으로 본 근사치 — 위 docstring 참고)
shirt_src_points = [
    (0.260, 0.286),  # shoulder_left(원본 이미지 기준 왼쪽)
    (0.729, 0.286),  # shoulder_right
    (0.201, 0.436),  # sleeve_end_left
]
shirt_dst_points = [shoulder_left_xy, shoulder_right_xy, elbow_left_xy]

warped_shirt = warp_garment(shirt_image, shirt_src_points, shirt_dst_points, (WIDTH, HEIGHT))
warped_shirt.save(os.path.join(OUT_DIR, "person1_warped_condition.png"))
vis_mask(person_image, mask_result["mask"]).save(os.path.join(OUT_DIR, "person1_mask.png"))

person1_result = generate(person_image, warped_shirt, mask)
person1_result.save(os.path.join(OUT_DIR, "person1_tryon.png"))

# =========================================================
# person2: 긴바지 원본 + 반바지 -> 엉덩이/무릎으로 워핑
# =========================================================
print("\n=== person2 + 반바지(랜드마크 워핑 조건 이미지) ===")
person2_image = resize_and_crop(
    Image.open("image/alpha_2/person.png").convert("RGB"), (WIDTH, HEIGHT)
)
pants_image = Image.open("image/alpha_2/pants.png").convert("RGB")

mask2_result = automasker(person2_image, mask_type="lower", fit_type="regular")
mask2 = mask_processor.blur(mask2_result["mask"], blur_factor=9)
densepose2_np = np.array(mask2_result["densepose"])

left_thigh_top, left_thigh_bottom, left_thigh_l, left_thigh_r = _bbox(
    part_mask_of(["left thigh"], densepose2_np, DENSE_INDEX_MAP)
)
right_thigh_top, right_thigh_bottom, right_thigh_l, right_thigh_r = _bbox(
    part_mask_of(["right thigh"], densepose2_np, DENSE_INDEX_MAP)
)

waist_left_xy = (left_thigh_l, left_thigh_top)
waist_right_xy = (right_thigh_r, right_thigh_top)
knee_left_xy = ((left_thigh_l + left_thigh_r) // 2, left_thigh_bottom)

pants_src_points = [
    (0.12, 0.12),  # waist_left
    (0.88, 0.12),  # waist_right
    (0.15, 0.85),  # hem_left(반바지 밑단)
]
pants_dst_points = [waist_left_xy, waist_right_xy, knee_left_xy]

warped_pants = warp_garment(pants_image, pants_src_points, pants_dst_points, (WIDTH, HEIGHT))
warped_pants.save(os.path.join(OUT_DIR, "person2_warped_condition.png"))
vis_mask(person2_image, mask2_result["mask"]).save(os.path.join(OUT_DIR, "person2_mask.png"))

person2_result = generate(person2_image, warped_pants, mask2)
person2_result.save(os.path.join(OUT_DIR, "person2_tryon.png"))

print(f"\n완료 -> {OUT_DIR}/")
