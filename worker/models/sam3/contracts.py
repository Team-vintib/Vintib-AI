"""품질 검수 job result 계약 — 워커 쪽 사본 (SAM3 백엔드용).

`worker/models/clipseg/contracts.py`와 **필드 단위로 동일한 사본**이다. BE에는 세그멘터가
CLIPSeg든 SAM3든 같은 모양의 JSON이 나가야 하므로, 두 백엔드가 독립 배포 단위(각자 conda
환경)로 나뉘어도 이 계약만은 어긋나면 안 된다 — `AI/test/quality/test_quality_contract.py`가
`AI/app/quality/schemas.py` 및 두 워커 사본 전부를 상호 대조한다.

**pydantic을 쓰지 않는다.** 워커 의존성을 가볍게 유지하려는 것이다. 대신 `to_dict()`로 job
result에 실을 순수 dict를 만든다 — 검증은 요청 시점에 게이트웨이가 이미 한다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class GarmentCategory(str, Enum):
    top_knit = "TOP_KNIT"
    top_shirt = "TOP_SHIRT"
    outer_jacket = "OUTER_JACKET"
    outer_coat = "OUTER_COAT"
    bottom_pants = "BOTTOM_PANTS"
    bottom_skirt = "BOTTOM_SKIRT"


class BaseColor(str, Enum):
    light = "LIGHT"
    dark = "DARK"
    patterned = "PATTERNED"


class DefectType(str, Enum):
    stain = "STAIN"
    dirt_mark = "DIRT_MARK"
    hole_tear = "HOLE_TEAR"
    discoloration = "DISCOLORATION"
    pilling = "PILLING"
    fray = "FRAY"


class FindingStatus(str, Enum):
    detected = "DETECTED"
    suspected = "SUSPECTED"


class Severity(str, Enum):
    minor = "MINOR"
    moderate = "MODERATE"
    major = "MAJOR"


class ConditionGrade(str, Enum):
    s = "S"
    a = "A"
    b = "B"
    c = "C"


class GarmentSection(str, Enum):
    # 상의·아웃터
    shoulder_left = "SHOULDER_LEFT"
    collar = "COLLAR"
    shoulder_right = "SHOULDER_RIGHT"
    sleeve_left = "SLEEVE_LEFT"
    chest_center = "CHEST_CENTER"
    sleeve_right = "SLEEVE_RIGHT"
    hem_left = "HEM_LEFT"
    hem_center = "HEM_CENTER"
    hem_right = "HEM_RIGHT"
    # 하의 (HEM_LEFT / HEM_RIGHT 는 위와 공유)
    waist_left = "WAIST_LEFT"
    waist_center = "WAIST_CENTER"
    waist_right = "WAIST_RIGHT"
    thigh_left = "THIGH_LEFT"
    crotch = "CROTCH"
    thigh_right = "THIGH_RIGHT"
    shin_center = "SHIN_CENTER"


def _plain(value):
    """enum은 값으로, 나머지는 그대로 — JSON 직렬화 가능한 형태로 편다."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    return value


@dataclass(frozen=True)
class Finding:
    """하자 항목 1건. 필드 의미는 `AI/app/quality/schemas.py`의 동명 모델과 같다."""

    key: str
    defect_type: DefectType
    status: FindingStatus
    image_index: int
    section_no: int
    section: GarmentSection
    confidence: float
    area_ratio: float
    bbox: tuple[float, float, float, float]
    severity: Severity
    matched_prompt: str
    statement_required: bool
    needs_seller_review: bool

    def to_dict(self) -> dict:
        return {key: _plain(value) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class SectionScore:
    section_no: int
    section: GarmentSection
    score: float

    def to_dict(self) -> dict:
        return {key: _plain(value) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class AttentionMap:
    image_index: int
    defect_type: DefectType
    url: str

    def to_dict(self) -> dict:
        return {key: _plain(value) for key, value in asdict(self).items()}
