"""`AnswerStore.list_for_live()`의 `since` 필터 — naive/aware datetime 혼용 회귀(-571).

BE 연동 실측에서 `since` 쿼리 파라미터가 오프셋 없이(naive) 올 수 있는데, `created_at`은
항상 `datetime.now(UTC)`(aware)라 그대로 비교하면 `TypeError: can't compare offset-naive
and offset-aware datetimes`로 500이 났다.

그 크래시를 고친 뒤에도 두 번째 버그가 남아 있었다 — naive를 UTC로 간주했는데 실제로는
BE 서버 타임존(KST) 벽시계 시각이었다. 9시간 오차 때문에 방송 시작 직후 생성된 답변이
전부 "since 이전"으로 잘려나가 영원히 조회되지 않았다(실측으로 발견, -571 후속).
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
    # since(naive) = KST 09:30 = UTC 00:30. old는 그 전, new는 그 후에 생성된 상황.
    store.save(_answer("a_1_old", 1, datetime(2026, 8, 7, 0, 0, tzinfo=UTC)))
    store.save(_answer("a_1_new", 1, datetime(2026, 8, 7, 1, 0, tzinfo=UTC)))

    found = store.list_for_live(1, since=datetime(2026, 8, 7, 9, 30))

    assert [a.ticket for a in found] == ["a_1_new"]


def test_naive_since는_KST로_해석된다():
    """실측으로 발견된 버그의 재현 시나리오: 방송이 KST 14:00에 시작했고(BE가 이 시각을
    naive로 그대로 보냄), 반복질문 답변은 그 26분 뒤(UTC 05:26 = KST 14:26)에 생성됐다.
    naive를 UTC로 잘못 간주하면 since가 실제보다 9시간 앞선 것으로 취급돼 이 답변이
    걸러진다 — KST로 올바르게 해석하면 정상적으로 조회돼야 한다."""
    store = InMemoryAnswerStore()
    store.save(_answer("a_1_new", 1, datetime(2026, 8, 7, 5, 26, tzinfo=UTC)))

    since_kst_naive = datetime(2026, 8, 7, 14, 0)  # BE가 보내는 원본 형태(오프셋 없음)
    found = store.list_for_live(1, since=since_kst_naive)

    assert len(found) == 1


def test_aware_since도_그대로_동작한다():
    store = InMemoryAnswerStore()
    store.save(_answer("a_1_x", 1, datetime(2026, 8, 7, 0, 20, tzinfo=UTC)))

    found = store.list_for_live(1, since=datetime(2026, 8, 7, 0, 0, tzinfo=UTC))

    assert len(found) == 1
