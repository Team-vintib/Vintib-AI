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
# 다른 환경에서 위치가 다르면 CATVTON_CODE_PATH 환경변수로 덮어쓸 수 있다.
# (구 경로는 AI/test/ → AI/validation/ 이었다 — 추론 코드는 AI/에 두지 않는다는 원칙에 따라
#  worker/models/ 로 옮겼다.)
CATVTON_CODE_PATH = os.getenv(
    "CATVTON_CODE_PATH",
    os.path.join(os.path.dirname(__file__), "models", "catvton"),
)
sys.path.insert(0, CATVTON_CODE_PATH)

from model.cloth_masker import AutoMasker, vis_mask  # noqa: E402
from model.pipeline import CatVTONPipeline  # noqa: E402
from utils import init_weight_dtype, resize_and_crop, resize_and_padding  # noqa: E402

WIDTH, HEIGHT = 768, 1024  # verify_fit_tryon.py 와 동일한 기본값


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

    def _ensure_loaded(self):
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

    def run_inference(self, payload: dict) -> dict:
        """
        payload 예:
        {
            "user_image_url": "https://.../person.jpg",
            "product_image_url": "https://.../cloth.jpg",
            "fit_type": "regular",   # regular | oversized | cropped — 아래 두 값이 있으면 무시됨
            "body_measurements": {"waist_cm": 80.0},   # 선택
            "garment_measurements": {"WAIST_WIDTH": 42.0}   # 선택
        }

        `body_measurements`/`garment_measurements`는 둘 다 있고 바지(mask_type="lower")
        허리 너비 축에 필요한 키(`waist_cm`/`WAIST_WIDTH`)가 있을 때만 적응형 마스킹이
        켜진다(`model.adaptive_fit.compute_mask_adjustment` 참고) — 그 외에는 `fit_type`
        고정 3단계로 그대로 동작한다. 기장(길이) 축은 없다 — 마스크를 잘라 기장을 줄이면
        그 자리에 맨살을 새로 생성해야 해서 AI 가드레일상 정책적으로 뺐다. AI는 이 값들을
        BE에 재조회하지 않고 payload로 받은 그대로 쓴다.
        """
        self._ensure_loaded()

        fit_type = payload.get("fit_type", "regular")
        if fit_type not in ("regular", "oversized", "cropped"):
            raise ValueError(f"지원하지 않는 fit_type: {fit_type}")
        body_measurements = payload.get("body_measurements")
        garment_measurements = payload.get("garment_measurements")

        person_image = download_image(payload["user_image_url"]).convert("RGB")
        cloth_image = download_image(payload["product_image_url"]).convert("RGB")

        person_image = resize_and_crop(person_image, (WIDTH, HEIGHT))
        cloth_image = resize_and_padding(cloth_image, (WIDTH, HEIGHT))

        generator = torch.Generator(device="cuda").manual_seed(42)

        mask_result = self._automasker(
            person_image,
            mask_type="upper",
            fit_type=fit_type,
            body_measurements=body_measurements,
            garment_measurements=garment_measurements,
        )
        mask = mask_result["mask"]
        mask = self._mask_processor.blur(mask, blur_factor=9)

        result_image = self._pipeline(
            image=person_image,
            condition_image=cloth_image,
            mask=mask,
            num_inference_steps=20,
            guidance_scale=2.5,
            generator=generator,
        )[0]
        result_image = composite_with_original(person_image, result_image, mask)

        image_url = upload_image(result_image, prefix="tryon-results")

        # 마스크 시각화도 참고용으로 같이 업로드 (디버깅에 유용)
        masked_person = vis_mask(person_image, mask)
        mask_url = upload_image(masked_person, prefix="tryon-masks")

        return {
            "image_url": image_url,
            "mask_preview_url": mask_url,
            "fit_type": fit_type,
            "adaptive_masking_used": bool(body_measurements and garment_measurements),
        }


if __name__ == "__main__":
    TryonWorker().loop()
