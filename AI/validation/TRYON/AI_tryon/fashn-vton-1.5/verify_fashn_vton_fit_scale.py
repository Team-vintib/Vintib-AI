"""마스크리스 장점을 유지한 채(segmentation_free=True 그대로) 핏을 조절할 수 있는지 검증한다.

아이디어: 사람 사진이나 diffusion 결과물이 아니라, flat-lay 레퍼런스 의류 사진 자체를
가로 폭만 미리 스케일링해서(흰 배경 위에 좁게/넓게) 넣어본다. flat-lay 레퍼런스는
`disable_masking=garment_photo_type == "flat-lay"`라서 어차피 마스킹 없이 그대로 조건으로
들어가므로, 이 전처리는 모델의 마스크리스 경로(사람 쪽)를 전혀 건드리지 않는다.

원본(1.0) / 타이트(0.85) / 루즈(1.15) 세 버전을 같은 인물(alpha1/person.png)에 입혀서
비교한다. num_timesteps=10 — 스텝 비교 검증에서 육안상 30스텝과 차이가 거의 없었다.
"""

import os
import time

import torch
from fashn_vton import TryOnPipeline
from PIL import Image

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_ALPHA_DIR = os.path.join(_REPO_ROOT, "AI", "validation", "TRYON", "AI_tryon", "CatVTON", "image")
_WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "fashn-vton-1.5", "weights")
_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "fit_scale_test")
os.makedirs(_RESULTS_DIR, exist_ok=True)

PERSON = os.path.join(_ALPHA_DIR, "alpha_1", "person.png")
GARMENT = os.path.join(_ALPHA_DIR, "alpha_1", "shirt.png")
NUM_TIMESTEPS = 10

SCALE_VARIANTS = [
    ("tight", 0.85),
    ("original", 1.0),
    ("loose", 1.15),
]


def make_width_scaled_garment(image: Image.Image, scale: float) -> Image.Image:
    """flat-lay 의류 이미지를 가로로만 scale배 하고, 원본 크기의 흰 배경 캔버스 중앙에 얹는다."""
    if scale == 1.0:
        return image

    w, h = image.size
    new_w = max(1, int(w * scale))
    resized = image.resize((new_w, h), Image.LANCZOS)

    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    paste_x = (w - new_w) // 2  # scale<1이면 중앙에 좁게, scale>1이면 넘치는 만큼 크롭됨
    if new_w <= w:
        canvas.paste(resized, (paste_x, 0))
    else:
        crop_x = (new_w - w) // 2
        cropped = resized.crop((crop_x, 0, crop_x + w, h))
        canvas.paste(cropped, (0, 0))
    return canvas


print("=== 파이프라인 로드 ===")
t0 = time.time()
pipeline = TryOnPipeline(weights_dir=_WEIGHTS_DIR)
print(f"로드 완료 ({time.time() - t0:.1f}s)")

person_image = Image.open(PERSON).convert("RGB")
garment_image = Image.open(GARMENT).convert("RGB")

for name, scale in SCALE_VARIANTS:
    scaled_garment = make_width_scaled_garment(garment_image, scale)
    scaled_garment.save(os.path.join(_RESULTS_DIR, f"garment_{name}_x{scale}.png"))

    print(f"\n=== 생성: {name} (scale={scale}) ===")
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    result = pipeline(
        person_image=person_image,
        garment_image=scaled_garment,
        category="tops",
        garment_photo_type="flat-lay",
        num_samples=1,
        num_timesteps=NUM_TIMESTEPS,
        seed=42,
        segmentation_free=True,  # 마스크리스 경로 그대로 유지
    )
    elapsed = time.time() - t0
    peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else 0.0

    out_path = os.path.join(_RESULTS_DIR, f"result_{name}_x{scale}.png")
    result.images[0].save(out_path)
    print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")

print("\n=== 전체 완료 ===")
