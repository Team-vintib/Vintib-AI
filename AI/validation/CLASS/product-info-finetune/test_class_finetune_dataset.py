"""`aihub_dataset.py` 순수 로직 테스트 — 무거운 의존성이 없어 CI에서 그대로 돈다.

파일명이 리포 전체에서 유일해야 한다(`AI/CLAUDE.md`, 브리핑 §9). 형제 모듈도 `aihub_`
접두어라 `REC/recommendation-embedding-finetune/dataset.py`와 충돌하지 않는다.

여기서 검증하는 건 **LAB-76이 기록한 파싱 함정 3개**와 **브리핑 §5 매핑 우선순위**,
그리고 **브리핑 §8 그룹 누수 방지**다 — 원격에서만 돌릴 수 있는 scan을 로컬에서 대신
믿을 수 있게 하려면 이 세 가지가 픽스처로 고정돼 있어야 한다.
"""

from __future__ import annotations

import json

import aihub_dataset as ad

# LAB-76에 실린 실제 JSON 샘플(shirt / wear / Gray)을 그대로 축약한 것.
# 함정 1(점 포함 평탄 키) · 2(문자열 "null", 숫자도 문자열) · 3(annotation_point)이 전부 들어 있다.
SAMPLE_JSON: dict = {
    "dataset": {
        "dataset.id": 4168,
        "dataset.name": "01_sou_000834_004168_wear_02top_04shirt_woman",
        "dataset.image_path": "./008.의류 통합 데이터(3-1)/원천데이터/상품/상의/shirt/x.jpg",
        "dataset.category": 8,
        "dataset.type": 1,
        "dataset.width": 607,
        "dataset.height": 1080,
        "dataset.file_size": 68654,
    },
    "annotation": [
        {
            "annotation_type": "Polygon",
            "annotation_id": 56,
            "annotation_point_count": 3.0,
            "annotation_point": [282.7, 365.09, 272.43, 367.0, 260.0, 370.0],
        }
    ],
    "metadata.model": {
        "metadata.model.gender": "FEMALE",
        "metadata.model.type": "wear",
        "metadata.model.chest_size_male": "null",
        "metadata.model.weight": "56",
    },
    "metadata.clothes": {
        "metadata.clothes.type": "02top_04shirt",
        "metadata.clothes.color": "Gray",
        "metadata.clothes.sleeve_length_type": "long sleeves",
        "metadata.clothes.topneck_color_design": "shirts collar",
        "metadata.top.front_length": "66.0",
        "metadata.pants.pants_length": "null",
    },
}


def _clothes(**overrides: object) -> dict:
    """`SAMPLE_JSON`의 `metadata.clothes`만 갈아끼운 사본."""
    js = json.loads(json.dumps(SAMPLE_JSON))
    js["metadata.clothes"].update(overrides)
    return js


# --------------------------------------------------------------------------
# 함정 1~3
# --------------------------------------------------------------------------


def test_parse_reads_flat_dotted_keys() -> None:
    label = ad.parse_label(SAMPLE_JSON, label_path="a/b.json")

    assert label.source_type == "02top_04shirt"
    assert label.color == "Gray"
    assert label.shot_type == "wear"
    assert label.neck == "shirts collar"
    assert label.width == 607 and label.height == 1080


def test_parse_treats_string_null_as_missing() -> None:
    assert ad.clean("null") is None
    assert ad.clean(" NULL ") is None
    assert ad.clean("") is None
    assert ad.clean("  Gray ") == "Gray"
    # 숫자도 문자열로 온다
    assert ad.to_float("66.0") == 66.0
    assert ad.to_float("null") is None
    assert ad.to_float("not-a-number") is None

    label = ad.parse_label(SAMPLE_JSON)
    assert label.pants_length is None  # "null" 문자열이었다


def test_parse_reads_annotation_point_actual_key() -> None:
    # 명세는 annotation.point지만 실제 키는 annotation_point다(함정 3).
    assert ad.parse_label(SAMPLE_JSON).polygon_points == 3

    no_annotation = json.loads(json.dumps(SAMPLE_JSON))
    no_annotation["annotation"] = []
    assert ad.parse_label(no_annotation).polygon_points == 0


def test_pants_length_is_found_inside_clothes_block() -> None:
    """`metadata.pants.*`가 별도 블록이 아니라 `metadata.clothes` 안에 들어 있다."""
    label = ad.parse_label(_clothes(**{"metadata.pants.pants_length": "38.5"}))
    assert label.pants_length == 38.5


# --------------------------------------------------------------------------
# 브리핑 §5 — 매핑과 파생 우선순위
# --------------------------------------------------------------------------


def test_direct_category_mapping() -> None:
    label = ad.parse_label(SAMPLE_JSON)
    assert ad.map_subcategory(label)[0] == "SHIRT"


def test_hood_derivation_beats_direct_mapping() -> None:
    label = ad.parse_label(_clothes(**{"metadata.clothes.topneck_color_design": "hood"}))
    assert ad.map_subcategory(label)[0] == "HOODIE"


def test_hood_beats_sleeveless_when_both_match() -> None:
    label = ad.parse_label(
        _clothes(
            **{
                "metadata.clothes.topneck_color_design": "hood",
                "metadata.clothes.sleeve_length_type": "sleeveless",
            }
        )
    )
    assert ad.map_subcategory(label)[0] == "HOODIE"


def test_sleeveless_derivation() -> None:
    label = ad.parse_label(_clothes(**{"metadata.clothes.sleeve_length_type": "sleeveless"}))
    assert ad.map_subcategory(label)[0] == "SLEEVELESS"


