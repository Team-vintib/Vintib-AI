"""추천 도메인 요청/응답 스키마.

브랜드 유사도 그래프 서비스의 응답 모델. `entity`로 브랜드 ↔ 판매 상점(seller)
유사도를 전환할 수 있도록 추상화한다. 설계: .claude/plans/ai/001-brand-similarity-graph.md
"""

from enum import Enum

from pydantic import BaseModel


class EntityType(str, Enum):
    """유사도 그래프의 노드 단위."""

    brand = "brand"
    seller = "seller"


class GraphNode(BaseModel):
    id: str
    name: str
    x: float
    y: float
    size: float
    thumbnail: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float


class GraphResponse(BaseModel):
    entity: EntityType
    focus: str | None = None
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class SimilarItem(BaseModel):
    id: str
    name: str
    score: float
    thumbnail: str | None = None


class SimilarResponse(BaseModel):
    entity: EntityType
    id: str
    items: list[SimilarItem]
