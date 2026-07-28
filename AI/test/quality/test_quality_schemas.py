"""품질 검수 API 계약(`app/quality/schemas.py`) 검증.

서비스 로직이 아니라 **BE와 주고받는 계약의 모양**을 고정한다. enum 값은 BE/FE가 문자열로
비교하므로 조용히 바뀌면 안 되고, 요청 검증 경계는 그대로 422 응답이 된다.

비동기 전환 후 이 파일의 모델은 두 갈래다 — `InspectionRequest`/`InspectionEnqueued`는 게이트웨이가
실제로 쓰고, `InspectionResult` 이하는 **워커가 만드는 job result의 형태를 문서화·고정**한다.
워커 사본과의 일치는 `test_quality_contract.py`가 본다.
"""

import pytest
from pydantic import ValidationError

from app.quality.schemas import (
    AttentionMap,
    BaseColor,
    ConditionGrade,
    DefectType,
    Finding,
    FindingStatus,
    GarmentCategory,
    GarmentSection,
    InspectionEnqueued,
    InspectionRequest,
    InspectionResult,
    ModelInfo,
    SectionScore,
    Severity,
)

_ALL_ENUMS = [
    GarmentCategory,
    BaseColor,
    DefectType,
    FindingStatus,
    Severity,
    ConditionGrade,
    GarmentSection,
]


def _request(**overrides) -> dict:
    payload = {
        "product_id": 1042,
        "image_urls": ["https://example.test/front.jpg"],
        "category": "TOP_KNIT",
    }
    payload.update(overrides)
    return payload


def _finding(**overrides) -> dict:
    payload = {
        "key": "stain_0_5_1",
        "defect_type": "STAIN",
        "status": "DETECTED",
        "image_index": 0,
        "section_no": 5,
        "section": "CHEST_CENTER",
        "confidence": 0.81,
        "area_ratio": 0.031,
        "bbox": [0.42, 0.35, 0.55, 0.47],
        "severity": "MODERATE",
        "matched_prompt": "a stain on light-colored knit sweater fabric",
        "statement_required": True,
        "needs_seller_review": False,
    }
    payload.update(overrides)
    return payload


# --- enum 값 고정 ---------------------------------------------------------


@pytest.mark.parametrize("enum_cls", _ALL_ENUMS)
def test_enum_values_are_upper_snake_strings(enum_cls):
    # BE/FE가 문자열 리터럴로 비교하는 값이다 — 소문자/케밥으로 새는 걸 막는다.
    for member in enum_cls:
        assert isinstance(member.value, str)
        assert member.value == member.value.upper()
        assert " " not in member.value


@pytest.mark.parametrize("enum_cls", _ALL_ENUMS)
def test_enum_values_are_unique(enum_cls):
    values = [member.value for member in enum_cls]
    assert len(set(values)) == len(values)


def test_condition_grades_are_exactly_four_letters():
    assert [g.value for g in ConditionGrade] == ["S", "A", "B", "C"]


def test_finding_status_has_only_two_confidence_levels():
    assert {s.value for s in FindingStatus} == {"DETECTED", "SUSPECTED"}


def test_categories_split_into_top_and_bottom_families():
    values = {c.value for c in GarmentCategory}
    assert values == {
        "TOP_KNIT",
        "TOP_SHIRT",
        "OUTER_JACKET",
        "OUTER_COAT",
        "BOTTOM_PANTS",
        "BOTTOM_SKIRT",
    }


def test_base_colors_cover_the_three_prompt_variants():
    assert {c.value for c in BaseColor} == {"LIGHT", "DARK", "PATTERNED"}


# --- 요청 검증 (그대로 422가 된다) ----------------------------------------


def test_minimal_request_defaults_to_light_base_color():
    request = InspectionRequest(**_request())
    assert request.base_color is BaseColor.light
    assert request.category is GarmentCategory.top_knit


def test_request_accepts_multiple_images_in_order():
    urls = [f"https://example.test/{i}.jpg" for i in range(8)]
    assert InspectionRequest(**_request(image_urls=urls)).image_urls == urls


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"product_id": 0}, id="product_id는 1 이상"),
        pytest.param({"image_urls": []}, id="이미지 최소 1장"),
        pytest.param({"image_urls": [f"u{i}" for i in range(9)]}, id="이미지 최대 8장"),
        pytest.param({"category": "SOCKS"}, id="미등록 카테고리"),
        pytest.param({"base_color": "NEON"}, id="미등록 기본색"),
    ],
)
def test_request_rejects_invalid_payload(overrides):
    with pytest.raises(ValidationError):
        InspectionRequest(**_request(**overrides))


@pytest.mark.parametrize("field", ["product_id", "image_urls", "category"])
def test_request_requires_core_fields(field):
    payload = _request()
    del payload[field]
    with pytest.raises(ValidationError):
        InspectionRequest(**payload)


