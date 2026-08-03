"""FASHN VTON v1.5 — 실제 의류 랜드마크(HRNet)로 어깨/허리/밑단 위치를 정확히 잡고
tight/loose 핏을 테스트한다. 알파테스트1(shirt.png)만, base/tight/loose 3장만 빠르게 본다.

이전 실험(verify_fashn_vton_part_fit.py)은 부위별 y구간을 눈대중 %로 잡았는데, 이번엔
`worker/models/garment_measurement`의 HRNet 랜드마크 검출기를 그대로 재사용한다.

주의: `short_sleeve_top` 카테고리엔 허리/가슴 랜드마크가 없다(DeepFashion2 자체에 없음) —
어깨(`shoulder_left/right`)와 밑단(`hem_left/center/right`)만 실제 랜드마크로 정확히 잡고,
허리는 어깨 y좌표와 밑단 y좌표의 중간점으로 추정한다(사용자 승인: "정밀한 게 좋긴 한데
허리도 테스트").

이전 실험에서 loose(1.15배)는 거의 반응이 없었다 — 이번엔 loose를 더 강하게(1.35배) 준다.
tight(0.85배)는 이전에 잘 반응했으므로 그대로 유지.
"""

import os
import sys
import time

import cv2
import numpy as np
import torch
from fashn_vton import TryOnPipeline
from PIL import Image

# --- garment_measurement 랜드마크 검출기 재사용 -----------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_MEASUREMENT_CODE_PATH = os.path.join(_REPO_ROOT, "worker", "models")
sys.path.insert(0, _MEASUREMENT_CODE_PATH)
from garment_measurement.contracts import GarmentCategory, LandmarkType  # noqa: E402
from garment_measurement.landmark_detector import HRNetLandmarkDetector  # noqa: E402

_HRNET_CHECKPOINT = os.path.join(
    _REPO_ROOT, "AI", "validation", "garment-landmark-check", "models",
    "pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth",
)

_ALPHA_DIR = os.path.join(_REPO_ROOT, "AI", "validation", "TRYON", "AI_tryon", "CatVTON", "image")
_WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "fashn-vton-1.5", "weights")
_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "landmark_fit_test")
os.makedirs(_RESULTS_DIR, exist_ok=True)

NUM_TIMESTEPS = 10
TIGHT, LOOSE = 0.85, 1.35  # loose를 1.15 -> 1.35로 강화
TAPER_FRAC = 0.08
BAND_HALF_HEIGHT_FRAC = 0.05  # 랜드마크 y좌표를 중심으로 +-5% 구간을 밴드로 삼음

SHIRT_PATH = os.path.join(_ALPHA_DIR, "alpha_1", "shirt.png")
PERSON_PATH = os.path.join(_ALPHA_DIR, "alpha_1", "person.png")


def warp_local_width(image: Image.Image, y_center_frac: float, scale: float) -> Image.Image:
    """y_center_frac을 중심으로 +-BAND_HALF_HEIGHT_FRAC 구간만 가로로 scale배, 위아래로 전이."""
    img_np = np.array(image)
    h, w = img_np.shape[:2]
    band_half = BAND_HALF_HEIGHT_FRAC * h
    y_start, y_end, taper = y_center_frac * h - band_half, y_center_frac * h + band_half, TAPER_FRAC * h

    ys = np.arange(h, dtype=np.float32)
    weight = np.zeros(h, dtype=np.float32)
    weight[(ys >= y_start) & (ys <= y_end)] = 1.0
    upper = (ys >= y_start - taper) & (ys < y_start)
    weight[upper] = (ys[upper] - (y_start - taper)) / taper
    lower = (ys > y_end) & (ys <= y_end + taper)
    weight[lower] = 1.0 - (ys[lower] - y_end) / taper
    row_scale = 1.0 + weight * (scale - 1.0)

    cx = w / 2.0
    xs = np.arange(w, dtype=np.float32)
    map_x = (cx + (xs[None, :] - cx) / row_scale[:, None]).astype(np.float32)
    map_y = np.tile(ys.reshape(h, 1), (1, w)).astype(np.float32)

    warped = cv2.remap(
        img_np, map_x, map_y, interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
    )
    return Image.fromarray(warped)


