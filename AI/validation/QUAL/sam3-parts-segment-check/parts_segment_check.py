"""스파이크: "옷 전체 크롭 → 하자 탐지"(현재 방식) vs "옷 → 파츠별 조각 → 파츠 안에서 하자
탐지"(새 방식)를 같은 이미지로 나란히 돌려 비교한다. bbox 사각형 대신 마스크 윤곽선+반투명
채우기로 하자를 표시하는 것도 같이 테스트한다.

**프로덕션(`app/`, `worker/`)은 건드리지 않는다.** 여기서 잘 나오면 별도 계획 문서로
프로덕션 반영 여부를 결정한다(CH006이 sam3-condition-check 스파이크를 승격했던 것과 같은
절차). 이 스크립트 자체는 두 파이프라인의 산출물(overlay PNG·JSON)을 비교하려고 만든
것이지, 어느 쪽이 낫다고 이미 결론 내린 게 아니다.

**두 파이프라인이 공유하는 로직**(의류 탐지·크롭+마스킹·양성 억제·cross-type dedup·
좌표 remap)은 `qc_shared.py`를 그대로 재사용한다 — 다른 QUAL 스파이크들과 같은 이유로,
비교가 성립하려면 두 파이프라인이 "파츠 단계 유무" 말고는 전부 같은 로직을 써야 한다.

사전 준비 (`sam3-condition-check/requirements-sam3.txt`와 동일한 의존성 재사용):
1) `pip install -r ../sam3-condition-check/requirements-sam3.txt` (torch>=2.4,
   transformers>=5.0, opencv-python)
2) `facebook/sam3`는 gated repo — `huggingface-cli login` 또는 `HF_TOKEN` 필요
3) 이미지: `sam3-condition-check/sample_images/`에 이미 있는 공용 샘플을 그대로 쓴다
   (`qc_shared.list_images()`)

⚠️ 이 스크립트는 실행되지 않았다 — GPU/gated 모델 접근이 필요해 사용자가 직접 돌려야
한다(`AI/CLAUDE.md`: 무거운 GPU 추론은 AI가 실행하지 않는다). 배선 확인만 하려면
DRY_RUN=True로 두면 모델 로드 없이 파이프라인 분기(파츠 발견/미발견, 폴백 등)만 점검할 수
있다 — 다만 이 경우 실제 탐지 결과는 항상 빈 리스트다.
"""

import json
import sys
from pathlib import Path

from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, "..")
import qc_shared  # noqa: E402

from border_overlay import draw_bordered_findings, draw_part_boundaries  # noqa: E402
from parts import (  # noqa: E402
    PART_CROP_PAD_RATIO,
    PART_PROMPTS_BY_GROUP,
    PART_SCORE_THRESHOLD,
    part_group_for,
)
from sam3_caller import Sam3Caller, crop_and_mask_to  # noqa: E402

# ---------------- 설정 ----------------
CATEGORY = "TOP_KNIT"  # qc_shared.DEFECT_PROMPTS/PART_PROMPTS_BY_GROUP 를 고르는 키
GARMENT_CROP_PAD_RATIO = 0.05  # 프로덕션 registry.py의 같은 이름 상수와 동일한 값 사용 권장
DRY_RUN = False  # True면 모델을 로드하지 않고 배선만 확인(탐지 결과는 항상 빈 리스트)
# ---------------------------------------

OUTPUT_DIR = Path("./outputs/parts_segment_check")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _detect_defects_and_benigns(caller: Sam3Caller, image: Image.Image, dry_run: bool) -> tuple:
    if dry_run:
        return [], []
    threshold = qc_shared.BACKEND_THRESHOLDS["sam3"]["score"]
    vision_embeds = caller.vision_embeds(image)
    defects = [
        inst
        for defect_type, prompt in qc_shared.DEFECT_PROMPTS.items()
        for inst in caller.detect(image, defect_type, prompt, threshold, vision_embeds)
    ]
    benigns = [
        inst
        for benign_type, prompt in qc_shared.BENIGN_PROMPTS.items()
        for inst in caller.detect(image, benign_type, prompt, threshold, vision_embeds)
    ]
    return defects, benigns


