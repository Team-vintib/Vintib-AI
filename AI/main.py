import json

import redis
from fastapi import FastAPI, HTTPException, Header, Query

from config import settings
from schemas import FeatureType, Job, JobResult, new_job

app = FastAPI(title=settings.app_name)

r = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password or None,
    decode_responses=True,
)

QUEUE_PREFIX = "queue:"
RESULT_PREFIX = "result:"
DEAD_LETTER_KEY = "dead_letter"
RESULT_TTL_SECONDS = 3600
POLL_TIMEOUT_SECONDS = 5
MAX_RETRY = 3


def _check_worker_key(x_api_key: str | None):
    if not settings.worker_api_key or x_api_key != settings.worker_api_key:
        raise HTTPException(status_code=401, detail="invalid worker api key")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ai/{feature}")
def enqueue_job(feature: FeatureType, data: dict):
    job = new_job(feature, data)
    r.rpush(f"{QUEUE_PREFIX}{feature}", job.model_dump_json())
    r.set(f"{RESULT_PREFIX}{job.job_id}",
          JobResult(job_id=job.job_id, status="queued").model_dump_json(),
          ex=RESULT_TTL_SECONDS)
    return {"job_id": job.job_id}


@app.get("/ai/jobs/{job_id}")
def get_job_status(job_id: str):
    raw = r.get(f"{RESULT_PREFIX}{job_id}")
    if raw is None:
        raise HTTPException(status_code=404, detail="job not found or expired")
    return json.loads(raw)


@app.get("/ai/workers/poll")
def poll_job(feature: FeatureType = Query(...), x_api_key: str | None = Header(default=None)):
    _check_worker_key(x_api_key)
    item = r.blpop([f"{QUEUE_PREFIX}{feature}"], timeout=POLL_TIMEOUT_SECONDS)
    if item is None:
        return {"job": None}
    _, raw_job = item
    job = json.loads(raw_job)
    r.set(f"{RESULT_PREFIX}{job['job_id']}",
          JobResult(job_id=job["job_id"], status="processing").model_dump_json(),
          ex=RESULT_TTL_SECONDS)
    return {"job": job}


@app.post("/ai/workers/result")
def submit_result(
    job: Job,
    status: str,
    result: dict | None = None,
    error: str | None = None,
    worker_id: str | None = None,
    x_api_key: str | None = Header(default=None),
):
    _check_worker_key(x_api_key)

    if status == "success":
        r.set(f"{RESULT_PREFIX}{job.job_id}",
              JobResult(job_id=job.job_id, status="success", result=result, worker_id=worker_id).model_dump_json(),
              ex=RESULT_TTL_SECONDS)
        return {"ok": True}

    job.retry_count += 1
    if job.retry_count > MAX_RETRY:
        r.rpush(DEAD_LETTER_KEY, job.model_dump_json())
        r.set(f"{RESULT_PREFIX}{job.job_id}",
              JobResult(job_id=job.job_id, status="failed", error=error, worker_id=worker_id).model_dump_json(),
              ex=RESULT_TTL_SECONDS)
    else:
        r.rpush(f"{QUEUE_PREFIX}{job.type}", job.model_dump_json())
        r.set(f"{RESULT_PREFIX}{job.job_id}",
              JobResult(job_id=job.job_id, status="queued", worker_id=worker_id).model_dump_json(),
              ex=RESULT_TTL_SECONDS)

    return {"ok": True}