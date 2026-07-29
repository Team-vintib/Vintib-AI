"""기준 물체(A4 용지) 검출 — 1단계.

`ReferenceDetector` 구현체만 갈아끼우면 downstream(원단 분할·랜드마크 검출·cm 환산)과 API
계약은 그대로 유지된다. 활성 구현은 `registry.ACTIVE_REFERENCE_BACKEND` 키 하나로 결정된다.

Phase 2에서 `opencv_contour`(OpenCV 컨투어 + A4 종횡비 필터, `registry.A4_ASPECT_RATIO`)가
이 자리에 들어간다 — 사용자가 이미 "전통 CV로 충분"이라 결론 내려서 별도 PoC 없이 바로 구현
예정.

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from . import registry
from .scenarios import get_scenario


@dataclass(frozen=True)
class ReferenceDetection:
    """기준 물체 검출 결과. `pixel_to_cm_ratio`는 못 찾았으면 `None`이다."""

    found: bool
    pixel_to_cm_ratio: float | None


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


def build_reference_detector(key: str | None = None) -> ReferenceDetector:
    """레지스트리 키에 맞는 기준 물체 검출기를 만든다. **여기가 유일한 스왑 지점이다.**"""
    resolved = key or registry.ACTIVE_REFERENCE_BACKEND
    registry.reference_backend_config(resolved)  # 미등록 키면 여기서 즉시 실패
    if resolved == "mock":
        return MockReferenceDetector()
    raise NotImplementedError(f"아직 구현되지 않은 기준 물체 검출 백엔드입니다: {resolved!r}")
