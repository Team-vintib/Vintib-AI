import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

FeatureType = Literal[
    "tryon", "quality_check", "chat_rag", "recommend_offline", "stt", "garment_measurement"
]
JobStatus = Literal["queued", "processing", "success", "failed"]


class Job(BaseModel):
    job_id: str
    type: FeatureType
    payload: dict
    created_at: str
    retry_count: int = 0


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    result: dict | None = None
    error: str | None = None
    worker_id: str | None = None
    finished_at: str | None = None


def new_job(feature: FeatureType, data: dict) -> Job:
    return Job(
        job_id=str(uuid.uuid4()),
        type=feature,
        payload=data,
        created_at=datetime.now(UTC).isoformat(),
    )
