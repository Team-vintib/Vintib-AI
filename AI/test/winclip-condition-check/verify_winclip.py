"""
WinCLIP zero-shot / few-shot 얼룩 탐지 - 개선판 검증 스크립트

사용법:
1) 검사할 이미지 경로를 TARGET_IMAGE에 지정
2) few-shot을 쓰려면 정상(오염 없는) 옷 사진 2~5장을 REFERENCE_IMAGES에 지정
   - 없으면 REFERENCE_IMAGES = [] 로 두면 zero-shot으로 동작
3) 여러 scale 조합을 SCALE_OPTIONS에 넣으면 한 번에 비교됨
"""

import torch
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from anomalib.models.image.winclip.torch_model import WinClipModel

# ---------------- 설정 ----------------
TARGET_IMAGE = "contaminated clothing.jpg"
REFERENCE_IMAGES = [
    "normal_shirt_1.jpg",
    "normal_shirt_2.jpg",
    "normal_shirt_3.jpg",
]
CLASS_NAME = "white dress shirt"  # 검사 대상에 맞게 구체적으로
SCALE_OPTIONS = [(2, 3), (1, 2)]  # 기본값 vs 더 촘촘한 윈도우
# ---------------------------------------

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"device: {device}")


def load_tensor(transform_fn, path):
    pil_img = Image.open(path).convert("RGB")
    return transform_fn(np.array(pil_img)), pil_img


def run_one(class_name, scales, target_path, reference_paths):
    model = WinClipModel(class_name=class_name, scales=scales).to(device).eval()

    if reference_paths:
        ref_tensors = torch.stack([load_tensor(model.transform, p)[0] for p in reference_paths]).to(
            device
        )
        model.k_shot = len(reference_paths)
        model.setup(class_name=class_name, reference_images=ref_tensors)

    batch, pil_img = load_tensor(model.transform, target_path)
    batch = batch.unsqueeze(0).to(device)

    with torch.no_grad():
        out = model(batch)

    amap = out.anomaly_map.squeeze(0).cpu().numpy()
    score = out.pred_score.item()

    yx = np.unravel_index(np.argmax(amap), amap.shape)
    peak_rel = (yx[0] / amap.shape[0], yx[1] / amap.shape[1])

    return pil_img, amap, score, peak_rel


results = []
mode = "few-shot" if REFERENCE_IMAGES else "zero-shot"
for scales in SCALE_OPTIONS:
    pil_img, amap, score, peak_rel = run_one(CLASS_NAME, scales, TARGET_IMAGE, REFERENCE_IMAGES)
    label = f"{mode}, scales={scales}"
    print(f"[{label}] score={score:.3f}  peak_rel(y,x)={peak_rel}")
    results.append((label, pil_img, amap, score))

# ---------------- 시각화 ----------------
n = len(results)
fig, axes = plt.subplots(1, n + 1, figsize=(4 * (n + 1), 4))

axes[0].imshow(results[0][1])
axes[0].set_title("Original")
axes[0].axis("off")

for i, (label, pil_img, amap, score) in enumerate(results):
    ax = axes[i + 1]
    ax.imshow(pil_img)
    ax.imshow(amap, cmap="jet", alpha=0.5)
    ax.set_title(f"{label}\nscore={score:.3f}")
    ax.axis("off")

plt.tight_layout()
plt.savefig("winclip_compare_result.png", dpi=120)
print("saved -> winclip_compare_result.png")