def apply_multi_band_warp(image: Image.Image, band_centers_frac: dict, scale: float) -> Image.Image:
    """여러 부위(어깨/허리/밑단)를 순차적으로 같은 scale로 워핑."""
    out = image
    for _part, y_center_frac in band_centers_frac.items():
        out = warp_local_width(out, y_center_frac, scale)
    return out


print("=== 랜드마크 검출 (HRNet, short_sleeve_top) ===")
detector = HRNetLandmarkDetector(checkpoint_path=_HRNET_CHECKPOINT)
landmarks = detector.detect(SHIRT_PATH, product_id=0, category=GarmentCategory.short_sleeve_top)
by_type = {lm.type: lm for lm in landmarks}
for lm in landmarks:
    print(f"  {lm.type.value}: ({lm.pixel_x:.1f}, {lm.pixel_y:.1f}) conf={lm.confidence:.2f}")

del detector
if torch.cuda.is_available():
    torch.cuda.empty_cache()
    print("HRNet GPU 메모리 해제 완료")

shirt_img = Image.open(SHIRT_PATH).convert("RGB")
h = shirt_img.height

shoulder_y = (by_type[LandmarkType.shoulder_left].pixel_y + by_type[LandmarkType.shoulder_right].pixel_y) / 2
hem_y = (
    by_type[LandmarkType.hem_left].pixel_y
    + by_type[LandmarkType.hem_center].pixel_y
    + by_type[LandmarkType.hem_right].pixel_y
) / 3
waist_y = (shoulder_y + hem_y) / 2  # 실제 랜드마크 없음 -> 어깨-밑단 중간점으로 추정

band_centers_frac = {
    "shoulder": shoulder_y / h,
    "waist": waist_y / h,
    "hem": hem_y / h,
}
print(f"\n밴드 중심(이미지 높이 비율): {band_centers_frac}")

print("\n=== 파이프라인 로드 ===")
t0 = time.time()
pipeline = TryOnPipeline(weights_dir=_WEIGHTS_DIR)
print(f"로드 완료 ({time.time() - t0:.1f}s)")

person_image = Image.open(PERSON_PATH).convert("RGB")

garment_variants = {
    "base": shirt_img,
    "tight": apply_multi_band_warp(shirt_img, band_centers_frac, TIGHT),
    "loose": apply_multi_band_warp(shirt_img, band_centers_frac, LOOSE),
}

log = []
for name, garment in garment_variants.items():
    garment.save(os.path.join(_RESULTS_DIR, f"garment_{name}.png"))

    print(f"\n=== 생성: {name} ===")
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    result = pipeline(
        person_image=person_image,
        garment_image=garment,
        category="tops",
        garment_photo_type="flat-lay",
        num_samples=1,
        num_timesteps=NUM_TIMESTEPS,
        skip_cfg_last_n_steps=3,  # 기본 1 -> 3: 마지막 3스텝은 CFG(조건부+무조건부 이중 연산) 스킵
        seed=42,
        segmentation_free=True,
    )
    elapsed = time.time() - t0
    peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else 0.0

    out_path = os.path.join(_RESULTS_DIR, f"result_{name}.png")
    result.images[0].save(out_path)
    line = f"{name}: 추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB -> {out_path}"
    print(line)
    log.append((name, f"{elapsed:.1f}", f"{peak_vram_gb:.2f}"))

summary_path = os.path.join(_RESULTS_DIR, "summary.md")
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("# 랜드마크 기반 부위별 핏 조절 테스트 (alpha1 상의)\n\n")
    f.write(f"tight={TIGHT}, loose={LOOSE}, band_half_height={BAND_HALF_HEIGHT_FRAC}, taper={TAPER_FRAC}\n\n")
    f.write(f"밴드 중심(랜드마크 기반): {band_centers_frac}\n\n")
    f.write("| case | elapsed(s) | peak VRAM(GB) |\n|---|---|---|\n")
    for row in log:
        f.write(f"| {row[0]} | {row[1]} | {row[2]} |\n")
print(f"\n요약 저장: {summary_path}")
print("\n=== 전체 완료 ===")
