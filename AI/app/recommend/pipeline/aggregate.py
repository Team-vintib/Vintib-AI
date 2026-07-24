"""항목(상품) 임베딩을 엔티티(브랜드/상점)별 대표 벡터로 집계한다.

`group_ids` 만 브랜드 id ↔ 상점 id 로 바꾸면 상점 유사도로 그대로 재사용된다.
"""

import numpy as np


def aggregate_by_group(item_vectors: np.ndarray, group_ids: list[str]):
    """항목 임베딩을 그룹별 평균(L2 정규화) 대표 벡터로 집계한다.

    Args:
        item_vectors: (M, D) 항목 임베딩.
        group_ids: 길이 M. 각 항목이 속한 그룹(브랜드/상점) id.

    Returns:
        (ids, vectors, counts): 그룹 id 목록(첫 등장 순), (G, D) 정규화 대표 벡터,
        각 그룹의 항목 수.
    """
    ids: list[str] = []
    index: dict[str, int] = {}
    for gid in group_ids:
        if gid not in index:
            index[gid] = len(ids)
            ids.append(gid)

    dim = item_vectors.shape[1]
    sums = np.zeros((len(ids), dim), dtype=np.float64)
    counts = np.zeros(len(ids), dtype=np.int64)
    for vec, gid in zip(item_vectors, group_ids):
        i = index[gid]
        sums[i] += vec
        counts[i] += 1

    means = sums / counts[:, None]
    norms = np.linalg.norm(means, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    vectors = (means / norms).astype(np.float32)
    return ids, vectors, counts.tolist()
