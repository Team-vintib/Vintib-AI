"""HRNet(DeepFashion2 사전학습) 랜드마크 검출 PoC — 단일 이미지 추론.

이 저장소(`svip-lab/HRNet-for-Fashion-Landmark-Estimation.PyTorch`)엔 사진 한 장을 바로 넣는
데모 스크립트가 없다 — `tools/test.py`/`train.py`는 DeepFashion2 데이터셋(정답 bbox 포함)을
대량으로 돌리는 용도다. 이 스크립트가 그 빈틈을 메운다: 실제 top-down pose estimation 표준
파이프라인(bbox → center/scale → affine crop/resize → 정규화 → 모델 → heatmap → 좌표 역변환)을
`lib/dataset/coco.py`(`_xywh2cs`)·`lib/dataset/JointsDataset.py`·`tools/test.py`의 실제 코드를
그대로 따라 재현했다.

**아직 안 된 것**: 이 모델은 DeepFashion2 카테고리(13종)별로 294개 랜드마크 중 일부만 유효한
구조인데, "몇 번 인덱스가 어깨/소매/밑단인지"는 이 저장소가 아니라 DeepFashion2 데이터셋 원본
저장소(`switchablenorms/DeepFashion2`)의 카테고리별 정의표에 있다 — 이번 PoC는 "모델이 실제로
돌고 신뢰도 높은 포인트가 그럴듯한 위치에 찍히는지"만 확인한다. `AI/app/measurement`의
`LandmarkType`(SHOULDER_LEFT 등)으로의 정확한 매핑은 여기서 확인 후 별도 후속 작업이다.

bbox(원단 위치)는 인자로 안 주면 이미지 전체를 쓴다 — 실제 파이프라인(Phase 6)에서는
`worker/models/garment_measurement/segmenter.py`(GrabCut)가 찾은 영역을 bbox로 넘기면 된다.

사용법:
    python verify_hrnet_landmarks.py <이미지경로> [--confidence 0.3] [--top 20]

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from types import SimpleNamespace

import cv2
import numpy as np
import torch
import torchvision.transforms as transforms

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR = os.path.join(_THIS_DIR, "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from config import cfg, update_config  # noqa: E402
from utils.transforms import get_affine_transform, transform_preds  # noqa: E402
from core.inference import get_final_preds  # noqa: E402
import models  # noqa: E402

_CFG_PATH = os.path.join(
    _THIS_DIR, "experiments", "deepfashion2", "hrnet", "w48_384x288_adam_lr1e-3.yaml"
)
_DEFAULT_CHECKPOINT = os.path.join(
    _THIS_DIR, "models", "pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth"
)

# lib/dataset/coco.py의 _xywh2cs와 동일한 상수(pixel_std=200, margin=1.25).
_PIXEL_STD = 200.0
_SCALE_MARGIN = 1.25
_NORMALIZE_MEAN = [0.485, 0.456, 0.406]
_NORMALIZE_STD = [0.229, 0.224, 0.225]


def _load_config(checkpoint_path: str):
    args = SimpleNamespace(
        cfg=_CFG_PATH,
        opts=["TEST.MODEL_FILE", checkpoint_path],
        modelDir="",
        logDir="",
        dataDir="",
    )
    update_config(cfg, args)
    return cfg


def _build_model(cfg, device: str):
    model = models.pose_hrnet.get_pose_net(cfg, is_train=False)
    state_dict = torch.load(cfg.TEST.MODEL_FILE, map_location=device)
    # DataParallel로 저장된 체크포인트면 키에 "module." 접두어가 붙어 있다 — 방어적으로 벗긴다.
    if any(k.startswith("module.") for k in state_dict):
        state_dict = {k.removeprefix("module."): v for k, v in state_dict.items()}
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def _xywh2cs(x: float, y: float, w: float, h: float, aspect_ratio: float) -> tuple:
    """`lib/dataset/coco.py`의 `_xywh2cs`와 동일한 로직 — bbox를 (center, scale)로 바꾼다."""
    center = np.array([x + w * 0.5, y + h * 0.5], dtype=np.float32)
    if w > aspect_ratio * h:
        h = w / aspect_ratio
    elif w < aspect_ratio * h:
        w = h * aspect_ratio
    scale = np.array([w / _PIXEL_STD, h / _PIXEL_STD], dtype=np.float32) * _SCALE_MARGIN
    return center, scale


def run_inference(image_path: str, checkpoint_path: str, bbox: tuple | None = None) -> dict:
    """이미지 한 장에 대해 294개 랜드마크 좌표 + 신뢰도를 돌려준다.

    반환: {"landmarks": [(x, y, confidence), ...] (294개), "load_ms":, "inference_ms":,
           "device":, "peak_vram_mb": (cuda일 때만)}
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"

    load_started = time.perf_counter()
    cfg = _load_config(checkpoint_path)
    model = _build_model(cfg, device)
    load_ms = (time.perf_counter() - load_started) * 1000

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()

    # COLOR_RGB: false — BGR 그대로 둔다(학습 때와 동일하게, 직관과 다르지만 원본 코드 그대로 따름).
    image = cv2.imread(image_path, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    if image is None:
        raise FileNotFoundError(f"이미지를 읽을 수 없습니다: {image_path}")
    height, width = image.shape[:2]

    if bbox is None:
        bbox = (0.0, 0.0, float(width), float(height))

    image_size = cfg.MODEL.IMAGE_SIZE  # [width, height], 예: [288, 384]
    aspect_ratio = image_size[0] / image_size[1]
    center, scale = _xywh2cs(*bbox, aspect_ratio=aspect_ratio)

    trans = get_affine_transform(center, scale, 0, image_size)
    warped = cv2.warpAffine(
        image, trans, (int(image_size[0]), int(image_size[1])), flags=cv2.INTER_LINEAR
    )

    normalize = transforms.Normalize(mean=_NORMALIZE_MEAN, std=_NORMALIZE_STD)
    input_tensor = transforms.Compose([transforms.ToTensor(), normalize])(warped)
    input_tensor = input_tensor.unsqueeze(0).to(device)

    inference_started = time.perf_counter()
    with torch.no_grad():
        output = model(input_tensor)
    if device == "cuda":
        torch.cuda.synchronize()
    inference_ms = (time.perf_counter() - inference_started) * 1000

    heatmaps = output.detach().cpu().numpy()
    coords, maxvals = get_final_preds(cfg, heatmaps, np.expand_dims(center, 0), np.expand_dims(scale, 0))
    original_coords = transform_preds(coords[0], center, scale, cfg.MODEL.HEATMAP_SIZE)

    landmarks = [
        (float(original_coords[i, 0]), float(original_coords[i, 1]), float(maxvals[0, i, 0]))
        for i in range(original_coords.shape[0])
    ]

    result = {
        "landmarks": landmarks,
        "load_ms": round(load_ms, 1),
        "inference_ms": round(inference_ms, 1),
        "device": device,
    }
    if device == "cuda":
        result["peak_vram_mb"] = round(torch.cuda.max_memory_allocated() / (1024 * 1024), 1)
    return result


def _draw_and_save(image_path: str, landmarks: list, confidence_threshold: float, out_path: str) -> None:
    image = cv2.imread(image_path, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    for x, y, conf in landmarks:
        if conf < confidence_threshold:
            continue
        cv2.circle(image, (int(x), int(y)), 5, (0, 0, 255), -1)
        cv2.putText(
            image, f"{conf:.2f}", (int(x) + 6, int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1
        )
    cv2.imwrite(out_path, image)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="테스트할 옷 사진 경로")
    parser.add_argument("--checkpoint", default=_DEFAULT_CHECKPOINT)
    parser.add_argument("--confidence", type=float, default=0.3, help="이 이상만 출력/표시")
    parser.add_argument("--top", type=int, default=20, help="신뢰도 상위 몇 개까지 출력할지")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("X", "Y", "W", "H"), default=None)
    parser.add_argument("--out", default="result_landmarks.png")
    args = parser.parse_args()

    bbox = tuple(args.bbox) if args.bbox else None
    result = run_inference(args.image, args.checkpoint, bbox=bbox)

    print(f"device={result['device']}  load={result['load_ms']}ms  inference={result['inference_ms']}ms")
    if "peak_vram_mb" in result:
        print(f"peak_vram={result['peak_vram_mb']}MB")

    ranked = sorted(result["landmarks"], key=lambda lm: lm[2], reverse=True)
    above_threshold = [lm for lm in ranked if lm[2] >= args.confidence]
    print(f"신뢰도 {args.confidence} 이상: {len(above_threshold)}/294개")
    print(f"상위 {args.top}개 (index는 정렬 후 순번이라 원본 조인트 번호가 아님에 주의):")
    for x, y, conf in ranked[: args.top]:
        print(f"  ({x:7.1f}, {y:7.1f})  confidence={conf:.3f}")

    _draw_and_save(args.image, result["landmarks"], args.confidence, args.out)
    print(f"시각화 저장: {args.out}")


if __name__ == "__main__":
    main()
