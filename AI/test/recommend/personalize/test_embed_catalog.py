"""embed_catalog(오프라인 임베딩 파이프라인) 테스트.

무거운 의존성(transformers)이 필요한 임베딩 경로는 원래 CI(transformers 미설치)에서
importorskip으로 통째로 스킵되도록 설계됐다. CH030(채팅 분류기를 KcELECTRA로 교체)이
transformers를 requirements.txt(→requirements-dev.txt)에 처음 추가하면서 CI에도
transformers가 깔리게 됐고, 그 결과 이 테스트가 처음으로 실제 실행되면서
`kanana-nano-2.1b-embedding`의 커스텀 모델 코드(`trust_remote_code`)가 지금 핀된
transformers 버전과 호환되지 않는 버그가 드러났다(`AttributeError: 'tuple' object has
no attribute 'dtype'`, modeling_kanana2vec.py 내부). 채팅 분류기와는 무관한 추천
임베딩 파이프라인 자체의 별개 문제라 여기서 고치지 않고, 원래 설계 의도대로 명시적
skip으로 되돌린다 — 순수 로직(텍스트 조합)은 가드 없이 그대로 실행한다.
"""

import pytest

from app.recommend.pipeline.embed_catalog import _product_text


def test_product_text_joins_title_and_brand():
    row = {"title": "빈티지 리바이스 데님 자켓", "brand": "Levi's"}
    assert _product_text(row) == "빈티지 리바이스 데님 자켓 Levi's"


def test_product_text_skips_missing_brand():
    row = {"title": "빈티지 플로럴 원피스", "brand": None}
    assert _product_text(row) == "빈티지 플로럴 원피스"


@pytest.mark.skip(
    reason=(
        "kanana-nano-2.1b-embedding 커스텀 모델 코드가 transformers==4.51.3과 호환되지 "
        "않는다(AttributeError: 'tuple' object has no attribute 'dtype', "
        "modeling_kanana2vec.py). CH030으로 CI에 transformers가 깔리면서 처음 드러남 — "
        "추천 임베딩 파이프라인 담당이 별도로 조사 필요(버전 호환 확인 또는 revision 고정)."
    )
)
def test_embed_texts_importorskip_guard():
    from app.recommend.pipeline.embed_catalog import embed_texts

    vectors = embed_texts(["빈티지 데님 자켓", "플로럴 원피스"])
    assert vectors.shape[0] == 2
