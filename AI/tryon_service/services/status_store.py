"""
시착 요청의 상태(PENDING/PROCESSING/COMPLETED/FAILED)와 타임스탬프를
Redis Hash에 저장/조회하는 간단한 저장소.

Celery의 result backend와 별개로 이 저장소를 두는 이유:
- Celery AsyncResult만으로는 "큐에 쌓인 시각", "추론 시작 시각" 같은
  세분화된 타임스탬프를 다루기 번거로움
- 폴링 API(GET /tryon/{request_id})가 Celery 내부 구조에 의존하지 않도록
  분리해서, 추후 워커 프레임워크를 바꾸더라도 API 계약이 안정적으로 유지되게 함
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

import redis

from app.schemas.tryon import TryOnStatus

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

_KEY_PREFIX = "tryon:request:"
_TTL_SECONDS = 60 * 60 * 24  # 결과는 24시간 후 자동 만료 (스토리지 무한 증가 방지)


def _key(request_id: str) -> str:
    return f"{_KEY_PREFIX}{request_id}"


def create_pending(request_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "request_id": request_id,
        "status": TryOnStatus.PENDING.value,
        "queued_at": now,
        "started_at": "",
        "completed_at": "",
        "result_image_url": "",
        "error_message": "",
    }
    _redis_client.set(_key(request_id), json.dumps(data), ex=_TTL_SECONDS)


def mark_processing(request_id: str) -> None:
    data = get(request_id)
    if data is None:
        return
    data["status"] = TryOnStatus.PROCESSING.value
    data["started_at"] = datetime.now(timezone.utc).isoformat()
    _redis_client.set(_key(request_id), json.dumps(data), ex=_TTL_SECONDS)


def mark_completed(request_id: str, result_image_url: str) -> None:
    data = get(request_id)
    if data is None:
        return
    data["status"] = TryOnStatus.COMPLETED.value
    data["completed_at"] = datetime.now(timezone.utc).isoformat()
    data["result_image_url"] = result_image_url
    _redis_client.set(_key(request_id), json.dumps(data), ex=_TTL_SECONDS)


def mark_failed(request_id: str, error_message: str) -> None:
    data = get(request_id)
    if data is None:
        return
    data["status"] = TryOnStatus.FAILED.value
    data["completed_at"] = datetime.now(timezone.utc).isoformat()
    data["error_message"] = error_message
    _redis_client.set(_key(request_id), json.dumps(data), ex=_TTL_SECONDS)


def get(request_id: str) -> Optional[dict]:
    raw = _redis_client.get(_key(request_id))
    if raw is None:
        return None
    return json.loads(raw)
