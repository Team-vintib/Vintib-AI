"""추천 서빙 로직 테스트 (표준 라이브러리만 사용 — CI에서 그대로 실행)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.recommend.schemas import EntityType
from app.recommend.service import (
    ArtifactNotFound,
    EntityItemNotFound,
    RecommendService,
    get_recommend_service,
)


def _write_sample_artifact(base: Path) -> None:
    entity_dir = base / "brand"
    entity_dir.mkdir(parents=True)
    nodes = [
        {"id": "a", "name": "Alpha", "x": 0.0, "y": 0.0, "size": 10.0, "thumbnail": "a.jpg"},
        {"id": "b", "name": "Beta", "x": 10.0, "y": 0.0, "size": 12.0, "thumbnail": "b.jpg"},
        {"id": "c", "name": "Gamma", "x": 50.0, "y": 50.0, "size": 8.0, "thumbnail": None},
    ]
    edges = [
        {"source": "a", "target": "b", "weight": 0.9},
        {"source": "a", "target": "c", "weight": 0.3},
    ]
    neighbors = {
        "a": [["b", 0.9], ["c", 0.3]],
        "b": [["a", 0.9], ["c", 0.25]],
        "c": [["a", 0.3], ["b", 0.25]],
    }
    meta = {"entity_type": "brand", "embedding_model": "test", "dim": 4, "count": 3}
    (entity_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (entity_dir / "nodes.json").write_text(json.dumps(nodes), encoding="utf-8")
    (entity_dir / "edges.json").write_text(json.dumps(edges), encoding="utf-8")
    (entity_dir / "neighbors.json").write_text(json.dumps(neighbors), encoding="utf-8")


def test_get_graph_full(tmp_path):
    _write_sample_artifact(tmp_path)
    service = RecommendService(tmp_path)
    resp = service.get_graph(EntityType.brand, None, 10)
    assert {n.id for n in resp.nodes} == {"a", "b", "c"}
    assert len(resp.edges) == 2


def test_get_graph_focus_returns_subgraph(tmp_path):
    _write_sample_artifact(tmp_path)
    service = RecommendService(tmp_path)
    resp = service.get_graph(EntityType.brand, "a", 1)
    assert {n.id for n in resp.nodes} == {"a", "b"}  # focus + top-1 이웃
    assert len(resp.edges) == 1  # keep 집합 내부 엣지만
    assert all(e.source in {"a", "b"} and e.target in {"a", "b"} for e in resp.edges)


def test_get_similar_ranked_desc(tmp_path):
    _write_sample_artifact(tmp_path)
    service = RecommendService(tmp_path)
    resp = service.get_similar(EntityType.brand, "a", 5)
    assert [it.id for it in resp.items] == ["b", "c"]
    assert resp.items[0].name == "Beta"
    assert resp.items[0].score == 0.9


def test_unknown_item_raises(tmp_path):
    _write_sample_artifact(tmp_path)
    service = RecommendService(tmp_path)
    with pytest.raises(EntityItemNotFound):
        service.get_similar(EntityType.brand, "zzz", 5)


def test_missing_artifact_raises(tmp_path):
    service = RecommendService(tmp_path)
    with pytest.raises(ArtifactNotFound):
        service.get_graph(EntityType.brand, None, 5)


def test_api_503_without_artifact(tmp_path):
    app.dependency_overrides[get_recommend_service] = lambda: RecommendService(tmp_path)
    try:
        resp = TestClient(app).get("/recommend/graph", params={"entity": "brand"})
        assert resp.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_api_graph_and_similar_ok(tmp_path):
    _write_sample_artifact(tmp_path)
    app.dependency_overrides[get_recommend_service] = lambda: RecommendService(tmp_path)
    try:
        client = TestClient(app)
        graph = client.get("/recommend/graph", params={"entity": "brand"})
        assert graph.status_code == 200
        assert len(graph.json()["nodes"]) == 3
        similar = client.get("/recommend/brand/a/similar", params={"k": 5})
        assert similar.status_code == 200
        assert [i["id"] for i in similar.json()["items"]] == ["b", "c"]
        missing = client.get("/recommend/brand/zzz/similar")
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
