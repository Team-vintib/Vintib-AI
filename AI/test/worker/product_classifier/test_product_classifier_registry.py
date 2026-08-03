"""product_classifier 백엔드 레지스트리 정합성 검증 — quality_vlm의
test_quality_vlm_registry.py와 같은 목적. 카테고리·색상 두 축 모두 확인한다."""

import pytest
from product_classifier import registry


def test_active_category_backend_is_registered():
    assert registry.ACTIVE_CATEGORY_BACKEND in registry.CATEGORY_BACKENDS


def test_active_color_backend_is_registered():
    assert registry.ACTIVE_COLOR_BACKEND in registry.COLOR_BACKENDS


def test_default_category_backend_needs_no_heavy_dependency():
    # 기본값이 실모델이면 CI(torch 미설치)에서 전 경로 테스트가 불가능해진다.
    assert registry.ACTIVE_CATEGORY_BACKEND == "mock"
    assert registry.CATEGORY_BACKENDS["mock"]["model_id"] is None


def test_default_color_backend_needs_no_heavy_dependency():
    assert registry.ACTIVE_COLOR_BACKEND == "mock"
    assert registry.COLOR_BACKENDS["mock"]["model_id"] is None


def test_category_backend_config_defaults_to_active_backend():
    assert registry.category_backend_config() is registry.CATEGORY_BACKENDS["mock"]


def test_color_backend_config_defaults_to_active_backend():
    assert registry.color_backend_config() is registry.COLOR_BACKENDS["mock"]


def test_category_backend_config_rejects_unknown_backend():
    with pytest.raises(ValueError, match="등록되지 않은"):
        registry.category_backend_config("no_such_backend")


def test_color_backend_config_rejects_unknown_backend():
    with pytest.raises(ValueError, match="등록되지 않은"):
        registry.color_backend_config("no_such_backend")
