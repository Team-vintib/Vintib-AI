"""`aihub_embedding_quality_check.py`의 순수 함수(`intra_inter_gap`/`knn_category_purity`)
테스트. 임베딩 계산 자체는 torch가 필요해 CI에서 못 돈다 — 여기선 손으로 만든 벡터로
지표 계산 로직만 고정한다.
"""

from __future__ import annotations

import numpy as np
import pytest

import aihub_embedding_quality_check as quality


def _normalize(vectors: np.ndarray) -> np.ndarray:
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def test_intra_inter_gap_is_positive_when_categories_are_well_separated():
    """카테고리마다 서로 직교에 가까운 방향에 모여 있으면 intra > inter라 gap이 양수여야 한다."""
    vectors = _normalize(
        np.array(
            [
                [1.0, 0.0, 0.0],
                [0.95, 0.05, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.95, 0.05],
            ],
            dtype=np.float32,
        )
    )
    categories = ["A", "A", "B", "B"]

    result = quality.intra_inter_gap(vectors, categories)

    assert result["gap"] > 0
    assert result["intra_mean"] > result["inter_mean"]


def test_intra_inter_gap_is_zero_when_no_separation():
    """모든 벡터가 완전히 같은 방향이면(카테고리 무관) intra == inter == 1.0, gap == 0."""
    vectors = _normalize(np.ones((4, 3), dtype=np.float32))
    categories = ["A", "A", "B", "B"]

    result = quality.intra_inter_gap(vectors, categories)

    assert result["intra_mean"] == pytest.approx(1.0, abs=1e-5)
    assert result["inter_mean"] == pytest.approx(1.0, abs=1e-5)
    assert result["gap"] == pytest.approx(0.0, abs=1e-5)


def test_knn_category_purity_is_one_when_neighbors_all_match():
    vectors = _normalize(
        np.array(
            [
                [1.0, 0.0],
                [0.99, 0.01],
                [0.98, 0.02],
                [0.0, 1.0],
                [0.01, 0.99],
                [0.02, 0.98],
            ],
            dtype=np.float32,
        )
    )
    categories = ["A", "A", "A", "B", "B", "B"]

    purity = quality.knn_category_purity(vectors, categories, top_k=2)

    assert purity == pytest.approx(1.0, abs=1e-5)


def test_knn_category_purity_excludes_self():
    """자기 자신은 최근접 이웃에서 빠져야 한다 — 안 빼면 순도가 항상 뻥튀기된다."""
    vectors = _normalize(
        np.array(
            [
                [1.0, 0.0],
                [0.0, 1.0],
            ],
            dtype=np.float32,
        )
    )
    categories = ["A", "B"]

    purity = quality.knn_category_purity(vectors, categories, top_k=1)

    # 자기 자신을 빼면 유일하게 남는 이웃은 다른 카테고리뿐이라 순도는 0이어야 한다.
    assert purity == pytest.approx(0.0, abs=1e-5)
