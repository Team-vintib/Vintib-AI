"""개인화 상품 추천 서빙 로직.

브랜드 그래프(001)와 달리 유저별 취향 벡터가 요청마다 달라져 **완전 사전계산이 불가**하다.
오프라인은 아이템 임베딩 캐시까지만(catalog.py), 취향 집계·후보 필터·코사인 재정렬·폴백은
요청 시점에 온라인으로 계산한다. 서빙 경로는 표준 라이브러리 + numpy(경량)만 쓴다.

콜드스타트 티어(요청 신호에 따라 자동 선택, 응답 strategy로 노출):
    T0 popularity  — 신호 없음/익명 → view_count 인기순. personalized=False.
    T1 onboarding  — 관심 카테고리/브랜드 → 프로토타입 벡터 코사인 + 인기순 백필. personalized=True.
    T2 interaction — 찜/구매 상호작용 → 취향 벡터(상호작용 아이템 평균) 코사인. personalized=True.

설계: .claude/plans/ai/002-personalized-recommendation-mvp.md
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

import numpy as np

from app.recommend.personalize.catalog import (
    Catalog,
    CatalogItem,
    CatalogNotReady,
    get_catalog,
)
from app.recommend.personalize.schemas import (
    ProductCard,
    RecommendResponse,
    Strategy,
)
from app.recommend.personalize.signals import (
    MockSignalProvider,
    SignalProvider,
    UserSignals,
)

# CatalogNotReady 를 라우터가 import 하기 쉽도록 재노출(503 매핑용).
__all__ = ["PersonalizeService", "CatalogNotReady", "get_personalize_service"]


class PersonalizeService:
    """카탈로그(아이템 벡터)와 유저 신호를 받아 티어별 랭킹을 계산한다."""

    def __init__(
        self,
        catalog_loader: Callable[[], Catalog],
        signal_provider: SignalProvider,
    ) -> None:
        self._catalog_loader = catalog_loader
        self._signal_provider = signal_provider

    def recommend(
        self,
        user_id: int | None,
        category_id: int | None,
        brand_id: int | None,
        page: int,
        size: int,
    ) -> RecommendResponse:
        catalog = self._catalog_loader()  # 실패 시 CatalogNotReady → 라우터 503
        signals = self._signal_provider.get_signals(user_id)
        candidates = self._filter_candidates(catalog, category_id, brand_id)

        if not candidates:
            return RecommendResponse(
                strategy=Strategy.popularity,
                personalized=False,
                page=page,
                size=size,
                total=0,
                items=[],
            )

        strategy, personalized, ranked = self._rank(catalog, candidates, signals)
        total = len(ranked)
        start = (page - 1) * size
        page_slice = ranked[start : start + size]
        items = [self._to_card(catalog.items[idx], score) for idx, score in page_slice]
        return RecommendResponse(
            strategy=strategy,
            personalized=personalized,
            page=page,
            size=size,
            total=total,
            items=items,
        )

    # -- 후보 필터 --------------------------------------------------------
    def _filter_candidates(
        self, catalog: Catalog, category_id: int | None, brand_id: int | None
    ) -> list[int]:
        """가시성 + 카테고리/브랜드 필터를 통과한 아이템 인덱스 목록."""
        result: list[int] = []
        for idx, item in enumerate(catalog.items):
            if not item.is_visible:
                continue
            if category_id is not None and item.category_id != category_id:
                continue
            if brand_id is not None and item.brand_id != brand_id:
                continue
            result.append(idx)
        return result

    # -- 티어 선택 + 랭킹 -------------------------------------------------
    def _rank(
        self, catalog: Catalog, candidates: list[int], signals: UserSignals
    ) -> tuple[Strategy, bool, list[tuple[int, float]]]:
        interaction_indices = [
            i for pid in signals.interaction_product_ids if (i := catalog.index_of(pid)) is not None
        ]
        if interaction_indices:
            taste = self._mean_vector(catalog, interaction_indices)
            ranked = self._cosine_rank(catalog, candidates, taste)
            return Strategy.interaction, True, ranked

        if signals.interest_category_ids or signals.interest_brand_ids:
            ranked = self._onboarding_rank(catalog, candidates, signals)
            return Strategy.onboarding, True, ranked

        return Strategy.popularity, False, self._popularity_rank(catalog, candidates)

    def _onboarding_rank(
        self, catalog: Catalog, candidates: list[int], signals: UserSignals
    ) -> list[tuple[int, float]]:
        """관심 카테고리/브랜드 매칭 후보는 프로토타입 코사인, 나머지는 인기순 백필."""
        interest_categories = set(signals.interest_category_ids)
        interest_brands = set(signals.interest_brand_ids)
        matched = [
            idx
            for idx in candidates
            if catalog.items[idx].category_id in interest_categories
            or catalog.items[idx].brand_id in interest_brands
        ]
        matched_set = set(matched)
        rest = [idx for idx in candidates if idx not in matched_set]

        matched_ranked: list[tuple[int, float]] = []
        if matched:
            prototype = self._mean_vector(catalog, matched)
            matched_ranked = self._cosine_rank(catalog, matched, prototype)
        return matched_ranked + self._popularity_rank(catalog, rest)

    def _popularity_rank(self, catalog: Catalog, indices: list[int]) -> list[tuple[int, float]]:
        """view_count 내림차순 + view_count/max_view 정규화 점수."""
        if not indices:
            return []
        max_view = max(catalog.items[i].view_count for i in indices)
        scored = [
            (idx, (catalog.items[idx].view_count / max_view) if max_view > 0 else 0.0)
            for idx in indices
        ]
        # 동점은 원래 순서(카탈로그 인덱스) 유지 — 결정적 정렬.
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored

    # -- 벡터 유틸 --------------------------------------------------------
    def _mean_vector(self, catalog: Catalog, indices: list[int]) -> np.ndarray:
        mean = catalog.vectors[indices].mean(axis=0)
        norm = np.linalg.norm(mean)
        return mean if norm == 0.0 else mean / norm

    def _cosine_rank(
        self, catalog: Catalog, indices: list[int], query: np.ndarray
    ) -> list[tuple[int, float]]:
        """query 와 후보 벡터의 코사인 내림차순(벡터는 이미 L2 정규화 → 내적=코사인)."""
        idx_arr = np.asarray(indices)
        sims = catalog.vectors[idx_arr] @ query
        order = np.argsort(-sims, kind="stable")
        return [(int(idx_arr[o]), float(sims[o])) for o in order]

    # -- 응답 변환 --------------------------------------------------------
    def _to_card(self, item: CatalogItem, score: float) -> ProductCard:
        return ProductCard(
            product_id=item.product_id,
            title=item.title,
            thumbnail=item.thumbnail,
            price=item.price,
            brand=item.brand,
            sale_type=item.sale_type,
            sale_status=item.sale_status,
            score=round(score, 4),
        )


@lru_cache
def get_personalize_service() -> PersonalizeService:
    """FastAPI 의존성 주입용 서비스 프로바이더(싱글턴).

    MVP 기본은 목업 신호(MockSignalProvider). 실 신호 API가 생기면 signals.py의
    StubSignalProvider(또는 실 구현)로 교체한다.
    """
    return PersonalizeService(catalog_loader=get_catalog, signal_provider=MockSignalProvider())
