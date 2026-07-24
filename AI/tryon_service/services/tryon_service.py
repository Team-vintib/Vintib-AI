"""
시착 요청을 접수하고 Celery 큐에 적재하는 서비스 레이어.
API 라우터(app/api/routes/tryon.py)는 이 모듈만 호출하고, Celery/저장소
세부 구현은 이 레이어 안에 캡슐화한다.
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from app.schemas.tryon import MaskFitType, TryOnRequestAccepted, TryOnStatus
from app.services import status_store
from app.worker.tasks import run_tryon_inference

UPLOAD_DIR = Path(os.environ.get("TRYON_UPLOAD_DIR", "/data/tryon_uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 입력 검증 정책 (S15P11A108-182 이미지 생성 범위 정책과 맞춰 조정 필요)
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


class InvalidTryOnRequestError(Exception):
    """입력 검증 실패 시 발생. API 레이어에서 4xx로 변환한다."""


async def _save_upload(file: UploadFile, request_id: str, label: str) -> str:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidTryOnRequestError(
            f"{label} 이미지 형식이 지원되지 않습니다: {file.content_type} "
            f"(허용: {', '.join(ALLOWED_CONTENT_TYPES)})"
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise InvalidTryOnRequestError(
            f"{label} 이미지 용량이 제한({MAX_FILE_SIZE_BYTES // (1024*1024)}MB)을 초과했습니다."
        )
    if len(contents) == 0:
        raise InvalidTryOnRequestError(f"{label} 이미지가 비어 있습니다.")

    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    save_path = UPLOAD_DIR / f"{request_id}_{label}{ext}"
    with open(save_path, "wb") as f:
        f.write(contents)

    return str(save_path)


async def submit_tryon_request(
    person_image: UploadFile,
    cloth_image: UploadFile,
    mask_type: str = "upper",
    fit_type: MaskFitType = MaskFitType.REGULAR,
    num_inference_steps: int = 30,
    guidance_scale: float = 2.5,
) -> TryOnRequestAccepted:
    """
    업로드된 이미지를 검증/저장하고, 추론 작업을 Celery 큐에 적재한다.
    이 함수는 큐 적재까지만 담당하며, 실제 추론 완료를 기다리지 않는다
    (비동기 처리 아키텍처, S15P11A108-181).
    """
    request_id = str(uuid.uuid4())

    person_path = await _save_upload(person_image, request_id, "person")
    cloth_path = await _save_upload(cloth_image, request_id, "cloth")

    status_store.create_pending(request_id)

    run_tryon_inference.delay(
        request_id=request_id,
        person_image_path=person_path,
        cloth_image_path=cloth_path,
        mask_type=mask_type,
        fit_type=fit_type.value,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
    )

    return TryOnRequestAccepted(
        request_id=request_id,
        status=TryOnStatus.PENDING,
        queued_at=datetime.now(timezone.utc),
        # 대략치. 실측 벤치마크(steps=30, 768x1024 기준 약 76초)를 근거로 산정.
        # 큐 대기 중인 작업 수를 반영하려면 celery inspect 등으로 정교화 필요.
        estimated_wait_seconds=80,
    )
