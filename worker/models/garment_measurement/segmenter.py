"""원단 분할(배경 제거) — 2단계.

`GarmentSegmenter` 구현체만 갈아끼우면 downstream(랜드마크 검출·cm 환산)과 API 계약은 그대로
유지된다. 활성 구현은 `registry.ACTIVE_SEGMENTATION_BACKEND` 키 하나로 결정된다.

`grabcut`: OpenCV GrabCut. 촬영 배경이 단색 매트/책상이고 옷이 프레임 중앙 대부분을 차지한다고
가정해, 중앙을 크게 남긴 사각형을 전경 후보로 GrabCut에 넘긴다. 이 가정이 실측으로 부족하다고
확인되면(패턴 매트·그림자 등) `yolo_seg`(DressCode 파인튜닝) 비교 스파이크를
`AI/validation/garment-measurement-check/`에 따로 연다 — 지금은 자리만 남겨둔다.

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from . import registry
from .image_io import load_image
from .scenarios import get_scenario

# GrabCut 반복 횟수. 늘리면 정확도가 조금 오르지만 처리 시간도 늘어난다 — 첫 버전 상수.
_GRABCUT_ITERATIONS = 5

# 전경 후보 사각형을 이미지 테두리에서 얼마나 안쪽으로 잡을지(비율). 옷이 프레임 중앙 대부분을
# 차지한다는 촬영 가정에 근거한다 — 실제 샘플 사진으로 계속 보정해야 하는 값이다.
_INITIAL_RECT_MARGIN_RATIO = 0.08

# GrabCut 결과 전경 픽셀 비율이 이 미만이면 "원단을 못 찾음"으로 본다(노이즈/빈 프레임 방어).
_MIN_FOREGROUND_AREA_RATIO = 0.03


@dataclass(frozen=True)
class SegmentationResult:
    """원단 분할 결과. v1은 "찾았는지" 여부만 쓴다 — 마스크 자체는 랜드마크 검출 단계가
    이미지에서 직접 다시 찾으므로 여기서 넘길 필요가 없다."""

    found: bool


class GarmentSegmenterNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치) → job 실패."""


class GarmentSegmenter(ABC):
    """이미지 한 장 → 원단 분할 결과. **여기가 유일한 알고리즘 교체 경계다.**"""

    @abstractmethod
    def segment(self, image_url: str, product_id: int) -> SegmentationResult:
        raise NotImplementedError


class MockGarmentSegmenter(GarmentSegmenter):
    """목업 시나리오로 결정적 결과를 돌려준다(torch/opencv 불필요)."""

    def segment(self, image_url: str, product_id: int) -> SegmentationResult:
        scenario = get_scenario(product_id)
        return SegmentationResult(found=scenario["garment_found"])


class GrabCutGarmentSegmenter(GarmentSegmenter):
    """중앙 사각형을 전경 후보로 GrabCut을 돌려 원단 유무를 판단한다.

    실측 대상 픽셀 수를 세는 게 아니라 "원단이 있긴 한지"만 보는 v1이라, GrabCut의 전경 마스크
    면적이 최소 기준(`_MIN_FOREGROUND_AREA_RATIO`)을 넘는지로 판정한다.
    """

    def segment(self, image_url: str, product_id: int) -> SegmentationResult:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise GarmentSegmenterNotReady(
                "grabcut 백엔드에는 opencv-python-headless가 필요합니다"
            ) from exc

        image = load_image(image_url)
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        height, width = frame.shape[:2]

        margin_x = int(width * _INITIAL_RECT_MARGIN_RATIO)
        margin_y = int(height * _INITIAL_RECT_MARGIN_RATIO)
        initial_rect = (margin_x, margin_y, width - 2 * margin_x, height - 2 * margin_y)

        mask = np.zeros((height, width), dtype=np.uint8)
        background_model = np.zeros((1, 65), dtype=np.float64)
        foreground_model = np.zeros((1, 65), dtype=np.float64)

        cv2.grabCut(
            frame,
            mask,
            initial_rect,
            background_model,
            foreground_model,
            _GRABCUT_ITERATIONS,
            cv2.GC_INIT_WITH_RECT,
        )

        # GC_FGD(확정 전경)와 GC_PR_FGD(추정 전경) 둘 다 "원단"으로 센다.
        foreground = np.isin(mask, [cv2.GC_FGD, cv2.GC_PR_FGD])
        foreground_ratio = foreground.sum() / foreground.size

        # numpy.bool_은 JSON 직렬화도 안 되고 `is True/False` 비교도 파이썬 bool과 다르게
        # 동작한다 — 명시적으로 파이썬 bool로 바꾼다.
        return SegmentationResult(found=bool(foreground_ratio >= _MIN_FOREGROUND_AREA_RATIO))


def build_segmenter(key: str | None = None) -> GarmentSegmenter:
    """레지스트리 키에 맞는 원단 분할기를 만든다. **여기가 유일한 스왑 지점이다.**"""
    resolved = key or registry.ACTIVE_SEGMENTATION_BACKEND
    registry.segmentation_backend_config(resolved)
    if resolved == "mock":
        return MockGarmentSegmenter()
    if resolved == "grabcut":
        return GrabCutGarmentSegmenter()
    raise NotImplementedError(f"아직 구현되지 않은 원단 분할 백엔드입니다: {resolved!r}")
