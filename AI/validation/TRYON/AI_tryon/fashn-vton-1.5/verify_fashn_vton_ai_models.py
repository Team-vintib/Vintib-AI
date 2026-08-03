"""AI로 생성한 철수(남)/영희(여) 모델 사진에 알파테스트 의류(shirt/pants)를 입혀본다.

배경이 지저분한 alpha_1/alpha_2 실사 인물 사진 대신, 배경이 깔끔한 AI 생성 모델
(`models_ai_generated/cheolsu.png`, `younghee.png`)을 써서 결과 비교를 더 보기 쉽게 한다.
같은 의류(shirt=상의, pants=하의)를 두 사람 모두에게 입혀서 체형에 따라 착샷이 어떻게
달라지는지도 같이 볼 수 있다(세션 초반에 나왔던 아이디어와 동일한 취지).
"""

import os
import time

import torch
from fashn_vton import TryOnPipeline
from PIL import Image

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_ALPHA_DIR = os.path.join(_REPO_ROOT, "AI", "validation", "TRYON", "AI_tryon", "CatVTON", "image")
_MODELS_DIR = os.path.join(_REPO_ROOT, "AI", "validation", "TRYON", "AI_tryon", "models_ai_generated")
_WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "fashn-vton-1.5", "weights")
_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "ai_models_test")
os.makedirs(_RESULTS_DIR, exist_ok=True)

NUM_TIMESTEPS = 10

PEOPLE = {
    "dooly": os.path.join(_MODELS_DIR, "dooly.png"),
}
GARMENTS = {
    "shirt": (os.path.join(_ALPHA_DIR, "alpha_1", "shirt.png"), "tops"),
    "pants": (os.path.join(_ALPHA_DIR, "alpha_2", "pants.png"), "bottoms"),
}

print("=== 파이프라인 로드 ===")
t0 = time.time()
pipeline = TryOnPipeline(weights_dir=_WEIGHTS_DIR)
print(f"로드 완료 ({time.time() - t0:.1f}s)")

log = []
for person_name, person_path in PEOPLE.items():
    person_image = Image.open(person_path).convert("RGB")
    for garment_name, (garment_path, category) in GARMENTS.items():
        garment_image = Image.open(garment_path).convert("RGB")
        case_name = f"{person_name}_{garment_name}"

        print(f"\n=== 생성: {case_name} (category={category}) ===")
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        t0 = time.time()
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

        out_path = os.path.join(_RESULTS_DIR, f"{case_name}.png")
        result.images[0].save(out_path)
        line = f"{case_name}: 추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB -> {out_path}"
        print(line)
        log.append((case_name, f"{elapsed:.1f}", f"{peak_vram_gb:.2f}"))

summary_path = os.path.join(_RESULTS_DIR, "summary.md")
with open(summary_path, "w", encoding="utf-8") as f:
    f.write("# AI 모델(철수/영희) 시착 결과\n\n")
    f.write(f"num_timesteps={NUM_TIMESTEPS}\n\n")
    f.write("| case | elapsed(s) | peak VRAM(GB) |\n|---|---|---|\n")
    for row in log:
        f.write(f"| {row[0]} | {row[1]} | {row[2]} |\n")
print(f"\n요약 저장: {summary_path}")
print("\n=== 전체 완료 ===")
