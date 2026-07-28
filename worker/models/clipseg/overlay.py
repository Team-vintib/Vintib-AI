"""Attention Map — 확률 마스크를 원본 위에 얹은 히트맵 PNG.

**검수 파이프라인의 필수 단계가 아니다.** 상품 등록 흐름에서 오버레이가 필요 없을 수 있어,
요청이 명시적으로 요구할 때만 호출된다(`InspectionRequest.include_attention_maps`, 기본 off).
이 모듈은 검수 서비스에 의존하지 않으므로 발표자료용 배치 렌더처럼 **밖에서 그냥 호출해도**
동작한다.

**matplotlib을 쓰지 않는다.** `verify_clipseg.py`가 matplotlib으로 하던 일을 Pillow + numpy로
다시 썼다 — 서빙 경로에 넣기엔 무거운 의존성이기 때문이다. jet 근사 컬러맵은 256단 LUT로
만든다.

**알파를 확률에 비례시킨다.** 균일 알파로 덮으면 옷 전체가 파랗게 물들어 어디가 문제인지
오히려 안 보인다. `defect_threshold` 미만은 완전 투명이라 원본이 그대로 보이고, 임계치를 넘는
영역만 색이 올라온다 — 화면에 보이는 것과 findings가 일치한다.

**워커는 결과 이미지를 자기 디스크에 쓰지 않는다.** 노트북 디스크는 외부에서 접근할 수 없어서,
게이트웨이의 업로드 엔드포인트로 보내고 공개 URL을 받아야 한다(인프라 문서 §3.5). 그래서
`build_attention_maps()`가 **업로더 함수를 주입받는다** — `worker/storage_utils.upload_image`를
그대로 넘기면 되고, 테스트에서는 가짜 함수를 넘겨 디스크·네트워크 없이 검증할 수 있다.
(게이트웨이 안에서 돌던 시절에는 `RESULTS_DIR`에 직접 썼는데, 그 코드는 여기 없다.)

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

import numpy as np
from contracts import AttentionMap, DefectType, Finding
from findings import normalize_mask
from PIL import Image
from prompts import PromptSet
from registry import SegmenterConfig
from segmenter import SegmentationResult

# 히트맵이 원본을 덮는 최대 불투명도. 1.0이면 원본이 완전히 가려져 무엇 위의 하자인지 알 수 없다.
HEATMAP_MAX_ALPHA = 0.62

# 업로드 시 게이트웨이에 넘기는 prefix — `/results/{prefix}/...` 로 서빙된다.
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


def render_overlay(
    base_image: Image.Image,
    mask: np.ndarray,
    *,
    floor: float = 0.0,
    max_alpha: float = HEATMAP_MAX_ALPHA,
) -> Image.Image:
    """원본 위에 확률 히트맵을 알파 합성한 RGB 이미지를 만든다.

    `floor` 미만은 완전 투명이라 원본이 그대로 보인다 — 보통 백엔드의 `defect_threshold`를
    넘겨서, 화면에 색이 올라온 영역과 실제 findings가 어긋나지 않게 한다.
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
    findings: Sequence[Finding],
    prompt_set: PromptSet,
    config: SegmenterConfig,
    upload: ImageUploader,
) -> list[AttentionMap]:
    """findings가 실제로 나온 (이미지, 하자유형) 조합만 오버레이로 만든다.

    프롬프트 전부를 렌더하면 이미지 1장에 PNG 6개가 쌓이는데, 아무것도 검출되지 않은 유형의
    히트맵은 판매자에게 보여줄 이유가 없다. **화면에 보이는 것과 항목 리스트를 일치시킨다.**

    마스크는 findings와 **같은 정규화**를 거친 것을 쓴다 — 원본 마스크를 그리면 프린트처럼
    대조 정규화로 상쇄된 영역이 화면에서는 시뻘겋게 보이는 모순이 생긴다.

    `upload`는 `(이미지, prefix) -> 공개 URL` 함수다(`storage_utils.upload_image`).
    업로드 실패는 여기서 삼키지 않고 그대로 올린다 — 호출자(워커)가 검수 결과 전체를 살릴지
    판단한다.
    """
    by_image = {result.image_index: result for result in results}
    prompt_by_type = {defect_type: prompt for prompt, defect_type in prompt_set.defect_prompts}

    wanted: list[tuple[int, DefectType]] = []
    for finding in findings:
        pair = (finding.image_index, finding.defect_type)
        if pair not in wanted:
            wanted.append(pair)

    maps: list[AttentionMap] = []
    for image_index, defect_type in wanted:
        result = by_image.get(image_index)
        prompt = prompt_by_type.get(defect_type)
        if result is None or prompt is None or prompt not in result.masks:
            continue  # 세그멘터가 해당 마스크를 내지 않은 경우 — 렌더할 게 없다

        normalized = normalize_mask(result.masks[prompt], result.clean_mask, config["clean_margin"])
        image = render_overlay(result.base_image, normalized, floor=config["defect_threshold"])
        maps.append(
            AttentionMap(
                image_index=image_index,
                defect_type=defect_type,
                url=upload(image, OVERLAY_PREFIX),
            )
        )
    return maps
