"""
WinCLIP zero-shot / few-shot 얼룩 탐지 - 시각화 정합성 수정판

핵심 수정: CLIP 전처리(Resize+CenterCrop)로 인해 모델이 실제로 보는 영역은
원본 이미지의 '중앙 정사각형' 부분뿐입니다. anomaly map은 이 크롭된 영역
기준으로 계산되므로, 원본 전체 이미지가 아니라 '모델이 실제로 본 크롭 이미지'
위에 겹쳐 그려야 위치가 정확히 맞습니다.
"""

import matplotlib.pyplot as plt
import numpy as np
import torch
from anomalib.models.image.winclip.torch_model import WinClipModel
from PIL import Image
from torchvision.transforms import CenterCrop, Compose, Resize

# ---------------- 설정 ----------------
TARGET_IMAGE = "normal_shirt_1.jpg"
REFERENCE_IMAGES = [
    "normal_shirt_1.jpg",
    "normal_shirt_2.jpg",
    "normal_shirt_3.jpg",
]
CLASS_NAME = "white dress shirt"
SCALES = (2, 3)
# ---------------------------------------

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"device: {device}")

model = WinClipModel(class_name=CLASS_NAME, scales=SCALES).to(device).eval()

# 모델 전처리와 동일한 리사이즈+크롭 (정규화 전 단계) -- 시각화용 "모델이 실제로 본 이미지"
crop_size = 240  # WinClip 기본 입력 해상도. model.transform 출력에서 확인 가능
preview_transform = Compose([Resize(crop_size, antialias=True), CenterCrop((crop_size, crop_size))])


def load_tensor(path):
    pil_img = Image.open(path).convert("RGB")
    return model.transform(np.array(pil_img)), preview_transform(pil_img)


if REFERENCE_IMAGES:
    ref_tensors = torch.stack([load_tensor(p)[0] for p in REFERENCE_IMAGES]).to(device)
    model.k_shot = len(REFERENCE_IMAGES)
    model.setup(class_name=CLASS_NAME, reference_images=ref_tensors)

batch, cropped_preview = load_tensor(TARGET_IMAGE)
batch = batch.unsqueeze(0).to(device)

with torch.no_grad():
    out = model(batch)

amap = out.anomaly_map.squeeze(0).cpu().numpy()
score = out.pred_score.item()
print(f"score={score:.3f}  amap shape={amap.shape}  cropped_preview size={cropped_preview.size}")

# 원본 전체 이미지도 참고용으로 같이 표시
original_full = Image.open(TARGET_IMAGE).convert("RGB")

fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))

axes[0].imshow(original_full)
axes[0].set_title("Original (full)")
axes[0].axis("off")

axes[1].imshow(cropped_preview)
axes[1].set_title("Actual model input\n(Resize+CenterCrop)")
axes[1].axis("off")

axes[2].imshow(cropped_preview)
axes[2].imshow(amap, cmap="jet", alpha=0.5, extent=(0, crop_size, crop_size, 0))
axes[2].set_title(f"Anomaly map (aligned)\nscore={score:.3f}")
axes[2].axis("off")

plt.tight_layout()
plt.savefig("winclip_aligned_result3.png", dpi=120)
print("saved -> winclip_aligned_result3.png")
