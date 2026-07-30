"""실제 판매 사진 3번째(반팔 상의 + 실제 A4 프린트물) — 전체 파이프라인 4단계를 실사진으로 왕복.

`valid_image3.jpg`는 반팔 상의(SHORT_SLEEVE_TOP, 검증된 카테고리)라 랜드마크 검출·cm 환산까지
실사진으로 전부 테스트할 수 있다. 아이폰으로 찍어 EXIF `Orientation` 태그가 붙어 있다 —
`image_io.load_image`의 EXIF 보정 버그를 이 사진으로 발견했다.

기준 물체가 흰 A4 낱장, 옷도 흰색/크림색 계열이라 대비가 약하다 — 이 낮은 대비 조건 자체가
유의미한 테스트 포인트(사용자가 사전에 우려했던 시나리오).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "worker" / "models"))

import cv2
import numpy as np

from garment_measurement import registry
from garment_measurement.cm_converter import convert
from garment_measurement.contracts import GarmentCategory
from garment_measurement.landmark_detector import HRNetLandmarkDetector
from garment_measurement.reference_detector import (
    OpenCVContourReferenceDetector,
    _CANNY_LOW,
    _CANNY_HIGH,
)
from garment_measurement.segmenter import GrabCutGarmentSegmenter

HERE = Path(__file__).resolve().parent
IMAGE_PATH = HERE / "valid_image3.jpg"
PREFIX = "report_real3"


def find_reference_contour_debug(frame_bgr):
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.dilate(cv2.Canny(blurred, _CANNY_LOW, _CANNY_HIGH), None, iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        rect = cv2.minAreaRect(approx)
        (_, (w, h), _) = rect
        if w <= 0 or h <= 0:
            continue
        short_side, long_side = sorted((w, h))
        ratio = long_side / short_side
        deviation = abs(ratio - registry.A4_ASPECT_RATIO) / registry.A4_ASPECT_RATIO
        candidates.append(
            {
                "box": cv2.boxPoints(rect),
                "area": w * h,
                "ratio": ratio,
                "deviation": deviation,
                "within_tolerance": deviation <= 0.15,
            }
        )
    return edges, candidates


def main():
    frame = cv2.imread(str(IMAGE_PATH))
    if frame is None:
        raise SystemExit(f"이미지를 못 읽었습니다: {IMAGE_PATH}")

    cv2.imwrite(str(HERE / f"{PREFIX}_00_input.png"), frame)
    result = {"image": IMAGE_PATH.name, "image_size": [frame.shape[1], frame.shape[0]]}

    # --- 1단계: 기준 물체 검출 ---
    edges, candidates = find_reference_contour_debug(frame)
    cv2.imwrite(str(HERE / f"{PREFIX}_01b_edges.png"), edges)

    ref_detector = OpenCVContourReferenceDetector()
    detection = ref_detector.detect(str(IMAGE_PATH), product_id=1)

    ref_viz = frame.copy()
    candidates_sorted = sorted(candidates, key=lambda c: -c["area"])
    for cand in candidates_sorted[:8]:
        color = (0, 200, 0) if cand["within_tolerance"] else (0, 0, 220)
        box_int = cand["box"].astype(int)
        cv2.drawContours(ref_viz, [box_int], 0, color, 2)
        x, y = box_int[0]
        cv2.putText(
            ref_viz, f"ratio {cand['ratio']:.2f} (dev {cand['deviation']:.0%})",
            (int(x), max(int(y) - 8, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA,
        )
    status = (
        f"REFERENCE FOUND (ratio->cm {detection.pixel_to_cm_ratio:.4f})"
        if detection.found else "REFERENCE NOT FOUND"
    )
    cv2.putText(
        ref_viz, status, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
        (0, 200, 0) if detection.found else (0, 0, 220), 2, cv2.LINE_AA,
    )
    cv2.imwrite(str(HERE / f"{PREFIX}_01_reference.png"), ref_viz)

    result["reference_detection"] = {
        "found": bool(detection.found),
        "pixel_to_cm_ratio": detection.pixel_to_cm_ratio,
        "quad_candidates_considered": len(candidates),
        "candidates_within_a4_aspect_tolerance": sum(c["within_tolerance"] for c in candidates),
        "top_candidates": [
            {
                "ratio": round(c["ratio"], 4),
                "deviation_from_a4": round(c["deviation"], 4),
                "within_tolerance": c["within_tolerance"],
                "area_px": round(c["area"], 1),
            }
            for c in candidates_sorted[:8]
        ],
    }

    # --- 2단계: 원단 분할 ---
    segmenter = GrabCutGarmentSegmenter()
    seg = segmenter.segment(str(IMAGE_PATH), product_id=1)

    seg_viz = frame.copy()
    if seg.found and seg.bbox is not None:
        x, y, w, h = [int(v) for v in seg.bbox]
        cv2.rectangle(seg_viz, (x, y), (x + w, y + h), (0, 140, 255), 3)
        cv2.putText(seg_viz, "GARMENT BBOX", (x, max(y - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2, cv2.LINE_AA)
    else:
        cv2.putText(seg_viz, "GARMENT NOT FOUND", (16, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 220), 2, cv2.LINE_AA)
    cv2.imwrite(str(HERE / f"{PREFIX}_02_segmentation.png"), seg_viz)

    result["segmentation"] = {"found": bool(seg.found), "bbox": list(seg.bbox) if seg.bbox else None}

    # --- 3단계: 랜드마크 검출 (SHORT_SLEEVE_TOP) ---
    landmark_detector = HRNetLandmarkDetector()
    landmarks = landmark_detector.detect(
        str(IMAGE_PATH), product_id=1,
        category=GarmentCategory.short_sleeve_top,
        bbox=seg.bbox,
    )

    lm_viz = frame.copy()
    for lm in landmarks:
        x, y = int(lm.pixel_x), int(lm.pixel_y)
        cv2.circle(lm_viz, (x, y), 6, (255, 80, 0), -1)
        cv2.putText(lm_viz, lm.type.value, (x + 8, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 80, 0), 1, cv2.LINE_AA)
    cv2.imwrite(str(HERE / f"{PREFIX}_03_landmarks.png"), lm_viz)

    result["landmarks"] = [
        {"type": lm.type.value, "x": round(lm.pixel_x, 1), "y": round(lm.pixel_y, 1),
         "confidence": round(lm.confidence, 3)}
        for lm in landmarks
    ]

    # --- 4단계: cm 환산 ---
    measurements = []
    if detection.found and detection.pixel_to_cm_ratio:
        measurements = convert(landmarks, detection.pixel_to_cm_ratio)
    result["measurements"] = [
        {"type": m.type.value, "value_cm": m.value_cm, "confidence": round(m.confidence, 3)}
        for m in measurements
    ]

    (HERE / f"{PREFIX}_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
