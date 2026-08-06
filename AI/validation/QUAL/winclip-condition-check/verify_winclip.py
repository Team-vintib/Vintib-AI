"""
WinCLIP zero-shot 얼룩 탐지 - 개선판 검증 스크립트

CLIPSeg/SAM3 검증 스크립트(`verify_clipseg.py`, `sam3_qc_test.ipynb`)와 같은 공용 이미지 세트
(`qc_shared.list_images()` → `sam3-condition-check/sample_images/`)를 그대로 써서 세 아키텍처를
같은 입력으로 비교한다. 공용 세트에는 정상/오염 라벨이 없어 few-shot 참조 이미지를 고를 근거가
없으므로 zero-shot(REFERENCE_IMAGES 없음)으로 전체 이미지를 순회한다.

사용법:
1) 여러 scale 조합을 SCALE_OPTIONS에 넣으면 이미지마다 한 번에 비교됨
2) 특정 이미지에 few-shot을 시도하고 싶으면 REFERENCE_IMAGES에 sample_images/ 안의 다른 파일
   경로를 넣는다(정상 후보로 쓸 만한 이미지를 직접 골라야 한다 — 공용 세트는 라벨이 없다)
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from anomalib.models.image.winclip.torch_model import WinClipModel
from PIL import Image

# 검증 스크립트/노트북 전부(clipseg_qc_test.ipynb/sam3_qc_test.ipynb/verify_clipseg.py)가 같은
# 이미지를 쓴다 (validation/QUAL/qc_shared.py 공용 경로) — 하드코딩된 개별 이미지 파일은 없다.
sys.path.insert(0, "..")
from qc_shared import list_images  # noqa: E402

# ---------------- 설정 ----------------
REFERENCE_IMAGES: list[str] = []  # 공용 세트는 정상/오염 라벨이 없어 기본은 zero-shot
CLASS_NAME = "clothing"  # SAM3 쪽 GARMENT_PROMPT("clothing")와 맞춘 일반 명사 — 이미지마다 소재가 달라 특정 의류명을 못 씀
SCALE_OPTIONS = [(2, 3), (1, 2)]  # 기본값 vs 더 촘촘한 윈도우
# ---------------------------------------

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"device: {device}")

IMAGE_PATHS = list_images()
if not IMAGE_PATHS:
    raise FileNotFoundError(
        "검증 노트북이 쓰는 sample_images/ 에 이미지가 없습니다. "
        "sam3_qc_test.ipynb 를 먼저 실행해 이미지를 채우거나 직접 넣어 주세요."
    )

OUTPUT_DIR = Path("./outputs/verify_winclip")  # 노트북/스크립트별 하위 폴더 — 다른 결과와 안 섞이게
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_tensor(transform_fn, path):
    pil_img = Image.open(path).convert("RGB")
    return transform_fn(np.array(pil_img)), pil_img


def run_one(model, target_path, reference_paths):
    if reference_paths:
        ref_tensors = torch.stack([load_tensor(model.transform, p)[0] for p in reference_paths]).to(
            device
        )
        model.k_shot = len(reference_paths)
        model.setup(class_name=CLASS_NAME, reference_images=ref_tensors)

    batch, pil_img = load_tensor(model.transform, target_path)
    batch = batch.unsqueeze(0).to(device)

    with torch.no_grad():
        out = model(batch)

    amap = out.anomaly_map.squeeze(0).cpu().numpy()
    score = out.pred_score.item()

    yx = np.unravel_index(np.argmax(amap), amap.shape)
    peak_rel = (yx[0] / amap.shape[0], yx[1] / amap.shape[1])

    return pil_img, amap, score, peak_rel


mode = "few-shot" if REFERENCE_IMAGES else "zero-shot"

for image_path in IMAGE_PATHS:
    results = []
    for scales in SCALE_OPTIONS:
        model = WinClipModel(class_name=CLASS_NAME, scales=scales).to(device).eval()
        pil_img, amap, score, peak_rel = run_one(model, image_path, REFERENCE_IMAGES)
        label = f"{mode}, scales={scales}"
        print(f"[{image_path.name}] [{label}] score={score:.3f}  peak_rel(y,x)={peak_rel}")
        results.append((label, pil_img, amap, score))

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
    out_path = OUTPUT_DIR / f"winclip_result_{image_path.stem}.png"
    plt.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"saved -> {out_path}")
