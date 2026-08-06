"""`aihub_cache_pixels.py`의 순수 함수 테스트.

`cache_pixel_rows()` 본체는 torch/transformers/Pillow가 필요해 CI에서 못 돈다(무거운
의존성, `validation/requirements-test.txt`). 여기서 고정하는 건 그 앞단 — 소스별 캐시
파일명이 서로 안 겹치는 것. `aihub_train_head.head_filename()`과 같은 이유로 존재한다:
소스 필터를 건 캐시와 안 건 캐시가 같은 이름으로 저장되면 둘 중 하나가 조용히 덮인다.
"""

from __future__ import annotations

import aihub_cache_pixels as cp


def test_pixel_tag_without_source() -> None:
    assert cp.pixel_tag("train", "masked") == "train_masked_pixels"


def test_pixel_tag_with_source_is_distinct() -> None:
    assert cp.pixel_tag("train", "masked", "clothes") == "train_masked_clothes_pixels"
    assert cp.pixel_tag("train", "masked") != cp.pixel_tag("train", "masked", "clothes")


def test_pixel_tag_varies_by_split_and_variant() -> None:
    assert cp.pixel_tag("val", "masked") != cp.pixel_tag("train", "masked")
    assert cp.pixel_tag("train", "raw") != cp.pixel_tag("train", "masked")
