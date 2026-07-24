from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid

FeatureType = Literal["tryon", "quality_check", "chat_rag", "recommend_offline"]
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
    result: Optional[dict] = None
    error: Optional[str] = None
    worker_id: Optional[str] = None
    finished_at: Optional[str] = None


def new_job(feature: FeatureType, data: dict) -> Job:
    return Job(
        job_id=str(uuid.uuid4()),
        type=feature,
        payload=data,
        created_at=datetime.now(timezone.utc).isoformat(),
    )