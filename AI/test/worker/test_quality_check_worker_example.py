"""`worker/quality_check_worker_example.py`의 `_embed_first_garment()` 검증 — 유사 상품
추천용 임베딩 계산을 검수 결과에 실을지 말지 결정하는 순수 로직.

실제 임베딩 계산(`sam3.garment_embedding.embed_garment`)은 torch가 필요해 여기서
monkeypatch로 대체한다. `AI/test/conftest.py`가 `worker/`를 sys.path에 넣어 둬서
`import quality_check_worker_example`이 바로 된다.
"""

from types import SimpleNamespace

import quality_check_worker_example as worker_module


def _result(garment_crop=None):
    return SimpleNamespace(garment_crop=garment_crop)


def test_returns_none_when_no_result_has_a_garment_crop(monkeypatch):
    calls = []
    monkeypatch.setattr(worker_module, "embed_garment", lambda image: calls.append(image))

    out = worker_module.QualityCheckWorker._embed_first_garment([_result(), _result()])

    assert out is None
    assert calls == []


def test_embeds_the_first_available_garment_crop(monkeypatch):
    """이미지 여러 장 중 첫 번째로 의류를 찾은 크롭만 쓴다 — 상품당 벡터는 1개면 충분하다."""
    calls = []
    monkeypatch.setattr(
        worker_module, "embed_garment", lambda image: calls.append(image) or [0.1, 0.2]
    )

    out = worker_module.QualityCheckWorker._embed_first_garment(
        [_result(garment_crop=None), _result(garment_crop="crop-2"), _result(garment_crop="crop-3")]
    )

    assert out == [0.1, 0.2]
    assert calls == ["crop-2"]  # crop-3까지 안 가고 멈춘다


def test_not_ready_error_is_swallowed(monkeypatch):
    def _raise(image):
        raise worker_module.GarmentEmbeddingNotReady("torch 없음")

    monkeypatch.setattr(worker_module, "embed_garment", _raise)

    out = worker_module.QualityCheckWorker._embed_first_garment([_result(garment_crop="crop")])

    assert out is None


def test_unexpected_error_is_swallowed(monkeypatch):
    """임베딩 계산 실패가 검수 자체를 막으면 안 된다 — 어떤 예외든 None으로 삼킨다."""

    def _raise(image):
        raise RuntimeError("무언가 터짐")

    monkeypatch.setattr(worker_module, "embed_garment", _raise)

    out = worker_module.QualityCheckWorker._embed_first_garment([_result(garment_crop="crop")])

    assert out is None
