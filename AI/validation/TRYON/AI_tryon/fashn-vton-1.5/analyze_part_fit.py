"""부위별 핏 테스트 결과를 사람이 보기 쉽게 비교 이미지로 만든다.

같은 seed=42를 모든 케이스에 썼기 때문에(초기 노이즈 동일) baseline과의 픽셀 차이는
순수하게 "우리가 바꾼 레퍼런스 이미지"에서 온 것 — diff 히트맵이 의미 있는 신호다.

각 부위마다:
  1. tight | baseline | loose 3연 비교 이미지(라벨 포함)
  2. baseline 위에 |tight-baseline|, |loose-baseline| 차이를 빨간 히트맵으로 오버레이
     → 변화가 실제로 의도한 부위(허리/가슴/어깨 등)에 집중되는지 한눈에 확인
"""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "part_fit_test")
_OUT_DIR = os.path.join(_RESULTS_DIR, "analysis")
os.makedirs(_OUT_DIR, exist_ok=True)

LABEL_H = 36


def load(name):
    path = os.path.join(_RESULTS_DIR, f"{name}.png")
    if not os.path.exists(path):
        return None
    return Image.open(path).convert("RGB")


def with_label(img, text):
    canvas = Image.new("RGB", (img.width, img.height + LABEL_H), (255, 255, 255))
    canvas.paste(img, (0, LABEL_H))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    draw.text((8, 6), text, fill=(0, 0, 0), font=font)
    return canvas


def diff_heatmap_overlay(base: Image.Image, other: Image.Image, label: str) -> Image.Image:
    base_np = np.array(base).astype(np.float32)
    other_np = np.array(other).astype(np.float32)
    diff = np.abs(base_np - other_np).mean(axis=2)  # (h, w)
    d_max = diff.max() if diff.max() > 0 else 1.0
    diff_norm = np.clip(diff / d_max, 0, 1)

    overlay = base_np.copy()
    red = np.zeros_like(overlay)
    red[..., 0] = 255
    alpha = (diff_norm[..., None] ** 0.6) * 0.7  # 강한 차이일수록 더 붉게
    blended = overlay * (1 - alpha) + red * alpha
    result = Image.fromarray(blended.astype(np.uint8))
    return with_label(result, label)


def make_triptych(part_name, tight_name, base_name, loose_name):
    tight, base, loose = load(tight_name), load(base_name), load(loose_name)
    if base is None:
        print(f"[건너뜀] {part_name}: baseline 결과 없음 ({base_name})")
        return
    if tight is None or loose is None:
        print(f"[건너뜀] {part_name}: tight/loose 결과 아직 없음")
        return

    row1 = [with_label(tight, "TIGHT"), with_label(base, "BASELINE"), with_label(loose, "LOOSE")]
    row2 = [
        with_label(base, "BASELINE"),
        diff_heatmap_overlay(base, tight, "diff: TIGHT vs baseline"),
        diff_heatmap_overlay(base, loose, "diff: LOOSE vs baseline"),
    ]

    w, h = row1[0].size
    canvas = Image.new("RGB", (w * 3 + 20, h * 2 + 30), (230, 230, 230))
    for i, im in enumerate(row1):
        canvas.paste(im, (i * (w + 10), 0))
    for i, im in enumerate(row2):
        canvas.paste(im, (i * (w + 10), h + 30))

    out_path = os.path.join(_OUT_DIR, f"compare_{part_name}.png")
    canvas.save(out_path)
    print(f"저장: {out_path}")


CASES = [
    ("tops_shoulder", "tops_shoulder_tight", "tops_baseline", "tops_shoulder_loose"),
    ("tops_chest", "tops_chest_tight", "tops_baseline", "tops_chest_loose"),
    ("tops_waist", "tops_waist_tight", "tops_baseline", "tops_waist_loose"),
    ("bottoms_waist", "bottoms_waist_tight", "bottoms_baseline", "bottoms_waist_loose"),
    ("bottoms_hem", "bottoms_hem_tight", "bottoms_baseline", "bottoms_hem_loose"),
]

for part_name, tight_name, base_name, loose_name in CASES:
    make_triptych(part_name, tight_name, base_name, loose_name)

print("\n완료")
