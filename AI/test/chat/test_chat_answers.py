"""`AnswerStore.list_for_live()`의 `since` 필터 — naive/aware datetime 혼용 회귀(-571).

BE 연동 실측에서 `since` 쿼리 파라미터가 오프셋 없이(naive) 올 수 있는데, `created_at`은
항상 `datetime.now(UTC)`(aware)라 그대로 비교하면 `TypeError: can't compare offset-naive
and offset-aware datetimes`로 500이 났다.
"""

from datetime import UTC, datetime

from app.chat.answers import InMemoryAnswerStore
from app.chat.schemas import FaqAnswer


def _answer(ticket: str, live_id: int, created_at: datetime) -> FaqAnswer:
    return FaqAnswer(
        ticket=ticket,
        live_id=live_id,
        question="이거 프리사이즈인가요?",
        cluster_size=2,
        answer="네, 프리사이즈입니다.",
        grounded=True,
        grounding_score=1.0,
        sources=[],
        created_at=created_at,
    )


def test_naive_since와_aware_created_at을_비교해도_터지지_않는다():
    store = InMemoryAnswerStore()
    store.save(_answer("a_1_x", 1, datetime(2026, 8, 7, 0, 20, tzinfo=UTC)))

    naive_since = datetime(2026, 8, 7, 0, 0)  # tzinfo 없음 — BE가 실제로 보내는 형태
    found = store.list_for_live(1, since=naive_since)

    assert len(found) == 1


def test_since_이전_답변은_제외된다():
    store = InMemoryAnswerStore()
    store.save(_answer("a_1_old", 1, datetime(2026, 8, 7, 0, 0, tzinfo=UTC)))
    store.save(_answer("a_1_new", 1, datetime(2026, 8, 7, 1, 0, tzinfo=UTC)))

    found = store.list_for_live(1, since=datetime(2026, 8, 7, 0, 30))

    assert [a.ticket for a in found] == ["a_1_new"]


def test_aware_since도_그대로_동작한다():
    store = InMemoryAnswerStore()
    store.save(_answer("a_1_x", 1, datetime(2026, 8, 7, 0, 20, tzinfo=UTC)))

    found = store.list_for_live(1, since=datetime(2026, 8, 7, 0, 0, tzinfo=UTC))

    assert len(found) == 1
