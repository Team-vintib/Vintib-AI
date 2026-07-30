"""의류 랜드마크 검출 — 3단계. 이 파이프라인에서 가장 무겁고 불확실한 단계다.

`LandmarkDetector` 구현체만 갈아끼우면 downstream(cm 환산)과 API 계약은 그대로 유지된다.
활성 구현은 `registry.ACTIVE_LANDMARK_BACKEND` 키 하나로 결정된다.

`hrnet_deepfashion2`: DeepFashion2 사전학습 HRNet(`svip-lab/HRNet-for-Fashion-Landmark-
Estimation.PyTorch`). `AI/validation/garment-landmark-check/`에서 실제 사진 + 공식 랜드마크
정의도로 눈으로 대조 검증한 뒤에 여기로 승격했다(CatVTON/CLIPSeg와 같은 "PoC 먼저" 원칙) —
그 PoC의 `verify_hrnet_landmarks.py`와 추론 로직은 동일하고, 이 파일은 `registry`의 카테고리별
매핑(`DF2_CATEGORY_RANGES`/`DF2_LANDMARK_MAPPING`)을 적용해 294개 원시 출력을 `LandmarkType`이
붙은 목록으로 바꾸는 부분만 다르다.

**모델 코드 자체(`hrnet/`)는 이 저장소 안에 다시 두지 않고 복제한다** — validation/과 worker/는
배포 단위가 달라서(validation/은 프로덕션에서 import 안 함) 필요한 최소 파일만
`worker/models/garment_measurement/hrnet/`에 복사해 뒀다(pose_hrnet.py/inference.py/
transforms.py/config, 전부 원본 저장소 그대로 — 학습·평가·NMS 등 추론에 안 쓰는 코드는 안 가져왔다).

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from types import SimpleNamespace

from . import registry
from .contracts import GarmentCategory, Landmark, LandmarkType
from .scenarios import get_scenario

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_HRNET_DIR = os.path.join(_THIS_DIR, "hrnet")
_DEFAULT_CFG_PATH = os.path.join(_HRNET_DIR, "w48_384x288_adam_lr1e-3.yaml")
_DEFAULT_CHECKPOINT_PATH = os.path.join(
    _HRNET_DIR, "models", "pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth"
)

# lib/dataset/coco.py의 _xywh2cs와 동일한 상수(pixel_std=200, margin=1.25) — PoC 스크립트에서
# 그대로 가져온 값. `AI/validation/garment-landmark-check/verify_hrnet_landmarks.py` 참고.
_PIXEL_STD = 200.0
_SCALE_MARGIN = 1.25
_NORMALIZE_MEAN = [0.485, 0.456, 0.406]
_NORMALIZE_STD = [0.229, 0.224, 0.225]


class LandmarkDetector(ABC):
    """이미지 한 장 → 랜드마크 목록. **여기가 유일한 모델 교체 경계다.**"""

    @abstractmethod
    def detect(
        self,
        image_url: str,
        product_id: int,
        category: GarmentCategory,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[Landmark]:
        """`bbox`는 (x, y, w, h), 원본 이미지 픽셀 좌표 — 원단 분할 단계가 찾은 옷 영역.
        `None`이면 이미지 전체를 옷 영역으로 본다."""
        raise NotImplementedError


class MockLandmarkDetector(LandmarkDetector):
    """목업 시나리오로 결정적 좌표를 돌려준다(torch 불필요)."""

    def detect(
        self,
        image_url: str,
        product_id: int,
        category: GarmentCategory,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[Landmark]:
        scenario = get_scenario(product_id)
        return [
            Landmark(
                type=LandmarkType(type_name),
                pixel_x=point["x"],
                pixel_y=point["y"],
                confidence=point["confidence"],
            )
            for type_name, point in scenario.get("landmarks", {}).items()
        ]


class LandmarkDetectorNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치·체크포인트 없음) → job 실패."""


