"""유저 신호(온보딩 관심/상호작용 로그) 조달 추상화.

개인화 취향 벡터는 유저별 신호(찜·구매·온보딩 관심)에서 나온다. AI가 그 신호를 어떻게 읽을지
(BE 내부 REST 조회 vs 요청 바디 push vs DB 직접 접근)는 아직 미결정이라, 여기서는 조달 방식을
`SignalProvider` 인터페이스로 추상화한다. 신호 원천(member_interest_*, wish, orders)은 스키마만
있고 API가 아직 없으므로, 실제 조달 구현은 빈 스텁(`StubSignalProvider`)으로 두고 BE 회신 후
교체한다. MVP는 목업(`MockSignalProvider`)으로 전체 파이프라인(T0/T1/T2)을 굴린다.

설계·요청: .claude/plans/ai/002-personalized-recommendation-mvp.md,
           .claude/requests/be/001-personalized-rec-signals.md
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class UserSignals:
    """한 유저의 개인화 신호. 전부 비어 있으면 익명/신규와 동일하게 T0로 폴백한다.

    Attributes:
        interaction_product_ids: 찜/구매 등 상호작용한 상품 id(취향 벡터 집계용). → T2
        interest_category_ids: 온보딩에서 고른 관심 카테고리 id. → T1
        interest_brand_ids: 온보딩에서 고른 관심 브랜드 id. → T1
    """

    interaction_product_ids: list[int] = field(default_factory=list)
    interest_category_ids: list[int] = field(default_factory=list)
    interest_brand_ids: list[int] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (
            self.interaction_product_ids or self.interest_category_ids or self.interest_brand_ids
        )


class SignalProvider(ABC):
    """user_id로 개인화 신호를 조회하는 인터페이스(옵션 A: BE 내부 REST 조회 형태)."""

    @abstractmethod
    def get_signals(self, user_id: int | None) -> UserSignals:
        """user_id의 신호를 반환한다. 익명(None)/신호 없음이면 빈 UserSignals."""
        raise NotImplementedError


class StubSignalProvider(SignalProvider):
    """실 신호 조달 자리(빈 스텁). 항상 빈 신호 → 모든 유저가 T0로 폴백한다.

    TODO(BE): 신호 조달 방식(.claude/requests/be/001-personalized-rec-signals.md)이 확정되면
    이 구현만 교체한다. 옵션 A 채택 시 여기서 httpx로 BE 내부 신호 API를 호출하게 된다.
    """

    def get_signals(self, user_id: int | None) -> UserSignals:
        return UserSignals()


# --- 목업 신호: BE API 없이 전체 파이프라인(T0/T1/T2)을 굴리기 위한 데모용 ---
# 목업 카탈로그(data/mock_catalog.json)의 상품/카테고리/브랜드 id에 맞춰 하드코딩돼 있다.
# 실데이터 전환 시 StubSignalProvider(또는 실 조달 구현)로 한 줄만 교체하면 된다.
_MOCK_INTERACTIONS: dict[int, list[int]] = {
    1: [101, 102],  # 리바이스 데님 2건 → T2(데님/Levi's 취향)
}
_MOCK_INTERESTS: dict[int, tuple[list[int], list[int]]] = {
    2: ([2], [5]),  # 원피스 카테고리 + Polo 브랜드 → T1
}


class MockSignalProvider(SignalProvider):
    """목업 신호 프로바이더(TODO(BE): 실 신호 API로 교체).

    user_id=1 → 상호작용(데님 2건)으로 T2, user_id=2 → 관심(원피스+Polo)으로 T1,
    그 외/미지정/None → 빈 신호로 T0.
    """

    def get_signals(self, user_id: int | None) -> UserSignals:
        if user_id is None:
            return UserSignals()
        interactions = _MOCK_INTERACTIONS.get(user_id)
        if interactions:
            return UserSignals(interaction_product_ids=list(interactions))
        interests = _MOCK_INTERESTS.get(user_id)
        if interests:
            category_ids, brand_ids = interests
            return UserSignals(
                interest_category_ids=list(category_ids),
                interest_brand_ids=list(brand_ids),
            )
        return UserSignals()
