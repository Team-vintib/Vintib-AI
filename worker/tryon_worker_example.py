"""가상 시착 워커 — VLM 캡션 → (신체 치수 근사 + 핏 계산) → FLUX worn-reference 생성.

**CH027: CatVTON 합성 단계 없음.** 예전엔 FLUX가 만든 worn-reference를 CatVTON이 다시
마스크 영역만 실제 옷 사진 조건부로 재합성했는데(`tryon_worker_catvton_legacy.py`에 그대로
보존), CatVTON이 마스크 영역을 항상 순수 노이즈에서부터 다시 그리는 구조라 FLUX가 이미
정확하게 반영한 디테일(끈, 이너 티, 원단 질감)을 오히려 지워버리는 문제가 있었다. FLUX.2가
`image=[사람 사진, 옷 사진]` 두 장을 함께 참조하도록 바꾸자 CatVTON 없이도 색상/로고/질감을
충분히 정확하게 반영하면서 자연스러운 드레이프까지 얻어져(`docs/plans/AI/
CH027-tryon-flux-final-pipeline.md`), FLUX 결과를 그대로 최종본으로 쓴다.

**GPU 없이도 돌릴 수 있다.** `TRYON_VLM_BACKEND=mock`(기본값)/`TRYON_FLUX_BACKEND=mock`
(기본값)이면 각각 정적 문구/참조 이미지 그대로 반환으로 대체되어, 전 경로(잡 폴링 → 결과
업로드)를 GPU 없이도 검증할 수 있다(`quality_check_worker_example.py`와 같은 컨벤션).

```bash
python tryon_worker_example.py                                     # 전부 mock
TRYON_VLM_BACKEND=qwen3_vl TRYON_FLUX_BACKEND=flux2_klein python tryon_worker_example.py
```

**두 모델(VLM/FLUX)은 동시에 상주하지 않는다.** 프로덕션엔 GPU 서버가 없고 팀원 노트북
(6GB급)이 워커로 붙는 구조라(`AI/docs/infra-architecture.md`), VLM 캡션이 끝나면 명시적으로
`del`+`torch.cuda.empty_cache()`한 뒤 FLUX를 로드한다.

**최종 결과에는 실제 고객 사진(`user_image_url`)이 나온다.** FLUX worn-reference는 그
고객 사진을 참조로 생성하므로 재사용/캐싱 대상이 아니다 — 매 요청마다 다시 생성한다
(`AI/docs/tryon-advancement-strategy.md` §10 프로덕션 반영 절 참고).

설계: `.claude/plans/ai/CH019-tryon-worker-promotion.md`, `docs/plans/AI/
CH027-tryon-flux-final-pipeline.md`
"""

import gc
import os
import sys

import torch
from PIL import Image

from base_worker import BaseWorker
from storage_utils import download_image, upload_image

# body_estimate.py/model.adaptive_fit/model.fit_summary/utils.py는 순수 계산 + PIL 리사이즈
# 유틸이라(무거운 CatVTON 모델 자체는 더 이상 안 씀) 가볍다. 실제 CatVTON 합성 로직은
# `tryon_worker_catvton_legacy.py`가 필요할 때만 따로 import한다.
CATVTON_CODE_PATH = os.getenv(
    "CATVTON_CODE_PATH",
    os.path.join(os.path.dirname(__file__), "models", "catvton"),
)
sys.path.insert(0, CATVTON_CODE_PATH)

from body_estimate import estimate_body_measurements  # noqa: E402
from model.adaptive_fit import compute_width_adjustment  # noqa: E402
from model.fit_summary import fit_summary_ko  # noqa: E402
from utils import resize_and_crop, resize_and_padding  # noqa: E402

# `tryon_flux`/`quality_vlm`은 `sam3`/`garment_measurement`와 같은 이유로 진짜
# 서브패키지다 -- 부모 디렉터리(worker/models/)를 sys.path에 넣고 네임스페이스로만 접근한다.
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
sys.path.insert(0, os.getenv("TRYON_MODEL_CODE_PATH", _MODELS_DIR))

from quality_vlm import registry as vlm_registry  # noqa: E402
from quality_vlm.loader import generate_from_image, load_qwen_vl  # noqa: E402
from tryon_flux import registry as flux_registry  # noqa: E402
from tryon_flux.generator import build_generator  # noqa: E402
from tryon_flux.prompts import (  # noqa: E402
    build_dress_prompt,
    build_regular_dress_prompt,
    fit_descriptor,
)

WIDTH, HEIGHT = 768, 1024  # verify_fit_tryon.py 와 동일한 기본값

