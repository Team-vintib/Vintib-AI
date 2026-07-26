"""대표 벡터 간 코사인 유사도 기반 그래프 엣지·이웃 목록 계산."""

import numpy as np


def _cosine_matrix(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = vectors / norms
    sim = normalized @ normalized.T
    np.fill_diagonal(sim, -1.0)
    return sim


def knn_edges(vectors: np.ndarray, ids: list[str], k: int = 8, threshold: float = 0.0):
    """각 노드의 상위 k 이웃을 무방향 엣지로 만든다(양방향 중복은 큰 가중치로 dedup)."""
    sim = _cosine_matrix(vectors)
    edges: dict[tuple[str, str], float] = {}
    for i in range(len(ids)):
        for j in np.argsort(-sim[i])[:k]:
            weight = float(sim[i, int(j)])
            if weight < threshold:
                continue
            a, b = sorted((ids[i], ids[int(j)]))
            if a == b:
                continue
            prev = edges.get((a, b))
            if prev is None or weight > prev:
                edges[(a, b)] = weight
    return [{"source": a, "target": b, "weight": round(w, 4)} for (a, b), w in edges.items()]


def top_neighbors(vectors: np.ndarray, ids: list[str], n: int = 50):
    """노드별 상위 n 이웃을 유사도 내림차순 [[id, score], ...] 로 반환한다."""
    sim = _cosine_matrix(vectors)
    neighbors: dict[str, list] = {}
    for i in range(len(ids)):
        row = []
        for j in np.argsort(-sim[i])[:n]:
            score = float(sim[i, int(j)])
            if score <= -1.0:
                continue
            row.append([ids[int(j)], round(score, 4)])
        neighbors[ids[i]] = row
    return neighbors
