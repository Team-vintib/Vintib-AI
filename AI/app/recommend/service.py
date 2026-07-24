"""추천 도메인 로직.

현재는 스캐폴드 단계다. 사전계산 아티팩트(브랜드 벡터·2D 좌표·kNN 엣지)를 인메모리로
로드해 그래프/유사도 질의를 처리하는 실제 구현은
`.claude/plans/ai/001-brand-similarity-graph.md` 계획에 따라 후속 진행한다.
"""

from app.recommend.schemas import EntityType, GraphResponse, SimilarResponse


class RecommendService:
    """사전계산 아티팩트 기반 그래프/유사도 서빙(예정)."""

    def get_graph(self, entity: EntityType, focus: str | None, k: int) -> GraphResponse:
        raise NotImplementedError("브랜드 그래프 서빙은 후속 구현 예정(001 계획)")

    def get_similar(self, entity: EntityType, entity_id: str, k: int) -> SimilarResponse:
        raise NotImplementedError("유사 엔티티 서빙은 후속 구현 예정(001 계획)")


def get_recommend_service() -> RecommendService:
    """FastAPI 의존성 주입용 서비스 프로바이더."""
    return RecommendService()
