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
import aihub_finetune_plots as fp
import aihub_finetune_vit as fv


def test_pixel_split_tag_matches_cache_pixels_naming() -> None:
    assert fv.pixel_split_tag("train", "masked") == cp.pixel_tag("train", "masked")
    assert fv.pixel_split_tag("val", "raw") == cp.pixel_tag("val", "raw")


def test_run_name_varies_by_hyperparameter() -> None:
    base = fv.run_name("category", "masked", 2, 1e-5)
    assert base != fv.run_name("category", "masked", 4, 1e-5)  # layer 수
    assert base != fv.run_name("category", "masked", 2, 1e-4)  # lr
    assert base != fv.run_name("color", "masked", 2, 1e-5)  # task


def test_run_name_warm_start_gets_distinct_suffix() -> None:
    """색상 독립학습과 순차학습(카테고리 체크포인트에서 이어받음)은 같은 하이퍼파라미터를
    써도 서로 다른 폴더에 저장돼야 한다 — 하나가 다른 하나를 덮어쓰면 비교가 불가능하다."""
    scratch = fv.run_name("color", "masked", 4, 1e-5)
    warm = fv.run_name("color", "masked", 4, 1e-5, warm_start=True)
    assert warm != scratch
    assert warm == scratch + "_warm"


def test_run_name_warm_start_still_classified_correctly() -> None:
    """`_warm` 접미사가 붙어도 `aihub_finetune_plots.method_of()`의 접두어 분류는
    그대로 동작해야 한다 — 안 그러면 순차학습 run이 플랏/리더보드에서 "기타"로 빠진다."""
    warm = fv.run_name("color", "masked", 4, 1e-5, warm_start=True)
    assert fp.method_of(warm) == "last-N 언프리즈"


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


def test_next_versioned_dir_returns_bare_name_when_absent(tmp_path) -> None:
    target = tmp_path / "vit_last4_category_masked_lr1e-05"
    assert fv.next_versioned_dir(target) == target


def test_next_versioned_dir_bumps_version_when_taken(tmp_path) -> None:
    """torch 시드를 고정해도 라이브러리/CUDA 버전 차이로 재실행 결과가 달라질 수 있어,
    같은 이름으로 다시 돌리면 이전 run 폴더를 덮어쓰는 대신 버전을 올려야 한다
    (2026-08-05: 시드 없이 재실행해 last-N=4 결과가 조용히 덮인 사고의 재발 방지)."""
    base_dir = tmp_path / "vit_last4_category_masked_lr1e-05"
    base_dir.mkdir()
    assert fv.next_versioned_dir(base_dir) == tmp_path / "vit_last4_category_masked_lr1e-05_v2"

    (tmp_path / "vit_last4_category_masked_lr1e-05_v2").mkdir()
    assert fv.next_versioned_dir(base_dir) == tmp_path / "vit_last4_category_masked_lr1e-05_v3"
