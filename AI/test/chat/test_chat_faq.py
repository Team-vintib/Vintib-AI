"""반복질문 경로 — 질문 판별(B-1) / 클러스터링(B-2) / 근거 검색(B-3) / 백엔드 스왑.

목업 임베더는 결정적이라 유사도 값이 고정된다. 아래 임계치 분리 테스트가
`registry.EMBEDDER_BACKENDS["mock_bigram"]` 값의 근거를 코드로 붙잡아 둔다 — 목업 데이터를
고치다 분리가 깨지면 여기서 먼저 터진다.
"""

import pytest

from app.chat import registry
from app.chat.faq import (
    KananaAnswerGenerator,
    KnowledgeBaseNotReady,
    MockRetriever,
    PgvectorRetriever,
    QuestionClusterer,
    QuestionDetector,
    TemplateAnswerGenerator,
    build_generator,
    build_retriever,
    cosine,
    embed,
)

MOCK = registry.EMBEDDER_BACKENDS["mock_bigram"]
CLUSTER_THRESHOLD = MOCK["cluster_similarity"]
GROUNDING_THRESHOLD = MOCK["grounding_threshold"]

SIZE_QUESTION = "이거 M 사이즈 있나요?"
SIZE_PARAPHRASES = [
    "M 사이즈도 있나요?",
    "혹시 M 사이즈 있나요??",
    "사이즈 M 있어요?",
    "엠 사이즈 재고 있나요",
]
OTHER_QUESTIONS = [
    "배송 얼마나 걸리나요?",
    "결제는 어떻게 해요?",
    "교환 되나요?",
    "가격 얼마예요?",
]

# --- B-1: 질문 판별 -------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["이거 M 사이즈 있나요?", "배송은 얼마나 걸리나요?", "교환 되나요", "가격 얼마예요"],
)
def test_questions_are_detected(text):
    assert QuestionDetector().is_question(text) is True


@pytest.mark.parametrize(
    "text",
    ["이 옷 진짜 예쁘네요", "품절이요 품절이요 품절이요", "잘 보고 있습니다"],
)
def test_non_questions_are_ignored(text):
    assert QuestionDetector().is_question(text) is False


# --- B-2: 클러스터링 임계치 근거 고정 --------------------------------------


def test_paraphrases_stay_above_cluster_threshold():
    base = embed(SIZE_QUESTION)
    worst = min(cosine(base, embed(q)) for q in SIZE_PARAPHRASES)
    assert worst >= CLUSTER_THRESHOLD, f"패러프레이즈 최저 유사도 {worst:.4f}"


def test_unrelated_questions_stay_below_cluster_threshold():
    base = embed(SIZE_QUESTION)
    worst = max(cosine(base, embed(q)) for q in OTHER_QUESTIONS)
    assert worst < CLUSTER_THRESHOLD, f"무관 질문 최고 유사도 {worst:.4f}"


def test_clusterer_groups_paraphrases_and_splits_others():
    clusterer = QuestionClusterer(similarity_threshold=CLUSTER_THRESHOLD)
    first = clusterer.add(12, SIZE_QUESTION)
    assert first.size == 1

    second = clusterer.add(12, "M 사이즈도 있나요?")
    assert second.ticket == first.ticket
    assert second.size == 2

    other = clusterer.add(12, "배송 얼마나 걸리나요?")
    assert other.ticket != first.ticket
    assert other.size == 1


def test_clusters_do_not_leak_across_lives():
    # 같은 질문이어도 방송이 다르면 별개 세션이다.
    clusterer = QuestionClusterer(similarity_threshold=CLUSTER_THRESHOLD)
    clusterer.add(12, SIZE_QUESTION)
    other_live = clusterer.add(99, SIZE_QUESTION)
    assert other_live.size == 1


def test_ticket_is_stable_for_the_same_question():
    a = QuestionClusterer(similarity_threshold=CLUSTER_THRESHOLD).add(12, SIZE_QUESTION)
    b = QuestionClusterer(similarity_threshold=CLUSTER_THRESHOLD).add(12, SIZE_QUESTION)
    assert a.ticket == b.ticket


# --- B-3: 근거 검색과 그라운딩 게이트 --------------------------------------


@pytest.mark.parametrize(
    ("query", "expected_doc"),
    [
        ("이거 M 사이즈 있나요?", "faq_size_01"),
        ("배송은 얼마나 걸리나요?", "faq_ship_01"),
        ("가격이 얼마예요?", "faq_price_01"),
        ("교환 되나요?", "faq_return_01"),
    ],
)
def test_known_questions_retrieve_grounded_docs(query, expected_doc):
    top = MockRetriever().search(query, registry.RETRIEVE_TOP_K)[0]
    assert top.doc_id == expected_doc
    assert top.score >= GROUNDING_THRESHOLD


@pytest.mark.parametrize(
    "query",
    [
        "매장 위치가 어디인가요?",
        "주차 되나요?",
        "사장님 키가 어떻게 되세요?",
        "다음 방송은 언제 하나요?",
    ],
)
def test_unknown_questions_fall_below_grounding_threshold(query):
    # 근거가 없으면 답변을 만들지 않는다 — 이 분리가 "근거 있는 경우에만 응답"의 근거다.
    top = MockRetriever().search(query, registry.RETRIEVE_TOP_K)[0]
    assert top.score < GROUNDING_THRESHOLD, f"{query} → {top.score:.4f}"


def test_retriever_reports_missing_knowledge_base(tmp_path):
    missing = MockRetriever(path=tmp_path / "nope.json")
    with pytest.raises(KnowledgeBaseNotReady):
        missing.search("아무 질문", 1)


def test_retriever_reports_empty_knowledge_base(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text("[]", encoding="utf-8")
    with pytest.raises(KnowledgeBaseNotReady):
        MockRetriever(path=empty).search("아무 질문", 1)


# --- 백엔드 스왑 ----------------------------------------------------------


def test_default_backends_need_no_model():
    assert isinstance(build_retriever(), MockRetriever)
    assert isinstance(build_generator(), TemplateAnswerGenerator)


def test_rag_backends_are_declared_but_not_implemented():
    # RAG 실구현을 비워 둔 자리 — 인터페이스는 있고 호출하면 명확히 실패한다.
    with pytest.raises(NotImplementedError):
        PgvectorRetriever().search("질문", 1)
    with pytest.raises(NotImplementedError):
        KananaAnswerGenerator().generate("질문", [])


def test_unknown_backends_fail_fast():
    with pytest.raises(ValueError, match="등록되지 않은 retriever"):
        build_retriever("faiss")
    with pytest.raises(ValueError, match="등록되지 않은 generator"):
        build_generator("gpt")
    with pytest.raises(ValueError, match="등록되지 않은 임베더"):
        registry.embedder_config("word2vec")


def test_template_generator_returns_evidence_verbatim():
    # 생성이 없으니 환각도 없다 — 근거 문서의 답변을 그대로 돌려준다.
    docs = MockRetriever().search("배송은 얼마나 걸리나요?", 3)
    assert TemplateAnswerGenerator().generate("배송은 얼마나 걸리나요?", docs) == docs[0].answer
