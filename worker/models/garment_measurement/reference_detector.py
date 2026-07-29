"""기준 물체(A4 용지) 검출 — 1단계.

`ReferenceDetector` 구현체만 갈아끼우면 downstream(원단 분할·랜드마크 검출·cm 환산)과 API
계약은 그대로 유지된다. 활성 구현은 `registry.ACTIVE_REFERENCE_BACKEND` 키 하나로 결정된다.

`opencv_contour`: OpenCV 컨투어 검출 + A4 종횡비(`registry.A4_ASPECT_RATIO`, 1:sqrt(2)) 필터.
사용자가 이미 "전통 CV로 충분"이라 결론 내려서 별도 PoC 없이 바로 구현했다 — 실제 샘플 사진으로
`_ASPECT_TOLERANCE`를 계속 보정할 여지가 있는 첫 버전이다.

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from . import registry
from .image_io import load_image
from .scenarios import get_scenario

# A4 대비 종횡비 허용 오차(비율). 카메라 렌즈 왜곡·촬영 각도 오차를 흡수하려는 여유값 —
# 실제 샘플 사진으로 계속 보정해야 하는 첫 버전 상수다.
_ASPECT_TOLERANCE = 0.15

# Canny 엣지 검출 임계값. 배경(단색 매트/책상)과 흰 A4 용지의 대비가 크다는 전제로 잡은 값.
_CANNY_LOW = 50
_CANNY_HIGH = 150


@dataclass(frozen=True)
class ReferenceDetection:
    """기준 물체 검출 결과. `pixel_to_cm_ratio`는 못 찾았으면 `None`이다."""

    found: bool
    pixel_to_cm_ratio: float | None


class ReferenceDetectorNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치) → job 실패."""


class ReferenceDetector(ABC):
    """이미지 한 장 → 기준 물체 검출 결과. **여기가 유일한 알고리즘 교체 경계다.**"""

    @abstractmethod
    def detect(self, image_url: str, product_id: int) -> ReferenceDetection:
        raise NotImplementedError


class MockReferenceDetector(ReferenceDetector):
    """목업 시나리오로 결정적 결과를 돌려준다(torch/opencv 불필요)."""

    def detect(self, image_url: str, product_id: int) -> ReferenceDetection:
        scenario = get_scenario(product_id)
        found = scenario["reference_found"]
        return ReferenceDetection(
            found=found,
            pixel_to_cm_ratio=scenario.get("pixel_to_cm_ratio") if found else None,
        )


class OpenCVContourReferenceDetector(ReferenceDetector):
    """A4 용지를 컨투어 검출 + 종횡비 필터로 찾는다.

    그레이스케일 → 블러 → Canny 엣지 → 컨투어 검출 → 4각형으로 근사되는 컨투어 중 A4 비율에
    가장 가까운 것을 채택한다. 여러 개가 조건을 만족하면 가장 넓은 것을 고른다(원거리 배경
    잡음보다 실제로 촬영 대상인 A4가 화면에서 더 크게 나온다는 전제).
    """

    def __init__(self, aspect_tolerance: float = _ASPECT_TOLERANCE) -> None:
        self._aspect_tolerance = aspect_tolerance

    def detect(self, image_url: str, product_id: int) -> ReferenceDetection:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise ReferenceDetectorNotReady(
                "opencv_contour 백엔드에는 opencv-python-headless가 필요합니다"
            ) from exc

        image = load_image(image_url)
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.dilate(cv2.Canny(blurred, _CANNY_LOW, _CANNY_HIGH), None, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        best_sides: tuple[float, float] | None = None
        best_area = 0.0
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            if len(approx) != 4 or not cv2.isContourConvex(approx):
                continue

            (_, (w, h), _) = cv2.minAreaRect(approx)
            if w <= 0 or h <= 0:
                continue

            short_side, long_side = sorted((w, h))
            ratio = long_side / short_side
            deviation = abs(ratio - registry.A4_ASPECT_RATIO) / registry.A4_ASPECT_RATIO
            if deviation > self._aspect_tolerance:
                continue

            area = w * h
            if area > best_area:
                best_sides = (short_side, long_side)
                best_area = area

        if best_sides is None:
            return ReferenceDetection(found=False, pixel_to_cm_ratio=None)

        short_px, long_px = best_sides
        # 짧은 변/긴 변 각각으로 계산한 비율을 평균한다 — 촬영 각도가 완전히 수직이 아니면
        # 두 변의 오차가 서로 다른 방향일 수 있어서, 평균이 한쪽만 쓰는 것보다 안정적이다.
        ratio_from_short = (registry.A4_WIDTH_MM / 10.0) / short_px
        ratio_from_long = (registry.A4_HEIGHT_MM / 10.0) / long_px
        pixel_to_cm_ratio = (ratio_from_short + ratio_from_long) / 2.0
        return ReferenceDetection(found=True, pixel_to_cm_ratio=pixel_to_cm_ratio)


def build_reference_detector(key: str | None = None) -> ReferenceDetector:
    """레지스트리 키에 맞는 기준 물체 검출기를 만든다. **여기가 유일한 스왑 지점이다.**"""
    resolved = key or registry.ACTIVE_REFERENCE_BACKEND
    registry.reference_backend_config(resolved)  # 미등록 키면 여기서 즉시 실패
    if resolved == "mock":
        return MockReferenceDetector()
    if resolved == "opencv_contour":
        return OpenCVContourReferenceDetector()
    raise NotImplementedError(f"아직 구현되지 않은 기준 물체 검출 백엔드입니다: {resolved!r}")
