"""embed_catalog(오프라인 임베딩 파이프라인) 테스트.

무거운 의존성(transformers)이 필요한 임베딩 경로는 CI(라이브러리 미설치)에서 스킵되도록
importorskip 으로 가드한다. 순수 로직(텍스트 조합)은 가드 없이 실행한다.
"""

from app.recommend.pipeline.embed_catalog import _product_text


def test_product_text_joins_title_and_brand():
    row = {"title": "빈티지 리바이스 데님 자켓", "brand": "Levi's"}
    assert _product_text(row) == "빈티지 리바이스 데님 자켓 Levi's"


def test_product_text_skips_missing_brand():
    row = {"title": "빈티지 플로럴 원피스", "brand": None}
    assert _product_text(row) == "빈티지 플로럴 원피스"


def test_embed_texts_importorskip_guard():
    # transformers 미설치(CI) 환경에서는 이 테스트가 통째로 스킵된다.
    import pytest

    pytest.importorskip("transformers")

    from app.recommend.pipeline.embed_catalog import embed_texts

    vectors = embed_texts(["빈티지 데님 자켓", "플로럴 원피스"])
    assert vectors.shape[0] == 2
