"""색상(주색상/보조색상) 추출 — 모델 교체 경계.

`classifier.py`와 같은 ABC+팩토리 패턴. 결과 데이터 모양(`ColorFieldPrediction`)은
`contracts.py`에 있다 — 게이트웨이 스키마와 대조되는 계약 사본이다. 원래 설계안(경량
마스크+k-means+팔레트 스냅)은 `AI/validation/CLASS/product-info-check/REPORT.md` §V3
실측에서 **0% 정확도로 완전히 실패**했다(배경 오염, 클로즈업 마스크 붕괴) — 그래서 여기
실백엔드를 아직 안 넣었다. "CLIP 임베딩+분류 헤드" 등 대체 방식이 검증 중이며 결정되지
않았다(2026-08-02).

설계: `.claude/plans/ai/CH012-~2.MD`
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image

from . import registry
from .contracts import ColorCandidate, ColorFieldPrediction
from .thresholds import COLOR_THRESHOLDS, resolve_action


class ColorExtractorNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치 등)."""


# 색상 팔레트(코드 -> hex). **13종 + MIXED로 사용자가 확정했다(2026-08-03)** — 이전 19종에서
# IVORY·KHAKI·SKYBLUE·WINE·SILVER·GOLD를 뺐다. 선정 근거와 은퇴 코드 매핑은
# `AI/validation/CLASS/product-info-check/color.py`의 주석 참고 — 두 파일은 항상 같은 값을
# 쓴다(한쪽만 고치면 워커와 검증 스파이크의 라벨 집합이 갈린다).
PALETTE: dict[str, str] = {
    "BLACK": "#1A1A1A",
    "WHITE": "#FFFFFF",
    "GRAY": "#9B9B9B",
    "RED": "#C43D3D",
    "ORANGE": "#E08A2E",
    "PINK": "#E6A9C0",
    "YELLOW": "#E8D44D",
    "BROWN": "#7B5B3A",
    "GREEN": "#4F7942",
    "BLUE": "#3B6FB6",
    "PURPLE": "#7D5BA6",
    "BEIGE": "#D8C7A8",
    "NAVY": "#22304A",
}
MIXED_LABEL = "MIXED"  # 팔레트 색 하나로 스냅하기 어려운 패턴/멀티컬러용 특수 라벨


@dataclass
class ColorPrediction:
    """주색상/보조색상 쌍 — extract()의 반환 타입. BE JSON에는 각 필드가 독립적으로
    실리므로(fields.color_primary/color_secondary) 이 쌍 자체는 계약 대상이 아니다."""

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
