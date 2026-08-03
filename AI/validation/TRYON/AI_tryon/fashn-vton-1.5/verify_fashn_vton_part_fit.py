"""FASHN VTON v1.5 — 마스크리스 유지한 채 부위별(어깨/가슴/허리/밑단) 핏 조절이 되는지 검증.

이전 실험(verify_fashn_vton_fit_scale.py)은 flat-lay 레퍼런스 전체를 균일하게 가로
스케일링했는데, 허리는 변했지만 기장(밑단 위치)까지 같이 밀리는 부작용이 있었다. 이번엔
이미지의 특정 세로 구간(부위)만 국소적으로 폭을 조절하고, 그 구간 위아래는 부드럽게
원본으로 전이(taper)시켜서 다른 부위에 영향이 안 가게 한다.

실제 의류 랜드마크 검출기(HRNet, `worker/models/garment_measurement/`)는 체크포인트가
OneDrive 수동 다운로드 대상이라 이 환경엔 없다 — 그래서 부위별 세로 구간(%)은 실제 이미지를
눈으로 보고 잡은 휴리스틱 값이다(사용자 승인됨). `right/left/up/down` 방향 dilation을 마스크에
직접 주는 CatVTON/FASHN 내부 방식과 달리, 여기서는 마스크 자체를 안 쓰고 **레퍼런스 이미지를
입력 전에 미리 워핑**하는 방식이라 `segmentation_free=True`(마스크리스 경로)를 그대로 유지한다.

세 그룹을 테스트한다:
  1. 상의(shirt.png) — 어깨/가슴/허리 부위별 tight/loose
  2. 하의(pants.png, 반바지) — 허리/밑단(다리통) 부위별 tight/loose
     ("종아리"에 해당하는 축은 이 레퍼런스가 반바지라 없음 — 밑단/다리통 폭으로 대체)
  3. 결합(상의+하의 순차 적용) — alpha_2 인물에 alpha_1 상의를 먼저 입히고, 그 결과에
     alpha_2 하의를 이어서 입힌다(CatVTON에서 쓴 것과 같은 순차 적용 방식,
     `tryon-advancement-strategy.md` §7.2 참고). 베이스라인(원본 비율)만 확인한다.
"""

import os
import time

import cv2
import numpy as np
import torch
from fashn_vton import TryOnPipeline
from PIL import Image

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_ALPHA_DIR = os.path.join(_REPO_ROOT, "AI", "validation", "TRYON", "AI_tryon", "CatVTON", "image")
_WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "fashn-vton-1.5", "weights")
_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "part_fit_test")
os.makedirs(_RESULTS_DIR, exist_ok=True)

NUM_TIMESTEPS = 10
TIGHT, LOOSE = 0.85, 1.15
TAPER_FRAC = 0.08  # 구간 위아래로 부드럽게 전이되는 폭(이미지 높이 비율)

# 부위별 세로 구간(y_start_frac, y_end_frac) — shirt.png/pants.png를 직접 보고 잡은 값
TOPS_PARTS = {
    "shoulder": (0.22, 0.32),
    "chest": (0.33, 0.47),
    "waist": (0.55, 0.66),
}
BOTTOMS_PARTS = {
    "waist": (0.0, 0.15),
    "hem": (0.80, 1.0),  # 반바지라 "종아리" 대신 밑단/다리통 폭
}


def warp_local_width(image: Image.Image, y_start_frac: float, y_end_frac: float, scale: float) -> Image.Image:
    """이미지의 [y_start_frac, y_end_frac] 구간만 가로로 scale배, 위아래로 부드럽게 전이."""
    img_np = np.array(image)
    h, w = img_np.shape[:2]
    y_start, y_end, taper = y_start_frac * h, y_end_frac * h, TAPER_FRAC * h

    ys = np.arange(h, dtype=np.float32)
    weight = np.zeros(h, dtype=np.float32)
    weight[(ys >= y_start) & (ys <= y_end)] = 1.0
    upper = (ys >= y_start - taper) & (ys < y_start)
    weight[upper] = (ys[upper] - (y_start - taper)) / taper
    lower = (ys > y_end) & (ys <= y_end + taper)
    weight[lower] = 1.0 - (ys[lower] - y_end) / taper
    row_scale = 1.0 + weight * (scale - 1.0)  # (h,)

    cx = w / 2.0
    xs = np.arange(w, dtype=np.float32)
    map_x = cx + (xs[None, :] - cx) / row_scale[:, None]
    map_x = map_x.astype(np.float32)
    map_y = np.tile(ys.reshape(h, 1), (1, w)).astype(np.float32)

    warped = cv2.remap(
        img_np, map_x, map_y, interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
    )
    return Image.fromarray(warped)


