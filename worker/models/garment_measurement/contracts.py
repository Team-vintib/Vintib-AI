"""의류 실측(cm) 측정 job result 계약 — 워커 쪽 사본.

**`AI/app/measurement/schemas.py`와 짝을 이루는 복제본이다.** 워커는 게이트웨이와 배포 단위가
달라서(팀원 노트북에서 git clone으로 실행, 도커 이미지에 안 들어감) `AI/` 코드를 import할 수
없다. 그래서 계약만 여기 다시 정의한다.

**pydantic을 쓰지 않는다.** 워커 의존성을 가볍게 유지하려는 것이다. 대신 `to_dict()`로 job
result에 실을 순수 dict를 만든다 — 검증은 요청 시점에 게이트웨이(`app/measurement/schemas.py`)가
이미 한다.

⚠️ **양쪽이 어긋나면 BE가 받는 JSON이 조용히 달라진다.** enum 값이 일치하는지는
`AI/test/measurement/test_measurement_contract.py`가 이 파일을 직접 읽어 검사한다 — 필드를
바꿀 때는 반드시 양쪽을 함께 고칠 것.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class ReferenceObjectType(str, Enum):
    a4_paper = "A4_PAPER"


class GarmentCategory(str, Enum):
    """DeepFashion2 13개 카테고리 중 실사진으로 검증된 3개만. 나머지는 검증 전까지 범위 밖."""

    short_sleeve_top = "SHORT_SLEEVE_TOP"
    trousers = "TROUSERS"
    long_sleeve_dress = "LONG_SLEEVE_DRESS"


class LandmarkType(str, Enum):
    # 상의/원피스 공통
    shoulder_left = "SHOULDER_LEFT"
    shoulder_right = "SHOULDER_RIGHT"
    sleeve_end_left = "SLEEVE_END_LEFT"
    sleeve_end_right = "SLEEVE_END_RIGHT"
    neckline_center = "NECKLINE_CENTER"
    hem_left = "HEM_LEFT"
    hem_center = "HEM_CENTER"
    hem_right = "HEM_RIGHT"

    # 하의(바지) 전용
    waist_left = "WAIST_LEFT"
    waist_center = "WAIST_CENTER"
    waist_right = "WAIST_RIGHT"
    hip_left = "HIP_LEFT"
    hip_right = "HIP_RIGHT"
    crotch = "CROTCH"
    hem_left_outer = "HEM_LEFT_OUTER"
    hem_left_inner = "HEM_LEFT_INNER"
    hem_right_outer = "HEM_RIGHT_OUTER"
    hem_right_inner = "HEM_RIGHT_INNER"


class MeasurementType(str, Enum):
    shoulder_width = "SHOULDER_WIDTH"
    sleeve_length = "SLEEVE_LENGTH"
    total_length = "TOTAL_LENGTH"
    hem_width = "HEM_WIDTH"

    waist_width = "WAIST_WIDTH"
    inseam_length = "INSEAM_LENGTH"
    outseam_length = "OUTSEAM_LENGTH"
    leg_opening_width = "LEG_OPENING_WIDTH"


class RetakeReason(str, Enum):
    reference_not_found = "REFERENCE_NOT_FOUND"
    garment_not_found = "GARMENT_NOT_FOUND"
    garment_not_flat = "GARMENT_NOT_FLAT"
    low_landmark_confidence = "LOW_LANDMARK_CONFIDENCE"


def _plain(value):
    """enum은 값으로, 나머지는 그대로 — JSON 직렬화 가능한 형태로 편다."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    return value


@dataclass(frozen=True)
class Landmark:
    """랜드마크 1개. 필드 의미는 `AI/app/measurement/schemas.py`의 동명 모델과 같다."""

    type: LandmarkType
    pixel_x: float
    pixel_y: float
    confidence: float

    def to_dict(self) -> dict:
        return {key: _plain(value) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class Measurement:
    type: MeasurementType
    value_cm: float
    confidence: float

    def to_dict(self) -> dict:
        return {key: _plain(value) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class ModelInfo:
    reference_backend: str
    segmentation_backend: str
    landmark_backend: str

    def to_dict(self) -> dict:
        return {key: _plain(value) for key, value in asdict(self).items()}
