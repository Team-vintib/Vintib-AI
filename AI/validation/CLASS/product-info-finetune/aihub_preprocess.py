"""Polygon 세그멘테이션 → 마스크 → bbox 크롭 + 배경 흰색 치환.

브리핑 §3(A): 색상 헤드는 **입력 변형 2개를 반드시 비교**해야 한다 — ① 원본 이미지,
② 마스크 bbox 크롭 + 배경 흰색. 그 차이가 곧 "배경 제거의 가치"다. 과거 색상 실패의 원인이
배경 오염이었다(`REPORT.md` §V3: 콘크리트 바닥이 1등 클러스터로 잡힘).

이 모듈은 `aihub_embed.py`가 **함수로 호출**한다 — 5만 장을 크롭해서 디스크에 또 쓰지
않는다(임베딩만 캐시하면 되고, 크롭본은 재생성이 싸다). CLI는 **눈으로 확인할 샘플 몇 장만**
떨구는 용도다.

좌표 규약
---------
- 의류 통합 데이터: `annotation[0].annotation_point`가 평탄 `[x1,y1,x2,y2,…]`.
- 액세서리 데이터: `annotation[0].segmentation`이 `{"클래스인덱스": [[링1 평탄좌표], …]}`.
  링이 여러 개일 수 있다(귀걸이 좌/우 등).

**절대좌표인지 정규화좌표인지 파일마다 확신할 수 없다.** LAB-76 샘플은 절대 픽셀로 보이지만
(width 607에 x=282.7), 명세는 "dataset.width/height로 정규화"라고 적어 뒀다. 그래서
`normalize_polygon()`이 값의 범위를 보고 판단한다 — 최대값이 1.0 이하면 정규화된 것으로
보고 이미지 크기를 곱한다. 판단 근거를 반환해 CLI가 찍는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

# 크롭할 때 bbox 바깥으로 남길 여백 비율. 0이면 옷이 프레임에 꽉 차서 CLIP이 보던 분포와
# 멀어진다(CLIP은 여백 있는 제품컷으로 학습됐다).
BBOX_PADDING_RATIO = 0.06

VARIANTS = ("raw", "masked")


@dataclass(frozen=True)
class Polygon:
    """이미지 1장의 세그멘테이션. `rings`는 [(x, y), …] 리스트의 리스트(절대 픽셀)."""

    rings: list[list[tuple[float, float]]]
    was_normalized: bool  # 0~1 정규화 좌표를 픽셀로 되돌렸는지

    @property
    def points(self) -> list[tuple[float, float]]:
        return [point for ring in self.rings for point in ring]


def _pairs(flat: Iterable[float]) -> list[tuple[float, float]]:
    values = [float(v) for v in flat]
    return list(zip(values[0::2], values[1::2]))


def extract_rings(js: Any) -> list[list[tuple[float, float]]]:
    """라벨 JSON에서 폴리곤 링들을 뽑는다. 두 데이터셋의 서로 다른 형태를 모두 받는다."""
    annotations = js.get("annotation")
    if not isinstance(annotations, list) or not annotations:
        return []

    rings: list[list[tuple[float, float]]] = []
    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue

        # 의류 통합 데이터 — 평탄 배열 하나
        flat = annotation.get("annotation_point")
        if isinstance(flat, list) and len(flat) >= 6:
            rings.append(_pairs(flat))
            continue

        # 액세서리 — {클래스인덱스: [[링], …]}
        segmentation = annotation.get("segmentation")
        if isinstance(segmentation, dict):
            for ring_group in segmentation.values():
                if not isinstance(ring_group, list):
                    continue
                for ring in ring_group:
                    if isinstance(ring, list) and len(ring) >= 6:
                        rings.append(_pairs(ring))
    return rings


def normalize_polygon(
    rings: list[list[tuple[float, float]]], width: int | None, height: int | None
) -> Polygon | None:
    """0~1 정규화 좌표면 픽셀로 되돌린다. 링이 없으면 None."""
    if not rings:
        return None
    all_values = [value for ring in rings for point in ring for value in point]
    if not all_values:
        return None

    was_normalized = max(all_values) <= 1.0
    if was_normalized and width and height:
        rings = [[(x * width, y * height) for x, y in ring] for ring in rings]
    return Polygon(rings=rings, was_normalized=was_normalized)


def bbox_of(
    polygon: Polygon,
    width: int | None,
    height: int | None,
    padding_ratio: float = BBOX_PADDING_RATIO,
) -> tuple[int, int, int, int]:
    """폴리곤을 감싸는 사각형 + 여백. 이미지 경계로 clamp한다."""
    xs = [x for x, _ in polygon.points]
    ys = [y for _, y in polygon.points]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)

    pad_x = (right - left) * padding_ratio
    pad_y = (bottom - top) * padding_ratio
    left, right = left - pad_x, right + pad_x
    top, bottom = top - pad_y, bottom + pad_y

    max_x = width if width else int(right) + 1
    max_y = height if height else int(bottom) + 1
    left = max(0, int(round(left)))
    top = max(0, int(round(top)))
    right = min(max_x, int(round(right)))
    bottom = min(max_y, int(round(bottom)))
    # 폭/높이가 0이 되는 퇴화 케이스 방어
    if right <= left:
        right = min(max_x, left + 1)
    if bottom <= top:
        bottom = min(max_y, top + 1)
    return left, top, right, bottom


def load_polygon(label_path: Path, width: int | None, height: int | None) -> Polygon | None:
    """라벨 JSON 파일에서 폴리곤을 읽는다. 없거나 깨졌으면 None."""
    try:
        js = json.loads(label_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return normalize_polygon(extract_rings(js), width, height)


def render_variant(image: Any, polygon: Polygon | None, variant: str) -> Any:
    """PIL Image + 폴리곤 → 변형된 PIL Image (RGB).

    - ``raw``    : 원본 그대로(RGB 변환만)
    - ``masked`` : 폴리곤 밖을 흰색으로 지우고 bbox로 크롭

    폴리곤이 없으면 `masked`여도 원본을 그대로 돌려준다 — 조용히 검은 이미지를 만들면
    임베딩이 오염되고 원인을 못 찾는다. 호출부가 "몇 건이 폴백했는지" 세게 한다.
    """
    from PIL import Image, ImageDraw

    rgb = image.convert("RGB")
    if variant == "raw" or polygon is None:
        return rgb

    mask = Image.new("L", rgb.size, 0)
    draw = ImageDraw.Draw(mask)
    for ring in polygon.rings:
        if len(ring) >= 3:
            draw.polygon(ring, fill=255)

    white = Image.new("RGB", rgb.size, (255, 255, 255))
    composited = Image.composite(rgb, white, mask)
    return composited.crop(bbox_of(polygon, rgb.width, rgb.height))


# --------------------------------------------------------------------------
# CLI — 눈으로 확인할 샘플만 떨군다(대량 크롭 저장은 하지 않는다)
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="마스크 크롭 결과를 샘플 몇 장만 저장해 눈으로 확인한다",
    )
    parser.add_argument("--index", type=Path, required=True, help="aihub_dataset index 산출 JSONL")
    parser.add_argument("--label-root", type=Path, required=True, help="라벨 JSON 루트")
    parser.add_argument("--image-root", type=Path, required=True, help="이미지 루트")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=12)
    args = parser.parse_args(argv)

    from PIL import Image

    import aihub_embed  # 경로 해석 규칙을 한 곳에만 두려고 재사용한다

    args.out_dir.mkdir(parents=True, exist_ok=True)
    saved = 0
    missing = 0
    no_polygon = 0
    normalized = 0

    with args.index.open(encoding="utf-8") as handle:
        for line in handle:
            if saved >= args.count:
                break
            row = json.loads(line)
            image_path = aihub_embed.resolve_image_path(row, args.image_root)
            if image_path is None or not image_path.exists():
                missing += 1
                continue
            polygon = load_polygon(
                args.label_root / row["label_path"], row.get("width"), row.get("height")
            )
            if polygon is None:
                no_polygon += 1
            elif polygon.was_normalized:
                normalized += 1

            with Image.open(image_path) as image:
                raw = render_variant(image, polygon, "raw")
                masked = render_variant(image, polygon, "masked")

            stem = Path(row["name"]).stem
            raw.save(args.out_dir / f"{stem}__raw.jpg", quality=90)
            masked.save(args.out_dir / f"{stem}__masked.jpg", quality=90)
            saved += 1

    print(f"저장 {saved}쌍 → {args.out_dir}")
    print(f"이미지 못 찾음 {missing} · 폴리곤 없음 {no_polygon} · 정규화 좌표였음 {normalized}")
    print("두 파일을 나란히 열어 배경이 실제로 지워졌는지 확인할 것.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
