"""`aihub_finetune_vit.py`의 순수 함수 테스트.

`train_finetune()`/`load_model()` 본체는 torch/transformers가 필요해 CI에서 못 돈다(무거운
의존성, `validation/requirements-test.txt`). 여기서 고정하는 건 그 앞뒤 — 라벨 인코딩,
train에 없는 클래스 걸러내기, 캐시 파일명이 `aihub_cache_pixels.py`와 어긋나지 않는 것.
마지막 게 특히 중요하다: 두 스크립트가 파일명 규칙을 각자 들고 있어서, 하나만 바뀌면 다른
쪽이 조용히 "캐시가 없다" 에러를 낸다.
"""

from __future__ import annotations

import numpy as np

import aihub_cache_pixels as cp
import aihub_finetune_vit as fv


def test_pixel_split_tag_matches_cache_pixels_naming() -> None:
    assert fv.pixel_split_tag("train", "masked") == cp.pixel_tag("train", "masked")
    assert fv.pixel_split_tag("val", "raw") == cp.pixel_tag("val", "raw")


def test_run_name_varies_by_hyperparameter() -> None:
    base = fv.run_name("category", "masked", 2, 1e-5)
    assert base != fv.run_name("category", "masked", 4, 1e-5)  # layer 수
    assert base != fv.run_name("category", "masked", 2, 1e-4)  # lr
    assert base != fv.run_name("color", "masked", 2, 1e-5)  # task


def test_encode_labels_sorts_classes_and_matches_indices() -> None:
    indices, classes = fv.encode_labels(["SHIRT", "TSHIRT", "SHIRT", "JACKET"])
    assert classes == ["JACKET", "SHIRT", "TSHIRT"]
    # 인덱스로 라벨을 되짚으면 원본과 일치해야 한다
    assert [classes[i] for i in indices] == ["SHIRT", "TSHIRT", "SHIRT", "JACKET"]


def test_filter_known_classes_drops_and_reindexes() -> None:
    x = np.arange(4 * 3).reshape(4, 3)
    labels = ["TSHIRT", "SHOES", "SHIRT", "TSHIRT"]  # SHOES는 train에 없는 클래스
    label_index = {"TSHIRT": 0, "SHIRT": 1}

    x_kept, y, dropped = fv.filter_known_classes(x, labels, label_index)

    assert dropped == 1
    assert y == [0, 1, 0]
    assert np.array_equal(x_kept, x[[0, 2, 3]])


def test_filter_known_classes_keeps_everything_when_all_known() -> None:
    x = np.arange(2 * 3).reshape(2, 3)
    labels = ["TSHIRT", "SHIRT"]
    label_index = {"TSHIRT": 0, "SHIRT": 1}

    x_kept, y, dropped = fv.filter_known_classes(x, labels, label_index)

    assert dropped == 0
    assert y == [0, 1]
    assert np.array_equal(x_kept, x)
