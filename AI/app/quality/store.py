"""검수 결과 보관소.

`POST /quality/inspections`가 만든 결과를 `GET /quality/inspections/{id}`로 다시 꺼내기 위한
저장소다. BE가 상품 등록을 확정하기 전에 결과를 재조회하거나, FE가 새로고침해도 같은 판정을
보여줄 수 있게 한다.

**TTL이 있는 이유**: 검수 결과는 상품 등록이 끝나면 BE가 자기 DB에 옮겨 담는다. AI 쪽 보관은
그 사이를 잇는 임시 버퍼일 뿐이라 무한정 들고 있을 이유가 없다.

인메모리 구현은 프로세스마다 저장소가 갈리므로 워커가 늘어나면 조회가 실패할 수 있다 —
상태 공유는 Redis 구현으로 교체한다(`app/chat/answers.py`와 같은 한계·같은 해법).

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from app.quality.schemas import InspectionResponse

# 보관 기간. 게이트웨이의 `RESULT_TTL_SECONDS`(1시간)와 같은 값으로 맞춰 둔다 — 상품 등록
# 한 건이 진행되는 동안만 살아 있으면 된다.
INSPECTION_TTL_SECONDS = 3600.0


class InspectionNotFound(Exception):
    """검수 id가 없거나 TTL이 지남 → 404."""


class InspectionStore(ABC):
    """검수 결과 보관소."""

    @abstractmethod
    def save(self, inspection: InspectionResponse) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, inspection_id: str) -> InspectionResponse:
        """없거나 만료됐으면 `InspectionNotFound`."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError


class InMemoryInspectionStore(InspectionStore):
    """프로세스 인메모리 저장소. 단일 워커 전용(기본값).

    만료 항목은 조회·저장 시점에 걷어낸다 — 백그라운드 청소 스레드를 두지 않기 위한 선택이며,
    프로토타입 규모(상품 등록 빈도)에서는 이걸로 충분하다.
    """

    def __init__(self, ttl_seconds: float = INSPECTION_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._items: dict[str, tuple[float, InspectionResponse]] = {}

    def save(self, inspection: InspectionResponse) -> None:
        self._evict_expired()
        self._items[inspection.inspection_id] = (time.monotonic(), inspection)

    def get(self, inspection_id: str) -> InspectionResponse:
        entry = self._items.get(inspection_id)
        if entry is None:
            raise InspectionNotFound(inspection_id)

        stored_at, inspection = entry
        if self._is_expired(stored_at):
            del self._items[inspection_id]
            raise InspectionNotFound(inspection_id)
        return inspection

    def clear(self) -> None:
        self._items.clear()

    def _is_expired(self, stored_at: float) -> bool:
        return time.monotonic() - stored_at > self._ttl

    def _evict_expired(self) -> None:
        expired = [key for key, (at, _) in self._items.items() if self._is_expired(at)]
        for key in expired:
            del self._items[key]


class RedisInspectionStore(InspectionStore):
    """Redis 공유 저장소 자리(빈 스텁).

    TODO(-211): `app/core/config.py`의 redis_* 설정으로 붙어서
    `quality:inspection:{id}` 키에 `model_dump_json()`을 넣고 `ex=INSPECTION_TTL_SECONDS`로
    만료를 Redis에 맡긴다(게이트웨이 `RESULT_PREFIX`와 같은 방식).
    """

    def save(self, inspection: InspectionResponse) -> None:
        raise NotImplementedError(
            "RedisInspectionStore는 아직 구현되지 않았습니다 (S15P11A108-211)"
        )

    def get(self, inspection_id: str) -> InspectionResponse:
        raise NotImplementedError(
            "RedisInspectionStore는 아직 구현되지 않았습니다 (S15P11A108-211)"
        )

    def clear(self) -> None:
        raise NotImplementedError(
            "RedisInspectionStore는 아직 구현되지 않았습니다 (S15P11A108-211)"
        )


STORE_BACKENDS: dict[str, str] = {
    "memory": "프로세스 인메모리 TTL 저장소 (단일 워커 전용)",
    "redis": "Redis 공유 저장소 (미구현 — 다중 워커 필수)",
}
ACTIVE_STORE = "memory"  # <- 여기 키만 바꾸면 스왑


def build_inspection_store(key: str | None = None) -> InspectionStore:
    resolved = key or ACTIVE_STORE
    if resolved == "memory":
        return InMemoryInspectionStore()
    if resolved == "redis":
        return RedisInspectionStore()
    raise ValueError(f"등록되지 않은 검수 저장소 백엔드입니다: {resolved!r}")
