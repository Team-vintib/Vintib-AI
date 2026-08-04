"""`aihub_train_head.py`의 데이터셋 조립 로직 테스트 — sklearn 없이 도는 부분만.

`train()`/`evaluate()`는 scikit-learn이 필요해 CI에서 못 돈다(무거운 의존성은
`validation/requirements-test.txt`, CI 미설치). 여기서 고정하는 건 그 앞단인
**태스크별 행 선택**이다 — 여기가 틀리면 엉뚱한 표본으로 학습해도 아무도 모른다.

특히 `only_source`는 색상 헤드에서 액세서리 금속색(실버→GRAY, 골드→YELLOW)을 빼기 위한
장치라 반드시 걸려 있어야 한다.
"""

from __future__ import annotations

import numpy as np

import aihub_train_head as th


def _rows() -> list[dict]:
    return [
        # 0. 의류 티셔츠(폴로) — polo 양성
        {
            "source": "clothes",
            "source_type": "02top_02t-shirt",
            "neck": "polo collar",
            "is_polo": True,
            "subcategory": "TSHIRT",
            "color": "BLACK",
        },
        # 1. 의류 셔츠(셔츠칼라) — polo 음성
        {
            "source": "clothes",
            "source_type": "02top_04shirt",
            "neck": "shirts collar",
            "is_polo": False,
            "subcategory": "SHIRT",
            "color": "WHITE",
        },
        # 2. 의류 티셔츠(라운드넥) — polo 대상 아님
        {
            "source": "clothes",
            "source_type": "02top_02t-shirt",
            "neck": "round neck",
            "is_polo": False,
            "subcategory": "TSHIRT",
            "color": "NAVY",
        },
        # 3. 액세서리 은목걸이 — 색상이 GRAY로 들어온다(오염원)
        {
            "source": "accessory",
            "source_type": "목걸이",
            "neck": None,
            "is_polo": False,
            "subcategory": "JEWELRY",
            "color": "GRAY",
        },
        # 4. 액세서리 안경테 — 카테고리는 없고 색상만 있다
        {
            "source": "accessory",
            "source_type": "안경테",
            "neck": None,
            "is_polo": False,
            "subcategory": None,
            "color": "BLACK",
        },
    ]


def _embeddings(n: int) -> np.ndarray:
    return np.arange(n * 4, dtype="float32").reshape(n, 4)


def test_color_task_takes_every_row_with_a_color() -> None:
    rows = _rows()
    x, y, kept = th.build_task_dataset(_embeddings(len(rows)), rows, "color")

    assert y == ["BLACK", "WHITE", "NAVY", "GRAY", "BLACK"]
    assert x.shape == (5, 4)
    assert len(kept) == 5


def test_only_source_clothes_drops_accessory_metal_colors() -> None:
    """색상 헤드의 핵심 방어선 — 은목걸이(GRAY)·안경테(BLACK)가 빠져야 한다."""
    rows = _rows()
    x, y, kept = th.build_task_dataset(_embeddings(len(rows)), rows, "color", only_source="clothes")

    assert y == ["BLACK", "WHITE", "NAVY"]
    assert all(row["source"] == "clothes" for row in kept)
    # 행 필터가 임베딩 행과 어긋나면 안 된다
    assert np.array_equal(x, _embeddings(len(rows))[[0, 1, 2]])


def test_only_source_accessory_keeps_only_accessory() -> None:
    rows = _rows()
    _x, y, kept = th.build_task_dataset(
        _embeddings(len(rows)), rows, "category", only_source="accessory"
    )

    assert y == ["JEWELRY"]  # 안경테는 subcategory가 없어 카테고리 태스크에서 빠진다
    assert kept[0]["source_type"] == "목걸이"


def test_category_task_includes_both_sources_by_default() -> None:
    """카테고리는 반대다 — 액세서리가 HAT·SUNGLASSES·JEWELRY를 유일하게 덮는다."""
    rows = _rows()
    _x, y, _kept = th.build_task_dataset(_embeddings(len(rows)), rows, "category")

    assert y == ["TSHIRT", "SHIRT", "TSHIRT", "JEWELRY"]


def test_polo_task_uses_only_the_confusable_pair() -> None:
    rows = _rows()
    _x, y, kept = th.build_task_dataset(_embeddings(len(rows)), rows, "polo")

    # 폴로 티셔츠 → TSHIRT 양성, 셔츠칼라 셔츠 → SHIRT 음성. 라운드넥 티는 대상이 아니다.
    assert y == ["TSHIRT", "SHIRT"]
    assert [row["neck"] for row in kept] == ["polo collar", "shirts collar"]


def test_head_filename_separates_sources() -> None:
    """소스별 헤드가 서로 덮어쓰면 두 조건을 비교할 수 없다."""
    assert th.head_filename("color", "masked") == "head_color_masked.joblib"
    assert th.head_filename("color", "masked", "clothes") == "head_color_masked_clothes.joblib"
    assert th.head_filename("color", "masked") != th.head_filename("color", "masked", "clothes")


def test_empty_result_keeps_embedding_width() -> None:
    """표본이 0건이어도 shape가 (0, D)여야 downstream이 안 깨진다."""
    rows = [{"source": "clothes", "subcategory": None, "color": None}]
    x, y, _kept = th.build_task_dataset(_embeddings(1), rows, "color")

    assert y == []
    assert x.shape[0] == 0
