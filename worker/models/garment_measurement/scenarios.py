"""목업 실측 시나리오 로더.

`data/mock_scans.json`을 `product_id`로 조회한다. `quality/scenarios.py`와 달리 다운스트림이
순수 기하 계산(`cm_converter`)뿐이라 시드 기반 절차적 합성까지는 필요 없다 — 등록 안 된
`product_id`는 `"default"` 시나리오로 폴백한다(데모 시 임의 `product_id`를 넣어도 동작).

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"
_MOCK_SCANS_FILE = _DATA_DIR / "mock_scans.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    return json.loads(_MOCK_SCANS_FILE.read_text(encoding="utf-8"))


def get_scenario(product_id: int) -> dict:
    scenarios = _load()["scenarios"]
    return scenarios.get(str(product_id), scenarios["default"])
