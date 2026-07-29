"""
의류 세그멘테이션 헤드 파인튜닝 스파이크 (LAB-24 1순위 전략: 마스킹/파싱 정밀도 향상)

CatVTON이 쓰는 SCHP는 범용 인물 파싱(신체부위 20/18클래스) 모델이라 학습 인프라가
벤더링되어 있지 않고, 우리 폴리곤 라벨의 taxonomy(상의/하의/아우터/원피스)와도 맞지
않는다(Notion LAB-24 검토 참고). 대신 torchvision의 경량 세그멘테이션 모델을 우리
라벨로 전이학습시켜, 추후 AutoMasker의 보조/대체 마스크 소스 후보로 검증하기 위한
스파이크다.

실행 전 준비사항:
- pip install -r AI/test/requirements-test.txt (torch, torchvision 포함)
- dataset.py의 DATASET_ROOT를 로컬 sample_dsets 경로로 조정할 것
- GPU 권장 (CPU에서도 동작은 하나 매우 느림)

주의: 이 스크립트는 코드 검증용 PoC로, 아직 실행해보지 않았다(로컬에 torch 실행
환경이 없어 문법/구조만 확인함). 실제 학습은 GPU 환경에서 진행할 것.
"""

import random
from pathlib import Path

import torch
from dataset import CLASS_NAMES, DATASET_ROOT, GarmentSegDataset, collect_samples
from torch.utils.data import DataLoader, random_split
from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large

# ---- 설정 ----
IMAGE_SIZE = (512, 512)
BATCH_SIZE = 4
NUM_EPOCHS = 10
LEARNING_RATE = 1e-4
VAL_RATIO = 0.15
SEED = 42
CHECKPOINT_PATH = Path(__file__).parent / "garment_seg_head.pth"


def build_model(num_classes: int) -> torch.nn.Module:
    """DeepLabV3(MobileNetV3 backbone) 사전학습 가중치를 불러오고 분류 헤드만 교체한다."""
    model = deeplabv3_mobilenet_v3_large(weights="DEFAULT")

    in_channels = model.classifier[4].in_channels
    model.classifier[4] = torch.nn.Conv2d(in_channels, num_classes, kernel_size=1)

    if model.aux_classifier is not None:
        aux_in_channels = model.aux_classifier[4].in_channels
        model.aux_classifier[4] = torch.nn.Conv2d(aux_in_channels, num_classes, kernel_size=1)

    return model


def train() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}")

    samples = collect_samples(DATASET_ROOT)
    print(f"수집된 (이미지, 라벨) 쌍: {len(samples)}개")
    if not samples:
        raise RuntimeError(
            f"{DATASET_ROOT} 아래에서 이미지/라벨 쌍을 찾지 못했습니다. "
            "dataset.py의 DATASET_ROOT를 확인하세요."
        )

    dataset = GarmentSegDataset(samples, image_size=IMAGE_SIZE)
    val_size = max(1, int(len(dataset) * VAL_RATIO))
    train_size = len(dataset) - val_size
    generator = torch.Generator().manual_seed(SEED)
    train_set, val_set = random_split(dataset, [train_size, val_size], generator=generator)

    train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=BATCH_SIZE, shuffle=False)

    model = build_model(num_classes=len(CLASS_NAMES)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    criterion = torch.nn.CrossEntropyLoss()

    for epoch in range(1, NUM_EPOCHS + 1):
        model.train()
        running_loss = 0.0
        for images, masks in train_loader:
            images, masks = images.to(device), masks.to(device)

            optimizer.zero_grad()
            outputs = model(images)["out"]
            loss = criterion(outputs, masks)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
        train_loss = running_loss / len(train_set)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for images, masks in val_loader:
                images, masks = images.to(device), masks.to(device)
                outputs = model(images)["out"]
                val_loss += criterion(outputs, masks).item() * images.size(0)
        val_loss /= max(1, len(val_set))

        print(f"[epoch {epoch}/{NUM_EPOCHS}] train_loss={train_loss:.4f} val_loss={val_loss:.4f}")

    torch.save(model.state_dict(), CHECKPOINT_PATH)
    print(f"체크포인트 저장 완료 -> {CHECKPOINT_PATH}")


if __name__ == "__main__":
    random.seed(SEED)
    train()