# --- 응답 모델 -----------------------------------------------------------


def test_finding_bbox_is_a_four_value_normalized_box():
    finding = Finding(**_finding())
    assert finding.bbox == (0.42, 0.35, 0.55, 0.47)


@pytest.mark.parametrize("bbox", [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3, 0.4, 0.5]])
def test_finding_rejects_malformed_bbox(bbox):
    with pytest.raises(ValidationError):
        Finding(**_finding(bbox=bbox))


@pytest.mark.parametrize(("field", "value"), [("confidence", 1.5), ("area_ratio", -0.1)])
def test_finding_rejects_out_of_range_probability(field, value):
    with pytest.raises(ValidationError):
        Finding(**_finding(**{field: value}))


@pytest.mark.parametrize("section_no", [0, 10])
def test_finding_section_number_stays_in_the_grid(section_no):
    with pytest.raises(ValidationError):
        Finding(**_finding(section_no=section_no))


def test_section_score_shares_the_grid_bounds():
    assert SectionScore(section_no=9, section=GarmentSection.hem_right, score=0.04).score == 0.04
    with pytest.raises(ValidationError):
        SectionScore(section_no=10, section=GarmentSection.hem_right, score=0.04)


def test_model_info_allows_a_null_model_id_for_mock_backends():
    info = ModelInfo(backend="mock", model_id=None, prompt_set="top_knit/light")
    assert info.model_id is None


# --- 접수 응답 (비동기 전환으로 새로 생긴 계약) ---------------------------


def test_enqueued_response_carries_job_id_and_echoes_product():
    """`POST /quality/inspections`는 결과가 아니라 **접수증**을 돌려준다."""
    enqueued = InspectionEnqueued(job_id="3f2a-...", product_id=1042)
    assert enqueued.job_id == "3f2a-..."
    assert enqueued.product_id == 1042


def test_enqueued_response_does_not_leak_result_fields():
    """접수 시점에는 판정 결과가 존재하지 않는다 — 여기 점수가 들어가면 계약이 거짓말이 된다."""
    fields = set(InspectionEnqueued.model_fields)
    assert fields == {"job_id", "product_id"}
    assert not fields & set(InspectionResult.model_fields) - {"product_id"}


def test_response_notes_default_to_empty():
    response = InspectionResult(
        inspection_id="insp_1042_7f3c",
        product_id=1042,
        model=ModelInfo(backend="mock", model_id=None, prompt_set="top_knit/light"),
        condition_score=100.0,
        condition_grade=ConditionGrade.s,
        summary="확인된 하자가 없습니다.",
        findings=[],
        section_scores=[],
        attention_maps=[],
        latency_ms=1.2,
    )
    assert response.notes == []


def test_response_serializes_enums_as_contract_strings():
    response = InspectionResult(
        inspection_id="insp_1042_7f3c",
        product_id=1042,
        model=ModelInfo(backend="mock", model_id=None, prompt_set="top_knit/light"),
        condition_score=78.5,
        condition_grade=ConditionGrade.b,
        summary="오염 1건이 확인되었습니다.",
        findings=[Finding(**_finding())],
        section_scores=[
            SectionScore(section_no=5, section=GarmentSection.chest_center, score=0.81)
        ],
        attention_maps=[
            AttentionMap(image_index=0, defect_type=DefectType.stain, url="https://x/0_stain.png")
        ],
        notes=["구멍·찢어짐은 판매자 확인이 필요합니다."],
        latency_ms=42.1,
    )
    dumped = response.model_dump(mode="json")
    assert dumped["condition_grade"] == "B"
    assert dumped["findings"][0]["defect_type"] == "STAIN"
    assert dumped["findings"][0]["status"] == "DETECTED"
    assert dumped["findings"][0]["severity"] == "MODERATE"
    assert dumped["findings"][0]["bbox"] == [0.42, 0.35, 0.55, 0.47]
    assert dumped["attention_maps"][0]["defect_type"] == "STAIN"


@pytest.mark.parametrize("score", [-1.0, 100.5])
def test_response_condition_score_stays_within_a_hundred(score):
    with pytest.raises(ValidationError):
        InspectionResult(
            inspection_id="insp_1_a",
            product_id=1,
            model=ModelInfo(backend="mock", model_id=None, prompt_set="top_knit/light"),
            condition_score=score,
            condition_grade=ConditionGrade.s,
            summary="",
            findings=[],
            section_scores=[],
            attention_maps=[],
            latency_ms=1.0,
        )


def test_seller_statement_body_is_not_part_of_the_ai_contract():
    """소명 본문은 BE가 저장한다 — AI 응답에 소명 텍스트 필드가 있으면 경계가 무너진다."""
    fields = set(Finding.model_fields)
    assert "statement" not in fields
    assert "seller_statement" not in fields
    assert {"key", "statement_required"} <= fields
