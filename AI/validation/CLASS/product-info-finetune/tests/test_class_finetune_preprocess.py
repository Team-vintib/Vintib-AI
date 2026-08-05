"""`aihub_preprocess.py`의 좌표 로직 테스트 — PIL 없이 도는 부분만 CI에서 검증한다.

`render_variant()`는 PIL이 필요해서 여기서 다루지 않는다(CI는 `requirements-dev.txt`만
설치한다). 대신 그 앞단인 **링 추출 · 정규화 판정 · bbox 계산**을 고정한다 — 여기가 틀리면
마스크가 엉뚱한 데를 오려내고, 임베딩이 조용히 오염된다.
"""

from __future__ import annotations

import aihub_preprocess as pp

CLOTHES_JSON: dict = {
    "annotation": [
        {
            "annotation_type": "Polygon",
            "annotation_point": [10.0, 20.0, 110.0, 20.0, 110.0, 220.0, 10.0, 220.0],
        }
    ]
}

ACCESSORY_JSON: dict = {
    "annotation": [
        {
            "segmentation": {
                "5": [
                    [10.0, 10.0, 20.0, 10.0, 20.0, 20.0],
                    [50.0, 50.0, 60.0, 50.0, 60.0, 60.0],
                ]
            }
        }
    ]
}


def test_extract_rings_reads_flat_clothes_polygon() -> None:
    rings = pp.extract_rings(CLOTHES_JSON)
    assert len(rings) == 1
    assert rings[0][0] == (10.0, 20.0)
    assert len(rings[0]) == 4


def test_extract_rings_reads_accessory_segmentation_dict() -> None:
    """액세서리는 `{클래스인덱스: [[링], …]}` 형태고 링이 여러 개일 수 있다(좌/우 귀걸이)."""
    rings = pp.extract_rings(ACCESSORY_JSON)
    assert len(rings) == 2
    assert rings[1][0] == (50.0, 50.0)


def test_extract_rings_returns_empty_when_absent() -> None:
    assert pp.extract_rings({}) == []
    assert pp.extract_rings({"annotation": []}) == []
    # 좌표가 3점(6값) 미만이면 폴리곤이 될 수 없다
    assert pp.extract_rings({"annotation": [{"annotation_point": [1.0, 2.0]}]}) == []


def test_absolute_coordinates_are_left_alone() -> None:
    polygon = pp.normalize_polygon(pp.extract_rings(CLOTHES_JSON), 607, 1080)
    assert polygon is not None
    assert polygon.was_normalized is False
    assert polygon.rings[0][0] == (10.0, 20.0)


def test_normalized_coordinates_are_scaled_back_to_pixels() -> None:
    rings = [[(0.1, 0.2), (0.5, 0.2), (0.5, 0.8)]]
    polygon = pp.normalize_polygon(rings, 600, 1000)
    assert polygon is not None
    assert polygon.was_normalized is True
    assert polygon.rings[0][0] == (60.0, 200.0)


def test_bbox_adds_padding_and_clamps_to_image() -> None:
    polygon = pp.normalize_polygon(pp.extract_rings(CLOTHES_JSON), 200, 300)
    assert polygon is not None
    left, top, right, bottom = pp.bbox_of(polygon, 200, 300, padding_ratio=0.1)

    # 원래 bbox는 (10,20)~(110,220). 여백 10%면 x는 ±10, y는 ±20.
    assert (left, top) == (0, 0)  # 위/왼쪽은 이미지 경계로 clamp
    assert right == 120
    assert bottom == 240


def test_bbox_never_degenerates_to_zero_size() -> None:
    """한 점만 있는 퇴화 폴리곤에서도 crop이 가능한 사각형이 나와야 한다."""
    polygon = pp.normalize_polygon([[(5.0, 5.0), (5.0, 5.0), (5.0, 5.0)]], 100, 100)
    assert polygon is not None
    left, top, right, bottom = pp.bbox_of(polygon, 100, 100)
    assert right > left
    assert bottom > top
