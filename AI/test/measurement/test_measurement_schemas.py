"""의류 실측 API 계약(`app/measurement/schemas.py`) 검증.

서비스 로직이 아니라 **BE와 주고받는 계약의 모양**을 고정한다. enum 값은 BE/FE가 문자열로
비교하므로 조용히 바뀌면 안 되고, 요청 검증 경계는 그대로 422 응답이 된다.

`MeasurementScanRequest`/`MeasurementScanEnqueued`는 게이트웨이가 실제로 쓰고,
`MeasurementResult` 이하는 **워커가 만드는 job result의 형태를 문서화·고정**한다. 워커 사본과의
일치는 `test_measurement_contract.py`가 본다.
"""

import pytest
from pydantic import ValidationError

from app.measurement.schemas import (
    GarmentCategory,
    Landmark,
    LandmarkType,
    Measurement,
    MeasurementResult,
    MeasurementScanEnqueued,
    MeasurementScanRequest,
    MeasurementType,
    ModelInfo,
    ReferenceObjectType,
    RetakeReason,
)

_ALL_ENUMS = [
    ReferenceObjectType,
    GarmentCategory,
    LandmarkType,
    MeasurementType,
    RetakeReason,
]


def _request(**overrides) -> dict:
    payload = {
        "product_id": 1042,
        "image_url": "https://example.test/scan.jpg",
        "category": "TOP",
    }
    payload.update(overrides)
    return payload


def _model_info(**overrides) -> ModelInfo:
    payload = {
        "reference_backend": "mock",
        "segmentation_backend": "mock",
        "landmark_backend": "mock",
    }
    payload.update(overrides)
    return ModelInfo(**payload)


# --- enum 값 고정 -------------------------------------------------------------


@pytest.mark.parametrize("enum_cls", _ALL_ENUMS)
def test_enum_values_are_upper_snake_strings(enum_cls):
    for member in enum_cls:
        assert isinstance(member.value, str)
        assert member.value == member.value.upper()
        assert " " not in member.value


@pytest.mark.parametrize("enum_cls", _ALL_ENUMS)
def test_enum_values_are_unique(enum_cls):
    values = [member.value for member in enum_cls]
    assert len(set(values)) == len(values)


def test_categories_cover_top_and_bottom_only():
    assert {c.value for c in GarmentCategory} == {"TOP", "BOTTOM"}


def test_reference_object_is_a4_only_for_privacy_reasons():
    """신용카드는 개인정보(번호·명의) 노출 위험 때문에 v1에서 제외했다 — A4만 지원한다."""
    assert {o.value for o in ReferenceObjectType} == {"A4_PAPER"}


# --- 요청 검증 (그대로 422가 된다) ---------------------------------------------


def test_minimal_request_defaults_to_a4_reference():
    request = MeasurementScanRequest(**_request())
    assert request.reference_object is ReferenceObjectType.a4_paper
    assert request.category is GarmentCategory.top


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"product_id": 0}, id="product_id는 1 이상"),
        pytest.param({"category": "DRESS"}, id="미등록 카테고리(v1 범위 밖)"),
        pytest.param({"reference_object": "CREDIT_CARD"}, id="미지원 기준 물체"),
    ],
)
def test_request_rejects_invalid_payload(overrides):
    with pytest.raises(ValidationError):
        MeasurementScanRequest(**_request(**overrides))


@pytest.mark.parametrize("field", ["product_id", "image_url", "category"])
def test_request_requires_core_fields(field):
    payload = _request()
    del payload[field]
    with pytest.raises(ValidationError):
        MeasurementScanRequest(**payload)


# --- 접수 응답 ------------------------------------------------------------------


def test_enqueued_response_carries_job_id_and_echoes_product():
    """`POST /measurement/scans`는 결과가 아니라 **접수증**을 돌려준다."""
    enqueued = MeasurementScanEnqueued(job_id="3f2a-...", product_id=1042)
    assert enqueued.job_id == "3f2a-..."
    assert enqueued.product_id == 1042


def test_enqueued_response_does_not_leak_result_fields():
    """접수 시점에는 실측 결과가 존재하지 않는다 — 여기 cm 값이 들어가면 계약이 거짓말이 된다."""
    fields = set(MeasurementScanEnqueued.model_fields)
    assert fields == {"job_id", "product_id"}


# --- 결과 모델 ------------------------------------------------------------------


def test_landmark_confidence_stays_in_probability_range():
    with pytest.raises(ValidationError):
        Landmark(type=LandmarkType.hem_center, pixel_x=1.0, pixel_y=1.0, confidence=1.5)


def test_measurement_result_needs_retake_can_omit_measurements():
    """카드/원단을 못 찾은 케이스 — `needs_retake=True`면 measurements가 비어 있어도 된다."""
    result = MeasurementResult(
        measurement_id="scan_1042_worker1",
        product_id=1042,
        model=_model_info(),
        reference_object_found=False,
        pixel_to_cm_ratio=None,
        landmarks=[],
        measurements=[],
        overall_confidence=0.0,
        needs_retake=True,
        retake_reason=RetakeReason.reference_not_found,
        latency_ms=12.3,
    )
    assert result.pixel_to_cm_ratio is None
    assert result.measurements == []


def test_measurement_result_serializes_enums_as_contract_strings():
    result = MeasurementResult(
        measurement_id="scan_1042_worker1",
        product_id=1042,
        model=_model_info(),
        reference_object_found=True,
        pixel_to_cm_ratio=0.2645,
        landmarks=[
            Landmark(type=LandmarkType.shoulder_left, pixel_x=320.0, pixel_y=210.0, confidence=0.93)
        ],
        measurements=[
            Measurement(type=MeasurementType.shoulder_width, value_cm=52.0, confidence=0.9)
        ],
        overall_confidence=0.9,
        needs_retake=False,
        retake_reason=None,
        latency_ms=340.5,
    )
    dumped = result.model_dump(mode="json")
    assert dumped["landmarks"][0]["type"] == "SHOULDER_LEFT"
    assert dumped["measurements"][0]["type"] == "SHOULDER_WIDTH"
    assert dumped["retake_reason"] is None


def test_seller_pii_never_enters_the_ai_contract():
    """A4 채택 이유를 계약으로도 고정한다 — 신용카드류 필드가 여기 생기면 경계가 무너진다."""
    fields = set(MeasurementScanRequest.model_fields) | set(MeasurementResult.model_fields)
    assert not fields & {"card_number", "card_holder", "reference_card_number"}
