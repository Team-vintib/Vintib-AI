"""반복 위반자 임시 음소거 — 방송(live_id) 단위(-571 후속, CH025).

메시지 단위 차단(스팸/악성 판정)과 별개다. 그건 "이 메시지 하나"를 막고, 여기는 "짧은 시간
안에 반복해서 걸린 사람"이 계속 시도하는 것 자체를 막는다. 방송 단위로 격리하는 이유는 채팅
자체가 방송 단위 공간이라, 다른 방송에서의 위반 이력과 섞이면 이상해서다.

설계: docs/plans/AI/CH025-chat-user-timeout.md
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass

from app.chat import registry


@dataclass(frozen=True)
class TimeoutStatus:
    muted: bool
    remaining_seconds: float


class UserTimeoutTracker:
    """방송+사용자 단위로 위반(스팸/악성 차단) 횟수를 세고, 임계치를 넘으면 음소거한다."""

    def __init__(
        self,
        *,
        violation_window_seconds: float = registry.TIMEOUT_VIOLATION_WINDOW_SECONDS,
        violation_threshold: int = registry.TIMEOUT_VIOLATION_THRESHOLD,
        mute_seconds: float = registry.TIMEOUT_MUTE_SECONDS,
    ) -> None:
        self._violation_window_seconds = violation_window_seconds
        self._violation_threshold = violation_threshold
        self._mute_seconds = mute_seconds
        self._violations: dict[str, deque[float]] = defaultdict(deque)
        self._muted_until: dict[str, float] = {}

    def status(self, live_id: int, user_id: int, *, now: float | None = None) -> TimeoutStatus:
        """지금 음소거 중인지. 판정 로직이 다른 검사보다 먼저 이걸 확인한다."""
        moment = time.time() if now is None else now
        key = self._key(live_id, user_id)
        until = self._muted_until.get(key)
        if until is not None and moment < until:
            return TimeoutStatus(muted=True, remaining_seconds=round(until - moment, 1))
        return TimeoutStatus(muted=False, remaining_seconds=0.0)

    def record_violation(self, live_id: int, user_id: int, *, now: float | None = None) -> None:
        """스팸/악성으로 차단된 메시지가 나올 때마다 호출한다."""
        moment = time.time() if now is None else now
        key = self._key(live_id, user_id)
        history = self._violations[key]
        history.append(moment)
        while history and moment - history[0] > self._violation_window_seconds:
            history.popleft()

        if len(history) >= self._violation_threshold:
            self._muted_until[key] = moment + self._mute_seconds
            history.clear()  # 음소거 거는 순간 리셋 — 풀리자마자 잔여 카운트로 재적발되지 않게

    def clear(self) -> None:
        self._violations.clear()
        self._muted_until.clear()

    @staticmethod
    def _key(live_id: int, user_id: int) -> str:
        return f"{live_id}:{user_id}"
