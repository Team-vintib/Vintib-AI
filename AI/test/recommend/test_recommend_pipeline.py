"""추천 오프라인 파이프라인의 순수 계산 로직 테스트.

numpy가 필요하므로 CI(무거운 의존성 미설치)에서는 importorskip으로 스킵된다.
CLIP 임베딩(embed_images)은 모델 다운로드가 필요해 여기서 다루지 않는다.
"""

import pytest

np = pytest.importorskip("numpy")

from app.recommend.pipeline.aggregate import aggregate_by_group  # noqa: E402
from app.recommend.pipeline.layout import project_2d  # noqa: E402
from app.recommend.pipeline.similarity import knn_edges, top_neighbors  # noqa: E402


def test_aggregate_groups_and_normalizes():
    vecs = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 2.0]], dtype=np.float32)
    ids, vectors, counts = aggregate_by_group(vecs, ["x", "x", "y"])
    assert ids == ["x", "y"]  # 첫 등장 순서
    assert counts == [2, 1]
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), [1.0, 1.0], atol=1e-6)
    np.testing.assert_allclose(vectors[0], [1.0, 0.0], atol=1e-6)


def test_knn_edges_dedup_and_threshold():
    vectors = np.array([[1.0, 0.0], [0.9, 0.1], [-1.0, 0.0]], dtype=np.float32)
    edges = knn_edges(vectors, ["a", "b", "c"], k=2, threshold=0.0)
    pairs = [(e["source"], e["target"]) for e in edges]
    assert ("a", "b") in pairs
    assert pairs == [tuple(sorted(p)) for p in pairs]  # 무방향 정렬
    assert len(pairs) == len(set(pairs))  # 중복 없음
    assert all(e["weight"] >= 0.0 for e in edges)  # 음수 유사도(c) 제외


def test_top_neighbors_sorted_desc():
    vectors = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]], dtype=np.float32)
    neighbors = top_neighbors(vectors, ["a", "b", "c"], n=2)
    assert neighbors["a"][0][0] == "b"  # a 와 가장 유사한 건 b
    scores = [s for _, s in neighbors["a"]]
    assert scores == sorted(scores, reverse=True)


def test_project_2d_shape_and_range():
    rng = np.random.default_rng(0)
    vectors = rng.normal(size=(6, 8)).astype(np.float32)
    coords = project_2d(vectors, seed=0, span=100.0)
    assert coords.shape == (6, 2)
    assert coords.min() >= -1e-6
    assert coords.max() <= 100.0 + 1e-6
