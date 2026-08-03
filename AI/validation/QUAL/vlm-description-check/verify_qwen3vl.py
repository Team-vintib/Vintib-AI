"""Qwen3-VL-4B-Instruct 가동 여부 1차 점검 — sVLM 후보 검증(CH009) 1단계.

이 스크립트가 확인하는 건 딱 하나: 이 노트북(RTX 4070 Laptop, VRAM 8GB)에서
Qwen3-VL-4B-Instruct를 4bit 양자화로 띄우고, SAM3 산출물(sam3-condition-check/outputs/
denim_qc.json)의 실제 bbox+한글 라벨을 넣어 한국어 한 줄 설명을 뽑을 수 있는가.
한국어 품질 정밀 평가·할루시네이션 육안 대조·SAM3와의 동시 VRAM 적재·지연시간 예산
검증(CH009 "검증 축" 전체)은 이 스모크 테스트를 통과한 다음 단계다.

실행:
    conda activate qual
    cd AI/validation/QUAL/vlm-description-check
    pip install -r requirements-vlm.txt   # qual 환경엔 bitsandbytes만 없음
    python verify_qwen3vl.py

최초 실행은 Qwen/Qwen3-VL-4B-Instruct 가중치(~8.9GB)를 허깅페이스에서 내려받는다.
GMS 무관 공개 체크포인트(gated 아님)라 AI/CLAUDE.md의 GMS 하드룰과 관련 없다.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "..")  # qc_shared.py(QUAL/), sam3-condition-check 산출물 재사용

import torch
from PIL import Image
from qc_shared import pad_bbox_clamped

from loaders import describe_defect, load_qwen_vl
from model_registry import ACTIVE_QUANTIZATION, ACTIVE_VLM, VLM_MODELS

# ---------------- 설정 ----------------
TARGET_IMAGE = Path("../sam3-condition-check/sample_images/denim.jpg")
TARGET_FINDINGS = Path("../sam3-condition-check/outputs/denim_qc.json")
CROP_PAD_RATIO = 0.6  # bbox가 17x20px 수준으로 작아서 맥락이 보이게 넉넉히 패딩한다
# ---------------------------------------

MODEL_ID = VLM_MODELS[ACTIVE_VLM]


def _vram_report(tag: str) -> tuple[float, float]:
    """(allocated_MB, peak_MB)를 찍고 반환. sam3_qc_test.ipynb §9의 관례와 동일."""
    if not torch.cuda.is_available():
        print(f"{tag:<20} (CPU 모드 - VRAM 측정 없음)")
        return (0.0, 0.0)
    alloc = torch.cuda.memory_allocated() / 1024**2
    peak = torch.cuda.max_memory_allocated() / 1024**2
    print(f"{tag:<20} allocated={alloc:9.1f} MB ({alloc / 1024:.2f} GB)   peak={peak:9.1f} MB")
    return (alloc, peak)


def main() -> None:
    print(f"model_id={MODEL_ID}  quantization={ACTIVE_QUANTIZATION}")
    print(f"torch={torch.__version__}  cuda_available={torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"gpu={torch.cuda.get_device_name(0)}")
        torch.cuda.reset_peak_memory_stats()

    _vram_report("로드 전")

    t0 = time.time()
    bundle = load_qwen_vl(MODEL_ID, quantization=ACTIVE_QUANTIZATION)
    load_s = time.time() - t0
    print(f"로드 소요: {load_s:.1f}s")
    _vram_report("로드 후")

    findings = json.loads(TARGET_FINDINGS.read_text(encoding="utf-8"))
    image = Image.open(TARGET_IMAGE).convert("RGB")
    print(
        f"\n대상 이미지: {TARGET_IMAGE.name}  size={image.size}  "
        f"findings={len(findings['instances'])}"
    )

    for inst in findings["instances"]:
        bbox = pad_bbox_clamped(inst["bbox"], CROP_PAD_RATIO, image.size)
        crop = image.crop(bbox)

        t0 = time.time()
        description = describe_defect(bundle, crop, defect_label=inst["label"])
        gen_s = time.time() - t0

        print(
            f"\n[{inst['no']}] {inst['label']} "
            f"(conf={inst['confidence']:.2f}, bbox={inst['bbox']})"
        )
        print(f"    crop_size={crop.size}  gen={gen_s:.2f}s")
        print(f"    -> {description}")

    _vram_report("전체 추론 후")


if __name__ == "__main__":
    main()
