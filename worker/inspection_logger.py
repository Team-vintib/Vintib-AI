"""검수 판단 근거 로컬 로그 — 판정 결과 전체를 JSON Lines로 남긴다.

Redis의 job result는 TTL 3600초 후 사라지고, BE는 finding의 `key`/`statement_required`만
저장하도록 문서화돼 있다(`.claude/requests/be/001-quality-inspection-async.md`) — score/
confidence/threshold/히트맵 URL 같은 판단 근거가 어디에도 안 남는다. 이 모듈은 워커가 검수
결과를 반환하기 직전에, 요청 컨텍스트 + 결과 전체를 로컬 파일에 한 줄씩 append한다.

**로깅 실패는 검수 응답을 막지 않는다** — best-effort다. 디스크 문제 등으로 로그를 못 남겨도
판매자/구매자에게 갈 응답은 그대로 나가야 한다.

설계: `.claude/plans/ai/CH008-quality-judgment-log.md`
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

_DEFAULT_LOG_DIR = Path(__file__).resolve().parent / "logs" / "quality"


def _log_dir() -> Path:
    return Path(os.getenv("QUALITY_LOG_DIR", str(_DEFAULT_LOG_DIR)))


def log_inspection_result(payload: dict, output: dict, *, log_dir: Path | None = None) -> None:
    """검수 요청 컨텍스트 + 결과 전체를 로컬 JSON Lines 파일에 한 줄 append한다.

    파일: `{log_dir}/{UTC 날짜}.jsonl` — 날짜별로 나눠 한 파일이 무한정 커지지 않게 한다.
    `output`은 `run_inference()`가 이미 만든 dict를 그대로 쓴다(추가 계산 없음). 실패해도
    예외를 올리지 않고 stderr 경고만 남긴다.
    """
    target_dir = log_dir if log_dir is not None else _log_dir()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC)
        record = {
            "logged_at": now.isoformat(),
            "image_urls": payload.get("image_urls"),
            "category": payload.get("category"),
            "base_color": payload.get("base_color"),
            **output,
        }
        log_path = target_dir / f"{now.date().isoformat()}.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 - 로깅 실패로 검수 응답을 막지 않는다
        print(f"[inspection_logger] 판단 근거 로그 기록 실패: {exc}", file=sys.stderr)
