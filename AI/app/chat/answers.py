"""생성된 반복질문 답변의 저장소.

판정(`POST /chat/moderate`)은 동기지만 답변 생성은 그 응답을 막지 않는다. 판정은 티켓만 돌려주고
답변은 여기 쌓였다가 `GET /chat/lives/{live_id}/answers`로 조회된다. 이 분리 덕분에 나중에
생성 LLM처럼 느린 백엔드를 끼워도 채팅 지연 예산(p95 300ms)에 영향이 없다.

인메모리 구현은 프로세스마다 저장소가 갈리므로 워커가 늘어나면 답변이 조회되지 않을 수 있다
— 상태 공유는 Redis 구현으로 교체한다(S15P11A108-188).

설계: .claude/plans/ai/003-live-comment-moderation-prototype.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from zoneinfo import ZoneInfo

from app.chat import registry
from app.chat.schemas import FaqAnswer

# BE가 naive(오프셋 없음)로 보내는 시각은 BE 서버 타임존(KST) 벽시계 시각이다 — UTC가 아니다.
# 이 프로젝트는 단일 지역(한국) 서비스라 BE 전체가 LocalDateTime(KST)로 일관되게 짜여 있고,
# AI만 내부적으로 UTC(datetime.now(UTC))를 쓴다. 예전엔 naive를 UTC로 잘못 간주해서, 방송
# 시작 시각(KST)이 실제보다 9시간 앞선 것으로 취급돼 그 뒤에 생성된 답변이 전부 "since 이전"
# 으로 잘려나가 영원히 조회되지 않는 버그가 있었다(S15P11A108-571 후속, 실측으로 발견).
_NAIVE_TIMEZONE = ZoneInfo("Asia/Seoul")


def _as_aware(moment: datetime) -> datetime:
    """`created_at`은 항상 `datetime.now(UTC)`(offset-aware)로 만든다(`gateway/router.py`).
    `since` 쿼리 파라미터는 BE가 오프셋 없이 보낸다(-571 BE 연동에서 실측) — naive면 BE 서버
    타임존(KST)으로 간주해 맞춰준다. 서로 다른 타임존이라도 둘 다 aware이기만 하면 비교
    연산자가 알아서 절대 시각으로 정규화해 비교한다."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=_NAIVE_TIMEZONE)


class AnswerNotFound(Exception):
    """티켓에 해당하는 답변이 없음(미생성 또는 근거 부족으로 생성 안 됨)."""


class AnswerStore(ABC):
    """생성된 답변 보관소."""

    @abstractmethod
    def save(self, answer: FaqAnswer) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, ticket: str) -> FaqAnswer:
        """없으면 `AnswerNotFound`."""
        raise NotImplementedError

    @abstractmethod
    def list_for_live(self, live_id: int, since: datetime | None = None) -> list[FaqAnswer]:
        """생성 시각 오름차순. `since`가 있으면 그 이후 생성분만."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError


class InMemoryAnswerStore(AnswerStore):
    """프로세스 인메모리 저장소. 단일 워커 전용(기본값)."""

    def __init__(self) -> None:
        self._by_ticket: dict[str, FaqAnswer] = {}

    def save(self, answer: FaqAnswer) -> None:
        self._by_ticket[answer.ticket] = answer

    def get(self, ticket: str) -> FaqAnswer:
        try:
            return self._by_ticket[ticket]
        except KeyError as exc:
            raise AnswerNotFound(ticket) from exc

    def list_for_live(self, live_id: int, since: datetime | None = None) -> list[FaqAnswer]:
        found = [a for a in self._by_ticket.values() if a.live_id == live_id]
        if since is not None:
            cutoff = _as_aware(since)
            found = [a for a in found if a.created_at > cutoff]
        found.sort(key=lambda a: a.created_at)
        return found

    def clear(self) -> None:
        self._by_ticket.clear()


class RedisAnswerStore(AnswerStore):
    """Redis 공유 저장소 자리(빈 스텁).

    TODO(-188): `app/core/config.py`의 redis_* 설정으로 붙어서 티켓 키에 JSON을 넣고,
    방송별 조회는 `live_id` 인덱스(sorted set, score=created_at)로 처리한다.
    """

    def save(self, answer: FaqAnswer) -> None:
        raise NotImplementedError("RedisAnswerStore는 아직 구현되지 않았습니다 (S15P11A108-188)")

    def get(self, ticket: str) -> FaqAnswer:
        raise NotImplementedError("RedisAnswerStore는 아직 구현되지 않았습니다 (S15P11A108-188)")

    def list_for_live(self, live_id: int, since: datetime | None = None) -> list[FaqAnswer]:
        raise NotImplementedError("RedisAnswerStore는 아직 구현되지 않았습니다 (S15P11A108-188)")

    def clear(self) -> None:
        raise NotImplementedError("RedisAnswerStore는 아직 구현되지 않았습니다 (S15P11A108-188)")


def build_answer_store(key: str | None = None) -> AnswerStore:
    """상태 저장소 레지스트리 키를 그대로 따른다(스팸 윈도우와 같은 백엔드를 쓴다)."""
    resolved = key or registry.ACTIVE_STATE_STORE
    if resolved == "memory":
        return InMemoryAnswerStore()
    if resolved == "redis":
        return RedisAnswerStore()
    raise ValueError(f"등록되지 않은 답변 저장소 백엔드입니다: {resolved!r}")
