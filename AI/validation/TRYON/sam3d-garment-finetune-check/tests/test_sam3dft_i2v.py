"""I2V 어댑터 — 요청 검증, 키를 env 에서만 읽는지, 미지원 옵션 신고, stub 의 과금 가드."""

from __future__ import annotations

import base64
import io

import numpy as np
import pytest

from garment3d.config import I2vConfig
from garment3d.i2v import (
    DummyI2vAdapter,
    HttpStubAdapter,
    I2vError,
    I2vRequest,
    build_i2v_adapter,
    encode_png_base64,
    request_from_config,
    resolve_api_key,
)
from garment3d.render.synthetic import synth_turntable


def _image(resolution: int = 32) -> np.ndarray:
    return synth_turntable(num_frames=1, resolution=resolution)[0]


def test_request_rejects_bad_image_shape():
    with pytest.raises(ValueError, match="image"):
        I2vRequest(image=np.zeros((8, 8)))


def test_request_rejects_single_frame():
    with pytest.raises(ValueError, match="num_frames"):
        I2vRequest(image=_image(), num_frames=1)


def test_resolve_api_key_reads_env(monkeypatch):
    monkeypatch.setenv("MY_VIDEOGEN_KEY", " secret ")
    config = I2vConfig(api_key_env="MY_VIDEOGEN_KEY")
    assert resolve_api_key(config) == "secret"


def test_resolve_api_key_raises_when_missing(monkeypatch):
    """키 없이 호출해 401 을 받는 것보다 먼저 죽는 게 낫다."""
    monkeypatch.delenv("MY_VIDEOGEN_KEY", raising=False)
    with pytest.raises(I2vError, match="MY_VIDEOGEN_KEY"):
        resolve_api_key(I2vConfig(api_key_env="MY_VIDEOGEN_KEY"))


def test_resolve_api_key_optional_returns_none(monkeypatch):
    monkeypatch.delenv("MY_VIDEOGEN_KEY", raising=False)
    assert resolve_api_key(I2vConfig(api_key_env="MY_VIDEOGEN_KEY"), required=False) is None


def test_request_from_config_drops_disabled_conditions():
    """플래그가 꺼져 있으면 조건 입력을 버린다 — 켜지 않은 옵션이 몰래 전송되면 안 된다."""
    image = _image()
    depth = np.zeros_like(image)
    config = I2vConfig(use_end_keyframe=False, use_depth_condition=False)
    request = request_from_config(image, config, end_keyframe=image, depth=depth)
    assert request.end_keyframe is None
    assert request.depth is None


def test_request_from_config_keeps_enabled_conditions():
    image = _image()
    config = I2vConfig(use_end_keyframe=True, use_depth_condition=True)
    request = request_from_config(image, config, end_keyframe=image, depth=image)
    assert request.end_keyframe is not None
    assert request.depth is not None


def test_dummy_adapter_returns_requested_frame_count_and_keeps_first():
    image = _image()
    response = DummyI2vAdapter().generate(I2vRequest(image=image, num_frames=7))
    assert response.frames.shape == (7, 32, 32, 3)
    assert np.array_equal(response.frames[0], image)
    assert response.backend == "dummy"
    assert response.latency_sec >= 0


def test_dummy_adapter_is_deterministic_by_seed():
    image = _image()
    left = DummyI2vAdapter().generate(I2vRequest(image=image, num_frames=6, seed=3)).frames
    right = DummyI2vAdapter().generate(I2vRequest(image=image, num_frames=6, seed=3)).frames
    assert np.array_equal(left, right)


def test_unsupported_options_are_reported_not_ignored():
    """미지원 옵션을 조용히 버리면 "depth 조건을 켰는데 효과가 없다"를 디버깅할 수 없다."""

    class NoOptionsAdapter(DummyI2vAdapter):
        supports = frozenset()

    image = _image()
    response = NoOptionsAdapter().generate(
        I2vRequest(image=image, num_frames=4, end_keyframe=image, depth=image)
    )
    assert len(response.warnings) == 2
    assert any("end_keyframe" in w for w in response.warnings)
    assert any("depth" in w for w in response.warnings)


def test_dummy_adapter_supports_both_options_without_warning():
    image = _image()
    response = DummyI2vAdapter().generate(
        I2vRequest(image=image, num_frames=4, end_keyframe=image, depth=image)
    )
    assert response.warnings == []


def test_encode_png_base64_is_decodable():
    from PIL import Image

    encoded = encode_png_base64(_image())
    decoded = Image.open(io.BytesIO(base64.b64decode(encoded)))
    assert decoded.size == (32, 32)
    assert decoded.format == "PNG"


def test_http_stub_builds_payload_with_conditions(monkeypatch):
    monkeypatch.setenv("VIDEOGEN_API_KEY", "k")
    image = _image()
    adapter = HttpStubAdapter(I2vConfig(model="m1"))
    payload = adapter.build_payload(
        I2vRequest(image=image, num_frames=5, fps=8, seed=1, end_keyframe=image, depth=image)
    )

    assert payload["model"] == "m1"
    assert payload["num_frames"] == 5
    assert payload["seed"] == 1
    assert set(payload) >= {"image", "end_image", "depth_image"}


def test_http_stub_omits_absent_conditions(monkeypatch):
    monkeypatch.setenv("VIDEOGEN_API_KEY", "k")
    payload = HttpStubAdapter(I2vConfig()).build_payload(I2vRequest(image=_image(), num_frames=4))
    assert "end_image" not in payload
    assert "depth_image" not in payload
    assert "seed" not in payload


def test_http_stub_refuses_without_endpoint(monkeypatch):
    """과금 경로다 — endpoint 가 비어 있으면 시도조차 하지 않는다."""
    monkeypatch.setenv("VIDEOGEN_API_KEY", "k")
    with pytest.raises(I2vError, match="endpoint"):
        HttpStubAdapter(I2vConfig()).generate(I2vRequest(image=_image(), num_frames=4))


def test_http_stub_refuses_without_key(monkeypatch):
    monkeypatch.delenv("VIDEOGEN_API_KEY", raising=False)
    config = I2vConfig(endpoint="https://example.invalid/v1/video")
    with pytest.raises(I2vError, match="VIDEOGEN_API_KEY"):
        HttpStubAdapter(config).generate(I2vRequest(image=_image(), num_frames=4))


def test_http_stub_transport_is_explicitly_unimplemented(monkeypatch):
    """제공자 규격을 추측해 구현하지 않았다는 사실이 코드로 드러나야 한다."""
    monkeypatch.setenv("VIDEOGEN_API_KEY", "k")
    config = I2vConfig(endpoint="https://example.invalid/v1/video")
    with pytest.raises(NotImplementedError, match="제공자 규격"):
        HttpStubAdapter(config).generate(I2vRequest(image=_image(), num_frames=4))


def test_build_adapter_default_is_free_backend():
    assert build_i2v_adapter(I2vConfig()).name == "dummy"


def test_build_adapter_unknown_backend():
    # Literal 검증을 우회해 팩토리의 방어를 직접 확인한다(config 는 정상 경로에서 이미 막는다).
    config = I2vConfig.model_construct(backend="runway")
    with pytest.raises(I2vError, match="알 수 없는"):
        build_i2v_adapter(config)
