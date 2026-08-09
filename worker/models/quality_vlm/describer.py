"""VLM 하자 설명 오케스트레이션 — crop → 프롬프트 → 생성 → 부위 합성.

`worker/models/sam3/segmenter.py`의 `DefectSegmenter(ABC)` + `build_segmenter()` 패턴을
그대로 따른다 — 여기가 VLM 모델 교체의 유일한 지점이다.

`sam3.contracts`/`sam3.prompts`/`sam3.segmenter`를 직접 import한다 — 두 패키지가
`worker/models/` sys.path 아래 형제 패키지로 함께 로드되는 건 이 워커에서 이미 정상적인
구조다(`quality_check_worker_example.py`도 `sam3.contracts`를 직접 쓴다).

설계: `.claude/plans/ai/CH011-quality-vlm-production-wiring.md`
"""

from __future__ import annotations

import dataclasses
import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence

from PIL import Image
from sam3.contracts import Finding
from sam3.segmenter import SegmentationResult

from . import registry
from .prompts import build_defect_prompt

logger = logging.getLogger(__name__)

# AI/validation/QUAL/vlm-description-check/vlm_description_check.ipynb에서 확인된 값 —
# 크롭이 너무 작으면(1차 스모크 테스트 14~46px) VLM 출력이 입력 라벨을 그대로 재진술하는
# 수준에 그친다는 게 실측으로 확인됐다.
_CROP_PAD_RATIO = 0.6
_MIN_CROP_SIZE = 160


class DescriberNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치 등)."""


class DefectDescriber(ABC):
    """크롭 이미지 + Finding -> 한 줄 설명. **여기가 VLM 모델 교체 경계다.**"""

    @abstractmethod
    def describe(self, image: Image.Image, finding: Finding) -> str:
        raise NotImplementedError


class MockDescriber(DefectDescriber):
    """정적 문구로 채운다(torch 불필요). CI/기본 경로."""

    def describe(self, image: Image.Image, finding: Finding) -> str:
        return f"{finding.label} 발견"


class Qwen3VlDescriber(DefectDescriber):
    """Qwen3-VL 계열 백엔드. torch/transformers/bitsandbytes는 지연 import."""

    def __init__(self, model_id: str, config: registry.VlmConfig) -> None:
        self._model_id = model_id
        self._config = config
        self._bundle = None

    def _ensure_loaded(self) -> None:
        """모델을 지연 로드한다(프로세스당 1회). 라이브러리가 없으면 `DescriberNotReady`."""
        if self._bundle is not None:
            return
        from .loader import load_qwen_vl

        try:
            self._bundle = load_qwen_vl(self._model_id, quantization=self._config["quantization"])
        except ImportError as exc:
            raise DescriberNotReady(
                "qwen3_vl 백엔드에는 torch/transformers/bitsandbytes가 필요합니다 "
                "(worker/models/quality_vlm/requirements.txt 참고)"
            ) from exc
        except Exception as exc:
            raise DescriberNotReady(f"VLM 모델을 불러오지 못했습니다: {exc}") from exc
        logger.info("Qwen3-VL 로드 완료 (model=%s)", self._model_id)

    def describe(self, image: Image.Image, finding: Finding) -> str:
        from .loader import generate_from_image

        self._ensure_loaded()
        label = finding.label or finding.defect_type.value
        prompt_text = build_defect_prompt(label)
        return generate_from_image(
            self._bundle, image, prompt_text, self._config["max_new_tokens"]
        )


def build_describer(key: str | None = None) -> DefectDescriber:
    """레지스트리 키에 맞는 describer를 만든다. **여기가 유일한 VLM 모델 스왑 지점이다.**

    워커는 `QUALITY_VLM_BACKEND` 환경변수로 이 키를 넘긴다.
    """
    resolved = key or registry.ACTIVE_VLM_BACKEND
    if resolved == "mock":
        return MockDescriber()
    if resolved == "qwen3_vl":
        config = registry.vlm_config(resolved)
        return Qwen3VlDescriber(model_id=config["model_id"], config=config)
    raise DescriberNotReady(f"아직 구현되지 않은 VLM 백엔드입니다: {resolved!r}")


def _expand_bbox_to_min_size(
    bbox_px: tuple[float, float, float, float],
    pad_ratio: float,
    min_size: float,
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """bbox에 여백을 주고, 결과가 min_size보다 작으면 중심 기준으로 더 넓힌다(경계는 clamp).

    image_size = (width, height). `vlm_description_check.ipynb`에서 검증된 로직과 동일하다.
    """
    x1, y1, x2, y2 = bbox_px
    img_w, img_h = image_size
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    half_w = max((x2 - x1) * (1 + pad_ratio) / 2, min_size / 2)
    half_h = max((y2 - y1) * (1 + pad_ratio) / 2, min_size / 2)
    return (
        max(0, int(cx - half_w)),
        max(0, int(cy - half_h)),
        min(img_w, int(cx + half_w)),
        min(img_h, int(cy + half_h)),
    )


def _crop_finding(base_image: Image.Image, finding: Finding, size: tuple[int, int]) -> Image.Image:
    """finding.bbox(정규화 xyxy)를 절대 픽셀로 되돌려 크롭한다. size = (height, width)."""
    height, width = size
    x1, y1, x2, y2 = finding.bbox
    bbox_px = (x1 * width, y1 * height, x2 * width, y2 * height)
    crop_box = _expand_bbox_to_min_size(bbox_px, _CROP_PAD_RATIO, _MIN_CROP_SIZE, (width, height))
    return base_image.crop(crop_box)


def attach_descriptions(
    results: Sequence[SegmentationResult],
    findings: Sequence[Finding],
    describer: DefectDescriber,
) -> list[Finding]:
    """DETECTED/SUSPECTED finding 전부에 crop + VLM 설명을 채운 새 리스트를 반환한다.

    `Finding`은 frozen dataclass라 `dataclasses.replace()`로 새 인스턴스를 만든다 — 원본
    리스트는 바뀌지 않는다.

    hotfix/472: 원래는 SUSPECTED를 건너뛰었다(호출 수를 줄이기 위한 v1 범위 제한, CH011
    계획 참고) — SUSPECTED도 설명이 나와야 한다는 요청으로 이 제한을 없앤다. finding 수만큼
    VLM을 순차 호출하는 구조라 SUSPECTED가 많은 이미지는 레이턴시가 그만큼 늘어난다.

    **개별 실패는 그 finding만 `description=None`으로 남기고 계속 진행한다** —
    `inspection_logger`의 "best-effort, 응답을 막지 않는다" 원칙과 동일하다. 설명 하나
    실패했다고 검수 결과 전체를 잃으면 안 된다.
    """
    by_image = {r.image_index: r for r in results}
    out: list[Finding] = []
    for finding in findings:
        result = by_image.get(finding.image_index)
        if result is None:
            out.append(finding)
            continue
        try:
            crop = _crop_finding(result.base_image, finding, result.size)
            description = describer.describe(crop, finding)
            out.append(dataclasses.replace(finding, description=description))
        except Exception as exc:
            logger.warning("하자 설명 생성 실패(key=%s): %s", finding.key, exc)
            out.append(finding)
    return out
