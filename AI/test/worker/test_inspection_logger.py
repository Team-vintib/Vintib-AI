"""`worker/inspection_logger.py` 검증 — 판단 근거 로컬 로그(CH008).

순수 로직(파일 append)이라 무거운 의존성이 없다. `AI/test/conftest.py`가 `worker/`를
sys.path에 넣어 둬서 `import inspection_logger`가 바로 된다.
"""

import json

from inspection_logger import log_inspection_result

_PAYLOAD = {
    "product_id": 42,
    "image_urls": ["https://x/front.jpg"],
    "category": "TOP_KNIT",
    "base_color": "LIGHT",
}
_OUTPUT = {
    "inspection_id": "insp_42_worker1",
    "product_id": 42,
    "condition_score": 86.0,
    "condition_grade": "A",
    "findings": [],
}


def _read_lines(log_dir):
    files = list(log_dir.glob("*.jsonl"))
    assert len(files) == 1, f"파일이 정확히 1개 있어야 합니다: {files}"
    return [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]


def test_writes_one_json_line_with_request_context_and_full_output(tmp_path):
    log_inspection_result(_PAYLOAD, _OUTPUT, log_dir=tmp_path)

    (record,) = _read_lines(tmp_path)
    assert record["image_urls"] == _PAYLOAD["image_urls"]
    assert record["category"] == "TOP_KNIT"
    assert record["base_color"] == "LIGHT"
    # output은 추가 계산 없이 그대로 실린다.
    assert record["inspection_id"] == "insp_42_worker1"
    assert record["condition_score"] == 86.0
    assert record["findings"] == []
    assert "logged_at" in record


def test_appends_multiple_calls_as_separate_lines(tmp_path):
    log_inspection_result(_PAYLOAD, _OUTPUT, log_dir=tmp_path)
    log_inspection_result(
        _PAYLOAD, {**_OUTPUT, "inspection_id": "insp_42_worker2"}, log_dir=tmp_path
    )

    records = _read_lines(tmp_path)
    assert len(records) == 2
    assert records[0]["inspection_id"] == "insp_42_worker1"
    assert records[1]["inspection_id"] == "insp_42_worker2"


def test_logging_failure_does_not_raise(tmp_path, capsys):
    # log_dir 자리에 이미 같은 이름의 '파일'이 있으면 mkdir(parents=True, exist_ok=True)가
    # FileExistsError를 낸다 — 디스크 문제를 흉내내는 결정적인 방법이다.
    blocked_path = tmp_path / "blocked"
    blocked_path.write_text("i'm a file, not a directory", encoding="utf-8")

    log_inspection_result(_PAYLOAD, _OUTPUT, log_dir=blocked_path)  # 예외를 던지면 테스트 실패

    captured = capsys.readouterr()
    assert "판단 근거 로그 기록 실패" in captured.err


def test_log_file_name_is_todays_utc_date(tmp_path):
    from datetime import UTC, datetime

    log_inspection_result(_PAYLOAD, _OUTPUT, log_dir=tmp_path)

    expected_name = f"{datetime.now(UTC).date().isoformat()}.jsonl"
    assert (tmp_path / expected_name).is_file()