def _finalize(defects, benigns, garment_mask):
    """공통 후처리: 의류 겹침 필터 → 양성 억제 → cross-type dedup → 번호 매기기.

    두 파이프라인(baseline/parts)이 여기서부터는 완전히 같은 로직을 탄다 — 차이는 오직
    "defects/benigns를 어떤 단계에서 모았는가"뿐이어야 비교가 공정하다.
    """
    kept, _dropped_off_garment = qc_shared.filter_by_garment(defects, garment_mask)
    kept, _dropped_benign = qc_shared.suppress_benign(kept, benigns)
    kept, _dropped_dupe = qc_shared.dedupe_cross_type(kept)
    return qc_shared.renumber(kept)


def _detect_garment(caller: Sam3Caller, image: Image.Image, dry_run: bool):
    """(garment mask 전체좌표, garment bbox 절대픽셀) 또는 (None, None)."""
    if dry_run:
        return None, None
    threshold = qc_shared.BACKEND_THRESHOLDS["sam3"]["garment_score"]
    ve = caller.vision_embeds(image)
    instances = caller.detect(image, "GARMENT", qc_shared.GARMENT_PROMPT, threshold, ve)
    picked = qc_shared.pick_largest(instances)
    if picked is None:
        return None, None
    return picked["mask"], picked["bbox"]


def run_baseline(caller: Sam3Caller, image: Image.Image, dry_run: bool) -> dict:
    """현재 방식: 의류 전체를 크롭+마스킹한 뒤 그 안에서 곧바로 하자를 탐지한다."""
    full_size = image.size
    garment_mask, garment_bbox = _detect_garment(caller, image, dry_run)

    if garment_mask is None:
        detect_image, crop_box = image, None
    else:
        detect_image, crop_box = crop_and_mask_to(
            image, garment_bbox, garment_mask, GARMENT_CROP_PAD_RATIO
        )

    defects, benigns = _detect_defects_and_benigns(caller, detect_image, dry_run)
    if crop_box is not None:
        defects = qc_shared.remap_instances_to_full(defects, crop_box, full_size)
        benigns = qc_shared.remap_instances_to_full(benigns, crop_box, full_size)

    kept = _finalize(defects, benigns, garment_mask)
    return {"kept": kept, "garment_found": garment_mask is not None}


