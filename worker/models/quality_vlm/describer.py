"""VLM 하자 설명 오케스트레이션 — 이미지 1장 + 번호별 힌트 -> 배치 설명 -> 파싱 합성.

`worker/models/sam3/segmenter.py`의 `DefectSegmenter(ABC)` + `build_segmenter()` 패턴을
그대로 따른다 — 여기가 VLM 모델 교체의 유일한 지점이다.

`sam3.contracts`/`sam3.prompts`/`sam3.segmenter`를 직접 import한다 — 두 패키지가
`worker/models/` sys.path 아래 형제 패키지로 함께 로드되는 건 이 워커에서 이미 정상적인
구조다(`quality_check_worker_example.py`도 `sam3.contracts`를 직접 쓴다).

hotfix/472: 크롭 1장 + finding 1건당 개별 호출 방식에서 **이미지 1장 + 번호별 위치·유형
힌트로 그 이미지의 finding 전부를 한 번에 묻는 배치 방식**으로 교체했다(`prompts.py`의
`build_batch_prompt`/`parse_batch_response` 참고) — 크롭을 만들지 않으므로 이 파일의
크롭 관련 헬퍼(`_crop_finding` 등)는 삭제했다.

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
from .prompts import build_batch_prompt, parse_batch_response

logger = logging.getLogger(__name__)


class DescriberNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치 등)."""


class DefectDescriber(ABC):
    """이미지 1장 + 그 이미지의 finding 전부 -> {no: 설명}. **여기가 VLM 모델 교체 경계다.**"""

    @abstractmethod
    def describe_batch(self, image: Image.Image, findings: Sequence[Finding]) -> dict[int, str | None]:
        raise NotImplementedError


class MockDescriber(DefectDescriber):
    """정적 문구로 채운다(torch 불필요). CI/기본 경로."""

    def describe_batch(self, image: Image.Image, findings: Sequence[Finding]) -> dict[int, str | None]:
        return {f.no: f"{f.label} 발견" for f in findings}


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

    def describe_batch(self, image: Image.Image, findings: Sequence[Finding]) -> dict[int, str | None]:
        from .loader import generate_from_image

        self._ensure_loaded()
        prompt_text = build_batch_prompt(findings)
        # config["max_new_tokens"]은 원래 crop 1건 예산이었다 — 배치에서는 finding 수만큼
        # 스케일링한다(검증 노트북의 `_TOKENS_PER_FINDING` 예산과 동일한 논리). 고정값으로
        # 두면 finding이 많은 이미지에서 응답이 중간에 끊긴다.
        max_new_tokens = max(1, len(findings)) * self._config["max_new_tokens"]
        raw_response = generate_from_image(self._bundle, image, prompt_text, max_new_tokens)
        return parse_batch_response(raw_response, [f.no for f in findings])


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


def attach_descriptions(
    results: Sequence[SegmentationResult],
    findings: Sequence[Finding],
    describer: DefectDescriber,
) -> list[Finding]:
    """이미지별로 묶어서 그 이미지의 finding 전부에 배치 VLM 설명을 채운 새 리스트를 반환한다.

    `Finding`은 frozen dataclass라 `dataclasses.replace()`로 새 인스턴스를 만든다 — 원본
    리스트는 바뀌지 않는다. 이미지 1장당 VLM 호출 1번이다(finding마다 부르지 않는다) —
    hotfix/472: 크롭 1장당 개별 호출 방식에서 배치 방식으로 교체.

    **개별 이미지 실패는 그 이미지의 finding들만 description=None으로 남기고 계속
    진행한다** — `inspection_logger`의 "best-effort, 응답을 막지 않는다" 원칙과 동일하다.
    배치 파싱이 일부 번호를 놓쳤을 때도(`parse_batch_response`가 `None`으로 남김) 그
    finding만 description 없이 남고 나머지는 정상 처리된다.
    """
    by_image = {r.image_index: r for r in results}
    findings_by_image: dict[int, list[Finding]] = {}
    for finding in findings:
        findings_by_image.setdefault(finding.image_index, []).append(finding)

    descriptions: dict[str, str | None] = {}
    for image_index, image_findings in findings_by_image.items():
        result = by_image.get(image_index)
        if result is None:
            continue
        try:
            by_no = describer.describe_batch(result.base_image, image_findings)
        except Exception as exc:
            logger.warning("하자 설명 생성 실패(image_index=%s): %s", image_index, exc)
            continue
        for finding in image_findings:
            descriptions[finding.key] = by_no.get(finding.no)

    return [
        dataclasses.replace(finding, description=descriptions[finding.key])
        if descriptions.get(finding.key)
        else finding
        for finding in findings
    ]
