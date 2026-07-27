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

저장 경로는 게이트웨이가 이미 쓰고 있는 `RESULTS_DIR`을 그대로 재사용한다(새 저장·서빙 경로를
만들지 않는다). `app/main.py`가 `/results`로 마운트해 둔 StaticFiles가 그대로 서빙한다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence

import numpy as np
from PIL import Image

from app.core.config import settings
from app.gateway.router import RESULTS_DIR
from app.quality.findings import normalize_mask
from app.quality.prompts import PromptSet
from app.quality.registry import SegmenterConfig
from app.quality.schemas import AttentionMap, DefectType, Finding
from app.quality.segmenter import SegmentationResult

# 히트맵이 원본을 덮는 최대 불투명도. 1.0이면 원본이 완전히 가려져 무엇 위의 하자인지 알 수 없다.
HEATMAP_MAX_ALPHA = 0.62

# 오버레이 PNG가 쌓이는 하위 디렉터리(`RESULTS_DIR/quality/{inspection_id}/`).
OVERLAY_SUBDIR = "quality"

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


def overlay_path(inspection_id: str, filename: str, results_dir: str = RESULTS_DIR) -> str:
    return os.path.join(results_dir, OVERLAY_SUBDIR, inspection_id, filename)


def overlay_url(inspection_id: str, filename: str) -> str:
    """StaticFiles가 서빙하는 공개 URL. `app/main.py`의 `/results` 마운트와 짝이다."""
    return f"{settings.public_base_url}/results/{OVERLAY_SUBDIR}/{inspection_id}/{filename}"


def save_overlay(
    image: Image.Image,
    inspection_id: str,
    filename: str,
    results_dir: str = RESULTS_DIR,
) -> str:
    """PNG로 저장하고 공개 URL을 돌려준다."""
    path = overlay_path(inspection_id, filename, results_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, format="PNG")
    return overlay_url(inspection_id, filename)


def build_attention_maps(
    inspection_id: str,
    results: Sequence[SegmentationResult],
    findings: Sequence[Finding],
    prompt_set: PromptSet,
    config: SegmenterConfig,
    results_dir: str = RESULTS_DIR,
) -> list[AttentionMap]:
    """findings가 실제로 나온 (이미지, 하자유형) 조합만 오버레이로 만든다.

    프롬프트 전부를 렌더하면 이미지 1장에 PNG 6개가 쌓이는데, 아무것도 검출되지 않은 유형의
    히트맵은 판매자에게 보여줄 이유가 없다. **화면에 보이는 것과 항목 리스트를 일치시킨다.**

    마스크는 findings와 **같은 정규화**를 거친 것을 쓴다 — 원본 마스크를 그리면 프린트처럼
    대조 정규화로 상쇄된 영역이 화면에서는 시뻘겋게 보이는 모순이 생긴다.
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
        filename = f"{image_index}_{defect_type.value.lower()}.png"
        maps.append(
            AttentionMap(
                image_index=image_index,
                defect_type=defect_type,
                url=save_overlay(image, inspection_id, filename, results_dir),
            )
        )
    return maps
