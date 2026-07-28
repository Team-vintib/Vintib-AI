"""목업 시나리오 데이터·로더 검증.

시나리오 JSON은 단순 픽스처가 아니라 **downstream 로직의 전제를 담은 계약**이다. 예를 들어
`printed_design`의 `clean_overlap`이 낮아지면 프린트 오탐 방어 테스트가 조용히 무력화된다 —
여기서 그 전제들을 데이터 수준에서 고정한다.
"""

import json

import pytest

import registry
from scenarios import (
    MockScenario,
    ScenarioNotReady,
    get_scenarios,
    load_mock_scenarios,
)
from contracts import (
    BaseColor,
    ConditionGrade,
    DefectType,
    FindingStatus,
    GarmentCategory,
    GarmentSection,
)

EXPECTED_SCENARIOS = {
    "stain_clear",
    "stain_faint",
    "hole_tear",
    "clean",
    "printed_design",
}


@pytest.fixture(scope="module")
def library():
    return get_scenarios()


def _scenario(library, name: str) -> MockScenario:
    return library.by_name(name)


# --- 로드 ------------------------------------------------------------------


def test_all_five_scenarios_load(library):
    assert {s.scenario for s in library.scenarios} == EXPECTED_SCENARIOS


def test_scenarios_are_parsed_into_enums(library):
    for scenario in library.scenarios:
        assert isinstance(scenario.category, GarmentCategory)
        assert isinstance(scenario.base_color, BaseColor)
        for blob in scenario.blobs:
            assert isinstance(blob.defect_type, DefectType)


def test_every_scenario_has_an_expectation_and_a_note(library):
    for scenario in library.scenarios:
        assert scenario.expected is not None, f"{scenario.scenario}: 기대치가 없습니다"
        assert scenario.note, f"{scenario.scenario}: 목적을 설명하는 note가 없습니다"


def test_product_ids_are_unique_and_indexed(library):
    ids = library.registered_product_ids()
    assert len(ids) == len(library.scenarios)
    for product_id in ids:
        found = library.for_product(product_id, GarmentCategory.top_knit, BaseColor.light)
        assert found.product_id == product_id


def test_unknown_scenario_name_raises(library):
    with pytest.raises(ScenarioNotReady, match="등록되지 않은 시나리오"):
        library.by_name("no_such_scenario")


def test_probabilities_and_coordinates_are_in_unit_range(library):
    for scenario in library.scenarios:
        assert 0.0 <= scenario.background_defect <= 1.0
        assert 0.0 <= scenario.background_clean <= 1.0
        for blob in scenario.blobs:
            assert 0.0 <= blob.center[0] <= 1.0
            assert 0.0 <= blob.center[1] <= 1.0
            assert 0.0 < blob.radius <= 1.0
            assert 0.0 <= blob.peak <= 1.0
            assert 0.0 <= blob.clean_overlap <= 1.0
            assert 0.0 <= blob.cross_talk <= 1.0


def test_blobs_are_filtered_by_image_index(library):
    scenario = _scenario(library, "stain_clear")
    assert scenario.image_count == 2
    assert len(scenario.blobs_for(0)) == 2
    assert len(scenario.blobs_for(1)) == 1
    # 요청 이미지 수가 시나리오보다 적을 때 남는 blob은 그냥 조회되지 않는다.
    assert scenario.blobs_for(9) == ()


# --- downstream 로직의 전제 고정 ------------------------------------------


def test_defect_blobs_exceed_the_binarization_threshold(library):
    """정규화 전 peak이 defect_threshold를 넘어야 애초에 파이프라인을 태울 수 있다."""
    threshold = registry.SEGMENTER_BACKENDS["mock"]["defect_threshold"]
    for scenario in library.scenarios:
        for blob in scenario.blobs:
            assert blob.peak > threshold, f"{scenario.scenario}: blob peak이 임계치 미달입니다"