class HRNetLandmarkDetector(LandmarkDetector):
    """DeepFashion2 사전학습 HRNet으로 실제 랜드마크를 검출한다.

    모델·설정은 워커 프로세스당 한 번만 로드한다(`_ensure_loaded()`). 체크포인트 파일은
    OneDrive에서 수동으로 받아야 해서(HuggingFace 미배포) `HRNET_CHECKPOINT_PATH` 환경변수로
    위치를 지정한다 — 기본값은 `hrnet/models/` 아래(README 참고).
    """

    def __init__(self, checkpoint_path: str | None = None) -> None:
        self._checkpoint_path = checkpoint_path or os.getenv(
            "HRNET_CHECKPOINT_PATH", _DEFAULT_CHECKPOINT_PATH
        )
        self._cfg = None
        self._model = None
        self._device = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return

        if not os.path.isfile(self._checkpoint_path):
            raise LandmarkDetectorNotReady(
                f"HRNet 체크포인트를 찾을 수 없습니다: {self._checkpoint_path} "
                "(OneDrive에서 pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth를 받아 "
                "이 경로에 두거나 HRNET_CHECKPOINT_PATH를 지정하세요 — worker/README.md 참고)"
            )

        try:
            import torch

            from .hrnet.config import cfg, update_config
            from .hrnet.pose_hrnet import get_pose_net
        except ImportError as exc:
            raise LandmarkDetectorNotReady(
                "hrnet_deepfashion2 백엔드에는 torch/torchvision/yacs/opencv-python이 필요합니다"
            ) from exc

        args = SimpleNamespace(
            cfg=_DEFAULT_CFG_PATH,
            opts=["TEST.MODEL_FILE", self._checkpoint_path],
            modelDir="",
            logDir="",
            dataDir="",
        )
        update_config(cfg, args)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = get_pose_net(cfg, is_train=False)
        state_dict = torch.load(cfg.TEST.MODEL_FILE, map_location=device, weights_only=True)
        if any(k.startswith("module.") for k in state_dict):
            state_dict = {k.removeprefix("module."): v for k, v in state_dict.items()}
        model.load_state_dict(state_dict)
        model.to(device)
        model.eval()

        self._cfg = cfg
        self._model = model
        self._device = device

    def detect(
        self,
        image_url: str,
        product_id: int,
        category: GarmentCategory,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[Landmark]:
        self._ensure_loaded()

        try:
            offset, size = registry.DF2_CATEGORY_RANGES[category]
        except KeyError as exc:
            raise LandmarkDetectorNotReady(
                f"실사진으로 검증되지 않은 카테고리입니다: {category!r} "
                "(registry.DF2_CATEGORY_RANGES 참고)"
            ) from exc
        mapping = registry.DF2_LANDMARK_MAPPING[category]

        raw = self._run_model(image_url, bbox)
        landmarks: list[Landmark] = []
        for local_index_1based, landmark_type in mapping.items():
            x, y, confidence = raw[offset + local_index_1based - 1]
            landmarks.append(
                Landmark(type=landmark_type, pixel_x=x, pixel_y=y, confidence=confidence)
            )
        return landmarks

    def _run_model(
        self, image_url: str, bbox: tuple[float, float, float, float] | None
    ) -> list[tuple[float, float, float]]:
        """294개 전부에 대한 (x, y, confidence)를 원본 이미지 좌표로 돌려준다."""
        import cv2
        import numpy as np
        import torch
        import torchvision.transforms as transforms

        from .hrnet.inference import get_final_preds
        from .hrnet.transforms import get_affine_transform, transform_preds
        from .image_io import load_image

        # COLOR_RGB: false — 학습 때도 BGR 그대로 넣었으므로 RGB로 바꾸지 않는다(다른 단계와
        # 같은 방식으로 PIL 로더를 재사용하되, 여기서만 BGR로 되돌린다).
        image = load_image(image_url)
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        height, width = frame.shape[:2]

        if bbox is None:
            bbox = (0.0, 0.0, float(width), float(height))

        image_size = self._cfg.MODEL.IMAGE_SIZE  # [width, height]
        aspect_ratio = image_size[0] / image_size[1]
        center, scale = _xywh2cs(*bbox, aspect_ratio=aspect_ratio)

        trans = get_affine_transform(center, scale, 0, image_size)
        warped = cv2.warpAffine(
            frame, trans, (int(image_size[0]), int(image_size[1])), flags=cv2.INTER_LINEAR
        )

        normalize = transforms.Normalize(mean=_NORMALIZE_MEAN, std=_NORMALIZE_STD)
        input_tensor = transforms.Compose([transforms.ToTensor(), normalize])(warped)
        input_tensor = input_tensor.unsqueeze(0).to(self._device)

        with torch.no_grad():
            output = self._model(input_tensor)

        heatmaps = output.detach().cpu().numpy()
        coords, maxvals = get_final_preds(
            self._cfg, heatmaps, np.expand_dims(center, 0), np.expand_dims(scale, 0)
        )
        original_coords = transform_preds(coords[0], center, scale, self._cfg.MODEL.HEATMAP_SIZE)

        return [
            (float(original_coords[i, 0]), float(original_coords[i, 1]), float(maxvals[0, i, 0]))
            for i in range(original_coords.shape[0])
        ]


def _xywh2cs(x: float, y: float, w: float, h: float, aspect_ratio: float):
    """`lib/dataset/coco.py`의 `_xywh2cs`와 동일한 로직 — bbox를 (center, scale)로 바꾼다."""
    import numpy as np

    center = np.array([x + w * 0.5, y + h * 0.5], dtype=np.float32)
    if w > aspect_ratio * h:
        h = w / aspect_ratio
    elif w < aspect_ratio * h:
        w = h * aspect_ratio
    scale = np.array([w / _PIXEL_STD, h / _PIXEL_STD], dtype=np.float32) * _SCALE_MARGIN
    return center, scale


def build_landmark_detector(key: str | None = None) -> LandmarkDetector:
    """레지스트리 키에 맞는 랜드마크 검출기를 만든다. **여기가 유일한 스왑 지점이다.**"""
    resolved = key or registry.ACTIVE_LANDMARK_BACKEND
    registry.landmark_backend_config(resolved)
    if resolved == "mock":
        return MockLandmarkDetector()
    if resolved == "hrnet_deepfashion2":
        return HRNetLandmarkDetector()
    raise NotImplementedError(f"아직 구현되지 않은 랜드마크 검출 백엔드입니다: {resolved!r}")
