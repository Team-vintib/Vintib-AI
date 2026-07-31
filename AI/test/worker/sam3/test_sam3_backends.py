"""SAM3 세그멘터 백엔드 레지스트리 정합성 검증.

"동작"이 아니라 **설정이 서로 어긋나지 않는지**를 지킨다. SAM3는 단일 `defect_threshold`가
아니라 `score_threshold`/`mask_threshold`/`garment_score_threshold` 세 갈래 임계치를 쓴다.
"""

import pytest

from sam3 import registry

_BACKENDS = sorted(registry.SEGMENTER_BACKENDS)
_RATIO_FIELDS = (
    "score_threshold",
    "mask_threshold",
    "confident_threshold",
    "garment_score_threshold",
    "garment_crop_pad_ratio",
    "garment_overlap_min",
    "benign_containment",
    "min_area_ratio",
    "max_defect_area_ratio",
)


def test_active_segmenter_is_registered():
    assert registry.ACTIVE_SEGMENTER in registry.SEGMENTER_BACKENDS


def test_default_backend_needs_no_heavy_dependency():
    # 기본값이 실모델이면 CI(torch 미설치)에서 전 경로 테스트가 불가능해진다.
    assert registry.ACTIVE_SEGMENTER == "mock"
    assert registry.SEGMENTER_BACKENDS["mock"]["model_id"] is None


def test_expected_backends_are_available():
    assert set(_BACKENDS) == {"mock", "sam3_pcs"}


def test_sam3_backend_points_at_the_gated_repo():
    assert registry.SEGMENTER_BACKENDS["sam3_pcs"]["model_id"] == "facebook/sam3"


@pytest.mark.parametrize("backend", _BACKENDS)
def test_every_backend_carries_its_own_thresholds(backend):
    config = registry.SEGMENTER_BACKENDS[backend]
    for field in _RATIO_FIELDS:
        assert field in config, f"{backend}: {field} 임계치가 없습니다"
        assert 0.0 <= config[field] <= 1.0, f"{backend}.{field} 가 [0,1] 범위를 벗어났습니다"


@pytest.mark.parametrize("backend", _BACKENDS)
def test_score_threshold_leaves_room_for_a_suspected_band(backend):
    # 채택 임계치가 DETECTED 임계치보다 높으면 SUSPECTED 구간이 사라진다.
    config = registry.SEGMENTER_BACKENDS[backend]
    assert config["score_threshold"] < config["confident_threshold"]


@pytest.mark.parametrize("backend", _BACKENDS)
def test_garment_threshold_is_far_more_lenient_than_defect_threshold(backend):
    # 의류 존재 확인은 "옷이 있는지"만 보는 거라 하자 채택 임계치보다 훨씬 관대해야 한다.
    config = registry.SEGMENTER_BACKENDS[backend]
    assert config["garment_score_threshold"] < config["score_threshold"]


@pytest.mark.parametrize("backend", _BACKENDS)
def test_every_backend_declares_a_description_and_benign_switch(backend):
    config = registry.SEGMENTER_BACKENDS[backend]
    assert config["description"], f"{backend}: 설명이 비어 있습니다"
    assert isinstance(config["suppress_benign"], bool)


def test_segmenter_config_defaults_to_active_backend():
    assert registry.segmenter_config() is registry.SEGMENTER_BACKENDS[registry.ACTIVE_SEGMENTER]


def test_segmenter_config_returns_the_requested_backend():
    assert registry.segmenter_config("sam3_pcs")["model_id"] is not None


def test_segmenter_config_rejects_unknown_backend():
    with pytest.raises(ValueError, match="등록되지 않은"):
        registry.segmenter_config("no_such_backend")
