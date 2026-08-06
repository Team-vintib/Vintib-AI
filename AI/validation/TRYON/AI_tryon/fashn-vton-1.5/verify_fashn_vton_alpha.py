"""FASHN VTON v1.5로 알파테스트 케이스(긴팔 원본 + 반팔 레퍼런스)를 실제로 시착해본다.

CatVTON/FLUX.2-Klein-9B가 오늘 계속 실패했거나(CatVTON: 팔뚝 애매) 실용성이 없었던(FLUX:
6GB VRAM에서 오프로딩 스와핑에 멈춤) 바로 그 케이스다. FASHN VTON v1.5는 마스크리스
(pixel-space, 세그멘테이션 마스크 불필요) + 972M 파라미터로 훨씬 작아 6GB VRAM에서
오프로딩 없이 될 가능성이 있다 — 이번 검증의 핵심 질문.

person_image/garment_image 두 장만 주면 내부적으로 DWPose+Human Parser로 알아서
처리한다(CatVTON의 AutoMasker나 FLUX의 image_reference 같은 별도 마스크 준비 불필요).
"""

import os
import time

import torch
from fashn_vton import TryOnPipeline
from PIL import Image

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_ALPHA_DIR = os.path.join(_REPO_ROOT, "AI", "validation", "TRYON", "AI_tryon", "CatVTON", "image")
_WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "fashn-vton-1.5", "weights")
_OUT_DIR = os.path.dirname(__file__)

CASES = [
    {
        "name": "alpha1_person_shirt_tops",
        "person": os.path.join(_ALPHA_DIR, "alpha_1", "person.png"),
        "garment": os.path.join(_ALPHA_DIR, "alpha_1", "shirt.png"),
        "category": "tops",
    },
    {
        "name": "alpha2_person_pants_bottoms",
        "person": os.path.join(_ALPHA_DIR, "alpha_2", "person.png"),
        "garment": os.path.join(_ALPHA_DIR, "alpha_2", "pants.png"),
        "category": "bottoms",
    },
]

print("=== 파이프라인 로드 ===")
t0 = time.time()
pipeline = TryOnPipeline(weights_dir=_WEIGHTS_DIR)
print(f"로드 완료 ({time.time() - t0:.1f}s)")

for case in CASES:
    if not (os.path.exists(case["person"]) and os.path.exists(case["garment"])):
        print(f"\n[건너뜀] {case['name']}: 입력 이미지 없음 ({case['person']} / {case['garment']})")
        continue

    print(f"\n=== 생성: {case['name']} (category={case['category']}) ===")
    person_image = Image.open(case["person"]).convert("RGB")
    garment_image = Image.open(case["garment"]).convert("RGB")

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    result = pipeline(
        person_image=person_image,
        garment_image=garment_image,
        category=case["category"],
        garment_photo_type="flat-lay",  # shirt.png/pants.png는 사람이 입은 사진이 아니라 제품 단독 촬영
        num_samples=1,
        num_timesteps=30,
        seed=42,
    )
    elapsed = time.time() - t0
    peak_vram_gb = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else 0.0

    out_path = os.path.join(_OUT_DIR, f"{case['name']}_result.png")
    result.images[0].save(out_path)
    print(f"완료: {out_path} (추론 {elapsed:.1f}s, Peak VRAM {peak_vram_gb:.2f}GB)")

print("\n=== 전체 완료 ===")
