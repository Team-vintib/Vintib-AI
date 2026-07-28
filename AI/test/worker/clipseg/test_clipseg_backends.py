"""세그멘터 백엔드 레지스트리 정합성 검증.

"동작"이 아니라 **설정이 서로 어긋나지 않는지**를 지킨다. 백엔드를 추가하거나 임계치를 손댔을 때
downstream(findings)이 조용히 깨지는 걸 막는 게 목적이다.
"""

import pytest

import registry

_BACKENDS = sorted(registry.SEGMENTER_BACKENDS)
_THRESHOLD_FIELDS = ("defect_threshold", "confident_threshold", "clean_margin", "min_area_ratio")


def test_active_segmenter_is_registered():
    assert registry.ACTIVE_SEGMENTER in registry.SEGMENTER_BACKENDS


def test_default_backend_needs_no_heavy_dependency():
    # 기본값이 실모델이면 CI(torch 미설치)에서 전 경로 테스트가 불가능해진다.
    assert registry.ACTIVE_SEGMENTER == "mock"
    assert registry.SEGMENTER_BACKENDS["mock"]["model_id"] is None


def test_expected_backends_are_available():
    # CLIPSeg는 LAB-12가 채택한 모델, mock은 GPU 없이 전 경로를 돌리기 위한 것.
    # (게이트웨이에 있던 시절의 remote_worker 백엔드는 이 코드가 그 워커 안으로 들어오면서
    #  의미가 없어져 제거했다.)
    assert set(_BACKENDS) == {"mock", "clipseg_rd64_refined"}


def test_clipseg_backend_points_at_the_adopted_checkpoint():
    assert registry.SEGMENTER_BACKENDS["clipseg_rd64_refined"]["model_id"] == (
        "CIDAS/clipseg-rd64-refined"
    )


@pytest.mark.parametrize("backend", _BACKENDS)
def test_every_backend_carries_its_own_thresholds(backend):
    config = registry.SEGMENTER_BACKENDS[backend]
    for field in _THRESHOLD_FIELDS:
        assert field in config, f"{backend}: {field} 임계치가 없습니다"
        assert 0.0 <= config[field] <= 1.0, f"{backend}.{field} 가 [0,1] 범위를 벗어났습니다"


@pytest.mark.parametrize("backend", _BACKENDS)
def test_binarization_threshold_leaves_room_for_a_suspected_band(backend):
    # 이진화 임계치가 DETECTED 임계치보다 높으면 SUSPECTED 구간이 사라진다.
    config = registry.SEGMENTER_BACKENDS[backend]
    assert config["defect_threshold"] < config["confident_threshold"]


@pytest.mark.parametrize("backend", _BACKENDS)
def test_every_backend_declares_a_mask_size_and_description(backend):
    config = registry.SEGMENTER_BACKENDS[backend]
    assert config["mask_size"] > 0
    assert config["description"], f"{backend}: 설명이 비어 있습니다"


def test_mock_backend_enables_clean_contrast_normalization():
    # 0이면 프린트 오탐 방어 시나리오(printed_design)가 성립하지 않는다.
    assert registry.SEGMENTER_BACKENDS["mock"]["clean_margin"] > 0.0


def test_clipseg_backend_keeps_normalization_off_until_measured():
    # 대조 정규화는 CLIPSeg 기준 미검증이라 "정규화 없음"이 안전한 기본값이다.
    assert registry.SEGMENTER_BACKENDS["clipseg_rd64_refined"]["clean_margin"] == 0.0


def test_segmenter_config_defaults_to_active_backend():
    assert registry.segmenter_config() is registry.SEGMENTER_BACKENDS[registry.ACTIVE_SEGMENTER]


def test_segmenter_config_returns_the_requested_backend():
    assert registry.segmenter_config("clipseg_rd64_refined")["model_id"] is not None


def test_segmenter_config_rejects_unknown_backend():
    with pytest.raises(ValueError, match="등록되지 않은"):
        registry.segmenter_config("no_such_backend")
