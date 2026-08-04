"""`aihub_evaluate.py`의 순수 함수 테스트 — numpy만 있으면 도는 부분.

`evaluate_holdout()`/`evaluate_ground_truth()` 전체는 joblib로 저장된 실제 sklearn 헤드와
fashion_clip 모델이 필요해 CI에서 못 돈다(무거운 의존성, `validation/requirements-test.txt`).
여기서 고정하는 건 그 안에서 쓰는 **zero-shot 채점 수학**이다 — 이게 틀리면 "헤드가 zero-shot
보다 실제로 나은가" 비교 자체가 잘못된 숫자를 낸다.

numpy는 `requirements.txt`(런타임 의존성)에 있어 `requirements-dev.txt`로 CI에 설치된다.
"""

from __future__ import annotations

import numpy as np

import aihub_evaluate as ae


def _unit(vector: list[float]) -> np.ndarray:
    array = np.array(vector, dtype="float32")
    return array / np.linalg.norm(array)


def test_softmax_rows_sum_to_one() -> None:
    scores = np.array([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]], dtype="float32")
    probabilities = ae._softmax(scores)
    assert np.allclose(probabilities.sum(axis=1), 1.0)
    # 셋째 열이 가장 커야 첫 행에서 확률도 가장 크다
    assert probabilities[0].argmax() == 2


def test_zero_shot_ranks_the_closest_text_first() -> None:
    codes = ["BLACK", "WHITE", "RED"]
    text_embeddings = np.stack([_unit([1, 0, 0]), _unit([0, 1, 0]), _unit([0, 0, 1])])
    # 이미지 임베딩이 WHITE 텍스트와 가장 가깝게 만든다
    image_embeddings = np.stack([_unit([0.1, 0.9, 0.0])])

    ranked = ae.zero_shot(image_embeddings, text_embeddings, codes)
    assert ranked[0][0][0] == "WHITE"
    # 확률 내림차순으로 정렬돼 있어야 한다
    scores = [score for _code, score in ranked[0]]
    assert scores == sorted(scores, reverse=True)


def test_zero_shot_labels_for_embeddings_returns_top1_only() -> None:
    codes = ["TSHIRT", "SHIRT"]
    text_embeddings = np.stack([_unit([1, 0]), _unit([0, 1])])
    image_embeddings = np.stack([_unit([0.9, 0.1]), _unit([0.1, 0.9])])

    labels = ae.zero_shot_labels_for_embeddings(image_embeddings, text_embeddings, codes)
    assert labels == ["TSHIRT", "SHIRT"]


def test_apply_polo_head_only_intervenes_on_tshirt_shirt_confusion() -> None:
    class _StubHead:
        def predict(self, embedding):
            return np.array(["SHIRT"])  # 항상 SHIRT로 뒤집는 스텁

    ranked_polo_pair = [("TSHIRT", 0.6), ("SHIRT", 0.4), ("JACKET", 0.01)]
    predicted, intervened = ae.apply_polo_head(ranked_polo_pair, np.zeros(4), _StubHead())
    assert (predicted, intervened) == ("SHIRT", True)

    # top-2가 폴로 쌍이 아니면 헤드가 있어도 개입하지 않는다
    ranked_other = [("JACKET", 0.7), ("COAT", 0.2), ("TSHIRT", 0.05)]
    predicted, intervened = ae.apply_polo_head(ranked_other, np.zeros(4), _StubHead())
    assert (predicted, intervened) == ("JACKET", False)

    # 헤드 자체가 없으면 zero-shot top1을 그대로 통과시킨다
    predicted, intervened = ae.apply_polo_head(ranked_polo_pair, np.zeros(4), None)
    assert (predicted, intervened) == ("TSHIRT", False)


def test_zero_shot_accuracy_matches_manual_count() -> None:
    """evaluate_holdout()의 zero-shot 비교 줄이 하는 계산을 축소 재현한다."""
    codes = ["BLACK", "WHITE"]
    text_embeddings = np.stack([_unit([1, 0]), _unit([0, 1])])
    image_embeddings = np.stack([_unit([0.9, 0.1]), _unit([0.1, 0.9]), _unit([0.8, 0.2])])
    truth = ["BLACK", "WHITE", "WHITE"]  # 세 번째는 zero-shot이 틀리는 경우

    labels = ae.zero_shot_labels_for_embeddings(image_embeddings, text_embeddings, codes)
    accuracy = sum(a == b for a, b in zip(labels, truth)) / len(truth)

    assert labels == ["BLACK", "WHITE", "BLACK"]
    assert accuracy == 2 / 3
