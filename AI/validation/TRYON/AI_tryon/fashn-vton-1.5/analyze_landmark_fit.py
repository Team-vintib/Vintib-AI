"""landmark_fit_test 결과(base/tight/loose)를 나란히 비교 + diff 히트맵으로 본다."""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "landmark_fit_test")
LABEL_H = 36


def load(name):
    return Image.open(os.path.join(_RESULTS_DIR, f"result_{name}.png")).convert("RGB")


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


def diff_heatmap_overlay(base, other, label):
    base_np, other_np = np.array(base).astype(np.float32), np.array(other).astype(np.float32)
    diff = np.abs(base_np - other_np).mean(axis=2)
    d_max = diff.max() if diff.max() > 0 else 1.0
    diff_norm = np.clip(diff / d_max, 0, 1)
    red = np.zeros_like(base_np)
    red[..., 0] = 255
    alpha = (diff_norm[..., None] ** 0.6) * 0.7
    blended = base_np * (1 - alpha) + red * alpha
    return with_label(Image.fromarray(blended.astype(np.uint8)), label)


base, tight, loose = load("base"), load("tight"), load("loose")
row1 = [with_label(tight, "TIGHT"), with_label(base, "BASE"), with_label(loose, "LOOSE")]
row2 = [
    with_label(base, "BASE"),
    diff_heatmap_overlay(base, tight, "diff: TIGHT vs base"),
    diff_heatmap_overlay(base, loose, "diff: LOOSE vs base"),
]
w, h = row1[0].size
canvas = Image.new("RGB", (w * 3 + 20, h * 2 + 30), (230, 230, 230))
for i, im in enumerate(row1):
    canvas.paste(im, (i * (w + 10), 0))
for i, im in enumerate(row2):
    canvas.paste(im, (i * (w + 10), h + 30))

out_path = os.path.join(_RESULTS_DIR, "compare.png")
canvas.save(out_path)
print(f"저장: {out_path}")