def run_case(pipeline, name, person_image, garment_image, category, log):
    t0 = time.time()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    result = pipeline(
        person_image=person_image,
        garment_image=garment_image,
        category=category,
        garment_photo_type="flat-lay",
        num_samples=1,
        num_timesteps=NUM_TIMESTEPS,
        seed=42,
        segmentation_free=True,
    )
    elapsed = time.time() - t0
    peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else 0.0
    out_image = result.images[0]
    out_path = os.path.join(_RESULTS_DIR, f"{name}.png")
    out_image.save(out_path)
    line = f"{name}: 추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB -> {out_path}"
    print(line)
    log.append((name, f"{elapsed:.1f}", f"{peak_vram_gb:.2f}"))
    return out_image


print("=== 파이프라인 로드 ===")
t0 = time.time()
pipeline = TryOnPipeline(weights_dir=_WEIGHTS_DIR)
print(f"로드 완료 ({time.time() - t0:.1f}s)")

person1 = Image.open(os.path.join(_ALPHA_DIR, "alpha_1", "person.png")).convert("RGB")
shirt = Image.open(os.path.join(_ALPHA_DIR, "alpha_1", "shirt.png")).convert("RGB")
person2 = Image.open(os.path.join(_ALPHA_DIR, "alpha_2", "person.png")).convert("RGB")
pants = Image.open(os.path.join(_ALPHA_DIR, "alpha_2", "pants.png")).convert("RGB")

log = []

# --- 1. 상의: 어깨/가슴/허리 부위별 tight/loose -----------------------------------
print("\n########## 상의(shirt) 부위별 테스트 ##########")
run_case(pipeline, "tops_baseline", person1, shirt, "tops", log)
for part, (y0, y1) in TOPS_PARTS.items():
    for direction, scale in (("tight", TIGHT), ("loose", LOOSE)):
        warped = warp_local_width(shirt, y0, y1, scale)
        warped.save(os.path.join(_RESULTS_DIR, f"garment_tops_{part}_{direction}.png"))
        run_case(pipeline, f"tops_{part}_{direction}", person1, warped, "tops", log)

# --- 2. 하의: 허리/밑단 부위별 tight/loose -----------------------------------------
print("\n########## 하의(pants) 부위별 테스트 ##########")
run_case(pipeline, "bottoms_baseline", person2, pants, "bottoms", log)
for part, (y0, y1) in BOTTOMS_PARTS.items():
    for direction, scale in (("tight", TIGHT), ("loose", LOOSE)):
        warped = warp_local_width(pants, y0, y1, scale)
        warped.save(os.path.join(_RESULTS_DIR, f"garment_bottoms_{part}_{direction}.png"))
        run_case(pipeline, f"bottoms_{part}_{direction}", person2, warped, "bottoms", log)

# --- 3. 결합: 상의 먼저, 그 결과에 하의 순차 적용(베이스라인만) ----------------------
print("\n########## 결합(상의+하의 순차 적용) 베이스라인 ##########")
combined_step1 = run_case(pipeline, "combined_step1_tops", person2, shirt, "tops", log)
run_case(pipeline, "combined_step2_bottoms", combined_step1, pants, "bottoms", log)

summary_path = os.path.join(_RESULTS_DIR, "summary.md")
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("# 부위별 핏 조절 테스트 결과\n\n")
    f.write(f"num_timesteps={NUM_TIMESTEPS}, tight={TIGHT}, loose={LOOSE}, taper={TAPER_FRAC}\n\n")
    f.write("| case | elapsed(s) | peak VRAM(GB) |\n|---|---|---|\n")
    for row in log:
        f.write(f"| {row[0]} | {row[1]} | {row[2]} |\n")
print(f"\n요약 저장: {summary_path}")
print("\n=== 전체 완료 ===")
