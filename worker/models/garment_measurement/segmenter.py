"""원단 분할(배경 제거) — 2단계.

`GarmentSegmenter` 구현체만 갈아끼우면 downstream(랜드마크 검출·cm 환산)과 API 계약은 그대로
유지된다. 활성 구현은 `registry.ACTIVE_SEGMENTATION_BACKEND` 키 하나로 결정된다.

Phase 3에서 `grabcut`(1차, 촬영 배경이 단색 매트/책상이라고 가정)이 이 자리에 들어간다.
GrabCut이 실측으로 부족하다고 확인되면(패턴 매트·그림자 등) `yolo_seg`(DressCode 파인튜닝) 비교
스파이크를 `AI/validation/garment-measurement-check/`에 따로 연다 — 지금은 자리만 남겨둔다.

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from . import registry
from .scenarios import get_scenario


@dataclass(frozen=True)
class SegmentationResult:
    """원단 분할 결과. v1은 "찾았는지" 여부만 쓴다 — 마스크 자체는 랜드마크 검출 단계가
    이미지에서 직접 다시 찾으므로 여기서 넘길 필요가 없다."""

    found: bool


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


def build_segmenter(key: str | None = None) -> GarmentSegmenter:
    """레지스트리 키에 맞는 원단 분할기를 만든다. **여기가 유일한 스왑 지점이다.**"""
    resolved = key or registry.ACTIVE_SEGMENTATION_BACKEND
    registry.segmentation_backend_config(resolved)
    if resolved == "mock":
        return MockGarmentSegmenter()
    raise NotImplementedError(f"아직 구현되지 않은 원단 분할 백엔드입니다: {resolved!r}")