def run_parts_based(caller: Sam3Caller, image: Image.Image, category: str, dry_run: bool) -> dict:
    """새 방식: 의류 크롭 안에서 파츠를 먼저 찾고, 파츠마다 다시 크롭해서 그 안에서 하자를
    탐지한다. 각 파츠의 defects/benigns는 파츠 크롭 좌표 -> 의류 크롭 좌표 -> 원본 좌표
    순으로 두 단계 remap을 거친다."""
    full_size = image.size
    garment_mask, garment_bbox = _detect_garment(caller, image, dry_run)

    if garment_mask is None:
        # 의류를 못 찾으면 파츠 단계 자체가 성립하지 않는다 — baseline과 동일하게
        # 원본 전체에서 곧바로 탐지한다("하자 없음"과 "탐지 실패"를 구별하기 위한 안전장치,
        # 프로덕션 findings.py의 같은 원칙).
        defects, benigns = _detect_defects_and_benigns(caller, image, dry_run)
        kept = _finalize(defects, benigns, garment_mask)
        return {"kept": kept, "garment_found": False, "parts": []}

    garment_crop, garment_crop_box = crop_and_mask_to(
        image, garment_bbox, garment_mask, GARMENT_CROP_PAD_RATIO
    )

    part_prompts = PART_PROMPTS_BY_GROUP[part_group_for(category)]
    part_threshold = PART_SCORE_THRESHOLD
    ve_garment = None if dry_run else caller.vision_embeds(garment_crop)
    part_instances = (
        []
        if dry_run
        else [
            inst
            for part_name, prompt in part_prompts.items()
            for inst in caller.detect(garment_crop, part_name, prompt, part_threshold, ve_garment)
        ]
    )

    all_defects: list[dict] = []
    all_benigns: list[dict] = []
    for part in part_instances:
        part_crop, part_crop_box = crop_and_mask_to(
            garment_crop, part["bbox"], part["mask"], PART_CROP_PAD_RATIO
        )
        defects, benigns = _detect_defects_and_benigns(caller, part_crop, dry_run)
        # 파츠 크롭 좌표 -> 의류 크롭 좌표(아직 원본 좌표 아님, 다음 단계에서 한 번 더 remap).
        all_defects.extend(
            qc_shared.remap_instances_to_full(defects, part_crop_box, garment_crop.size)
        )
        all_benigns.extend(
            qc_shared.remap_instances_to_full(benigns, part_crop_box, garment_crop.size)
        )

    if not part_instances:
        # 파츠를 하나도 못 찾았으면(어휘 미스매치 등) 의류 크롭 전체에서 곧바로 탐지 —
        # baseline과 사실상 같은 경로로 폴백한다.
        all_defects, all_benigns = _detect_defects_and_benigns(caller, garment_crop, dry_run)

    # 의류 크롭 좌표 -> 원본 좌표.
    all_defects = qc_shared.remap_instances_to_full(all_defects, garment_crop_box, full_size)
    all_benigns = qc_shared.remap_instances_to_full(all_benigns, garment_crop_box, full_size)
    part_instances_full = qc_shared.remap_instances_to_full(
        part_instances, garment_crop_box, full_size
    )

    kept = _finalize(all_defects, all_benigns, garment_mask)
    return {"kept": kept, "garment_found": True, "parts": part_instances_full}


def main() -> None:
    image_paths = qc_shared.list_images()
    if not image_paths:
        raise FileNotFoundError(
            "sample_images/ 에 이미지가 없습니다 (qc_shared.SHARED_IMAGE_DIR 참고)."
        )

    caller = Sam3Caller()
    print(f"category={CATEGORY}  dry_run={DRY_RUN}  이미지 {len(image_paths)}장")

    summary = []
    for path in image_paths:
        print(f"\n--- {path.name} ---")
        image = Image.open(path).convert("RGB")

        baseline = run_baseline(caller, image, DRY_RUN)
        parts_based = run_parts_based(caller, image, CATEGORY, DRY_RUN)

        stem = path.stem
        baseline_overlay = qc_shared.draw_numbered_boxes(image, baseline["kept"])
        Image.fromarray(baseline_overlay).save(OUTPUT_DIR / f"{stem}_baseline_bbox.png")

        border_overlay = draw_bordered_findings(
            image, parts_based["kept"], qc_shared.KOREAN_LABELS, qc_shared.korean_font_path
        )
        Image.fromarray(border_overlay).save(OUTPUT_DIR / f"{stem}_parts_border.png")

        if parts_based["parts"]:
            part_debug = draw_part_boundaries(
                image, parts_based["parts"], qc_shared.KOREAN_LABELS, qc_shared.korean_font_path
            )
            Image.fromarray(part_debug).save(OUTPUT_DIR / f"{stem}_parts_debug.png")

        row = {
            "image": path.name,
            "garment_found": baseline["garment_found"],
            "parts_found": [p["type"] for p in parts_based["parts"]],
            "baseline_finding_count": len(baseline["kept"]),
            "parts_based_finding_count": len(parts_based["kept"]),
            "baseline_findings": qc_shared.to_serializable(baseline["kept"]),
            "parts_based_findings": qc_shared.to_serializable(parts_based["kept"]),
        }
        summary.append(row)
        print(
            f"  파츠 탐지: {row['parts_found']}  "
            f"baseline={row['baseline_finding_count']}건  "
            f"parts_based={row['parts_based_finding_count']}건"
        )

    out_json = OUTPUT_DIR / "result.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장 -> {out_json}")
    print(f"오버레이 PNG -> {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
