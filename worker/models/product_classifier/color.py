"""색상(주색상/보조색상) 추출 — 모델 교체 경계.

`classifier.py`와 같은 ABC+팩토리 패턴. 원래 설계안(경량 마스크+k-means+팔레트 스냅)은
`AI/validation/CLASS/product-info-check/REPORT.md` §V3 실측에서 **0% 정확도로 완전히
실패**했다(배경 오염, 클로즈업 마스크 붕괴) — 그래서 여기 실백엔드를 아직 안 넣었다. "CLIP
임베딩+분류 헤드" 등 대체 방식이 검증 중이며 결정되지 않았다(2026-08-02).

설계: `.claude/plans/ai/CH012-~2.MD`
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from PIL import Image

from . import registry
from .thresholds import COLOR_THRESHOLDS, Action, resolve_action


class ColorExtractorNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치 등)."""


# 잠정 색상 팔레트(코드 -> hex). BE/FE 확정 전 placeholder — CH012 §12 "색상 팔레트 정의
# 주체" 미결정 사항 참고. `AI/validation/CLASS/product-info-check/color.py`와 동일한 값을
# 쓴다. FE가 실제 팔레트를 확정하면 이 dict만 갱신하면 된다.
PALETTE: dict[str, str] = {
    "BLACK": "#1A1A1A",
    "WHITE": "#FFFFFF",
    "GRAY": "#9B9B9B",
    "IVORY": "#F1EEE3",
    "BEIGE": "#D8C7A8",
    "BROWN": "#7B5B3A",
    "KHAKI": "#8C8560",
    "NAVY": "#22304A",
    "BLUE": "#3B6FB6",
    "SKYBLUE": "#8FC1E3",
    "GREEN": "#4F7942",
    "YELLOW": "#E8D44D",
    "ORANGE": "#E08A2E",
    "RED": "#C43D3D",
    "PINK": "#E6A9C0",
    "PURPLE": "#7D5BA6",
    "WINE": "#6E2A3A",
    "SILVER": "#C7C9CC",
    "GOLD": "#C9A646",
}
MULTI_LABEL = "MULTI"  # 팔레트 색 하나로 스냅하기 어려운 패턴/멀티컬러용 특수 라벨


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


@dataclass
class ColorPrediction:
    primary: ColorFieldPrediction
    secondary: ColorFieldPrediction | None


class ColorExtractor(ABC):
    """이미지 1장 -> 주색상/보조색상 예측. **여기가 색상 모델 교체 경계다.**"""

    @abstractmethod
    def extract(self, image: Image.Image) -> ColorPrediction:
        raise NotImplementedError


class MockColorExtractor(ColorExtractor):
    """정적 결과로 채운다(의존성 없음). CI/기본 경로.

    항상 팔레트의 첫 항목을 score=0.0으로 반환하고 보조색상은 None이다 —
    `classifier.py`의 `MockCategoryClassifier`와 같은 이유(score=0.0 -> action은 항상
    "none", mock 결과가 실수로 자동 채움되지 않는다).
    """

    def extract(self, image: Image.Image) -> ColorPrediction:
        code = next(iter(PALETTE))
        primary = ColorFieldPrediction(
            code=code,
            hex=PALETTE[code],
            score=0.0,
            action=resolve_action(0.0, COLOR_THRESHOLDS),
            candidates=[ColorCandidate(code=code, score=0.0)],
        )
        return ColorPrediction(primary=primary, secondary=None)


def build_color_extractor(key: str | None = None) -> ColorExtractor:
    """레지스트리 키에 맞는 추출기를 만든다. **여기가 유일한 색상 모델 스왑 지점이다.**

    워커는 `PRODUCT_CLASSIFIER_COLOR_BACKEND` 환경변수로 이 키를 넘긴다.
    """
    resolved = key or registry.ACTIVE_COLOR_BACKEND
    if resolved == "mock":
        return MockColorExtractor()
    raise ColorExtractorNotReady(f"아직 구현되지 않은 색상 백엔드입니다: {resolved!r}")
