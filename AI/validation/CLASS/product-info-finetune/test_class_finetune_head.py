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
            "color_raw": "Black",
        },
        # 1. 의류 셔츠(셔츠칼라) — polo 음성
        {
            "source": "clothes",
            "source_type": "02top_04shirt",
            "neck": "shirts collar",
            "is_polo": False,
            "subcategory": "SHIRT",
            "color": "WHITE",
            "color_raw": "White",
        },
        # 2. 의류 티셔츠(라운드넥) — polo 대상 아님
        {
            "source": "clothes",
            "source_type": "02top_02t-shirt",
            "neck": "round neck",
            "is_polo": False,
            "subcategory": "TSHIRT",
            "color": "NAVY",
            "color_raw": "Navy",
        },
        # 3. 액세서리 은목걸이 — 색상이 GRAY로 들어온다(오염원)
        {
            "source": "accessory",
            "source_type": "목걸이",
            "neck": None,
            "is_polo": False,
            "subcategory": "JEWELRY",
            "color": "GRAY",
            "color_raw": "실버",
        },
        # 4. 액세서리 안경테 — 카테고리는 없고 색상만 있다
        {
            "source": "accessory",
            "source_type": "안경테",
            "neck": None,
            "is_polo": False,
            "subcategory": None,
            "color": "BLACK",
            "color_raw": "블랙",
        },
    ]


def _embeddings(n: int) -> np.ndarray:
    return np.arange(n * 4, dtype="float32").reshape(n, 4)


def test_color_task_excludes_jewelry_by_default() -> None:
    """기본값이 JEWELRY 제외다 — 은목걸이(GRAY)가 의류 색상 경계를 흐리면 안 된다.

    안경테는 subcategory가 None이라 제외 대상이 아니고, 색상(BLACK)은 그대로 쓴다.
    """
    rows = _rows()
    x, y, kept = th.build_task_dataset(_embeddings(len(rows)), rows, "color")

    assert y == ["BLACK", "WHITE", "NAVY", "BLACK"]
    assert x.shape == (4, 4)
    assert all(row.get("subcategory") != "JEWELRY" for row in kept)


def test_color_exclusion_can_be_turned_off() -> None:
    rows = _rows()
    _x, y, _kept = th.build_task_dataset(_embeddings(len(rows)), rows, "color", color_exclude=())

    assert y == ["BLACK", "WHITE", "NAVY", "GRAY", "BLACK"]


def test_category_head_still_learns_jewelry() -> None:
    """색상에서만 뺀다 — 카테고리는 액세서리가 유일하게 덮는 클래스라 그대로 배운다."""
    rows = _rows()
    _x, y, _kept = th.build_task_dataset(_embeddings(len(rows)), rows, "category")

    assert "JEWELRY" in y


def test_only_source_clothes_drops_every_accessory_row() -> None:
    """소스 필터는 더 센 도구다 — 안경테(BLACK)까지 전부 빠진다."""
    rows = _rows()
    x, y, kept = th.build_task_dataset(_embeddings(len(rows)), rows, "color", only_source="clothes")

    assert y == ["BLACK", "WHITE", "NAVY"]
    assert all(row["source"] == "clothes" for row in kept)
    # 행 필터가 임베딩 행과 어긋나면 안 된다
    assert np.array_equal(x, _embeddings(len(rows))[[0, 1, 2]])


# --------------------------------------------------------------------------
# 네이티브 라벨공간 — 접기는 학습이 아니라 추론 후에
# --------------------------------------------------------------------------


def test_native_label_space_uses_raw_color_strings() -> None:
    rows = _rows()
    _x, y, _kept = th.build_task_dataset(
        _embeddings(len(rows)), rows, "color", label_space="native", color_exclude=()
    )

    # 접기 전 원본이 나와야 한다 — 실버가 GRAY로 미리 뭉개지지 않는다
    assert y == ["Black", "White", "Navy", "실버", "블랙"]


def test_native_drops_rows_that_cannot_be_collapsed() -> None:
    """'투명'처럼 팔레트에 접을 데가 없는 색은 배워도 출력할 수 없다."""
    rows = [
        {"source": "accessory", "subcategory": "SUNGLASSES", "color": None, "color_raw": "투명"},
        {"source": "accessory", "subcategory": "SUNGLASSES", "color": "BLACK", "color_raw": "블랙"},
    ]
    _x, y, _kept = th.build_task_dataset(
        _embeddings(2), rows, "color", label_space="native", color_exclude=()
    )

    assert y == ["블랙"]


def test_collapse_map_is_derived_from_the_data() -> None:
    rows = _rows()
    mapping = th.build_collapse_map(rows)

    assert mapping["실버"] == "GRAY"
    assert mapping["Navy"] == "NAVY"
    assert th.collapse_labels(["실버", "Black"], mapping) == ["GRAY", "BLACK"]
    # 맵에 없는 값은 그대로 통과시킨다(조용히 None으로 만들지 않는다)
    assert th.collapse_labels(["모름"], mapping) == ["모름"]


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


def test_next_versioned_path_returns_bare_name_when_absent(tmp_path) -> None:
    target = tmp_path / "head_color_masked.joblib"
    assert th.next_versioned_path(target) == target


def test_next_versioned_path_bumps_version_when_taken(tmp_path) -> None:
    base = tmp_path / "head_color_masked.joblib"
    base.write_bytes(b"v1")
    assert th.next_versioned_path(base) == tmp_path / "head_color_masked_v2.joblib"

    (tmp_path / "head_color_masked_v2.joblib").write_bytes(b"v2")
    assert th.next_versioned_path(base) == tmp_path / "head_color_masked_v3.joblib"


def test_latest_existing_version_none_when_nothing_saved(tmp_path) -> None:
    assert th.latest_existing_version(tmp_path / "head_color_masked.joblib") is None


def test_latest_existing_version_picks_highest(tmp_path) -> None:
    base = tmp_path / "head_color_masked.joblib"
    base.write_bytes(b"v1")
    assert th.latest_existing_version(base) == base

    (tmp_path / "head_color_masked_v2.joblib").write_bytes(b"v2")
    assert th.latest_existing_version(base) == tmp_path / "head_color_masked_v2.joblib"

    (tmp_path / "head_color_masked_v3.joblib").write_bytes(b"v3")
    assert th.latest_existing_version(base) == tmp_path / "head_color_masked_v3.joblib"

    # v2가 없이 v4만 있어도(수동 삭제 등) 순차 탐색이라 v3에서 멈춘다 — 의도된 동작:
    # 버전은 저장 시 항상 순차로 채워지므로 구멍이 생기는 건 사람이 지운 경우뿐이다.


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
