"""반복 위반자 임시 음소거(-571 후속, CH025) — 방송 단위 격리 + 윈도우/임계치 경계."""

from app.chat.timeout import UserTimeoutTracker

BASE = 1_000_000.0


def _tracker(**kwargs) -> UserTimeoutTracker:
    return UserTimeoutTracker(
        violation_window_seconds=kwargs.get("violation_window_seconds", 10.0),
        violation_threshold=kwargs.get("violation_threshold", 3),
        mute_seconds=kwargs.get("mute_seconds", 15.0),
    )


def test_not_muted_before_threshold():
    tracker = _tracker()
    tracker.record_violation(1, 7, now=BASE)
    tracker.record_violation(1, 7, now=BASE + 1)

    status = tracker.status(1, 7, now=BASE + 2)

    assert status.muted is False


def test_muted_once_threshold_reached():
    tracker = _tracker()
    tracker.record_violation(1, 7, now=BASE)
    tracker.record_violation(1, 7, now=BASE + 1)
    tracker.record_violation(1, 7, now=BASE + 2)

    status = tracker.status(1, 7, now=BASE + 2.1)

    assert status.muted is True
    assert status.remaining_seconds > 0


def test_mute_expires_after_configured_duration():
    tracker = _tracker(mute_seconds=15.0)
    for i in range(3):
        tracker.record_violation(1, 7, now=BASE + i)

    assert tracker.status(1, 7, now=BASE + 2 + 14.9).muted is True
    assert tracker.status(1, 7, now=BASE + 2 + 15.1).muted is False


def test_violations_outside_window_are_forgotten():
    tracker = _tracker(violation_window_seconds=10.0)
    tracker.record_violation(1, 7, now=BASE)
    tracker.record_violation(1, 7, now=BASE + 1)
    # 윈도우를 넘겨서 온 3번째 위반은 앞의 2건과 묶이지 않는다.
    tracker.record_violation(1, 7, now=BASE + 20)

    assert tracker.status(1, 7, now=BASE + 20.1).muted is False


def test_scoped_per_live_not_per_user_globally():
    tracker = _tracker()
    for i in range(3):
        tracker.record_violation(1, 7, now=BASE + i)

    # 같은 사용자라도 다른 방송에서는 음소거가 적용되지 않는다.
    assert tracker.status(1, 7, now=BASE + 2.1).muted is True
    assert tracker.status(2, 7, now=BASE + 2.1).muted is False


def test_scoped_per_user_not_per_live_globally():
    tracker = _tracker()
    for i in range(3):
        tracker.record_violation(1, 7, now=BASE + i)

    # 같은 방송이라도 다른 사용자는 음소거가 적용되지 않는다.
    assert tracker.status(1, 8, now=BASE + 2.1).muted is False


def test_violation_count_resets_when_mute_starts():
    tracker = _tracker(violation_threshold=3, mute_seconds=15.0)
    for i in range(3):
        tracker.record_violation(1, 7, now=BASE + i)
    # 음소거가 풀린 직후에도, 리셋되지 않은 잔여 카운트로 곧바로 재적발되면 안 된다.
    after_mute = BASE + 2 + 15.1
    tracker.record_violation(1, 7, now=after_mute)

    assert tracker.status(1, 7, now=after_mute + 0.1).muted is False
