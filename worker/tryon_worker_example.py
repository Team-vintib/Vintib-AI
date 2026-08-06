"""가상 시착 워커 — VLM 캡션 → (신체 치수 근사 + 핏 계산) → FLUX worn-reference 생성 →
CatVTON 합성.

**GPU 없이도 돌릴 수 있다.** `TRYON_VLM_BACKEND=mock`(기본값)/`TRYON_FLUX_BACKEND=mock`
(기본값)이면 각각 정적 문구/참조 이미지 그대로 반환으로 대체되어, CatVTON까지 포함한
전 경로(잡 폴링 → 결과 업로드)를 GPU 없이도 검증할 수 있다(`quality_check_worker_example.py`
와 같은 컨벤션).

```bash
python tryon_worker_example.py                                     # 전부 mock, CatVTON만 실제
TRYON_VLM_BACKEND=qwen3_vl TRYON_FLUX_BACKEND=flux2_klein python tryon_worker_example.py
```

**세 모델(VLM/FLUX/CatVTON)은 동시에 상주하지 않는다.** 프로덕션엔 GPU 서버가 없고 팀원
노트북(6GB급)이 워커로 붙는 구조라(`AI/docs/infra-architecture.md`), 한 단계가 끝나면
명시적으로 `del`+`torch.cuda.empty_cache()`한 뒤 다음 단계를 로드한다 — 피크 VRAM은
가장 큰 단일 스테이지(FLUX, ~5-6GB) 수준으로 억제된다.

**최종 결과에는 실제 고객 사진(`user_image_url`)이 나온다.** FLUX worn-reference는 그
고객 사진을 참조로 생성하므로 재사용/캐싱 대상이 아니다 — 매 요청마다 다시 생성한다
(`AI/docs/tryon-advancement-strategy.md` §10 프로덕션 반영 절 참고).

설계: `.claude/plans/ai/CH019-tryon-worker-promotion.md`
"""

import os
import sys

import numpy as np
import torch
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download
from PIL import Image

from base_worker import BaseWorker
from storage_utils import download_image, upload_image

# 기존 검증 코드(worker/models/catvton)를 import 할 수 있도록 경로 추가.
# (구 경로는 AI/test/ → AI/validation/ 이었다 — 추론 코드는 AI/에 두지 않는다는 원칙에 따라
#  worker/models/ 로 옮겼다.)
CATVTON_CODE_PATH = os.getenv(
    "CATVTON_CODE_PATH",
    os.path.join(os.path.dirname(__file__), "models", "catvton"),
)
sys.path.insert(0, CATVTON_CODE_PATH)

from body_estimate import estimate_body_measurements  # noqa: E402
from model.adaptive_fit import compute_width_adjustment  # noqa: E402
from model.cloth_masker import AutoMasker, vis_mask  # noqa: E402
from model.fit_summary import fit_summary_ko  # noqa: E402
from model.pipeline import CatVTONPipeline  # noqa: E402
from utils import init_weight_dtype, resize_and_crop, resize_and_padding  # noqa: E402

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


def composite_with_original(
    original_image: Image.Image,
    generated_image: Image.Image,
    mask: Image.Image,
) -> Image.Image:
    """마스크 안쪽은 생성된 이미지, 바깥쪽은 원본 이미지를 사용해 합성한다."""
    original_np = np.array(original_image.resize(generated_image.size)).astype(np.float32)
    generated_np = np.array(generated_image).astype(np.float32)

    mask_np = np.array(mask.resize(generated_image.size).convert("L")).astype(np.float32) / 255.0
    mask_np = np.expand_dims(mask_np, axis=-1)

    composited = generated_np * mask_np + original_np * (1 - mask_np)
    return Image.fromarray(composited.astype(np.uint8))


def _bypass_safety_checker(self, image):
    has_nsfw_concept = [False] * len(image) if isinstance(image, list) else [False]
    return image, has_nsfw_concept


