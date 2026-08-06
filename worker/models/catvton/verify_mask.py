import os
from huggingface_hub import snapshot_download
from model.cloth_masker import AutoMasker, vis_mask
from PIL import Image

repo_path = snapshot_download(repo_id="zhengchong/CatVTON")

masker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device='cuda',
)

person_img = Image.open("image/person.jpg").convert("RGB")

for fit_type in ["regular", "oversized", "cropped"]:
    result = masker(person_img, mask_type="upper", fit_type=fit_type)
    mask = result["mask"]
    mask.save(f"mask_{fit_type}.png")
    vis = vis_mask(person_img.resize(mask.size), mask)
    vis.save(f"vis_{fit_type}.png")
    print(f"{fit_type} 마스크 저장 완료")