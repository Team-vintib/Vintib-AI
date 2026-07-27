"""도배(스팸) 탐지 — 사용자별 슬라이딩 윈도우 rate-limit + 근접중복 매칭.

`test/model_selection/chat_agent.py`의 `SpamDetector`를 프로덕션으로 승격한 것이다
(`test/`는 프로덕션에서 import하지 않는 규약 — 로직만 옮겼다).

스팸은 **모델로 판정할 수 없다**. 텍스트 분류기는 문장 하나만 보므로 "같은 말을 몇 번 했는지"를
구조적으로 알 수 없다(`classifier_benchmark.py`가 스팸 라벨을 샘플셋에서 제외한 이유와 동일).
그래서 여기는 규칙 기반이고, 갈아끼울 대상은 모델이 아니라 **상태 저장소**다.

설계: .claude/plans/ai/003-live-comment-moderation-prototype.md
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.chat import registry


class StateStore(ABC):
    """사용자별 최근 발화 이력 저장소.

    인메모리 구현은 프로세스마다 상태가 갈리므로 워커가 늘어나면 도배 판정이 새어 나간다.
    다중 워커 대응은 Redis 구현으로 교체한다(S15P11A108-188).
    """

    @abstractmethod
    def recent(self, key: str, *, now: float, window_seconds: float) -> list[str]:
        """윈도우 안에 남아 있는 발화 본문 목록(오래된 것부터)."""
        raise NotImplementedError

    @abstractmethod
    def record(self, key: str, text: str, *, now: float) -> None:
        """발화를 이력에 남긴다."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """전체 이력 초기화(테스트/방송 종료용)."""
        raise NotImplementedError


class InMemoryStateStore(StateStore):
    """프로세스 인메모리 슬라이딩 윈도우. 단일 워커 전용(기본값)."""

    def __init__(self) -> None:
        self._history: dict[str, deque[tuple[float, str]]] = defaultdict(deque)

    def recent(self, key: str, *, now: float, window_seconds: float) -> list[str]:
        history = self._history[key]
        while history and now - history[0][0] > window_seconds:
            history.popleft()
        return [text for _, text in history]

    def record(self, key: str, text: str, *, now: float) -> None:
        self._history[key].append((now, text))

    def clear(self) -> None:
        self._history.clear()


class RedisStateStore(StateStore):
    """Redis 공유 상태 자리(빈 스텁).

    TODO(-188): 다중 워커 간 도배 상태 공유. `app/core/config.py`의 redis_* 설정을 써서
    `ZADD`/`ZREMRANGEBYSCORE`로 사용자별 sorted set 윈도우를 구현하면 된다. 인터페이스는
    `InMemoryStateStore`와 동일하므로 `service.get_chat_service()`에서 한 줄만 교체한다.
    """

    def recent(self, key: str, *, now: float, window_seconds: float) -> list[str]:
        raise NotImplementedError("RedisStateStore는 아직 구현되지 않았습니다 (S15P11A108-188)")

    def record(self, key: str, text: str, *, now: float) -> None:
        raise NotImplementedError("RedisStateStore는 아직 구현되지 않았습니다 (S15P11A108-188)")

    def clear(self) -> None:
        raise NotImplementedError("RedisStateStore는 아직 구현되지 않았습니다 (S15P11A108-188)")


def build_state_store(key: str | None = None) -> StateStore:
    """레지스트리 키로 상태 저장소를 만든다."""
    resolved = key or registry.ACTIVE_STATE_STORE
    if resolved == "memory":
        return InMemoryStateStore()
    if resolved == "redis":
        return RedisStateStore()
    raise ValueError(f"등록되지 않은 상태 저장소 백엔드입니다: {resolved!r}")


@dataclass(frozen=True)
class SpamResult:
    """도배 판정 결과. score는 판정 근거의 강도(0.0~1.0)."""

    is_spam: bool
    score: float
    reason: str  # rate_limit | near_duplicate | ""


class SpamDetector:
    """윈도우 안의 발화 수(도배)와 근접중복 횟수(복붙)를 함께 본다."""

    def __init__(
        self,
        store: StateStore,
        *,
        window_seconds: float = registry.SPAM_WINDOW_SECONDS,
        max_messages: int = registry.SPAM_MAX_MESSAGES,
        similarity_threshold: float = registry.SPAM_SIMILARITY,
        duplicate_count: int = registry.SPAM_DUPLICATE_COUNT,
    ) -> None:
        self._store = store
        self._window_seconds = window_seconds
        self._max_messages = max_messages
        self._similarity_threshold = similarity_threshold
        self._duplicate_count = duplicate_count

    def check(self, user_id: int, content: str, *, now: float | None = None) -> SpamResult:
        """이번 발화를 판정하고 이력에 남긴다(판정 → 기록 순서는 스파이크와 동일)."""
        moment = time.time() if now is None else now
        key = str(user_id)
        previous = self._store.recent(key, now=moment, window_seconds=self._window_seconds)

        similarities = [SequenceMatcher(None, prev, content).ratio() for prev in previous]
        duplicates = sum(1 for ratio in similarities if ratio >= self._similarity_threshold)
        flooding = len(previous) >= self._max_messages

        self._store.record(key, content, now=moment)

        if flooding:
            return SpamResult(is_spam=True, score=1.0, reason="rate_limit")
        if duplicates >= self._duplicate_count:
            return SpamResult(is_spam=True, score=1.0, reason="near_duplicate")

        # 아직 임계에 못 미친 상태의 근접도 — 튜닝 관찰용으로 점수만 노출한다.
        pressure = len(previous) / self._max_messages if self._max_messages else 0.0
        score = max(max(similarities, default=0.0), pressure)
        return SpamResult(is_spam=False, score=round(min(score, 0.99), 4), reason="")
