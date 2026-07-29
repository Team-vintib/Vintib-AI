"""추천 아티팩트 포맷 정의 및 입출력.

오프라인 파이프라인(app/recommend/pipeline/)이 브랜드 대표 벡터를 집계·유사도·2D 레이아웃까지
사전계산한 결과를 JSON으로 저장하고, 서빙(service)이 그것을 읽는다. 서빙 경로에 무거운 의존성이
없도록 이 모듈은 표준 라이브러리(json)만 사용한다.

엔티티별 디렉터리 구조:
    <base>/<entity>/meta.json       # {entity_type, embedding_model, dim, count, built_at}
    <base>/<entity>/nodes.json      # [{id, name, x, y, size, thumbnail}]
    <base>/<entity>/edges.json      # [{source, target, weight}]  (kNN, 무방향 dedup)
    <base>/<entity>/neighbors.json  # {id: [[neighbor_id, score], ...]}  (유사도 내림차순)
"""

import json
from dataclasses import dataclass
from pathlib import Path

META_FILE = "meta.json"
NODES_FILE = "nodes.json"
EDGES_FILE = "edges.json"
NEIGHBORS_FILE = "neighbors.json"


@dataclass(frozen=True)
class Artifact:
    meta: dict
    nodes: list[dict]
    edges: list[dict]
    neighbors: dict[str, list]
    node_by_id: dict[str, dict]


def _read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def artifact_exists(entity_dir: Path) -> bool:
    return (entity_dir / META_FILE).is_file()


def load_artifact(entity_dir: Path) -> Artifact:
    nodes = _read_json(entity_dir / NODES_FILE)
    return Artifact(
        meta=_read_json(entity_dir / META_FILE),
        nodes=nodes,
        edges=_read_json(entity_dir / EDGES_FILE),
        neighbors=_read_json(entity_dir / NEIGHBORS_FILE),
        node_by_id={node["id"]: node for node in nodes},
    )


def write_artifact(entity_dir: Path, meta, nodes, edges, neighbors) -> None:
    entity_dir.mkdir(parents=True, exist_ok=True)
    _write_json(entity_dir / META_FILE, meta)
    _write_json(entity_dir / NODES_FILE, nodes)
    _write_json(entity_dir / EDGES_FILE, edges)
    _write_json(entity_dir / NEIGHBORS_FILE, neighbors)
