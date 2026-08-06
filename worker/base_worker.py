"""
로컬 노트북에서 실행하는 워커 공통 골격.

Redis에 직접 붙지 않는다. EC2에선 backend/postgres/redis/ai 전부
호스트 포트를 열지 않고(docker-compose.prod.yml), Caddy(80/443)만
외부에 노출되어 있다. Caddy가 /ai/* 요청을 ai:8000 컨테이너로
리버스 프록시해주므로, 워커는 그 경로로만 게이트웨이와 통신한다.

GATEWAY_URL 환경변수에는 /ai 까지 포함해서 넣는다.
예: GATEWAY_URL=https://i15a108.p.ssafy.io/ai
"""

import os
import time
import socket
from pathlib import Path

import requests

# worker/.env를 자동으로 읽는다 — 없으면(패키지 미설치 포함) 조용히 넘어가고 기존처럼
# 셸에서 직접 export/set한 값을 그대로 쓴다. 매 워커 스크립트가 `from base_worker import
# BaseWorker`를 자기 자신의 os.getenv() 호출보다 먼저 하기 때문에, 여기서 로드해두면
# TRYON_VLM_BACKEND 같은 워커별 환경변수에도 그대로 적용된다.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass


class BaseWorker:
    feature: str = None  # 예: "tryon", "quality_check"

    def __init__(self):
        assert self.feature, "feature 를 서브클래스에서 정의해야 합니다"

        self.worker_id = f"{socket.gethostname()}-{self.feature}"

        gateway_url = os.getenv("GATEWAY_URL")
        api_key = os.getenv("WORKER_API_KEY")
        assert gateway_url and api_key, "GATEWAY_URL / WORKER_API_KEY 환경변수 필요"

        # 끝에 슬래시 있으면 제거해서 경로 이어붙일 때 // 안 생기게
        self.gateway_url = gateway_url.rstrip("/")
        self.headers = {"X-API-Key": api_key}

    def run_inference(self, payload: dict) -> dict:
        """모델별로 반드시 구현. 여기만 갈아끼우면 고도화 끝."""
        raise NotImplementedError

    def loop(self):
        print(f"[{self.worker_id}] polling {self.gateway_url}/workers/poll (feature={self.feature})")
        while True:
            job = self._poll()
            if job is None:
                continue
            self._process(job)

    def _poll(self):
        try:
            resp = requests.get(
                f"{self.gateway_url}/workers/poll",
                params={"feature": self.feature},
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("job")
        except requests.RequestException as e:
            print(f"[{self.worker_id}] poll failed: {e}, retry in 5s")
            time.sleep(5)
            return None

    def _process(self, job: dict):
        try:
            result = self.run_inference(job["payload"])
            self._submit(job, status="success", result=result)
        except Exception as e:
            print(f"[{self.worker_id}] inference failed: {e}")
            self._submit(job, status="failed", error=str(e))

    def _submit(self, job: dict, status: str, result: dict | None = None, error: str | None = None):
        try:
            requests.post(
                f"{self.gateway_url}/workers/result",
                params={"status": status, "worker_id": self.worker_id},
                json={"job": job, "result": result, "error": error},
                headers=self.headers,
                timeout=15,
            )
        except requests.RequestException as e:
            print(f"[{self.worker_id}] result submit failed: {e}")
