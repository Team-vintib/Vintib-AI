"""
가상 시착 추론을 실제로 수행하는 Celery 태스크.

모델 코드 위치에 대한 전제:
- AI/test/AI_tryon/catvton 에서 검증 완료된 CatVTONPipeline, AutoMasker 등을
  프로덕션 패키지 app/ml/catvton/ 로 그대로 복사해 옮겨온다고 가정함
  (스파이크 폴더를 프로덕션에서 직접 import하지 않는다 — 테스트 코드와
  프로덕션 코드의 배포 라이프사이클을 분리하기 위함).
- 실제 이관 시 model/pipeline.py, model/cloth_masker.py, utils.py 등을
  app/ml/catvton/ 아래로 복사하고, 아래 import 경로를 그에 맞게 조정할 것.

파이프라인은 워커 프로세스당 1회만 로드되는 싱글턴으로 관리한다.
(Celery worker_concurrency=1로 설정했으므로, 워커 프로세스 = GPU 1개 점유 단위)
"""

import logging
import os
from pathlib import Path

import torch
from PIL import Image

from app.services import status_store
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

RESULT_DIR = Path(os.environ.get("TRYON_RESULT_DIR", "/data/tryon_results"))
RESULT_DIR.mkdir(parents=True, exist_ok=True)

_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = 30


class _PipelineSingleton:
    """워커 프로세스당 한 번만 모델을 로드하기 위한 지연 초기화 싱글턴."""

    _pipeline = None
    _automasker = None
    _mask_processor = None

    @classmethod
    def get(cls):
        if cls._pipeline is None:
            logger.info("CatVTON 파이프라인 최초 로드 시작...")
            # NOTE: 아래 import는 app/ml/catvton/ 로 모델 코드 이관 완료 후 유효해짐.
            from app.ml.catvton.pipeline import CatVTONPipeline
            from app.ml.catvton.cloth_masker import AutoMasker
            from diffusers.image_processor import VaeImageProcessor
            from huggingface_hub import snapshot_download
            from app.ml.catvton.utils import init_weight_dtype

            repo_path = snapshot_download(repo_id="zhengchong/CatVTON")

            cls._pipeline = CatVTONPipeline(
                base_ckpt="booksforcharlie/stable-diffusion-inpainting",
                attn_ckpt=repo_path,
                attn_ckpt_version="mix",
                weight_dtype=init_weight_dtype("bf16"),
                use_tf32=True,
                device="cuda",
            )
            cls._mask_processor = VaeImageProcessor(
                vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True
            )
            cls._automasker = AutoMasker(
                densepose_ckpt=os.path.join(repo_path, "DensePose"),
                schp_ckpt=os.path.join(repo_path, "SCHP"),
                device="cuda",
            )
            logger.info("CatVTON 파이프라인 로드 완료")

        return cls._pipeline, cls._automasker, cls._mask_processor


@celery_app.task(
    name="app.worker.tasks.run_tryon_inference",
    bind=True,
    max_retries=_MAX_RETRIES,
    default_retry_delay=_RETRY_BACKOFF_SECONDS,
)
def run_tryon_inference(
    self,
    request_id: str,
    person_image_path: str,
    cloth_image_path: str,
    mask_type: str = "upper",
    fit_type: str = "regular",
    num_inference_steps: int = 30,
    guidance_scale: float = 2.5,
    width: int = 768,
    height: int = 1024,
):
    """
    시착 추론 1건을 처리한다.

    person_image_path / cloth_image_path: 업로드 시점에 서버 디스크(또는
    오브젝트 스토리지 마운트 경로)에 저장된 원본 이미지 경로. API 레이어
    (tryon_service.py)에서 저장 후 이 태스크에 경로만 넘긴다.
    """
    status_store.mark_processing(request_id)

    try:
        pipeline, automasker, mask_processor = _PipelineSingleton.get()

        # 지연 import: 모듈 최상단에서 import하면 워커 기동 시점에 무조건
        # torch/모델 관련 의존성을 전부 로드해야 해서 기동이 느려짐.
        from app.ml.catvton.utils import resize_and_crop, resize_and_padding

        person_image = Image.open(person_image_path).convert("RGB")
        cloth_image = Image.open(cloth_image_path).convert("RGB")
        person_image = resize_and_crop(person_image, (width, height))
        cloth_image = resize_and_padding(cloth_image, (width, height))

        mask_result = automasker(person_image, mask_type=mask_type, fit_type=fit_type)
        mask = mask_processor.blur(mask_result["mask"], blur_factor=9)

        generator = torch.Generator(device="cuda").manual_seed(42)

        result_image = pipeline(
            image=person_image,
            condition_image=cloth_image,
            mask=mask,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator,
        )[0]

        output_path = RESULT_DIR / f"{request_id}.png"
        result_image.save(output_path)

        # 실제 배포 환경에서는 S3/오브젝트 스토리지 URL로 대체
        result_url = f"/tryon-results/{request_id}.png"
        status_store.mark_completed(request_id, result_url)

        return {"request_id": request_id, "result_image_url": result_url}

    except torch.cuda.OutOfMemoryError as exc:
        # OOM은 일시적일 수 있으므로(동시 요청 몰림 등) 재시도 대상.
        logger.warning(f"[{request_id}] CUDA OOM 발생, 재시도 예정: {exc}")
        torch.cuda.empty_cache()
        raise self.retry(exc=exc)

    except Exception as exc:  # noqa: BLE001 — 추론 실패는 원인 무관하게 상태 기록 후 재시도/DLQ 이관해야 함
        logger.exception(f"[{request_id}] 추론 실패")
        if self.request.retries >= _MAX_RETRIES:
            _send_to_dead_letter(request_id, str(exc))
            status_store.mark_failed(request_id, str(exc))
            return {"request_id": request_id, "status": "failed", "error": str(exc)}
        raise self.retry(exc=exc)


def _send_to_dead_letter(request_id: str, error_message: str) -> None:
    """
    재시도를 모두 소진한 작업을 별도 dead-letter 큐(Redis List)에 적재한다.
    운영 중에는 별도 모니터링 프로세스나 알림(Slack 등)으로 이 큐를 감시해서
    수동 재처리/원인 분석에 활용한다.
    """
    import json

    from app.worker.celery_app import celery_app as _app

    dlq_entry = {"request_id": request_id, "error": error_message}
    _app.backend.client.rpush("tryon:dead_letter", json.dumps(dlq_entry))
    logger.error(f"[{request_id}] 재시도 소진, dead-letter 큐로 이관: {error_message}")
