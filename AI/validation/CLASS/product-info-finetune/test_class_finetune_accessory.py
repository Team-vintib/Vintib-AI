"""`aihub_accessory.py` 순수 로직 테스트 — 무거운 의존성 없이 CI에서 돈다.

파서가 AI-Hub **공개 명세만 보고** 작성됐다(실물 샘플이 로컬에 없다). 그래서 여기서
고정하는 건 "명세대로 생긴 JSON을 정확히 읽는가"와 "매핑 판단이 의도대로인가"다.
실제 파일 구조가 다르면 `scan --accessory-root`가 그걸 드러낸다.
"""

from __future__ import annotations

import json

import aihub_accessory as acc

# AI-Hub 데이터셋 상세의 "어노테이션 포멧 1) 제품착용" 샘플을 축약한 것.
IMAGE_JSON: dict = {
    "info": [
        {
            "description": "k-deep-fashion data",
            "id": "M007_0504_4",
            "accessory_id": "A0504",
            "model_id": "M007",
            "image": {
                "path": "/원천데이터/제품 착용/귀걸이/KAER0504M007P00A4.jpg",
                "width": "3024",
                "height": "4032",
                "angle": "좌90도",
            },
            "segmentation_class": ["Background", "Hat", "Earrings"],
        }
    ],
    "annotation": [{"segmentation": {"5": [[1118.8, 1779.5, 1109.6, 1804.6, 1112.2, 1829.8]]}}],
}

# "어노테이션 포멧 3) 액세서리" — 카테고리·색상이 **여기에만** 있다.
ATTRIBUTE_JSON: dict = {
    "accessory_id": "A0504",
    "accessory_type1": "귀걸이",
    "accessory_type2": "드롭",
    "accessory_color": "실버",
    "accessory_material": "은",
}


def test_type_mapping_folds_necklace_and_earring_into_jewelry() -> None:
    assert acc.map_accessory_type("모자") == ("HAT", "직접 매핑")
    assert acc.map_accessory_type("선글라스") == ("SUNGLASSES", "직접 매핑")
    assert acc.map_accessory_type("목걸이")[0] == "JEWELRY"
    assert acc.map_accessory_type("귀걸이")[0] == "JEWELRY"


def test_eyeglass_frames_are_excluded_not_folded_into_sunglasses() -> None:
    code, reason = acc.map_accessory_type("안경테")
    assert code is None
    assert "제외" in reason


def test_unknown_type_is_reported() -> None:
    code, reason = acc.map_accessory_type("스카프")
    assert code is None
    assert "알 수 없는" in reason


def test_color_mapping_follows_retired_color_map() -> None:
    """은퇴 코드의 흡수처는 `color.py`의 RETIRED_COLOR_MAP과 같아야 한다."""
    assert acc.map_accessory_color("실버") == "GRAY"
    assert acc.map_accessory_color("골드") == "YELLOW"
    assert acc.map_accessory_color("카키") == "GREEN"
    assert acc.map_accessory_color("와인") == "RED"
    assert acc.map_accessory_color("스카이블루") == "BLUE"
    # 명세 표기가 "스카이 블루"(공백)라 공백 정규화가 필요하다
    assert acc.map_accessory_color("스카이 블루") == "BLUE"


def test_colorless_values_are_dropped() -> None:
    assert acc.map_accessory_color("투명") is None
    assert acc.map_accessory_color("기타") is None
    assert acc.map_accessory_color("null") is None


def test_iter_attributes_finds_nested_records() -> None:
    flat = list(acc.iter_attributes(ATTRIBUTE_JSON))
    wrapped = list(acc.iter_attributes({"annotations": [ATTRIBUTE_JSON]}))

    for found in (flat, wrapped):
        assert len(found) == 1
        assert found[0].accessory_id == "A0504"
        assert found[0].raw_type == "귀걸이"
        assert found[0].raw_color == "실버"


def test_iter_images_reads_info_block() -> None:
    images = list(acc.iter_images(IMAGE_JSON))
    assert len(images) == 1
    image = images[0]
    assert image.accessory_id == "A0504"
    assert image.width == 3024 and image.height == 4032
    assert image.angle == "좌90도"
    assert image.image_path.endswith("KAER0504M007P00A4.jpg")


def test_shot_type_distinguishes_product_cut_from_worn() -> None:
    worn = list(acc.iter_images(IMAGE_JSON))[0]
    assert acc.shot_type_of(worn) == "worn"

    product_json = json.loads(json.dumps(IMAGE_JSON))
    product_json["info"][0]["image"]["path"] = "/원천데이터/제품/귀걸이/KAER0504P00.jpg"
    product_json["info"][0]["model_id"] = "null"
    product = list(acc.iter_images(product_json))[0]
    assert acc.shot_type_of(product) == "product"


def test_end_to_end_join_produces_records(tmp_path) -> None:
    (tmp_path / "라벨링데이터").mkdir()
    (tmp_path / "라벨링데이터" / "attr.json").write_text(
        json.dumps(ATTRIBUTE_JSON, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "라벨링데이터" / "img.json").write_text(
        json.dumps(IMAGE_JSON, ensure_ascii=False), encoding="utf-8"
    )

    stats = acc.AccessoryStats()
    records = list(acc.load_accessory_records(tmp_path, progress_every=0, stats=stats))

    assert len(records) == 1
    record = records[0]
    assert record.subcategory == "JEWELRY"
    assert record.color == "GRAY"  # 실버 → GRAY
    assert record.source == "accessory"
    assert record.shot_type == "worn"
    # 같은 액세서리의 모든 각도가 한 그룹 — split 누수 방지(브리핑 §8)
    assert record.group_key == "acc:A0504"
    assert stats.unmatched_images == 0


def test_image_without_matching_attribute_is_counted_not_silently_dropped(tmp_path) -> None:
    (tmp_path / "img.json").write_text(json.dumps(IMAGE_JSON, ensure_ascii=False), encoding="utf-8")

    stats = acc.AccessoryStats()
    records = list(acc.load_accessory_records(tmp_path, progress_every=0, stats=stats))

    assert records == []
    assert stats.unmatched_images == 1
