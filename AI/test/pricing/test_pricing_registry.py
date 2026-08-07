"""가격 책정 레지스트리 — 설정 조회 헬퍼 검증.

`comps_config()`/`retail_config()`는 `LlmWebSearchCompsSource`/`NaverRetailSource` 등
구현체 생성자에서 간접적으로만 쓰이고 있었다. 등록되지 않은 키를 넣었을 때의 실패
동작을 직접 고정해 둔다.
"""

import pytest

from app.pricing import registry


def test_comps_config_returns_active_backend_by_default():
    assert registry.comps_config() == registry.COMPS_BACKENDS[registry.ACTIVE_COMPS_SOURCE]


def test_comps_config_accepts_explicit_key():
    assert registry.comps_config("mock") == registry.COMPS_BACKENDS["mock"]


def test_internal_clip_backend_is_registered():
    """CH020 — internal_clip은 등록만 돼 있고 기본 활성은 아니다(아래 committed_defaults 참고)."""
    config = registry.comps_config("internal_clip")
    assert config["model_id"] == "patrickjohncyh/fashion-clip"
    assert config["min_comps_for_pricing"] >= 1


def test_internal_backend_is_registered():
    """CH024 — internal은 등록만 돼 있고 기본 활성은 아니다(아래 committed_defaults 참고)."""
    config = registry.comps_config("internal")
    assert config["min_comps_for_pricing"] >= 1


def test_comps_config_rejects_unknown_key():
    with pytest.raises(ValueError, match="등록되지 않은"):
        registry.comps_config("없는백엔드")


def test_retail_config_returns_active_backend_by_default():
    assert registry.retail_config() == registry.RETAIL_BACKENDS[registry.ACTIVE_RETAIL_SOURCE]


def test_retail_config_accepts_explicit_key():
    assert registry.retail_config("naver") == registry.RETAIL_BACKENDS["naver"]


def test_retail_config_rejects_unknown_key():
    with pytest.raises(ValueError, match="등록되지 않은"):
        registry.retail_config("없는백엔드")


def test_committed_defaults_are_mock():
    """실백엔드 전환은 사용자만 한다(AI/CLAUDE.md 하드 룰) — 커밋된 기본값은 항상 mock이어야 한다."""
    assert registry.ACTIVE_COMPS_SOURCE == "mock"
    assert registry.ACTIVE_RETAIL_SOURCE == "mock"
