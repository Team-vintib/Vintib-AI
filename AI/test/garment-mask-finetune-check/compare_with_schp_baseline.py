"""
파인튜닝된 세그멘테이션 모델을 기존 CatVTON의 SCHP+DensePose 기반 AutoMasker와
동일 이미지에서 비교하는 스파이크 (LAB-24 1순위 전략의 "기존 대비 개선" 검증용, 선택 실행).

K-Fashion 이미지만 비교 대상으로 삼는다 — 의류 통합 데이터/3D 데이터는 인물이 없는
상품 단독컷이라 인물 파싱 기반인 SCHP/DensePose 자체가 성립하지 않는다.

실행 전 준비사항:
- finetune_segmentation.py로 garment_seg_head.pth를 먼저 만들어둘 것
- huggingface_hub로 zhengchong/CatVTON 체크포인트(DensePose+SCHP, 수 GB) 다운로드 필요
- 나머지 세 스크립트와 달리 무겁고 선택적인 비교 실험이라 별도로 실행하는 용도
"""

import sys
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import snapshot_download
from PIL import Image

from dataset import CLASS_NAMES, DATASET_ROOT, collect_samples, rasterize
from finetune_segmentation import CHECKPOINT_PATH, IMAGE_SIZE, build_model

# catvton은 정식 배포 패키지가 아니라 리포에 통째로 벤더링된 코드라
# model.cloth_masker를 import하려면 그 루트를 sys.path에 넣어야 한다.
CATVTON_ROOT = Path(__file__).resolve().parent.parent / "AI_tryon" / "catvton"
sys.path.insert(0, str(CATVTON_ROOT))

from model.cloth_masker import AutoMasker  # noqa: E402

# 우리 4-클래스를 AutoMasker의 mask_type으로 근사 매핑한다(완전히 같은 개념은 아님 —
# 특히 '원피스'는 전용 옵션이 없어 몸통 전체를 덮는 'overall'로 근사).
CATEGORY_TO_MASK_TYPE = {
    "상의": "upper",
    "하의": "lower",
    "아우터": "outer",
    "원피스": "overall",
}


def _binary_iou(pred: np.ndarray, target: np.ndarray) -> float:
    union = np.logical_or(pred, target).sum()
    if union == 0:
        return float("nan")
    return float(np.logical_and(pred, target).sum() / union)


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"

    samples = [s for s in collect_samples(DATASET_ROOT) if s.source == "kfashion"]
    print(f"비교 대상 K-Fashion 이미지: {len(samples)}장")
    if not samples:
        raise RuntimeError(
            "K-Fashion 샘플을 찾지 못했습니다. dataset.py의 DATASET_ROOT를 확인하세요."
        )

    repo_path = snapshot_download(repo_id="zhengchong/CatVTON")
    masker = AutoMasker(
        densepose_ckpt=str(Path(repo_path) / "DensePose"),
        schp_ckpt=str(Path(repo_path) / "SCHP"),
        device=device,
    )

    finetuned = build_model(num_classes=len(CLASS_NAMES)).to(device)
    finetuned.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=device))
    finetuned.eval()

    schp_ious: dict[str, list[float]] = {category: [] for category in CATEGORY_TO_MASK_TYPE}
    finetuned_ious: dict[str, list[float]] = {category: [] for category in CATEGORY_TO_MASK_TYPE}

    for sample in samples:
        image = Image.open(sample.image_path).convert("RGB")
        gt_mask = rasterize(image.size, sample.polygons)

        with torch.no_grad():
            resized = np.array(image.resize(IMAGE_SIZE))
            image_tensor = torch.from_numpy(resized).permute(2, 0, 1).float() / 255.0
            logits = finetuned(image_tensor.unsqueeze(0).to(device))["out"]
            pred_small = logits.argmax(dim=1)[0].cpu().numpy().astype(np.uint8)
        pred = np.array(Image.fromarray(pred_small).resize(image.size, Image.NEAREST))

        for category, mask_type in CATEGORY_TO_MASK_TYPE.items():
            class_idx = CLASS_NAMES.index(category)
            gt_binary = gt_mask == class_idx
            if not gt_binary.any():
                continue

            schp_result = masker(image, mask_type=mask_type)
            schp_binary = np.array(schp_result["mask"].resize(image.size)) > 127
            pred_binary = pred == class_idx

            schp_ious[category].append(_binary_iou(schp_binary, gt_binary))
            finetuned_ious[category].append(_binary_iou(pred_binary, gt_binary))

    print(f"{'카테고리':10s} {'SCHP baseline IoU':>20s} {'파인튜닝 모델 IoU':>20s} {'n':>5s}")
    for category in CATEGORY_TO_MASK_TYPE:
        schp_values = schp_ious[category]
        finetuned_values = finetuned_ious[category]
        schp_mean = float(np.mean(schp_values)) if schp_values else float("nan")
        finetuned_mean = float(np.mean(finetuned_values)) if finetuned_values else float("nan")
        print(f"{category:10s} {schp_mean:20.4f} {finetuned_mean:20.4f} {len(schp_values):5d}")


if __name__ == "__main__":
    main()