# 어떤 VLM/FLUX 백엔드로 돌릴지. 각 registry.py의 *_BACKENDS 딕셔너리 키.
TRYON_VLM_BACKEND = os.getenv("TRYON_VLM_BACKEND", vlm_registry.ACTIVE_VLM_BACKEND)
TRYON_FLUX_BACKEND = os.getenv("TRYON_FLUX_BACKEND", flux_registry.ACTIVE_FLUX_BACKEND)

CAPTION_PROMPT = (
    "Describe this product's color, material, and style in one short phrase for a "
    "fashion photo shoot brief, e.g. 'a black wide-brim nylon bucket hat' or 'a "
    "dark navy denim jacket'. Do NOT mention the cut, fit, or silhouette (not "
    "'loose', 'fitted', 'oversized', etc.) -- that will be specified separately. "
    "Do not mention a person."
)


class TryonWorker(BaseWorker):
    feature = "tryon"

    def __init__(self):
        super().__init__()
        self._vlm_bundle = None
        self._flux_generator = None

    def _ensure_vlm_loaded(self):
        """describer와 달리 실패해도 mock으로 폴백하지 않는다 -- 캡션은 이 파이프라인의
        1단계라 실패하면 job 전체가 실패하는 게 맞다(캡션 없이 뒤 단계를 진행할 수 없음)."""
        if self._vlm_bundle is not None or TRYON_VLM_BACKEND == "mock":
            return
        config = vlm_registry.vlm_config(TRYON_VLM_BACKEND)
        print(f"[{self.worker_id}] VLM 로딩 중... (backend={TRYON_VLM_BACKEND})")
        try:
            self._vlm_bundle = load_qwen_vl(config["model_id"], quantization=config["quantization"])
        except Exception:
            # 로딩 도중 죽으면(네트워크 순단 등) 그 시점까지 GPU에 올라간 텐서가
            # empty_cache() 없이 그대로 남는다 -- 다음 job이 그 자리를 못 찾고 "CPU/disk로
            # 분산" 에러로 연쇄 실패하는 걸 실측으로 확인했다. 재시도가 최소한 깨끗한 VRAM
            # 상태에서 시작하도록 여기서 반드시 정리한다.
            gc.collect()
            torch.cuda.empty_cache()
            raise
        print(f"[{self.worker_id}] VLM 로딩 완료")

    def _unload_vlm(self):
        if self._vlm_bundle is None:
            return
        self._vlm_bundle = None
        # bitsandbytes 4bit 양자화 + accelerate device_map="auto" 훅이 참조 순환을 만든다 --
        # gc.collect() 없이 empty_cache()만 부르면 VRAM이 실제로는 반환되지 않는다.
        gc.collect()
        torch.cuda.empty_cache()

    def _caption_garment(self, cloth_image: Image.Image) -> str:
        if TRYON_VLM_BACKEND == "mock":
            return "garment"
        self._ensure_vlm_loaded()
        config = vlm_registry.vlm_config(TRYON_VLM_BACKEND)
        caption = generate_from_image(
            self._vlm_bundle, cloth_image, CAPTION_PROMPT, max_new_tokens=config["max_new_tokens"]
        )
        self._unload_vlm()
        return caption

    def _generate_worn_reference(
        self, person_image: Image.Image, cloth_image: Image.Image, prompt: str
    ) -> Image.Image:
        if self._flux_generator is None:
            print(f"[{self.worker_id}] FLUX 로딩 중... (backend={TRYON_FLUX_BACKEND})")
            try:
                self._flux_generator = build_generator(TRYON_FLUX_BACKEND)
            except Exception:
                # VLM과 같은 이유 -- 로딩 도중 죽어도(네트워크 순단 등) GPU에 이미 올라간
                # 만큼은 empty_cache()로 반드시 비운다. 안 그러면 다음 job(VLM 로딩)이
                # 그 자리를 못 찾고 연쇄로 계속 실패한다(실측 확인).
                gc.collect()
                torch.cuda.empty_cache()
                raise
            print(f"[{self.worker_id}] FLUX 로딩 완료")

        try:
            worn_reference = self._flux_generator.generate(person_image, cloth_image, prompt)
        finally:
            # generate() 자체가 실패해도(예: 생성 도중 OOM) unload는 반드시 실행 -- 예전엔
            # try/finally가 없어서 실패 시 _flux_generator가 언로드 안 된 채 남았다.
            if hasattr(self._flux_generator, "unload"):
                self._flux_generator.unload()
            self._flux_generator = None

        return worn_reference

    def run_inference(self, payload: dict) -> dict:
        """
        payload 예:
        {
            "user_image_url": "https://.../person.jpg",
            "product_image_url": "https://.../cloth.jpg",
            "mask_type": "upper",          # upper | lower — fit_title/description 라벨에만 씀
            "fit_type": "regular",         # regular | oversized (cropped는 가드레일상 없음) — 프롬프트 강조 톤에만 씀
            "body_height_cm": 170.0,       # 선택, BE 확정 컬럼
            "body_weight_kg": 65.0,        # 선택, BE 확정 컬럼
            "body_waist_cm": 75.0,         # 선택, BE 컬럼 미확정 -- 있으면 근사보다 우선
            "garment_measurements": {"WAIST_WIDTH": 42.0}   # 선택
        }

        `body_waist_cm`이 있으면 그 실측값을, 없고 `body_height_cm`/`body_weight_kg`가
        있으면 `body_estimate.py`의 키/몸무게 기반 근사치를 쓴다. 그마저 없거나
        `garment_measurements["WAIST_WIDTH"]`가 없으면 핏 계산 없이 "regular fit"으로
        FLUX worn-reference를 생성한다.

        `num_inference_steps`/`guidance_scale`는 CatVTON 전용이었던 필드라 CH027부터는
        받아도 무시한다(계약 하위호환 — BE가 계속 보내도 에러 안 남).

        AI는 이 값들을 BE에 재조회하지 않고 payload로 받은 그대로 쓴다.
        """
        mask_type = payload.get("mask_type", "upper")
        if mask_type not in ("upper", "lower"):
            raise ValueError(f"지원하지 않는 mask_type: {mask_type}")
        fit_type = payload.get("fit_type", "regular")
        if fit_type not in ("regular", "oversized"):
            raise ValueError(f"지원하지 않는 fit_type: {fit_type}")

        person_image = download_image(payload["user_image_url"]).convert("RGB")
        cloth_image = download_image(payload["product_image_url"]).convert("RGB")

        person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))
        cloth_image = resize_and_padding(cloth_image, (WIDTH, HEIGHT))

        # --- 1단계: 상품 사진 캡션 (VLM) ---------------------------------------
        garment_caption = self._caption_garment(cloth_image)

        # --- 2단계: 핏 계산 (신체 치수 근사 + 상품 사이즈표) ---------------------
        body_waist_cm = payload.get("body_waist_cm")
        adaptive_masking_used = False
        if body_waist_cm is None:
            height_cm = payload.get("body_height_cm")
            weight_kg = payload.get("body_weight_kg")
            if height_cm is not None and weight_kg is not None:
                try:
                    body_waist_cm = estimate_body_measurements(height_cm, weight_kg)["waist_cm"]
                except ValueError:
                    body_waist_cm = None

        garment_measurements = payload.get("garment_measurements")
        garment_waist_width = garment_measurements.get("WAIST_WIDTH") if garment_measurements else None
        ratio = compute_width_adjustment(body_waist_cm, garment_waist_width)

        # 고객용 "한 줄 핏 예상"(fit_title/fit_description) -- adaptive_fit이 지금
        # WAIST_WIDTH 축만 지원하므로(§7.5), 이 ratio는 mask_type="lower"일 때만
        # 의미가 있다. "upper"는 garment_measurements에 WAIST_WIDTH가 실릴 일이 없어
        # ratio가 자연히 None이 되고, fit_summary_ko()도 None을 그대로 돌려준다.
        fit_summary = fit_summary_ko(ratio, "waist" if mask_type == "lower" else "chest")

        if ratio is not None:
            fit_phrase, needs_emphasis = fit_descriptor(ratio)
            dress_prompt = build_dress_prompt(garment_caption, fit_phrase, needs_emphasis)
            adaptive_masking_used = True
        else:
            dress_prompt = build_regular_dress_prompt(garment_caption)

        # --- 3단계: FLUX worn-reference 생성 (최종 결과) -------------------------
        # image=[person_image, cloth_image] 두 장을 함께 참조로 준다 -- 옷의 실제 색상/
        # 로고/질감은 cloth_image에서, 포즈/배경/기존 옷차림은 person_image에서 상속된다.
        result_image = self._generate_worn_reference(person_image, cloth_image, dress_prompt)

        image_url = upload_image(result_image, prefix="tryon-results")

        return {
            "image_url": image_url,
            # CatVTON 없이 3단계 결과가 바로 최종본이라 별도 마스크/중간 산출물이 없다 --
            # 계약(`docs/requests/BE/040-tryon-job-contract.md`)엔 "FE 노출 불필요, 디버깅용"
            # 이라 명시돼 있어 null로 둬도 BE 파싱이 깨지지 않는다(BE는 image_url/fit_title/
            # fit_description만 읽음, TryOnResultService.refreshStatus 확인).
            "mask_preview_url": None,
            "worn_reference_url": image_url,
            "fit_type": fit_type,
            "adaptive_masking_used": adaptive_masking_used,
            "fit_title": fit_summary["title"] if fit_summary else None,
            "fit_description": fit_summary["description"] if fit_summary else None,
        }


if __name__ == "__main__":
    TryonWorker().loop()
