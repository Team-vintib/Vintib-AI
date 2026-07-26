"""추천 도메인 로직.

오프라인에서 사전계산한 아티팩트(브랜드 대표 벡터의 집계·유사도·2D 레이아웃 결과)를 읽어
그래프/유사도 질의를 처리한다. 서빙 경로는 표준 라이브러리만 사용한다(요청 시점에 임베딩·행렬
연산 없음 — 모두 오프라인에서 계산됨). 아티팩트 생성은 app/recommend/pipeline/ 이 담당한다.
설계: .claude/plans/ai/001-brand-similarity-graph.md
"""

from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.recommend.artifact import Artifact, artifact_exists, load_artifact
from app.recommend.schemas import (
    EntityType,
    GraphEdge,
    GraphNode,
    GraphResponse,
    SimilarItem,
    SimilarResponse,
)


class ArtifactNotFound(Exception):
    """요청한 엔티티의 사전계산 아티팩트가 아직 생성되지 않음."""


class EntityItemNotFound(Exception):
    """요청한 엔티티 id가 아티팩트에 존재하지 않음."""


class RecommendService:
    """엔티티별 아티팩트를 인메모리로 로드·캐시해 그래프/유사도 질의를 처리한다."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._cache: dict[str, Artifact] = {}

    def _artifact(self, entity: EntityType) -> Artifact:
        key = entity.value
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        entity_dir = self._base_dir / key
        if not artifact_exists(entity_dir):
            raise ArtifactNotFound(
                f"'{key}' 아티팩트가 없습니다. 오프라인 파이프라인(build_artifact)을 먼저 실행하세요."
            )
        artifact = load_artifact(entity_dir)
        self._cache[key] = artifact
        return artifact

    def get_graph(self, entity: EntityType, focus: str | None, k: int) -> GraphResponse:
        artifact = self._artifact(entity)
        if focus is None:
            nodes = [GraphNode(**node) for node in artifact.nodes]
            edges = [GraphEdge(**edge) for edge in artifact.edges]
            return GraphResponse(entity=entity, focus=None, nodes=nodes, edges=edges)

        if focus not in artifact.node_by_id:
            raise EntityItemNotFound(
                f"'{focus}' 를 '{entity.value}' 아티팩트에서 찾을 수 없습니다."
            )
        neighbor_ids = [nid for nid, _ in artifact.neighbors.get(focus, [])[:k]]
        keep = {focus, *neighbor_ids}
        nodes = [GraphNode(**artifact.node_by_id[i]) for i in keep if i in artifact.node_by_id]
        edges = [
            GraphEdge(**edge)
            for edge in artifact.edges
            if edge["source"] in keep and edge["target"] in keep
        ]
        return GraphResponse(entity=entity, focus=focus, nodes=nodes, edges=edges)

    def get_similar(self, entity: EntityType, entity_id: str, k: int) -> SimilarResponse:
        artifact = self._artifact(entity)
        if entity_id not in artifact.node_by_id:
            raise EntityItemNotFound(
                f"'{entity_id}' 를 '{entity.value}' 아티팩트에서 찾을 수 없습니다."
            )
        items = []
        for nid, score in artifact.neighbors.get(entity_id, [])[:k]:
            node = artifact.node_by_id.get(nid)
            if node is None:
                continue
            items.append(
                SimilarItem(id=nid, name=node["name"], score=score, thumbnail=node.get("thumbnail"))
            )
        return SimilarResponse(entity=entity, id=entity_id, items=items)


def _default_base_dir() -> Path:
    if settings.recommend_artifact_dir:
        return Path(settings.recommend_artifact_dir)
    return Path(__file__).resolve().parent / "artifacts"


@lru_cache
def get_recommend_service() -> RecommendService:
    """FastAPI 의존성 주입용 서비스 프로바이더(싱글턴, 아티팩트 캐시 공유)."""
    return RecommendService(_default_base_dir())
