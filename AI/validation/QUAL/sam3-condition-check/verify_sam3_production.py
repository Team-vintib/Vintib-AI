"""
프로덕션 SAM3 세그멘터(`worker/models/sam3/`) 스모크 테스트.

`sam3_qc_test_masking.ipynb`(스파이크)가 아니라 **이식이 끝난 프로덕션 패키지 자체**를
공용 이미지 세트(`qc_shared.list_images()`)로 돌려서, 마스킹 전처리 + findings 추출 +
점수 산정 + 오버레이까지 실제 서비스 코드 그대로 출력이 나오는지 확인한다.

Redis/게이트웨이가 없어도 되도록 `run_inference()`를 흉내내지 않고 `segmenter.py` /
`findings.py` / `scoring.py` / `overlay.py`를 직접 호출한다 — 이미지 업로드도 HTTP 대신
로컬 파일 저장으로 대체한다.

사전 준비:
1) `pip install -r ../../../../worker/models/sam3/requirements.txt` (torch>=2.4,
   transformers>=5.0 — sam3_qc_test_masking.ipynb 와 같은 conda 환경 재사용 가능)
2) `facebook/sam3`는 gated repo — `huggingface-cli login` 또는 `HF_TOKEN` 환경변수로
   승인된 계정 로그인 필요
3) BACKEND(아래 설정)를 "mock"으로 두면 위 준비 없이 파이프라인 배선만 확인 가능
"""

import json
import sys
from pathlib import Path

from PIL import Image

# Windows 콘솔 기본 코드페이지(cp949)는 한글 요약문의 일부 기호를 못 담아 print()가 죽는다 —
# 결과 파일은 항상 UTF-8로 저장되니 이건 콘솔 출력 전용 보정이다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 검증 스크립트 전부가 공유하는 샘플 이미지(validation/QUAL/qc_shared.py).
sys.path.insert(0, "..")
from qc_shared import list_images  # noqa: E402

# worker/models/ 를 sys.path 에 넣어야 `sam3.xxx` 네임스페이스로 프로덕션 패키지를 그대로
# 불러올 수 있다 — AI/test/conftest.py 가 pytest에서 쓰는 것과 같은 경로 규약.
_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "worker" / "models"))

from sam3 import registry  # noqa: E402
from sam3.contracts import BaseColor, GarmentCategory  # noqa: E402
from sam3.findings import extract_findings  # noqa: E402
from sam3.overlay import build_annotated_images, build_attention_maps  # noqa: E402
from sam3.prompts import select_prompt_set  # noqa: E402
from sam3.scoring import build_notes, score_findings, summarize  # noqa: E402
from sam3.segmenter import InspectionTarget, build_segmenter  # noqa: E402

# ---------------- 설정 ----------------
BACKEND = "sam3_pcs"  # "mock" 으로 바꾸면 torch/HF 로그인 없이 배선만 확인
CATEGORY = GarmentCategory.top_knit
BASE_COLOR = BaseColor.light
# ---------------------------------------

OUTPUT_DIR = Path("./outputs/verify_sam3_production")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _local_uploader(image: Image.Image, prefix: str) -> str:
    """게이트웨이 업로드 대신 로컬에 저장하고 파일 경로를 돌려준다."""
    idx = _local_uploader.counter = getattr(_local_uploader, "counter", 0) + 1
    dest = OUTPUT_DIR / f"{prefix}_{idx:02d}.png"
    image.save(dest)
    return str(dest)


def main() -> None:
    image_paths = list_images()
    if not image_paths:
        raise FileNotFoundError("sample_images/ 에 이미지가 없습니다.")

    print(f"backend={BACKEND}  category={CATEGORY.value}  base_color={BASE_COLOR.value}")
    print(f"이미지 {len(image_paths)}장: {[p.name for p in image_paths]}")
    print()

    config = registry.segmenter_config(BACKEND)
    segmenter = build_segmenter(BACKEND)
    prompt_set = select_prompt_set(CATEGORY, BASE_COLOR)
    target = InspectionTarget(
        product_id=1,
        image_urls=tuple(
            str(p) for p in image_paths
        ),  # 로컬 경로 — segmenter.load_source_image가 그대로 읽음
        prompt_set=prompt_set,
    )

    results = []
    for i, path in enumerate(image_paths):
        print(f"  [{i}] {path.name} 처리 중...")
        results.append(segmenter.segment(target, i))

    extracted = extract_findings(results, prompt_set, config)
    score, grade = score_findings(extracted.findings)
    notes = build_notes(extracted.findings, extracted.unreliable_prompts)
    attention_maps = build_attention_maps(
        results, extracted.kept_instances_by_image, extracted.findings, _local_uploader
    )
    annotated_images = build_annotated_images(results, extracted.findings, _local_uploader)

    output = {
        "model": {"backend": BACKEND, "model_id": config["model_id"], "prompt_set": prompt_set.key},
        "condition_score": score,
        "condition_grade": grade.value,
        "summary": summarize(extracted.findings),
        "findings": [f.to_dict() for f in extracted.findings],
        "section_scores": [s.to_dict() for s in extracted.section_scores],
        "attention_maps": [m.to_dict() for m in attention_maps],
        "annotated_images": [m.to_dict() for m in annotated_images],
        "notes": notes,
    }

    out_json = OUTPUT_DIR / "result.json"
    out_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print()
    print(f"결과 저장 -> {out_json}")
    print(f"어텐션 맵 PNG {len(attention_maps)}장 -> {OUTPUT_DIR}")
    print(f"넘버링 bbox 이미지 {len(annotated_images)}장 -> {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
