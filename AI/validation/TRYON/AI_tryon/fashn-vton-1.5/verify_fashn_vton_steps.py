"""FASHN VTON v1.5의 num_timesteps를 낮춰 속도/품질 트레이드오프를 비교한다.

alpha1(상의) 케이스는 30스텝 기준 추론 884.9s로 확인됐다(품질은 좋음 —
alpha1_person_shirt_tops_result.png). CLI 도움말상 20=fast/30=balanced/50=quality라 20부터
더 낮춰가며(20/15/10) 시간과 결과를 비교한다.
"""

import os
import time

import torch
from fashn_vton import TryOnPipeline
from PIL import Image

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_ALPHA_DIR = os.path.join(_REPO_ROOT, "AI", "validation", "TRYON", "AI_tryon", "CatVTON", "image")
_WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "fashn-vton-1.5", "weights")
_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "steps_comparison")
os.makedirs(_RESULTS_DIR, exist_ok=True)

PERSON = os.path.join(_ALPHA_DIR, "alpha_1", "person.png")
GARMENT = os.path.join(_ALPHA_DIR, "alpha_1", "shirt.png")
# 30스텝(기준) 결과는 이미 있음: alpha1_person_shirt_tops_result.png (추론 884.9s)
STEP_COUNTS = [20, 15, 10]

print("=== 파이프라인 로드 ===")
t0 = time.time()
pipeline = TryOnPipeline(weights_dir=_WEIGHTS_DIR)
print(f"로드 완료 ({time.time() - t0:.1f}s)")

person_image = Image.open(PERSON).convert("RGB")
garment_image = Image.open(GARMENT).convert("RGB")

summary_rows = [("steps", "elapsed_s", "peak_vram_gb")]

for steps in STEP_COUNTS:
    print(f"\n=== 생성: num_timesteps={steps} ===")
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    result = pipeline(
        person_image=person_image,
        garment_image=garment_image,
        category="tops",
        garment_photo_type="flat-lay",
        num_samples=1,
        num_timesteps=steps,
        seed=42,
    )
    elapsed = time.time() - t0
    peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else 0.0

    out_path = os.path.join(_RESULTS_DIR, f"steps{steps:02d}_result.png")
    result.images[0].save(out_path)
    print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")
    summary_rows.append((str(steps), f"{elapsed:.1f}", f"{peak_vram_gb:.2f}"))

summary_path = os.path.join(_RESULTS_DIR, "summary.md")
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("# 스텝 수별 속도/VRAM 비교 (alpha1 상의 케이스)\n\n")
    f.write("기준(30스텝): 추론 884.9s, Peak VRAM 3.17GB — `../../alpha1_person_shirt_tops_result.png`\n\n")
    f.write("| steps | elapsed(s) | peak VRAM(GB) |\n|---|---|---|\n")
    for row in summary_rows[1:]:
        f.write(f"| {row[0]} | {row[1]} | {row[2]} |\n")
print(f"\n요약 저장: {summary_path}")
print("\n=== 전체 완료 ===")
