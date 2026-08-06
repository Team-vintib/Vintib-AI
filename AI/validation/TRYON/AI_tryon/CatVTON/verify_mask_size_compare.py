"""철수/영희/둘리의 "하의(lower)" 마스크가 실제로 픽셀 크기가 얼마나 다른지 비교한다.

레퍼런스 이미지 자체(체형 매칭)는 문제가 없어 보이는데 둘리만 계속 실패하는 이유를
확인하기 위해, "마스크 절대 면적이 커서 인접 원본 편향을 못 이긴다"는 가설을 숫자로
검증한다.
"""

import os

import numpy as np
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image

from model.cloth_masker import AutoMasker
from utils import resize_and_crop

WIDTH, HEIGHT = 768, 1024
FIT_TYPE = "regular"

PEOPLE = {
    "cheolsu": os.path.join("..", "models_ai_generated", "cheolsu.png"),
    "younghee": os.path.join("..", "models_ai_generated", "younghee.png"),
    "dooly": os.path.join("..", "models_ai_generated", "dooly.png"),
}

print("=== 초기화 ===")
repo_path = snapshot_download(repo_id="zhengchong/CatVTON")
mask_processor = VaeImageProcessor(vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True)
automasker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device="cuda",
)
print("초기화 완료\n")

total_px = WIDTH * HEIGHT
for name, path in PEOPLE.items():
    person_image = Image.open(path).convert("RGB")
    person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))
    mask = automasker(person_image, mask_type="lower", fit_type=FIT_TYPE)["mask"]

    mask_np = np.array(mask.convert("L"))
    mask_px = int((mask_np > 127).sum())
    rows = np.where(mask_np.max(axis=1) > 127)[0]
    cols = np.where(mask_np.max(axis=0) > 127)[0]
    bbox_h = int(rows[-1] - rows[0]) if len(rows) else 0
    bbox_w = int(cols[-1] - cols[0]) if len(cols) else 0

    print(
        f"{name}: 마스크 픽셀수={mask_px} ({mask_px / total_px * 100:.1f}% of 전체), "
        f"바운딩박스={bbox_w}x{bbox_h}px"
    )
