"""대표 벡터를 2D 좌표로 투영한다(그래프 맵 배치용).

UMAP(코사인 메트릭)을 우선 사용하고, 미설치·실패 시 PCA로 폴백한다.
결과는 [0, span] 범위로 정규화한다.
"""

import numpy as np


def project_2d(vectors: np.ndarray, seed: int = 42, span: float = 100.0) -> np.ndarray:
    coords = _umap_2d(vectors, seed)
    if coords is None:
        coords = _pca_2d(vectors)
    return _normalize(coords, span)


def _umap_2d(vectors: np.ndarray, seed: int):
    try:
        import umap
    except Exception:
        return None
    try:
        reducer = umap.UMAP(n_components=2, metric="cosine", random_state=seed)
        return np.asarray(reducer.fit_transform(vectors), dtype=np.float64)
    except Exception:
        return None


def _pca_2d(vectors: np.ndarray) -> np.ndarray:
    centered = np.asarray(vectors, dtype=np.float64)
    centered = centered - centered.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    if vt.shape[0] < 2:
        vt = np.vstack([vt, np.zeros((2 - vt.shape[0], vt.shape[1]))])
    return centered @ vt[:2].T


def _normalize(coords: np.ndarray, span: float) -> np.ndarray:
    coords = np.asarray(coords, dtype=np.float64)
    mn = coords.min(axis=0)
    mx = coords.max(axis=0)
    rng = mx - mn
    rng[rng == 0] = 1.0
    return (coords - mn) / rng * span
