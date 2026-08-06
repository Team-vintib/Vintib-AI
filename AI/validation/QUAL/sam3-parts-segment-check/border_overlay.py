"""bbox 사각형 대신 **탐지 마스크의 윤곽선 + 반투명 채우기**로 하자 위치를 표시한다.

`qc_shared.draw_numbered_boxes`(기존, 사각형 bbox)와 나란히 비교하기 위한 대안 렌더러다.
사각형은 회전되거나 불규칙한 모양(찢어짐, 길쭉한 얼룩 등)을 실제보다 넓게 보여준다 —
SAM3 인스턴스는 이미 픽셀 단위 마스크를 갖고 있으므로, 그 마스크 윤곽을 그대로 쓰면
판매자가 보는 강조 영역이 실제 하자 형태에 더 가까워질 것이라는 가설을 테스트한다.

한글 라벨은 `qc_shared.korean_font_path`/`KOREAN_LABELS`를 호출부가 주입한다 — 이 모듈은
`qc_shared`를 직접 import하지 않는다(다른 폴더에서도 재사용할 수 있게 결합을 낮춘다).
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from PIL import Image


def draw_bordered_findings(
    pil_image: Image.Image,
    instances: list[dict],
    korean_labels: dict[str, str],
    font_path_fn: Callable[[int], object],
    border_color: tuple[int, int, int] = (255, 0, 0),
    fill_alpha: float = 0.28,
    thickness: int = 3,
) -> np.ndarray:
    """confidence 내림차순 **번호만** + 마스크 윤곽선(+반투명 채우기). RGB ndarray 반환.

    `qc_shared.draw_numbered_boxes`(bbox 버전)와 마찬가지로 하자 유형·확신도는 이미지에
    그리지 않는다 — 사용자에게는 번호만 보여주고, 유형·점수는 `qc_shared.to_serializable()`이
    만드는 JSON에만 담는다. `korean_labels`/`font_path_fn` 인자는 더 이상 텍스트 렌더링에
    쓰이지 않지만, 호출부(노트북 등)와의 시그니처 호환을 위해 그대로 남겨둔다.

    `qc_shared.draw_numbered_boxes`와 같은 인스턴스 dict 스키마(`bbox`/`mask`/`type`/
    `confidence`)를 받아 시그니처를 맞췄다 — 같은 인스턴스 리스트를 두 함수에 그대로 넘겨서
    bbox 버전/마스크 버전을 나란히 뽑을 수 있다.
    """
    import cv2
    from PIL import Image as PILImage
    from PIL import ImageDraw

    base = np.array(pil_image.convert("RGB")).copy()
    ordered = sorted(instances, key=lambda d: d["confidence"], reverse=True)

    # 1) 채우기 — 전부 먼저 합성해야 겹치는 마스크끼리 알파가 중첩되지 않는다.
    fill_layer = base.copy()
    for inst in ordered:
        mask_bool = inst["mask"].astype(bool)
        fill_layer[mask_bool] = border_color
    blended = cv2.addWeighted(fill_layer, fill_alpha, base, 1 - fill_alpha, 0)

    # 2) 윤곽선 — 채우기 위에 덧그린다.
    for inst in ordered:
        mask_u8 = inst["mask"].astype(np.uint8)
        contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(blended, contours, -1, border_color, thickness=thickness)

    pil_canvas = PILImage.fromarray(blended)
    draw = ImageDraw.Draw(pil_canvas)
    font_size = max(14, int(0.022 * max(pil_canvas.size)))
    font = font_path_fn(font_size)

    for no, inst in enumerate(ordered, start=1):
        rows_idx, cols_idx = np.nonzero(inst["mask"])
        if rows_idx.size == 0:
            continue
        # 라벨 위치: 마스크 최상단 픽셀 바로 위(사각형 bbox가 아니라 실제 마스크 기준).
        x1, y1 = int(cols_idx.min()), int(rows_idx.min())
        text = str(no)
        box = draw.textbbox((0, 0), text, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        ty = max(y1 - th - 6, 0)
        draw.rectangle([x1, ty, x1 + tw + 8, ty + th + 6], fill=border_color)
        draw.text((x1 + 4, ty + 2), text, fill=(255, 255, 255), font=font)

    return np.array(pil_canvas)


def draw_part_boundaries(
    pil_image: Image.Image,
    part_instances: list[dict],
    korean_labels: dict[str, str],
    font_path_fn: Callable[[int], object],
    thickness: int = 2,
) -> np.ndarray:
    """파츠 탐지 자체가 잘 됐는지 눈으로 확인하기 위한 디버그 렌더러.

    파츠마다 다른 색(팔레트 순환)으로 윤곽선만 그린다 — 채우기가 없어야 겹치는 파츠
    경계를 구분하기 쉽다(옷은 파츠가 서로 인접해 마스크가 겹칠 수 있다).
    """
    import cv2
    from PIL import Image as PILImage
    from PIL import ImageDraw

    palette = [
        (255, 0, 0),
        (0, 160, 255),
        (0, 200, 0),
        (255, 160, 0),
        (200, 0, 200),
        (0, 200, 200),
    ]

    canvas = np.array(pil_image.convert("RGB")).copy()
    for i, inst in enumerate(part_instances):
        color = palette[i % len(palette)]
        mask_u8 = inst["mask"].astype(np.uint8)
        contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(canvas, contours, -1, color, thickness=thickness)

    pil_canvas = PILImage.fromarray(canvas)
    draw = ImageDraw.Draw(pil_canvas)
    font_size = max(14, int(0.02 * max(pil_canvas.size)))
    font = font_path_fn(font_size)

    for i, inst in enumerate(part_instances):
        color = palette[i % len(palette)]
        rows_idx, cols_idx = np.nonzero(inst["mask"])
        if rows_idx.size == 0:
            continue
        x1, y1 = int(cols_idx.min()), int(rows_idx.min())
        label_ko = korean_labels.get(inst["type"], inst["type"])
        text = f"{label_ko} {inst['confidence']:.2f}"
        box = draw.textbbox((0, 0), text, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
        ty = max(y1 - th - 6, 0)
        draw.rectangle([x1, ty, x1 + tw + 8, ty + th + 6], fill=color)
        draw.text((x1 + 4, ty + 2), text, fill=(255, 255, 255), font=font)

    return np.array(pil_canvas)
