import json
import os
import uuid

import aiofiles
import redis
from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile

from app.core.config import settings
from app.gateway.schemas import FeatureType, Job, JobResult, new_job

router = APIRouter()

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

# S3 권한이 없어서 EC2 로컬 디스크에 저장 → Caddy가 /results/* 로 서빙
RESULTS_DIR = os.getenv("RESULTS_DIR", "/app/results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def _check_worker_key(x_api_key: str | None):
    if not settings.worker_api_key or x_api_key != settings.worker_api_key:
        raise HTTPException(status_code=401, detail="invalid worker api key")


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


# ---------- 백엔드(Spring Boot)가 호출하는 쪽 ----------


@router.post("/{feature}")
def enqueue_job(feature: FeatureType, data: dict):
    job = new_job(feature, data)
    r.rpush(f"{QUEUE_PREFIX}{feature}", job.model_dump_json())
    r.set(
        f"{RESULT_PREFIX}{job.job_id}",
        JobResult(job_id=job.job_id, status="queued").model_dump_json(),
        ex=RESULT_TTL_SECONDS,
    )
    return {"job_id": job.job_id}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    raw = r.get(f"{RESULT_PREFIX}{job_id}")
    if raw is None:
        raise HTTPException(status_code=404, detail="job not found or expired")
    return json.loads(raw)


# ---------- 로컬 노트북 워커가 호출하는 쪽 ----------


@router.get("/workers/poll")
def poll_job(
    feature: FeatureType = Query(...), x_api_key: str | None = Header(default=None)
):  # noqa: B008
    _check_worker_key(x_api_key)

    item = r.blpop([f"{QUEUE_PREFIX}{feature}"], timeout=POLL_TIMEOUT_SECONDS)
    if item is None:
        return {"job": None}

    _, raw_job = item
    job = json.loads(raw_job)

    r.set(
        f"{RESULT_PREFIX}{job['job_id']}",
        JobResult(job_id=job["job_id"], status="processing").model_dump_json(),
        ex=RESULT_TTL_SECONDS,
    )
    return {"job": job}


@router.post("/workers/result")
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
        payload = JobResult(job_id=job.job_id, status="success", result=result, worker_id=worker_id)
        r.set(f"{RESULT_PREFIX}{job.job_id}", payload.model_dump_json(), ex=RESULT_TTL_SECONDS)
        return {"ok": True}

    job.retry_count += 1
    if job.retry_count > MAX_RETRY:
        r.rpush(DEAD_LETTER_KEY, job.model_dump_json())
        payload = JobResult(job_id=job.job_id, status="failed", error=error, worker_id=worker_id)
        r.set(f"{RESULT_PREFIX}{job.job_id}", payload.model_dump_json(), ex=RESULT_TTL_SECONDS)
    else:
        r.rpush(f"{QUEUE_PREFIX}{job.type}", job.model_dump_json())
        payload = JobResult(job_id=job.job_id, status="queued", worker_id=worker_id)
        r.set(f"{RESULT_PREFIX}{job.job_id}", payload.model_dump_json(), ex=RESULT_TTL_SECONDS)

    return {"ok": True}


@router.post("/workers/upload-image")
async def upload_result_image(
    prefix: str = Query(...),
    file: UploadFile = File(...),  # noqa: B008
    x_api_key: str | None = Header(default=None),
):
    """
    워커(노트북)가 만든 결과 이미지를 EC2 디스크에 저장한다.
    S3 권한이 없어서 쓰는 대체 경로 — 저장 후 Caddy가 서빙 가능한 URL을 돌려준다.
    """
    _check_worker_key(x_api_key)

    target_dir = os.path.join(RESULTS_DIR, prefix)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(target_dir, filename)
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(await file.read())

    url = f"{settings.public_base_url}/results/{prefix}/{filename}"
    return {"url": url}


@router.post("/workers/upload-json")
async def upload_result_json(
    prefix: str = Query(...),
    name: str = Query(...),
    data: dict | None = None,
    x_api_key: str | None = Header(default=None),
):
    """품질검수 리포트처럼 JSON 결과물을 저장할 때 쓰는 엔드포인트."""
    _check_worker_key(x_api_key)

    target_dir = os.path.join(RESULTS_DIR, prefix)
    os.makedirs(target_dir, exist_ok=True)

    filepath = os.path.join(target_dir, f"{name}.json")
    async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False))

    url = f"{settings.public_base_url}/results/{prefix}/{name}.json"
    return {"url": url}
