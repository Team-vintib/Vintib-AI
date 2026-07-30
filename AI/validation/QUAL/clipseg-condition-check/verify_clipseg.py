"""
CLIPSeg: 텍스트 프롬프트 기반 오염/손상 영역 세그멘테이션 PoC
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image
from transformers import CLIPSegForImageSegmentation, CLIPSegProcessor

# 검증 노트북(clipseg_qc_test.ipynb/sam3_qc_test.ipynb)과 같은 이미지를 쓴다
# (validation/QUAL/qc_shared.py 공용 경로) — 하드코딩된 개별 이미지 파일은 리포에 없다.
sys.path.insert(0, "..")
from qc_shared import list_images  # noqa: E402

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"device: {device}")

MODEL_ID = "CIDAS/clipseg-rd64-refined"
processor = CLIPSegProcessor.from_pretrained(MODEL_ID)
model = CLIPSegForImageSegmentation.from_pretrained(MODEL_ID).to(device).eval()

IMAGE_PATHS = list_images()
if not IMAGE_PATHS:
    raise FileNotFoundError(
        "검증 노트북이 쓰는 sample_images/ 에 이미지가 없습니다. "
        "sam3_qc_test.ipynb 를 먼저 실행해 이미지를 채우거나 직접 넣어 주세요."
    )

PROMPTS = ["a stain on fabric", "a dirty mark", "a hole or tear in fabric", "clean fabric"]

OUTPUT_DIR = Path("./outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for image_path in IMAGE_PATHS:
    original = Image.open(image_path).convert("RGB")
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
    print(f"[{image_path.name}] mask shape: {probs.shape}")

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
    out_path = OUTPUT_DIR / f"clipseg_result_{image_path.stem}.png"
    plt.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"saved -> {out_path}")
