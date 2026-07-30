"""실제 판매자 사진(A4/메모지 + 옷) 한 장으로 실측 파이프라인 앞 2단계를 검증한다.

합성 이미지(배경-A4 대비가 인위적으로 좋음)와 달리, 실제 사진은 바닥재/조명 때문에
대비가 약할 수 있다는 사용자 지적을 확인하기 위한 스크립트. 결과 이미지와 수치를
`report_real_*.json`으로 남기고, md 리포트 작성 후 이 스크립트와 함께 정리한다.

카테고리 검증 상태: 사진 속 의류는 지퍼/카라가 있는 긴팔 아우터라 현재 실사진으로
검증된 3개 카테고리(반팔 상의/바지/긴팔 원피스) 중 어느 것에도 해당하지 않는다.
따라서 랜드마크 검출(3단계)은 이 사진으로 의미 있게 테스트할 수 없고, 여기서는
카테고리 무관 단계인 기준 물체 검출/원단 분할만 돌린다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "worker" / "models"))

import cv2
import numpy as np

from garment_measurement import registry
from garment_measurement.reference_detector import (
    OpenCVContourReferenceDetector,
    _CANNY_LOW,
    _CANNY_HIGH,
)
from garment_measurement.segmenter import GrabCutGarmentSegmenter

HERE = Path(__file__).resolve().parent
IMAGE_PATH = HERE / "valid_image.jpg"

OUT_INPUT = HERE / "report_real_00_input.png"
OUT_REFERENCE = HERE / "report_real_01_reference.png"
OUT_SEGMENTATION = HERE / "report_real_02_segmentation.png"
OUT_EDGES = HERE / "report_real_01b_edges.png"
OUT_JSON = HERE / "report_real_result.json"


def find_reference_contour_debug(frame_bgr):
    """OpenCVContourReferenceDetector 내부 로직을 그대로 재현해 디버그용 박스 좌표를 얻는다.

    프로덕션 detect()는 found/ratio만 반환하고 박스 좌표를 노출하지 않아서, 시각화를
    위해 여기서만 별도로 재현한다(판정 자체는 아래에서 진짜 OpenCVContourReferenceDetector로
    한다 — 이 함수는 그림 그리기 전용).
    """
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

    cv2.imwrite(str(OUT_INPUT), frame)

    result = {"image": str(IMAGE_PATH.name), "image_size": [frame.shape[1], frame.shape[0]]}

    # --- 1단계: 기준 물체(A4/메모지) 검출 ---
    edges, candidates = find_reference_contour_debug(frame)
    cv2.imwrite(str(OUT_EDGES), edges)

    detector = OpenCVContourReferenceDetector()
    detection = detector.detect(str(IMAGE_PATH), product_id=1)

    ref_viz = frame.copy()
    candidates_sorted = sorted(candidates, key=lambda c: -c["area"])
    for i, cand in enumerate(candidates_sorted[:8]):
        color = (0, 200, 0) if cand["within_tolerance"] else (0, 0, 220)
        box_int = cand["box"].astype(int)
        cv2.drawContours(ref_viz, [box_int], 0, color, 2)
        label = f"ratio {cand['ratio']:.2f} (dev {cand['deviation']:.0%})"
        x, y = box_int[0]
        cv2.putText(
            ref_viz, label, (int(x), max(int(y) - 8, 14)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA,
        )

    status_text = (
        f"REFERENCE FOUND (ratio->cm {detection.pixel_to_cm_ratio:.4f})"
        if detection.found
        else "REFERENCE NOT FOUND"
    )
    status_color = (0, 200, 0) if detection.found else (0, 0, 220)
    cv2.putText(
        ref_viz, status_text, (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2, cv2.LINE_AA
    )
    cv2.imwrite(str(OUT_REFERENCE), ref_viz)

    result["reference_detection"] = {
        "found": bool(detection.found),
        "pixel_to_cm_ratio": detection.pixel_to_cm_ratio,
        "quad_candidates_considered": len(candidates),
        "candidates_within_a4_aspect_tolerance": sum(
            1 for c in candidates if c["within_tolerance"]
        ),
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
        cv2.putText(
            seg_viz, "GARMENT BBOX", (x, max(y - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2, cv2.LINE_AA,
        )
    else:
        cv2.putText(
            seg_viz, "GARMENT NOT FOUND", (16, 32),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 220), 2, cv2.LINE_AA,
        )
    cv2.imwrite(str(OUT_SEGMENTATION), seg_viz)

    result["segmentation"] = {
        "found": bool(seg.found),
        "bbox": list(seg.bbox) if seg.bbox else None,
    }

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
