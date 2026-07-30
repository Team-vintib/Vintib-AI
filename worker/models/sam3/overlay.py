"""Attention Map — SAM3 인스턴스 마스크를 원본 위에 얹은 히트맵 PNG.

CLIPSeg 쪽(`worker/models/clipseg/overlay.py`)과 다른 점: 연속 확률 마스크가 아니라 **이산
인스턴스 마스크 여러 개**를 하나로 합쳐 렌더링용 의사 확률맵을 만든다 — 인스턴스가 있는
픽셀은 그 인스턴스의 confidence 값, 없는 픽셀은 0인 맵이다. 겹치는 인스턴스는 confidence가
더 높은 쪽이 이긴다(max). 이렇게 만들면 CLIPSeg와 같은 `render_overlay()`(Pillow + numpy
알파 합성)를 그대로 재사용할 수 있다.

**반드시 `FindingsResult.kept_instances_by_image`를 써야 한다** — `SegmentationResult.
instances`(원본, 필터 전)를 쓰면 의류 겹침 필터·양성 억제로 떨어졌어야 할 인스턴스까지
Attention Map에 그려지는 불일치가 생긴다. 화면에 보이는 것과 findings 리스트가 어긋나면
"AI가 왜 여기를 오염이라고 했는데 항목엔 없지"라는 혼란을 만든다.

설계: `.claude/plans/ai/CH006-sam3-quality-segmenter.md`
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

import numpy as np
from PIL import Image

from .contracts import AttentionMap, DefectType, Finding
from .segmenter import Instance, SegmentationResult

# 히트맵이 원본을 덮는 최대 불투명도. 1.0이면 원본이 완전히 가려져 무엇 위의 하자인지 알 수 없다.
HEATMAP_MAX_ALPHA = 0.62

# 업로드 시 게이트웨이에 넘기는 prefix — `/results/{prefix}/...`로 서빙된다.
OVERLAY_PREFIX = "quality-attention"

# 업로더 시그니처: (이미지, prefix) -> 공개 URL. `storage_utils.upload_image`가 이 형태다.
ImageUploader = Callable[[Image.Image, str], str]

logger = logging.getLogger(__name__)


def _jet_lut() -> np.ndarray:
    """jet 컬러맵 근사 LUT (256, 3). 파랑(낮음) → 초록 → 빨강(높음)."""
    x = np.linspace(0.0, 1.0, 256, dtype=np.float32)
    red = np.clip(1.5 - np.abs(4.0 * x - 3.0), 0.0, 1.0)
    green = np.clip(1.5 - np.abs(4.0 * x - 2.0), 0.0, 1.0)
    blue = np.clip(1.5 - np.abs(4.0 * x - 1.0), 0.0, 1.0)
    return (np.stack([red, green, blue], axis=1) * 255.0).astype(np.uint8)


_JET = _jet_lut()


def _resize_mask(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """마스크를 원본 이미지 크기(width, height)로 늘린다."""
    width, height = size
    if mask.shape == (height, width):
        return mask
    resized = Image.fromarray((np.clip(mask, 0.0, 1.0) * 255).astype(np.uint8)).resize(
        (width, height), Image.BILINEAR
    )
    return np.asarray(resized, dtype=np.float32) / 255.0


def _instances_to_pseudo_mask(instances: Sequence[Instance], size: tuple[int, int]) -> np.ndarray:
    """같은 하자 유형의 인스턴스 마스크들을 confidence 값으로 합친 의사 확률맵.

    겹치는 영역은 confidence가 더 높은 인스턴스가 이긴다(max) — `render_overlay()`가
    CLIPSeg와 같은 [0,1] 연속값 인터페이스를 그대로 받게 하는 어댑터다. size = (height, width).
    """
    height, width = size
    canvas = np.zeros((height, width), dtype=np.float32)
    for inst in instances:
        canvas = np.maximum(canvas, inst.mask.astype(np.float32) * inst.confidence)
    return canvas


def render_overlay(
    base_image: Image.Image,
    mask: np.ndarray,
    *,
    floor: float = 0.0,
    max_alpha: float = HEATMAP_MAX_ALPHA,
) -> Image.Image:
    """원본 위에 확률(의사) 히트맵을 알파 합성한 RGB 이미지를 만든다.

    `floor` 미만은 완전 투명이라 원본이 그대로 보인다. SAM3 경로는 마스크 자체가 이미
    "인스턴스 있음/없음" 이진 정보를 confidence로 담고 있어 `floor=0.0`이 기본이다 —
    CLIPSeg처럼 연속 히트맵을 findings와 맞추기 위해 추가로 자를 필요가 없다.
    """
    base = base_image.convert("RGB")
    resized = _resize_mask(mask, base.size)

    colors = _JET[(np.clip(resized, 0.0, 1.0) * 255).astype(np.uint8)].astype(np.float32)

    span = max(1.0 - floor, 1e-6)
    alpha = np.clip((resized - floor) / span, 0.0, 1.0) * max_alpha
    alpha = alpha[:, :, None].astype(np.float32)

    blended = np.asarray(base, dtype=np.float32) * (1.0 - alpha) + colors * alpha
    return Image.fromarray(blended.astype(np.uint8), mode="RGB")


def build_attention_maps(
    results: Sequence[SegmentationResult],
    kept_instances_by_image: dict[int, tuple[Instance, ...]],
    findings: Sequence[Finding],
    upload: ImageUploader,
) -> list[AttentionMap]:
    """findings가 실제로 나온 (이미지, 하자유형) 조합만 오버레이로 만든다.

    프롬프트 전부를 렌더하면 검출되지 않은 유형의 히트맵까지 쌓인다 — **화면에 보이는 것과
    항목 리스트를 일치시킨다.** 반드시 `kept_instances_by_image`(필터를 통과한 인스턴스만)를
    쓴다 — 모듈 docstring 참고.

    `upload`는 `(이미지, prefix) -> 공개 URL` 함수다(`storage_utils.upload_image`). 업로드
    실패는 여기서 삼키지 않고 그대로 올린다 — 호출자(워커)가 검수 결과 전체를 살릴지 판단한다.
    """
    by_image = {result.image_index: result for result in results}

    wanted: list[tuple[int, DefectType]] = []
    for finding in findings:
        pair = (finding.image_index, finding.defect_type)
        if pair not in wanted:
            wanted.append(pair)

    maps: list[AttentionMap] = []
    for image_index, defect_type in wanted:
        result = by_image.get(image_index)
        if result is None:  # pragma: no cover - findings는 항상 results에서 나오므로 방어용
            continue

        matching = [
            inst for inst in kept_instances_by_image.get(image_index, ()) if inst.defect_type is defect_type
        ]
        if not matching:
            continue  # 필터로 전부 제거된 유형 — 렌더할 게 없다

        mask = _instances_to_pseudo_mask(matching, result.size)
        image = render_overlay(result.base_image, mask, floor=0.0)
        maps.append(
            AttentionMap(
                image_index=image_index,
                defect_type=defect_type,
                url=upload(image, OVERLAY_PREFIX),
            )
        )
    return maps