def test_excluded_types_stay_excluded_even_when_derivable() -> None:
    """blouse·vest는 제외가 이긴다 — `04bottom_01pants`와 달리 예외 문구가 없다."""
    for source_type in ("02top_01blouse", "02top_05vest"):
        label = ad.parse_label(
            _clothes(
                **{
                    "metadata.clothes.type": source_type,
                    "metadata.clothes.sleeve_length_type": "sleeveless",
                }
            )
        )
        code, reason = ad.map_subcategory(label)
        assert code is None, source_type
        assert "제외" in reason

        # 스위치를 켜면 파생된다(scan이 이 건수를 따로 세어 준다).
        code_on, _ = ad.map_subcategory(label, derive_from_excluded_tops=True)
        assert code_on == "SLEEVELESS"


def test_jumper_is_excluded_pending_decision() -> None:
    label = ad.parse_label(_clothes(**{"metadata.clothes.type": "01outer_03jumper"}))
    code, reason = ad.map_subcategory(label)
    assert code is None
    assert "미결정" in reason


def test_pants_needs_threshold_for_short_pants() -> None:
    label = ad.parse_label(
        _clothes(
            **{
                "metadata.clothes.type": "04bottom_01pants",
                "metadata.pants.pants_length": "35.0",
            }
        )
    )
    # 임계가 없으면 파생하지 않는다(기본값 None — scan 전에 추측하지 않는다)
    assert ad.map_subcategory(label)[0] is None
    assert ad.map_subcategory(label, short_pants_max_cm=50.0)[0] == "SHORT_PANTS"
    assert ad.map_subcategory(label, short_pants_max_cm=30.0)[0] is None


def test_unknown_type_is_reported_not_silently_dropped() -> None:
    label = ad.parse_label(_clothes(**{"metadata.clothes.type": "99weird_thing"}))
    code, reason = ad.map_subcategory(label)
    assert code is None
    assert "알 수 없는" in reason


def test_color_mapping_normalizes_case_and_space() -> None:
    assert ad.map_color(" gray ") == "GRAY"
    assert ad.map_color("Navy") == "NAVY"
    assert ad.map_color("Mixed") == ad.MIXED_LABEL
    assert ad.map_color("Chartreuse") is None
    assert ad.map_color(None) is None


def test_polo_flag_is_separate_from_category_label() -> None:
    label = ad.parse_label(
        _clothes(
            **{
                "metadata.clothes.type": "02top_02t-shirt",
                "metadata.clothes.topneck_color_design": "polo collar",
            }
        )
    )
    record, _ = ad.to_record(label)
    assert record.is_polo is True
    assert record.subcategory == "TSHIRT"  # 카테고리 라벨은 그대로 둔다


# --------------------------------------------------------------------------
# 브리핑 §8 — 그룹 키와 누수 방지
# --------------------------------------------------------------------------


def test_group_key_picks_the_garment_id_not_the_image_id() -> None:
    key, matched = ad.group_key_from_name("01_sou_000834_004168_wear_02top_04shirt_woman")
    assert (key, matched) == ("000834", True)


def test_group_key_falls_back_to_whole_name() -> None:
    key, matched = ad.group_key_from_name("weird-name.jpg")
    assert (key, matched) == ("weird-name", False)


def _record(group: str, subcategory: str, index: int) -> ad.Record:
    return ad.Record(
        label_path=f"{group}/{index}.json",
        image_path=None,
        name=f"01_sou_{group}_{index:06d}_wear",
        width=100,
        height=200,
        group_key=group,
        subcategory=subcategory,
        color="BLACK",
        shot_type="wear",
        is_polo=False,
        source_type="02top_04shirt",
    )


def test_split_never_puts_one_group_in_two_splits() -> None:
    records = [
        _record(f"{g:06d}", "SHIRT" if g % 2 else "COAT", i)
        for g in range(60)
        for i in range(3)  # 같은 의류의 front/back/wear
    ]
    assignment = ad.split_groups(records)

    seen: dict[str, set[str]] = {}
    for record in records:
        seen.setdefault(record.group_key, set()).add(assignment[record.group_key])
    assert all(len(splits) == 1 for splits in seen.values())
    assert set(assignment.values()) == {"train", "val", "test"}


def test_split_is_deterministic_for_the_same_seed() -> None:
    records = [_record(f"{g:06d}", "SHIRT", 0) for g in range(40)]
    assert ad.split_groups(records) == ad.split_groups(records)
    assert ad.split_groups(records) != ad.split_groups(records, seed=7)


def test_stratified_selection_respects_caps() -> None:
    records = [_record(f"{g:06d}", "SHIRT", 0) for g in range(50)]
    records += [_record(f"9{g:05d}", "COAT", 0) for g in range(50)]
    selected = ad.select_stratified(records, category_cap=10, color_cap=0)

    counts: dict[str, int] = {}
    for record in selected:
        counts[record.subcategory] = counts.get(record.subcategory, 0) + 1
    assert counts == {"SHIRT": 10, "COAT": 10}


# --------------------------------------------------------------------------
# 파일 순회
# --------------------------------------------------------------------------


def test_load_labels_walks_and_survives_broken_json(tmp_path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "ok.json").write_text(
        json.dumps(SAMPLE_JSON, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("nope", encoding="utf-8")

    stats = ad.LoadStats()
    labels = list(ad.load_labels(tmp_path, progress_every=0, stats=stats))

    assert len(labels) == 1
    assert labels[0].source_type == "02top_04shirt"
    assert labels[0].label_path == "nested/ok.json"
    assert stats.total_files == 2  # .txt는 세지 않는다
    assert stats.parse_errors == 1
