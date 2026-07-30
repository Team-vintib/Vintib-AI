"""체형-의류 스펙 차이 기반 적응형 마스킹이 방향대로 동작하는지 육안 확인.

`AutoMasker`만 쓴다(diffusion 파이프라인은 안 돌린다) — 이 스크립트의 목적은 합성 품질이
아니라 "마스크 경계가 계산된 비율 방향대로 실제로 움직이는가"이기 때문에, 훨씬 무거운
CatVTONPipeline까지 돌릴 필요가 없다. `verify_fit_tryon.py`와 같은 초기화 방식(같은
person.jpg)을 쓰되 fit_type 대신 body_measurements/garment_measurements 조합을 바꿔가며
비교한다.

pytest 안 걸림 — `python verify_adaptive_masking.py`로 직접 실행 후 `result/`에 저장된
PNG를 육안 확인한다(기존 verify_*.py 관례).

**이 파일이 있는 `AI/validation/TRYON/AI_tryon/CatVTON/`은 `worker/models/catvton`을 복제한
실험용 스냅샷이라 적응형 마스킹 코드(`adaptive_fit.py`, `cloth_masker.py`의 새 함수들)가 아직
없다.** 스냅샷에 따로 복사해두는 대신, 검증하려는 실제 프로덕션 코드(`worker/models/catvton`)를
sys.path 맨 앞에 꽂아서 이 스크립트가 실제 배포될 코드를 그대로 쓰게 한다 — 여기서 검증하는
대상은 "새로 실험 중인 코드"가 아니라 "이미 구현된 프로덕션 코드"이기 때문이다.
"""

import os
import sys
from datetime import datetime

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
_PRODUCTION_CATVTON_PATH = os.path.join(_REPO_ROOT, "worker", "models", "catvton")
sys.path.insert(0, _PRODUCTION_CATVTON_PATH)

from huggingface_hub import snapshot_download  # noqa: E402
from PIL import Image  # noqa: E402

from model.adaptive_fit import compute_mask_adjustment  # noqa: E402
from model.cloth_masker import AutoMasker, vis_mask  # noqa: E402
from utils import resize_and_crop  # noqa: E402

print("=== AutoMasker 초기화 ===")
repo_path = snapshot_download(repo_id="zhengchong/CatVTON")
automasker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device="cuda",
)
print("초기화 완료")

OUT_DIR = os.path.join("result", "adaptive_masking_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 768, 1024
PERSON_PATH = "image/person.jpg"

person_image = Image.open(PERSON_PATH).convert("RGB")
person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))

# --- 길이 축(상의): 키 대비 상대적으로 짧은/긴 기장 비교 -----------------------
UPPER_CASES = {
    "baseline_no_measurements": (None, None),
    "relatively_short": ({"height_cm": 190.0}, {"TOTAL_LENGTH": 55.0}),
    "relatively_long": ({"height_cm": 150.0}, {"TOTAL_LENGTH": 90.0}),
}

print("\n=== 상의(길이 축) ===")
for label, (body, garment) in UPPER_CASES.items():
    adjustment = compute_mask_adjustment("upper", body, garment)
    print(f"{label}: body={body} garment={garment} -> adjustment(dilation_px, cutoff_ratio)={adjustment}")

    mask = automasker(
        person_image,
        mask_type="upper",
        fit_type="regular",  # body/garment 둘 다 있으면 이 값은 무시되고 적응형 계산이 대신 쓰인다
        body_measurements=body,
        garment_measurements=garment,
    )["mask"]
    vis_mask(person_image, mask).save(os.path.join(OUT_DIR, f"upper_{label}.png"))

# --- 너비 축(바지 허리): 몸 대비 타이트/루즈 비교 --------------------------------
LOWER_CASES = {
    "baseline_no_measurements": (None, None),
    "snug_fit": ({"height_cm": 170.0, "waist_cm": 70.0}, {"OUTSEAM_LENGTH": 102.0, "WAIST_WIDTH": 35.0}),
    "tight_for_body": ({"height_cm": 170.0, "waist_cm": 90.0}, {"OUTSEAM_LENGTH": 102.0, "WAIST_WIDTH": 35.0}),
    "roomy_for_body": ({"height_cm": 170.0, "waist_cm": 60.0}, {"OUTSEAM_LENGTH": 102.0, "WAIST_WIDTH": 50.0}),
}

print("\n=== 바지(너비 축) ===")
for label, (body, garment) in LOWER_CASES.items():
    adjustment = compute_mask_adjustment("lower", body, garment)
    print(f"{label}: body={body} garment={garment} -> adjustment(dilation_px, cutoff_ratio)={adjustment}")

    mask = automasker(
        person_image,
        mask_type="lower",
        fit_type="regular",
        body_measurements=body,
        garment_measurements=garment,
    )["mask"]
    vis_mask(person_image, mask).save(os.path.join(OUT_DIR, f"lower_{label}.png"))

print(f"\n완료 -> {OUT_DIR}/ 안의 upper_*.png / lower_*.png 비교")
print("확인 포인트: upper는 relatively_short가 relatively_long보다 마스크 하단이 더 위에서")
print("끊겨야 하고, lower는 tight_for_body가 roomy_for_body보다 마스크 폭이 더 좁아야 한다.")