def test_real_defects_have_low_clean_overlap(library):
    # 진짜 하자 자리는 clean 프롬프트가 낮아야 대조 정규화에서 살아남는다.
    for name in ("stain_clear", "stain_faint", "hole_tear"):
        for blob in _scenario(library, name).blobs:
            assert blob.clean_overlap <= 0.15, f"{name}: clean_overlap이 너무 높습니다"


def test_printed_design_is_indistinguishable_without_clean_contrast(library):
    """프린트 방어 케이스의 전제: 하자 프롬프트만 보면 오염과 구별되지 않는다."""
    scenario = _scenario(library, "printed_design")
    assert scenario.base_color is BaseColor.patterned
    (blob,) = scenario.blobs
    # clean 프롬프트가 하자 프롬프트보다 높아야 감산으로 지워진다.
    assert blob.clean_overlap > blob.peak
    # 정규화가 없으면(clean_margin=0) 임계치를 넘어 오탐이 된다 — 그게 이 케이스의 요점이다.
    margin = registry.SEGMENTER_BACKENDS["mock"]["clean_margin"]
    assert blob.peak > registry.SEGMENTER_BACKENDS["mock"]["defect_threshold"]
    assert blob.peak - margin * blob.clean_overlap < (
        registry.SEGMENTER_BACKENDS["mock"]["defect_threshold"]
    )


def test_faint_stain_lands_between_the_two_thresholds(library):
    """미세 오염이 SUSPECTED로 강등되는 전제: 정규화 후 두 임계치 사이에 있어야 한다."""
    config = registry.SEGMENTER_BACKENDS["mock"]
    scenario = _scenario(library, "stain_faint")
    (blob,) = scenario.blobs
    normalized = blob.peak - config["clean_margin"] * blob.clean_overlap
    assert config["defect_threshold"] < normalized < config["confident_threshold"]


def test_hole_tear_is_confident_yet_expected_to_be_suspected(library):
    """찢어짐은 확률이 충분히 높은데도 SUSPECTED여야 한다 — 강등이 유형 정책에서 온다는 증거."""
    config = registry.SEGMENTER_BACKENDS["mock"]
    scenario = _scenario(library, "hole_tear")
    (blob,) = scenario.blobs
    normalized = blob.peak - config["clean_margin"] * blob.clean_overlap
    assert normalized >= config["confident_threshold"]
    assert scenario.expected.must_include == ((DefectType.hole_tear, FindingStatus.suspected),)
    assert scenario.expected.any_needs_seller_review is True
    assert registry.defect_policy(DefectType.hole_tear)["trusted"] is False


def test_clean_scenario_has_no_defects_and_pins_the_top_grade(library):
    scenario = _scenario(library, "clean")
    assert scenario.blobs == ()
    assert scenario.background_clean > scenario.background_defect
    assert scenario.expected.finding_count_max == 0
    assert scenario.expected.grade is ConditionGrade.s


def test_grade_is_pinned_only_for_zero_finding_scenarios(library):
    """점수 가중치가 임의값이라, 등급은 findings 0건(=반드시 100점)일 때만 고정한다."""
    for scenario in library.scenarios:
        if scenario.expected.grade is not None:
            assert scenario.expected.finding_count_max == 0, (
                f"{scenario.scenario}: 하자가 있는 시나리오에 등급을 고정하면 "
                "가중치 튜닝 때마다 테스트가 깨집니다"
            )


def test_cross_talk_scenario_exercises_prompt_merging(library):
    """cross_talk가 있는 시나리오는 병합 실패 시 findings가 부풀도록 개수를 좁게 고정한다."""
    scenario = _scenario(library, "stain_clear")
    talking = [blob for blob in scenario.blobs if blob.cross_talk > 0.0]
    assert talking, "프롬프트 간 병합을 검증할 blob이 없습니다"
    expected = scenario.expected
    assert expected.finding_count_min == expected.finding_count_max == len(scenario.blobs)


