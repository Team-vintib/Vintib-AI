"""의류 랜드마크 검출 — 3단계. 이 파이프라인에서 가장 무겁고 불확실한 단계다.

`LandmarkDetector` 구현체만 갈아끼우면 downstream(cm 환산)과 API 계약은 그대로 유지된다.
활성 구현은 `registry.ACTIVE_LANDMARK_BACKEND` 키 하나로 결정된다.

**`hrnet_deepfashion2`는 아직 구현하지 않는다.** CatVTON/CLIPSeg 선례와 같은 원칙 —
검증 안 된 무거운 모델을 바로 여기 박지 않는다. `AI/validation/garment-landmark-check/`에서
사전학습 체크포인트로 PoC(랜드마크 정확도, RTX 4050 6GB 추론 속도/VRAM)를 먼저 하고, 통과해야만
이 파일에 실제 구현이 들어간다.

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from . import registry
from .contracts import GarmentCategory, Landmark, LandmarkType
from .scenarios import get_scenario


class LandmarkDetector(ABC):
    """이미지 한 장 → 랜드마크 목록. **여기가 유일한 모델 교체 경계다.**"""

    @abstractmethod
    def detect(self, image_url: str, product_id: int, category: GarmentCategory) -> list[Landmark]:
        raise NotImplementedError


class MockLandmarkDetector(LandmarkDetector):
    """목업 시나리오로 결정적 좌표를 돌려준다(torch 불필요)."""

    def detect(self, image_url: str, product_id: int, category: GarmentCategory) -> list[Landmark]:
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


def build_landmark_detector(key: str | None = None) -> LandmarkDetector:
    """레지스트리 키에 맞는 랜드마크 검출기를 만든다. **여기가 유일한 스왑 지점이다.**"""
    resolved = key or registry.ACTIVE_LANDMARK_BACKEND
    registry.landmark_backend_config(resolved)
    if resolved == "mock":
        return MockLandmarkDetector()
    raise NotImplementedError(f"아직 구현되지 않은 랜드마크 검출 백엔드입니다: {resolved!r}")
