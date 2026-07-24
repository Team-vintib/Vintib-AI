"""
가상 시착 서비스 요청/응답 스키마.

S15P11A108-181(비동기 처리 아키텍처), S15P11A108-182(이미지 생성 범위 정책)에서
정의된 설계를 따른다고 가정하고 작성함. 실제 필드명/제약은 해당 설계 문서와
대조하여 조정 필요.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TryOnStatus(str, Enum):
    PENDING = "pending"       # 큐에 적재됨, 아직 처리 전
    PROCESSING = "processing"  # 워커가 추론 중
    COMPLETED = "completed"    # 완료, 결과 조회 가능
    FAILED = "failed"          # 실패 (재시도 소진 포함)


class MaskFitType(str, Enum):
    """빈티지 의류 핏 옵션 (기존 AutoMasker.fit_type과 동일)"""
    REGULAR = "regular"
    OVERSIZED = "oversized"
    CROPPED = "cropped"


class TryOnRequestCreate(BaseModel):
    """
    시착 요청 생성 시 클라이언트가 보내는 메타데이터.
    실제 이미지 파일(person_image, cloth_image)은 별도 multipart/form-data로 받는다
    (see api/routes/tryon.py의 UploadFile 파라미터).
    """
    mask_type: str = Field(default="upper", description="upper/lower/overall/inner/outer")
    fit_type: MaskFitType = Field(default=MaskFitType.REGULAR)
    num_inference_steps: int = Field(default=30, ge=10, le=50)
    guidance_scale: float = Field(default=2.5, ge=1.0, le=10.0)


class TryOnRequestAccepted(BaseModel):
    """요청 접수 직후 즉시 반환하는 응답 (동기 대기 없음)"""
    request_id: str
    status: TryOnStatus = TryOnStatus.PENDING
    queued_at: datetime
    estimated_wait_seconds: Optional[int] = None


class TryOnResult(BaseModel):
    """결과 조회 API의 응답"""
    request_id: str
    status: TryOnStatus
    result_image_url: Optional[str] = None
    error_message: Optional[str] = None
    queued_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