def test_expected_sections_match_the_scenario_category(library):
    """기대 섹션 라벨이 카테고리의 부위 라벨 세트에 실제로 존재해야 한다."""
    from prompts import SECTION_LABELS

    for scenario in library.scenarios:
        allowed = set(SECTION_LABELS[scenario.category])
        for section in scenario.expected.sections:
            assert section in allowed, f"{scenario.scenario}: {section}는 이 카테고리에 없습니다"
            assert isinstance(section, GarmentSection)


# --- 폴백(미등록 product_id) ----------------------------------------------


def test_fallback_scenario_is_generated_for_unknown_product(library):
    unknown = 999_001
    assert unknown not in library.registered_product_ids()
    scenario = library.for_product(unknown, GarmentCategory.outer_coat, BaseColor.dark)
    assert scenario.scenario == f"generated_{unknown}"
    assert scenario.product_id == unknown
    # 요청 값을 그대로 쓴다(등록 시나리오와 달리 기대치를 문서화할 필요가 없다).
    assert scenario.category is GarmentCategory.outer_coat
    assert scenario.base_color is BaseColor.dark
    assert scenario.expected is None


def test_fallback_scenario_is_deterministic(library):
    first = library.for_product(424_242, GarmentCategory.top_knit, BaseColor.light)
    second = library.for_product(424_242, GarmentCategory.top_knit, BaseColor.light)
    assert first == second


def test_fallback_scenarios_differ_across_products(library):
    blobs = {
        pid: library.for_product(pid, GarmentCategory.top_knit, BaseColor.light).blobs
        for pid in range(900_000, 900_012)
    }
    assert len({str(v) for v in blobs.values()}) > 1, "모든 상품이 같은 시나리오로 합성됩니다"


def test_fallback_blobs_stay_within_valid_ranges(library):
    for pid in range(900_000, 900_030):
        scenario = library.for_product(pid, GarmentCategory.top_knit, BaseColor.light)
        assert len(scenario.blobs) <= 2
        for blob in scenario.blobs:
            assert blob.image_index == 0
            assert 0.0 <= blob.center[0] <= 1.0
            assert 0.0 <= blob.center[1] <= 1.0
            assert 0.0 < blob.radius <= 1.0
            assert 0.0 <= blob.peak <= 1.0


# --- 손상된 정의는 조용히 통과시키지 않는다 -------------------------------


