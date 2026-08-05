"""`worker/models/garment_measurement/registry.py`의 DeepFashion2 카테고리/랜드마크 매핑 검증.

이 매핑은 실제 사진 + `verify_hrnet_landmarks.py`로 인덱스를 찍어 눈으로 확인한 값이라, 여기선
"눈으로 확인한 값이 맞다"를 재검증하지 않는다 — 대신 매핑 자체의 **구조적 무결성**(오프셋 합이
294를 넘지 않는지, 매핑된 로컬 인덱스가 그 카테고리 크기 범위 안인지)만 확인한다. 이게 깨지면
`landmark_detector.py`가 엉뚱한 랜드마크를 다른 카테고리 값으로 잘못 읽게 된다.
"""

from garment_measurement.registry import (
    DF2_CATEGORY_RANGES,
    DF2_LANDMARK_MAPPING,
    _DF2_CATEGORY_SIZES,
)


def test_df2_category_sizes_sum_to_294():
    """DeepFashion2 전체 랜드마크 개수(NUM_JOINTS=294, w48_384x288 설정 기준)와 일치해야 한다."""
    assert sum(_DF2_CATEGORY_SIZES) == 294


def test_every_verified_category_has_a_range_and_a_mapping():
    assert set(DF2_CATEGORY_RANGES) == set(DF2_LANDMARK_MAPPING)


def test_mapped_local_indices_stay_within_the_category_size():
    """예: short_sleeve_top은 25개 포인트뿐이니 매핑된 로컬 인덱스도 1~25 안이어야 한다."""
    for category, (_, size) in DF2_CATEGORY_RANGES.items():
        local_indices = DF2_LANDMARK_MAPPING[category].keys()
        assert all(1 <= i <= size for i in local_indices), (category, local_indices, size)


def test_mapped_landmark_types_are_unique_within_a_category():
    """같은 카테고리 안에서 두 로컬 인덱스가 같은 LandmarkType을 가리키면 안 된다(덮어쓰기 버그)."""
    for category, mapping in DF2_LANDMARK_MAPPING.items():
        landmark_types = list(mapping.values())
        assert len(set(landmark_types)) == len(landmark_types), category


def test_category_ranges_do_not_overlap():
    """카테고리별 (오프셋, 개수) 구간이 서로 겹치면 다른 카테고리의 랜드마크를 잘못 읽게 된다."""
    intervals = sorted(DF2_CATEGORY_RANGES.values())
    for (start, size), (next_start, _) in zip(intervals, intervals[1:]):
        assert start + size <= next_start
