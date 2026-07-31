"""quality_vlm 백엔드 레지스트리 정합성 검증 — sam3의 test_sam3_backends.py와 같은 목적."""

import pytest
from quality_vlm import registry

_BACKENDS = sorted(registry.VLM_BACKENDS)
_REQUIRED_FIELDS = ("model_id", "description", "quantization", "max_new_tokens")


def test_active_vlm_backend_is_registered():
    assert registry.ACTIVE_VLM_BACKEND in registry.VLM_BACKENDS


def test_default_backend_needs_no_heavy_dependency():
    # 기본값이 실모델이면 CI(torch 미설치)에서 전 경로 테스트가 불가능해진다.
    assert registry.ACTIVE_VLM_BACKEND == "mock"
    assert registry.VLM_BACKENDS["mock"]["model_id"] is None


def test_expected_backends_are_available():
    assert set(_BACKENDS) == {"mock", "qwen3_vl"}


def test_qwen3_vl_backend_points_at_the_expected_checkpoint():
    assert registry.VLM_BACKENDS["qwen3_vl"]["model_id"] == "Qwen/Qwen3-VL-4B-Instruct"


@pytest.mark.parametrize("backend", _BACKENDS)
def test_every_backend_carries_required_fields(backend):
    config = registry.VLM_BACKENDS[backend]
    for field in _REQUIRED_FIELDS:
        assert field in config, f"{backend}: {field} 필드가 없습니다"


def test_vlm_config_defaults_to_active_backend():
    assert registry.vlm_config() is registry.VLM_BACKENDS[registry.ACTIVE_VLM_BACKEND]


def test_vlm_config_returns_the_requested_backend():
    assert registry.vlm_config("qwen3_vl")["model_id"] is not None


def test_vlm_config_rejects_unknown_backend():
    with pytest.raises(ValueError, match="등록되지 않은"):
        registry.vlm_config("no_such_backend")
