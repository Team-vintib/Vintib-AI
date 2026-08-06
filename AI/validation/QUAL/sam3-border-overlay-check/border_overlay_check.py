"""스파이크: 옷을 한 번만 세그먼트하고 그 크롭 안에서 곧바로 하자를 탐지한 뒤, bbox
사각형 대신 마스크 윤곽선+반투명 채우기로 표시하는 것만 테스트한다.

파츠 분할(`../sam3-parts-segment-check/`)은 실측 결과가 나빠 폐기했다 — 그 폴더는 기록으로
남겨두고 건드리지 않는다. 이 스파이크는 원래 계획대로 "옷 한 번 세그먼트 -> 하자 탐지"
(프로덕션과 같은 단계 수)만 다루고, 표현 방식(bbox vs border)만 비교한다.

`Sam3Caller`/`crop_and_mask_to`/`draw_bordered_findings`는 새로 만들지 않고
`sam3-parts-segment-check/`의 검증된 구현을 그대로 재사용한다(파츠 관련 함수·모듈은
가져오지 않는다 — `parts.py`는 아예 import하지 않는다).

사전 준비: `../sam3-condition-check/requirements-sam3.txt`와 동일(torch/transformers/opencv).
프로덕션(`app/`, `worker/`)은 건드리지 않는다.

⚠️ 이 스크립트는 실행되지 않았다 — GPU/gated 모델 접근이 필요해 사용자가 직접 돌려야 한다.
"""

import json
import sys
from pathlib import Path

from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, "..")
import qc_shared  # noqa: E402

sys.path.insert(0, "../sam3-parts-segment-check")
from border_overlay import draw_bordered_findings  # noqa: E402
from sam3_caller import Sam3Caller, crop_and_mask_to  # noqa: E402

# ---------------- 설정 ----------------
# sam3-condition-check/sam3_qc_test_masking.ipynb(§0-6)가 실제로 실측 검증한 값과 맞춘다.
# 이전엔 0.05로 임의로 적어둬서 그 노트북에서 잡히던 하자가 이 파이프라인에서는 0건으로
# 나오는 회귀가 있었다(2026-08-06 확인) — 크롭 여백이 좁아져 경계 하자가 잘려나갔다.
GARMENT_CROP_PAD_RATIO = 0.06
# qc_shared.filter_by_garment()의 기본값(GARMENT_OVERLAP_MIN=0.7)은 masking 노트북이
# §0-6에서 실측으로 확정한 0.6보다 더 엄격하다 — 0.7을 그대로 쓰면 실제로는 의류 안에 있는
# 하자도 "배경(off-garment)"으로 잘못 걸러진다. 그래서 이 파이프라인에서는 명시적으로
# 0.6을 준다(qc_shared의 공용 기본값은 다른 스파이크에 영향 줄 수 있어 그대로 둔다).
GARMENT_OVERLAP_MIN = 0.6
# ---------------------------------------

OUTPUT_DIR = Path("./outputs/border_overlay_check")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def detect_defects_and_benigns(caller: Sam3Caller, image: Image.Image, threshold: float) -> tuple:
    ve = caller.vision_embeds(image)
    defects = [
        inst
        for defect_type, prompt in qc_shared.DEFECT_PROMPTS.items()
        for inst in caller.detect(image, defect_type, prompt, threshold, ve)
    ]
    benigns = [
        inst
        for benign_type, prompt in qc_shared.BENIGN_PROMPTS.items()
        for inst in caller.detect(image, benign_type, prompt, threshold, ve)
    ]
    return defects, benigns


def run_one(caller: Sam3Caller, image: Image.Image) -> dict:
    """옷 한 번 세그먼트 -> 그 크롭 안에서 곧바로 하자 탐지(파츠 단계 없음, 프로덕션과 같은
    단계 수)."""
    full_size = image.size
    garment_threshold = qc_shared.BACKEND_THRESHOLDS["sam3"]["garment_score"]
    defect_threshold = qc_shared.BACKEND_THRESHOLDS["sam3"]["score"]

    ve_full = caller.vision_embeds(image)
    garment_instances = caller.detect(
        image, "GARMENT", qc_shared.GARMENT_PROMPT, garment_threshold, ve_full
    )
    garment = qc_shared.pick_largest(garment_instances)

    if garment is None:
        detect_image, crop_box, garment_mask = image, None, None
    else:
        garment_mask = garment["mask"]
        detect_image, crop_box = crop_and_mask_to(
            image, garment["bbox"], garment_mask, GARMENT_CROP_PAD_RATIO
        )

    defects, benigns = detect_defects_and_benigns(caller, detect_image, defect_threshold)
    if crop_box is not None:
        defects = qc_shared.remap_instances_to_full(defects, crop_box, full_size)
        benigns = qc_shared.remap_instances_to_full(benigns, crop_box, full_size)

    kept, _dropped_off_garment = qc_shared.filter_by_garment(
        defects, garment_mask, min_overlap=GARMENT_OVERLAP_MIN
    )
    kept, _dropped_benign = qc_shared.suppress_benign(kept, benigns)
    kept, _dropped_dupe = qc_shared.dedupe_cross_type(kept)
    kept = qc_shared.renumber(kept)

    return {"kept": kept, "garment_found": garment is not None}


def main() -> None:
    image_paths = qc_shared.list_images()
    if not image_paths:
        raise FileNotFoundError(
            "sample_images/ 에 이미지가 없습니다 (qc_shared.SHARED_IMAGE_DIR 참고)."
        )

    caller = Sam3Caller()
    print(f"이미지 {len(image_paths)}장: {[p.name for p in image_paths]}")

    summary = []
    for path in image_paths:
        print(f"\n--- {path.name} ---")
        image = Image.open(path).convert("RGB")
        result = run_one(caller, image)

        bbox_overlay = qc_shared.draw_numbered_boxes(image, result["kept"])
        Image.fromarray(bbox_overlay).save(OUTPUT_DIR / f"{path.stem}_bbox.png")

        border_overlay = draw_bordered_findings(
            image, result["kept"], qc_shared.KOREAN_LABELS, qc_shared.korean_font_path
        )
        Image.fromarray(border_overlay).save(OUTPUT_DIR / f"{path.stem}_border.png")

        row = {
            "image": path.name,
            "garment_found": result["garment_found"],
            "finding_count": len(result["kept"]),
            "findings": qc_shared.to_serializable(result["kept"]),
        }
        summary.append(row)
        print(f"  하자 {row['finding_count']}건, garment_found={row['garment_found']}")

    out_json = OUTPUT_DIR / "result.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장 -> {out_json}")
    print(f"오버레이 PNG -> {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