def _write(tmp_path, payload) -> "object":
    path = tmp_path / "mock_inspections.json"
    path.write_text(
        payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _valid_row() -> dict:
    return {
        "scenario": "sample",
        "note": "테스트용",
        "product_id": 1,
        "category": "TOP_KNIT",
        "base_color": "LIGHT",
        "image_count": 1,
        "background_defect": 0.06,
        "background_clean": 0.58,
        "blobs": [
            {
                "image_index": 0,
                "defect_type": "STAIN",
                "center": [0.5, 0.5],
                "radius": 0.1,
                "peak": 0.8,
                "clean_overlap": 0.05,
            }
        ],
        "expected": {"finding_count_min": 1, "finding_count_max": 1},
    }


def test_valid_minimal_definition_loads(tmp_path):
    library = load_mock_scenarios(_write(tmp_path, [_valid_row()]))
    (scenario,) = library.scenarios
    assert scenario.blobs[0].cross_talk == 0.0  # 생략 시 기본값
    assert scenario.expected.must_include == ()


def test_missing_file_raises(tmp_path):
    with pytest.raises(ScenarioNotReady, match="읽을 수 없습니다"):
        load_mock_scenarios(tmp_path / "absent.json")


def test_broken_json_raises(tmp_path):
    with pytest.raises(ScenarioNotReady, match="읽을 수 없습니다"):
        load_mock_scenarios(_write(tmp_path, "{not json"))


@pytest.mark.parametrize("payload", [[], {}])
def test_empty_definition_raises(tmp_path, payload):
    with pytest.raises(ScenarioNotReady, match="비어 있습니다"):
        load_mock_scenarios(_write(tmp_path, payload))


@pytest.mark.parametrize(
    "field", ["scenario", "product_id", "category", "base_color", "image_count", "blobs"]
)
def test_missing_required_field_raises(tmp_path, field):
    row = _valid_row()
    del row[field]
    with pytest.raises(ScenarioNotReady, match="필수 필드가 없습니다"):
        load_mock_scenarios(_write(tmp_path, [row]))


@pytest.mark.parametrize(
    ("field", "value"),
    [("category", "SOCKS"), ("base_color", "NEON")],
)
def test_unknown_enum_value_raises(tmp_path, field, value):
    row = _valid_row()
    row[field] = value
    with pytest.raises(ScenarioNotReady, match="유효하지 않습니다"):
        load_mock_scenarios(_write(tmp_path, [row]))


def test_unknown_defect_type_raises(tmp_path):
    row = _valid_row()
    row["blobs"][0]["defect_type"] = "MOTH_DAMAGE"
    with pytest.raises(ScenarioNotReady, match="유효하지 않습니다"):
        load_mock_scenarios(_write(tmp_path, [row]))


@pytest.mark.parametrize("field", ["peak", "clean_overlap", "cross_talk"])
def test_out_of_range_probability_raises(tmp_path, field):
    row = _valid_row()
    row["blobs"][0][field] = 1.4
    with pytest.raises(ScenarioNotReady, match="\\[0,1\\] 범위"):
        load_mock_scenarios(_write(tmp_path, [row]))


def test_zero_radius_raises(tmp_path):
    row = _valid_row()
    row["blobs"][0]["radius"] = 0.0
    with pytest.raises(ScenarioNotReady, match="0보다 커야"):
        load_mock_scenarios(_write(tmp_path, [row]))


def test_malformed_center_raises(tmp_path):
    row = _valid_row()
    row["blobs"][0]["center"] = 0.5
    with pytest.raises(ScenarioNotReady, match="center"):
        load_mock_scenarios(_write(tmp_path, [row]))


def test_blob_pointing_at_a_missing_image_raises(tmp_path):
    row = _valid_row()
    row["blobs"][0]["image_index"] = 3  # image_count가 1인데 4번째 이미지를 가리킨다
    with pytest.raises(ScenarioNotReady, match="image_index"):
        load_mock_scenarios(_write(tmp_path, [row]))


def test_duplicate_product_id_raises(tmp_path):
    first, second = _valid_row(), _valid_row()
    second["scenario"] = "sample2"
    with pytest.raises(ScenarioNotReady, match="product_id가 중복"):
        load_mock_scenarios(_write(tmp_path, [first, second]))


def test_duplicate_scenario_name_raises(tmp_path):
    first, second = _valid_row(), _valid_row()
    second["product_id"] = 2
    with pytest.raises(ScenarioNotReady, match="이름이 중복"):
        load_mock_scenarios(_write(tmp_path, [first, second]))


def test_inverted_finding_count_range_raises(tmp_path):
    row = _valid_row()
    row["expected"] = {"finding_count_min": 3, "finding_count_max": 1}
    with pytest.raises(ScenarioNotReady, match="finding_count_min"):
        load_mock_scenarios(_write(tmp_path, [row]))


def test_expectation_demanding_more_types_than_allowed_raises(tmp_path):
    row = _valid_row()
    row["expected"] = {
        "finding_count_min": 0,
        "finding_count_max": 1,
        "must_include": [
            {"defect_type": "STAIN", "status": "DETECTED"},
            {"defect_type": "HOLE_TEAR", "status": "SUSPECTED"},
        ],
    }
    with pytest.raises(ScenarioNotReady, match="must_include"):
        load_mock_scenarios(_write(tmp_path, [row]))
