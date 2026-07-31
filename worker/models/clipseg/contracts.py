"""품질 검수 job result 계약 — 워커 쪽 사본.

**`AI/app/quality/schemas.py`와 짝을 이루는 복제본이다.** 워커는 게이트웨이와 배포 단위가
달라서(팀원 노트북에서 git clone으로 실행, 도커 이미지에 안 들어감) `AI/` 코드를 import할 수
없다. 그래서 계약만 여기 다시 정의한다.

**pydantic을 쓰지 않는다.** 워커 의존성을 가볍게 유지하려는 것이다(`requests`·`Pillow`·`numpy`
만으로 돈다). 대신 `to_dict()`로 job result에 실을 순수 dict를 만든다 — 검증은 요청 시점에
게이트웨이(`app/quality/schemas.py`)가 이미 한다.

⚠️ **양쪽이 어긋나면 BE가 받는 JSON이 조용히 달라진다.** enum 값이 일치하는지는
`AI/test/quality/test_quality_contract.py`가 이 파일을 직접 읽어 검사한다 — 필드를 바꿀 때는
반드시 양쪽을 함께 고칠 것.
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
    # CH007(넘버링 bbox 이미지 + 불릿 리스트) 필드. 이 워커(clipseg)는 아직 채우지 않는다 —
    # test_quality_contract.py의 필드 이름 드리프트 가드를 맞추기 위해 이름만 동기화한다.
    no: int | None = None
    label: str | None = None
    description: str | None = None

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


@dataclass(frozen=True)
class AnnotatedImage:
    """숫자만 넘버링된 bbox 오버레이 PNG. 이 워커(clipseg)는 아직 생성하지 않는다(CH007 범위 밖)."""

    image_index: int
    url: str

    def to_dict(self) -> dict:
        return {key: _plain(value) for key, value in asdict(self).items()}
