"""
Celery 앱 설정.

브로커/백엔드 모두 Redis 사용. 큐를 용도별로 분리해서(tryon, dead_letter)
장애 발생 작업이 정상 큐를 막지 않도록 한다.

환경변수:
- REDIS_URL: 예) redis://localhost:6379/0
  (운영 배포 시에는 .env 또는 시크릿 매니저로 주입, 기본값은 로컬 개발용)
"""

import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "tryon_service",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    enable_utc=True,
    # 시착 추론은 GPU 자원을 오래 점유하므로, 워커당 동시 처리 1건으로 제한.
    # (워커 프로세스 자체를 여러 개 띄워 수평 확장하는 방식을 전제로 함)
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    # 재시도 정책: 일시적 오류(OOM 등)는 지수 백오프로 최대 2회 재시도.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "app.worker.tasks.run_tryon_inference": {"queue": "tryon"},
    },
    # 최대 재시도 후에도 실패하면 dead-letter 큐로 보낸다 (tasks.py의
    # on_failure 핸들러에서 별도 큐로 재발행).
)