class TryonWorker(BaseWorker):
    feature = "tryon"

    def __init__(self):
        super().__init__()
        self._pipeline = None
        self._automasker = None
        self._mask_processor = None
        self._vlm_bundle = None
        self._flux_generator = None

    def _ensure_catvton_loaded(self):
        """모델은 워커 프로세스당 한 번만 로드한다 (매 job마다 로드하면 너무 느림)."""
        if self._pipeline is not None:
            return

        print(f"[{self.worker_id}] CatVTON 파이프라인 로딩 중...")
        repo_path = snapshot_download(repo_id="zhengchong/CatVTON")

        pipeline = CatVTONPipeline(
            base_ckpt="booksforcharlie/stable-diffusion-inpainting",
            attn_ckpt=repo_path,
            attn_ckpt_version="mix",
            weight_dtype=init_weight_dtype("bf16"),
            use_tf32=True,
            device="cuda",
        )
        pipeline.safety_checker = None
        pipeline.run_safety_checker = _bypass_safety_checker.__get__(pipeline)

        self._pipeline = pipeline
        self._mask_processor = VaeImageProcessor(
            vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True
        )
        self._automasker = AutoMasker(
            densepose_ckpt=os.path.join(repo_path, "DensePose"),
            schp_ckpt=os.path.join(repo_path, "SCHP"),
            device="cuda",
        )
        print(f"[{self.worker_id}] CatVTON 파이프라인 로딩 완료")

    def _ensure_vlm_loaded(self):
        """describer와 달리 실패해도 mock으로 폴백하지 않는다 -- 캡션은 이 파이프라인의
        1단계라 실패하면 job 전체가 실패하는 게 맞다(캡션 없이 뒤 단계를 진행할 수 없음)."""
        if self._vlm_bundle is not None or TRYON_VLM_BACKEND == "mock":
            return
        config = vlm_registry.vlm_config(TRYON_VLM_BACKEND)
        print(f"[{self.worker_id}] VLM 로딩 중... (backend={TRYON_VLM_BACKEND})")
        # CatVTON이 이미 GPU에 상주한 채로 VLM을 얹는다 -- 6GB급 GPU에서는 그대로 두면
        # bitsandbytes device_map="auto"가 일부 레이어를 CPU로 보내려다 실패한다.
        self._vlm_bundle = load_qwen_vl(
            config["model_id"], quantization=config["quantization"], enable_cpu_offload=True
        )
        print(f"[{self.worker_id}] VLM 로딩 완료")

    def _unload_vlm(self):
        if self._vlm_bundle is None:
            return
        self._vlm_bundle = None
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

    def _generate_worn_reference(self, person_image: Image.Image, prompt: str) -> Image.Image:
        if self._flux_generator is None:
            print(f"[{self.worker_id}] FLUX 로딩 중... (backend={TRYON_FLUX_BACKEND})")
            self._flux_generator = build_generator(TRYON_FLUX_BACKEND)
            print(f"[{self.worker_id}] FLUX 로딩 완료")

        worn_reference = self._flux_generator.generate(person_image, prompt)

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
            "mask_type": "upper",          # upper | lower — 기본값 upper(하위호환)
            "fit_type": "regular",         # regular | oversized (cropped는 가드레일상 없음)
            "num_inference_steps": 50,     # CatVTON 스텝 수, 선택
            "guidance_scale": 3.0,         # CatVTON guidance, 선택
            "body_height_cm": 170.0,       # 선택, BE 확정 컬럼
            "body_weight_kg": 65.0,        # 선택, BE 확정 컬럼
            "body_waist_cm": 75.0,         # 선택, BE 컬럼 미확정 -- 있으면 근사보다 우선
            "garment_measurements": {"WAIST_WIDTH": 42.0}   # 선택
        }

        `body_waist_cm`이 있으면 그 실측값을, 없고 `body_height_cm`/`body_weight_kg`가
        있으면 `body_estimate.py`의 키/몸무게 기반 근사치를 쓴다. 그마저 없거나
        `garment_measurements["WAIST_WIDTH"]`가 없으면 핏 계산 없이 "regular fit"으로
        FLUX worn-reference를 생성한다(`fit_type`은 이 경로에서도 CatVTON 마스크 자체엔
        더 이상 안 쓰인다 -- worn-reference-as-person 방식은 마스크를 worn-reference에서
        새로 계산하므로, 핏은 FLUX 프롬프트가 담당한다).

        AI는 이 값들을 BE에 재조회하지 않고 payload로 받은 그대로 쓴다.
        """
        self._ensure_catvton_loaded()

        mask_type = payload.get("mask_type", "upper")
        if mask_type not in ("upper", "lower"):
            raise ValueError(f"지원하지 않는 mask_type: {mask_type}")
        fit_type = payload.get("fit_type", "regular")
        if fit_type not in ("regular", "oversized"):
            raise ValueError(f"지원하지 않는 fit_type: {fit_type}")
        num_inference_steps = payload.get("num_inference_steps", 50)
        guidance_scale = payload.get("guidance_scale", 3.0)

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

        # --- 3단계: FLUX worn-reference 생성 ------------------------------------
        worn_reference = self._generate_worn_reference(person_image, dress_prompt)

        # --- 4단계: CatVTON 합성 (worn-reference-as-person) ---------------------
        # image=worn-reference, condition_image=실제 상품 사진 -- 마스크를
        # worn-reference에서 새로 계산해 그래픽/색상 정확도를 확보한다(§10.2).
        generator = torch.Generator(device="cuda").manual_seed(42)

        mask_result = self._automasker(worn_reference, mask_type=mask_type, fit_type=fit_type)
        mask = mask_result["mask"]
        mask = self._mask_processor.blur(mask, blur_factor=2)

        result_image = self._pipeline(
            image=worn_reference,
            condition_image=cloth_image,
            mask=mask,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator,
        )[0]
        result_image = composite_with_original(worn_reference, result_image, mask)

        image_url = upload_image(result_image, prefix="tryon-results")

        # 마스크 시각화도 참고용으로 같이 업로드 (디버깅에 유용)
        masked_worn_reference = vis_mask(worn_reference, mask)
        mask_url = upload_image(masked_worn_reference, prefix="tryon-masks")
        worn_reference_url = upload_image(worn_reference, prefix="tryon-worn-references")

        return {
            "image_url": image_url,
            "mask_preview_url": mask_url,
            "worn_reference_url": worn_reference_url,
            "fit_type": fit_type,
            "adaptive_masking_used": adaptive_masking_used,
            "fit_title": fit_summary["title"] if fit_summary else None,
            "fit_description": fit_summary["description"] if fit_summary else None,
        }


if __name__ == "__main__":
    TryonWorker().loop()
