"""개인화 추천 서빙 로직 테스트.

표준 라이브러리 + numpy(서빙 경량 의존성) + FastAPI TestClient 만 사용 → CI에서 그대로 실행된다.
번들된 목업 카탈로그(data/mock_catalog.json)를 실제 로더로 읽어, 신호만 주입해 티어별 랭킹을
검증한다. 카탈로그 벡터는 id 기반 결정적 생성이라 재현 가능하다.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.recommend.personalize.catalog import CatalogNotReady, get_catalog
from app.recommend.personalize.service import (
    PersonalizeService,
    get_personalize_service,
)
from app.recommend.personalize.signals import SignalProvider, UserSignals

# 번들 목업 카탈로그의 고정 사실(테스트 기대값 근거).
VISIBLE_IDS = {101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115}
HIDDEN_IDS = {116, 117, 118}  # SOLD / DRAFT / PRIVATE
DENIM_OR_LEVIS = {101, 102, 110, 114}  # 카테고리4(데님) 또는 브랜드1(Levi's), 가시
POPULAR_TOP_ID = 104  # 가시 후보 중 view_count 최대(2110)


class _FixedSignals(SignalProvider):
    """항상 같은 신호를 돌려주는 테스트용 프로바이더."""

    def __init__(self, signals: UserSignals) -> None:
        self._signals = signals

    def get_signals(self, user_id):  # noqa: ANN001 - 테스트 스텁
        return self._signals


def _service(signals: UserSignals | None = None) -> PersonalizeService:
    return PersonalizeService(get_catalog, _FixedSignals(signals or UserSignals()))


def _ids(response) -> list[int]:
    return [item.product_id for item in response.items]


# --- 필터 -----------------------------------------------------------------
def test_visibility_filter_excludes_hidden():
    resp = _service().recommend(None, None, None, 1, 100)
    ids = set(_ids(resp))
    assert ids == VISIBLE_IDS
    assert not (ids & HIDDEN_IDS)
    assert resp.total == len(VISIBLE_IDS)


def test_category_filter():
    resp = _service().recommend(None, 4, None, 1, 100)  # 데님
    assert set(_ids(resp)) == {101, 102, 110, 114}


def test_brand_filter():
    resp = _service().recommend(None, None, 5, 1, 100)  # Polo (가시)
    assert set(_ids(resp)) == {106, 107, 109}


def test_empty_candidates_returns_empty():
    resp = _service().recommend(None, 999, None, 1, 20)
    assert resp.items == []
    assert resp.total == 0
    assert resp.strategy.value == "popularity"


# --- T0 popularity --------------------------------------------------------
def test_t0_popularity_order_and_flags():
    resp = _service().recommend(None, None, None, 1, 100)
    assert resp.strategy.value == "popularity"
    assert resp.personalized is False
    assert _ids(resp)[0] == POPULAR_TOP_ID
    views = [get_catalog().items[get_catalog().index_of(pid)].view_count for pid in _ids(resp)]
    assert views == sorted(views, reverse=True)  # view_count 내림차순


# --- T2 interaction -------------------------------------------------------
def test_t2_interaction_ranks_similar_first():
    signals = UserSignals(interaction_product_ids=[101, 102])  # 데님/Levi's 취향
    resp = _service(signals).recommend(None, None, None, 1, 100)
    assert resp.strategy.value == "interaction"
    assert resp.personalized is True
    ids = _ids(resp)
    assert ids[0] in DENIM_OR_LEVIS
    # 취향(데님/Levi's) 아이템은 무관한 원피스(108)보다 위에 온다.
    pos = {pid: i for i, pid in enumerate(ids)}
    assert pos[101] < pos[108]
    assert pos[102] < pos[108]
    assert pos[114] < pos[108]
    # 코사인 점수는 내림차순.
    scores = [item.score for item in resp.items]
    assert scores == sorted(scores, reverse=True)


def test_t2_ignores_unresolvable_interactions_falls_back_to_t0():
    # 카탈로그에 없는 상품 id만 있으면 취향 벡터를 못 만들어 T0로 폴백한다.
    signals = UserSignals(interaction_product_ids=[9998, 9999])
    resp = _service(signals).recommend(None, None, None, 1, 100)
    assert resp.strategy.value == "popularity"
    assert resp.personalized is False


# --- T1 onboarding --------------------------------------------------------
def test_t1_onboarding_matched_first_then_popularity_backfill():
    signals = UserSignals(interest_category_ids=[2], interest_brand_ids=[5])  # 원피스 + Polo
    resp = _service(signals).recommend(None, None, None, 1, 100)
    assert resp.strategy.value == "onboarding"
    assert resp.personalized is True
    ids = _ids(resp)
    # 관심 매칭(원피스 108/109 + Polo 106/107/109) 후보가 앞쪽을 차지한다.
    matched = {106, 107, 108, 109}
    assert set(ids[: len(matched)]) == matched
    # 나머지는 인기순 백필 — 첫 백필은 가장 인기 있는 비매칭 후보(104).
    assert ids[len(matched)] == POPULAR_TOP_ID


# --- 페이지네이션 ----------------------------------------------------------
def test_pagination_slices_full_ranking():
    svc = _service()
    page1 = svc.recommend(None, None, None, 1, 5)
    page2 = svc.recommend(None, None, None, 2, 5)
    page3 = svc.recommend(None, None, None, 3, 5)
    assert page1.total == page2.total == page3.total == len(VISIBLE_IDS)
    assert len(page1.items) == 5 and len(page2.items) == 5 and len(page3.items) == 5
    all_ids = _ids(page1) + _ids(page2) + _ids(page3)
    assert len(set(all_ids)) == 15  # 겹침 없이 전체 커버


def test_pagination_out_of_range_returns_empty():
    resp = _service().recommend(None, None, None, 99, 20)
    assert resp.items == []
    assert resp.total == len(VISIBLE_IDS)


# --- CatalogNotReady ------------------------------------------------------
def test_catalog_not_ready_propagates():
    def _broken_loader():
        raise CatalogNotReady("no artifact")

    svc = PersonalizeService(_broken_loader, _FixedSignals(UserSignals()))
    with pytest.raises(CatalogNotReady):
        svc.recommend(None, None, None, 1, 20)


# --- API 레이어 -----------------------------------------------------------
def test_api_products_ok_anonymous():
    client = TestClient(app)
    resp = client.get("/recommend/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["strategy"] == "popularity"
    assert body["personalized"] is False
    assert body["total"] == len(VISIBLE_IDS)


def test_api_products_personalized_user1():
    # 기본 서비스는 MockSignalProvider — user_id=1 → 상호작용(T2).
    client = TestClient(app)
    resp = client.get("/recommend/products", params={"user_id": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["strategy"] == "interaction"
    assert body["personalized"] is True


def test_api_503_when_catalog_not_ready():
    def _broken_loader():
        raise CatalogNotReady("no artifact")

    app.dependency_overrides[get_personalize_service] = lambda: PersonalizeService(
        _broken_loader, _FixedSignals(UserSignals())
    )
    try:
        resp = TestClient(app).get("/recommend/products")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "item embedding artifact not built"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("params", [{"size": 0}, {"size": 101}, {"page": 0}])
def test_api_422_invalid_params(params):
    resp = TestClient(app).get("/recommend/products", params=params)
    assert resp.status_code == 422
