"""하이브리드: CatVTON 1차 결과(긴바지로 잘못 나온 것)를 FASHN VTON 2차 인풋으로 넣어본다.

CatVTON은 마스크 전체(다리 전체)를 레퍼런스 원단으로 채워서 반바지가 긴바지처럼 나왔다
(`tryon_cheolsu_lower.png`). FASHN VTON은 마스크리스라 실제로 다리 맨살을 어느 정도
그릴 줄 아는 걸 오늘 확인했으니, CatVTON 결과를 person_image로, 같은 반바지 레퍼런스를
다시 넣어서 FASHN VTON이 "이건 원래 반바지여야 한다"를 제대로 완성해주는지 본다.
"""

import os
import time

import torch
from fashn_vton import TryOnPipeline
from PIL import Image

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_CATVTON_DIR = os.path.join(_REPO_ROOT, "AI", "validation", "TRYON", "AI_tryon", "CatVTON")
_ALPHA_DIR = os.path.join(_CATVTON_DIR, "image")
_WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "fashn-vton-1.5", "weights")
_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "hybrid_catvton_fashn")
os.makedirs(_RESULTS_DIR, exist_ok=True)

# CatVTON 1차 결과(긴바지 버그가 보이는 것) -- 이미 생성된 결과를 재사용
CATVTON_STAGE1 = os.path.join(
    _CATVTON_DIR, "result", "ai_models_regular_fit_20260803_141704", "tryon_cheolsu_lower.png"
)
PANTS_REF = os.path.join(_ALPHA_DIR, "alpha_2", "pants.png")

print("=== 파이프라인 로드 ===")
t0 = time.time()
pipeline = TryOnPipeline(weights_dir=_WEIGHTS_DIR)
print(f"로드 완료 ({time.time() - t0:.1f}s)")

person_image = Image.open(CATVTON_STAGE1).convert("RGB")
garment_image = Image.open(PANTS_REF).convert("RGB")

print("\n=== 생성: hybrid_cheolsu_pants (CatVTON 1차 -> FASHN VTON 2차) ===")
if torch.cuda.is_available():
    torch.cuda.reset_peak_memory_stats()
t0 = time.time()
result = pipeline(
    person_image=person_image,
    garment_image=garment_image,
    category="bottoms",
    garment_photo_type="flat-lay",
    num_samples=1,
    num_timesteps=10,
    seed=42,
    segmentation_free=True,
)
elapsed = time.time() - t0
peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else 0.0

out_path = os.path.join(_RESULTS_DIR, "hybrid_cheolsu_pants.png")
result.images[0].save(out_path)
print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")
