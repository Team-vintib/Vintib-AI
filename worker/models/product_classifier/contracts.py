"""상품 정보 분류 job result 계약 — 워커 쪽 사본.

`AI/app/product_classifier/schemas.py`와 **필드 단위로 동일한 사본**이다. 워커는 게이트웨이와
배포 단위가 달라서(팀원 노트북에서 git clone으로 실행, 도커 이미지에 안 들어감) `AI/` 코드를
import할 수 없다 — `garment_measurement/contracts.py`·`sam3/contracts.py`와 같은 이유다.

**pydantic을 쓰지 않는다.** 워커 의존성을 가볍게 유지하려는 것이다. 대신 `to_dict()`로 job
result에 실을 순수 dict를 만든다 — 검증은 요청 시점에 게이트웨이가 이미 한다.

⚠️ **양쪽이 어긋나면 BE가 받는 JSON이 조용히 달라진다.** 필드가 일치하는지는
`AI/test/product_classifier/test_product_classifier_contract.py`가 이 파일을 직접 읽어
검사한다 — 필드를 바꿀 때는 반드시 양쪽을 함께 고칠 것.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .taxonomy import MajorCategory, Subcategory, category_path, major_of

Action = Literal["autofill", "suggest", "none"]


@dataclass
class CategoryCandidate:
    subcategory: Subcategory
    score: float


@dataclass
class CategoryPrediction:
    subcategory: Subcategory | None
    major: MajorCategory | None
    path: list[str]
    score: float
    action: Action
    candidates: list[CategoryCandidate] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "value": self.subcategory.value if self.subcategory else None,
            "path": self.path,
            "score": self.score,
            "action": self.action,
            "candidates": [
                {"value": c.subcategory.value, "score": c.score} for c in self.candidates
            ],
        }


@dataclass
class ColorCandidate:
    code: str
    score: float


@dataclass
class ColorFieldPrediction:
    code: str | None
    hex: str | None
    score: float
    action: Action
    candidates: list[ColorCandidate] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "value": self.code,
            "hex": self.hex,
            "score": self.score,
            "action": self.action,
            "candidates": [{"value": c.code, "score": c.score} for c in self.candidates],
        }


def build_category_prediction(
    subcategory: Subcategory, score: float, action: Action, candidates: list[CategoryCandidate]
) -> CategoryPrediction:
    """`classifier.py` 백엔드가 흔히 반복할 조립(major/path 유도)을 한곳에 모은다."""
    return CategoryPrediction(
        subcategory=subcategory,
        major=major_of(subcategory),
        path=category_path(subcategory),
        score=score,
        action=action,
        candidates=candidates,
    )
