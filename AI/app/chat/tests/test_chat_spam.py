"""도배 탐지 — 슬라이딩 윈도우 경계 + 근접중복 + 상태 저장소 스왑."""

import pytest

from app.chat import registry
from app.chat.spam import (
    InMemoryStateStore,
    RedisStateStore,
    SpamDetector,
    build_state_store,
)

BASE = 1_000_000.0  # 테스트는 항상 now를 명시해 시계 의존성을 없앤다


def _detector(**kwargs) -> SpamDetector:
    return SpamDetector(InMemoryStateStore(), **kwargs)


# --- rate-limit 경계 ------------------------------------------------------


def test_flooding_trips_only_after_max_messages():
    detector = _detector(max_messages=4, duplicate_count=99)  # 중복 경로는 끄고 순수 rate-limit만
    # 서로 다른 문장 4건까지는 통과하고, 5번째에 윈도우가 가득 차 도배로 잡힌다.
    for i in range(4):
        assert detector.check(1, f"메시지 {i}", now=BASE + i).is_spam is False
    result = detector.check(1, "메시지 4", now=BASE + 4)
    assert result.is_spam is True
    assert result.reason == "rate_limit"


def test_messages_outside_window_are_forgotten():
    detector = _detector(max_messages=4, duplicate_count=99, window_seconds=10.0)
    for i in range(4):
        detector.check(1, f"메시지 {i}", now=BASE + i)
    # 윈도우(10초)를 넘겨서 오면 이전 이력이 만료되어 다시 통과한다.
    assert detector.check(1, "한참 뒤 메시지", now=BASE + 100).is_spam is False


def test_window_is_per_user():
    detector = _detector(max_messages=4, duplicate_count=99)
    for i in range(4):
        detector.check(1, f"메시지 {i}", now=BASE + i)
    assert detector.check(2, "다른 사람 첫 메시지", now=BASE + 4).is_spam is False


# --- 근접중복 -------------------------------------------------------------


def test_near_duplicates_trip_before_rate_limit():
    detector = _detector()
    text = "품절이요 품절이요 품절이요"
    assert detector.check(7, text, now=BASE).is_spam is False  # 1회차: 이력 없음
    assert detector.check(7, text, now=BASE + 1).is_spam is False  # 2회차: 중복 1건
    result = detector.check(7, text, now=BASE + 2)  # 3회차: 중복 2건 → 임계 도달
    assert result.is_spam is True
    assert result.reason == "near_duplicate"


def test_distinct_messages_are_not_duplicates():
    detector = _detector()
    for i, text in enumerate(["안녕하세요", "잘 보고 있습니다", "옷 예쁘네요"]):
        assert detector.check(8, text, now=BASE + i).is_spam is False


def test_non_spam_score_stays_below_one():
    detector = _detector()
    text = "품절이요 품절이요 품절이요"
    detector.check(9, text, now=BASE)
    result = detector.check(9, text, now=BASE + 1)
    # 아직 도배는 아니지만 근접도가 점수로 드러난다(튜닝 관찰용).
    assert result.is_spam is False
    assert 0.0 < result.score < 1.0


# --- 상태 저장소 스왑 -----------------------------------------------------


def test_default_store_is_in_memory():
    assert isinstance(build_state_store(), InMemoryStateStore)
    assert registry.ACTIVE_STATE_STORE == "memory"


def test_redis_store_is_declared_but_not_implemented():
    # 다중 워커 대응 자리(-188). 인터페이스만 있고 호출하면 명확히 실패한다.
    with pytest.raises(NotImplementedError):
        RedisStateStore().record("1", "x", now=BASE)


def test_unknown_store_backend_fails_fast():
    with pytest.raises(ValueError, match="등록되지 않은 상태 저장소"):
        build_state_store("dynamo")
