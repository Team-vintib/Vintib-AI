"""
파인튜닝된 의류 세그멘테이션 모델의 마스크 품질(클래스별 IoU) 평가 스파이크.

Notion LAB-1(프로토타입 모델 실험 기록)의 시착 기능 평가지표 예시(SSIM/LPIPS,
처리시간)에 맞춰, 이 스크립트의 출력(클래스별 IoU + mean IoU)을 그대로 실험 기록
표에 옮겨 적을 수 있게 구성했다.

실행 전 준비사항:
- finetune_segmentation.py를 먼저 실행해 garment_seg_head.pth를 만들어둘 것
- 학습 때와 동일한 SEED/VAL_RATIO로 val 분할을 재현하므로, finetune_segmentation.py의
  설정을 바꿨다면 이 스크립트도 함께 맞출 것
"""

import numpy as np
import torch
from torch.utils.data import DataLoader, random_split

from dataset import CLASS_NAMES, DATASET_ROOT, GarmentSegDataset, collect_samples
from finetune_segmentation import CHECKPOINT_PATH, IMAGE_SIZE, SEED, VAL_RATIO, build_model


def compute_iou(pred: np.ndarray, target: np.ndarray, num_classes: int) -> list[float]:
    """pred/target: (H, W) 정수 클래스맵. 클래스별 IoU를 반환(해당 배치에 없는 클래스는 nan)."""
    ious = []
    for class_idx in range(num_classes):
        pred_mask = pred == class_idx
        target_mask = target == class_idx
        union = np.logical_or(pred_mask, target_mask).sum()
        if union == 0:
            ious.append(float("nan"))
            continue
        intersection = np.logical_and(pred_mask, target_mask).sum()
        ious.append(float(intersection / union))
    return ious


def evaluate() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"

    samples = collect_samples(DATASET_ROOT)
    dataset = GarmentSegDataset(samples, image_size=IMAGE_SIZE)
    val_size = max(1, int(len(dataset) * VAL_RATIO))
    train_size = len(dataset) - val_size
    generator = torch.Generator().manual_seed(SEED)
    _, val_set = random_split(dataset, [train_size, val_size], generator=generator)
    val_loader = DataLoader(val_set, batch_size=1, shuffle=False)

    model = build_model(num_classes=len(CLASS_NAMES)).to(device)
    model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=device))
    model.eval()

    per_class_ious: list[list[float]] = [[] for _ in CLASS_NAMES]
    with torch.no_grad():
        for images, masks in val_loader:
            images = images.to(device)
            outputs = model(images)["out"]
            preds = outputs.argmax(dim=1).cpu().numpy()
            targets = masks.numpy()

            for pred, target in zip(preds, targets, strict=True):
                for class_idx, iou in enumerate(compute_iou(pred, target, len(CLASS_NAMES))):
                    if not np.isnan(iou):
                        per_class_ious[class_idx].append(iou)

    print(f"평가 이미지 수: {len(val_set)}")
    mean_ious = []
    for class_idx, name in enumerate(CLASS_NAMES):
        values = per_class_ious[class_idx]
        mean_iou = float(np.mean(values)) if values else float("nan")
        mean_ious.append(mean_iou)
        print(f"  {name:10s}: IoU={mean_iou:.4f} (n={len(values)})")

    valid = [v for v in mean_ious if not np.isnan(v)]
    if valid:
        print(f"mean IoU (전체 클래스 평균): {float(np.mean(valid)):.4f}")


if __name__ == "__main__":
    evaluate()
