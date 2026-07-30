"""
CLIPSeg: 텍스트 프롬프트 기반 오염/손상 영역 세그멘테이션 PoC
"""

import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image
from transformers import CLIPSegForImageSegmentation, CLIPSegProcessor

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"device: {device}")

MODEL_ID = "CIDAS/clipseg-rd64-refined"
processor = CLIPSegProcessor.from_pretrained(MODEL_ID)
model = CLIPSegForImageSegmentation.from_pretrained(MODEL_ID).to(device).eval()

IMAGE_PATH = "contaminated clothing7.jpg"
PROMPTS = ["a stain on fabric", "a dirty mark", "a hole or tear in fabric", "clean fabric"]

original = Image.open(IMAGE_PATH).convert("RGB")
orig_w, orig_h = original.size

# 통합 processor(...) 호출 대신 tokenizer/image_processor를 분리 호출
# -> kwarg가 서로 섞여 에러나는 문제 회피
text_inputs = processor.tokenizer(PROMPTS, return_tensors="pt", padding=True)
image_inputs = processor.image_processor(
    [original] * len(PROMPTS),
    size={"height": 224, "width": 224},
    return_tensors="pt",
)

inputs = {**text_inputs, "pixel_values": image_inputs["pixel_values"]}
inputs = {k: v.to(device) for k, v in inputs.items()}

with torch.no_grad():
    outputs = model(**inputs)

probs = torch.sigmoid(outputs.logits).cpu().numpy()  # (num_prompts, H, W)
print("mask shape:", probs.shape)

fig, axes = plt.subplots(1, len(PROMPTS) + 1, figsize=(4 * (len(PROMPTS) + 1), 4.2))
axes[0].imshow(original)
axes[0].set_title("Original")
axes[0].axis("off")

for i, prompt in enumerate(PROMPTS):
    mask_img = Image.fromarray((probs[i] * 255).astype(np.uint8)).resize(
        (orig_w, orig_h), Image.BILINEAR
    )
    mask_resized = np.array(mask_img) / 255.0

    axes[i + 1].imshow(original)
    axes[i + 1].imshow(mask_resized, cmap="jet", alpha=0.5, vmin=0, vmax=1)
    axes[i + 1].set_title(f'"{prompt}"\nmax={probs[i].max():.2f}')
    axes[i + 1].axis("off")

plt.tight_layout()
plt.savefig("clipseg_result8.png", dpi=120)
print("saved -> clipseg_result8.png")
