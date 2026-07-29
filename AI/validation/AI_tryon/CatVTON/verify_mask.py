import os
from datetime import datetime

from huggingface_hub import snapshot_download
from model.cloth_masker import AutoMasker, vis_mask
from PIL import Image

repo_path = snapshot_download(repo_id="zhengchong/CatVTON")

masker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device='cuda',
)

# ---- 결과 저장 폴더 (테스트 실행 시각별로 구분) ----
OUT_DIR = os.path.join("result", datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

person_img = Image.open("image/person.jpg").convert("RGB")

for fit_type in ["regular", "oversized", "cropped"]:
    result = masker(person_img, mask_type="upper", fit_type=fit_type)
    mask = result["mask"]
    mask.save(os.path.join(OUT_DIR, f"mask_{fit_type}.png"))
    vis = vis_mask(person_img.resize(mask.size), mask)
    vis.save(os.path.join(OUT_DIR, f"vis_{fit_type}.png"))
    print(f"{fit_type} 마스크 저장 완료 -> {OUT_DIR}/mask_{fit_type}.png")