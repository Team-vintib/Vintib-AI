"""파이프라인 오케스트레이션 + API 계약.

목업 시나리오(`data/mock_comments.json`)를 실제 파이프라인에 그대로 흘려서
욕설·도배·반복질문·근거부족 네 경로를 한 번에 검증한다.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.chat import registry
from app.chat.answers import InMemoryAnswerStore
from app.chat.classifier import RuleBasedClassifier
from app.chat.faq import (
    _DATA_DIR,
    MockRetriever,
    PgvectorRetriever,
    QuestionClusterer,
    QuestionDetector,
    TemplateAnswerGenerator,
)
from app.chat.schemas import ModerateRequest, ModerationAction, Verdict
from app.chat.service import ChatModerationService, get_chat_service
from app.chat.spam import InMemoryStateStore, SpamDetector
from app.main import app

# 테스트가 test/ 아래로 옮겨져 __file__ 기준 상대경로를 쓸 수 없다. 목업 데이터는 프로덕션
# 패키지(app/chat/data/)에 그대로 있으므로 그쪽 상수를 재사용한다.
# (`from app.main import app` 이 `app` 패키지 이름을 가려서 `app.chat.__file__` 은 못 쓴다.)
_MOCK_COMMENTS = _DATA_DIR / "mock_comments.json"

# 목업 시나리오에서 근거가 있어 답변이 생성되는 클러스터 / 생성되지 않는 클러스터.
GROUNDED_QUESTION = "이거 M 사이즈 있나요?"
UNGROUNDED_QUESTION = "매장 위치가 어디인가요?"


def _service(**overrides) -> ChatModerationService:
    """매번 새 상태로 조립한다(싱글턴 @lru_cache를 우회해 테스트 간 간섭을 없앰)."""
    embedder = registry.embedder_config()
    kwargs = {
        "spam_detector": SpamDetector(InMemoryStateStore()),
        "classifier": RuleBasedClassifier(),
        "question_detector": QuestionDetector(),
        "clusterer": QuestionClusterer(similarity_threshold=embedder["cluster_similarity"]),
        "retriever": MockRetriever(),
        "generator": TemplateAnswerGenerator(),
        "answer_store": InMemoryAnswerStore(),
        "grounding_threshold": embedder["grounding_threshold"],
    }
    kwargs.update(overrides)
    return ChatModerationService(**kwargs)


def _request(**overrides) -> ModerateRequest:
    payload = {"live_id": 12, "message_id": 1, "user_id": 1, "content": "안녕하세요"}
    payload.update(overrides)
    return ModerateRequest(**payload)


def _load_mock_comments() -> list[dict]:
    return json.loads(_MOCK_COMMENTS.read_text(encoding="utf-8"))


# --- 판정 우선순위 --------------------------------------------------------


def test_abusive_comment_is_blocked():
    response, deferred = _service().moderate(_request(content="진짜 미친놈인가"))
    assert response.verdict is Verdict.abusive
    assert response.action is ModerationAction.block
    assert deferred is None


def test_spam_is_evaluated_before_abuse():
    # 도배가 먼저 걸리면 분류기까지 가지 않는다(단락 평가) — 같은 욕설을 반복해도 SPAM이다.
    service = _service()
    text = "미친놈아 미친놈아"
    for _ in range(2):
        service.moderate(_request(content=text))
    response, _ = service.moderate(_request(content=text))
    assert response.verdict is Verdict.spam
    assert response.action is ModerationAction.hide


def test_first_question_is_not_yet_repeated():
    response, deferred = _service().moderate(_request(content=GROUNDED_QUESTION))
    assert response.verdict is Verdict.normal
    assert response.answer_ticket is None
    assert deferred is None


def test_second_question_becomes_repeated_and_defers_answer():
    service = _service()
    service.moderate(_request(content=GROUNDED_QUESTION))
    response, deferred = service.moderate(_request(content="M 사이즈도 있나요?"))

    assert response.verdict is Verdict.repeated_question
    assert response.action is ModerationAction.pass_  # 반복질문은 차단 대상이 아니다
    assert response.answer_ticket is not None
    assert deferred is not None


def test_normal_comment_passes():
    response, _ = _service().moderate(_request(content="이 옷 진짜 예쁘네요"))
    assert response.verdict is Verdict.normal
    assert response.action is ModerationAction.pass_


# --- 답변 생성 / 그라운딩 게이트 ------------------------------------------


def test_grounded_question_produces_an_answer():
    service = _service()
    service.moderate(_request(content=GROUNDED_QUESTION))
    response, deferred = service.moderate(_request(content="M 사이즈도 있나요?"))
    deferred()

    answer = service.get_answer(response.answer_ticket)
    assert answer.grounded is True
    assert answer.grounding_score >= registry.embedder_config()["grounding_threshold"]
    assert answer.sources
    assert answer.sources[0].doc_id == "faq_size_01"
    assert answer.answer  # 근거 문서의 답변이 그대로 들어온다


def test_ungrounded_question_stays_silent():
    from app.chat.answers import AnswerNotFound

    service = _service()
    service.moderate(_request(content=UNGROUNDED_QUESTION))
    response, deferred = service.moderate(_request(content=UNGROUNDED_QUESTION + "?"))
    deferred()

    # 반복질문으로는 잡히지만 근거가 약해 답변 자체가 만들어지지 않는다.
    assert response.verdict is Verdict.repeated_question
    with pytest.raises(AnswerNotFound):
        service.get_answer(response.answer_ticket)


def test_answer_is_generated_only_once_per_cluster():
    service = _service()
    service.moderate(_request(content=GROUNDED_QUESTION))
    _, first = service.moderate(_request(content="M 사이즈도 있나요?"))
    first()
    created_at = service.get_answer(_ticket(service, GROUNDED_QUESTION)).created_at

    _, second = service.moderate(_request(content="혹시 M 사이즈 있나요??"))
    second()
    assert service.get_answer(_ticket(service, GROUNDED_QUESTION)).created_at == created_at


def _ticket(service: ChatModerationService, question: str) -> str:
    answers = service.list_answers(12).answers
    assert answers, "답변이 생성되지 않았습니다"
    return answers[0].ticket


def test_answer_generation_never_breaks_moderation():
    # 지식베이스가 죽어 있어도 판정 자체는 정상적으로 끝나야 한다(채팅을 막지 않는다).
    service = _service(retriever=PgvectorRetriever())
    service.moderate(_request(content=GROUNDED_QUESTION))
    response, deferred = service.moderate(_request(content="M 사이즈도 있나요?"))
    assert response.verdict is Verdict.repeated_question
    deferred()  # 예외를 밖으로 내보내지 않고 로그만 남긴다


# --- 목업 시나리오 E2E ----------------------------------------------------


def test_mock_scenario_matches_expected_verdicts():
    service = _service()
    for row in _load_mock_comments():
        request = ModerateRequest(
            live_id=row["live_id"],
            message_id=row["message_id"],
            user_id=row["user_id"],
            content=row["content"],
        )
        response, deferred = service.moderate(request)
        if deferred is not None:
            deferred()
        assert response.verdict.value == row["expected_verdict"], f"{row['note']}: {row['content']}"


def test_mock_scenario_answers_only_grounded_clusters():
    service = _service()
    for row in _load_mock_comments():
        _, deferred = service.moderate(
            ModerateRequest(
                live_id=row["live_id"],
                message_id=row["message_id"],
                user_id=row["user_id"],
                content=row["content"],
            )
        )
        if deferred is not None:
            deferred()

    answered = {a.question for a in service.list_answers(12).answers}
    # 사이즈/배송은 지식베이스에 근거가 있고, 매장 위치는 없다.
    assert GROUNDED_QUESTION in answered
    assert "배송은 얼마나 걸리나요?" in answered
    assert UNGROUNDED_QUESTION not in answered


# --- API 계약 -------------------------------------------------------------


def _override(service: ChatModerationService) -> TestClient:
    app.dependency_overrides[get_chat_service] = lambda: service
    return TestClient(app)


def test_api_moderate_returns_verdict():
    client = _override(_service())
    try:
        resp = client.post(
            "/chat/moderate",
            json={"live_id": 12, "message_id": 1, "user_id": 1, "content": "진짜 미친놈인가"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["verdict"] == "ABUSIVE"
        assert body["action"] == "BLOCK"
        assert body["message_id"] == 1
    finally:
        app.dependency_overrides.clear()


def test_api_runs_answer_generation_in_background():
    service = _service()
    client = _override(service)
    try:
        client.post(
            "/chat/moderate",
            json={"live_id": 12, "message_id": 1, "user_id": 1, "content": GROUNDED_QUESTION},
        )
        resp = client.post(
            "/chat/moderate",
            json={"live_id": 12, "message_id": 2, "user_id": 2, "content": "M 사이즈도 있나요?"},
        )
        ticket = resp.json()["answer_ticket"]
        assert ticket is not None

        # TestClient는 응답 후 백그라운드 작업을 실행한다 — 그 시점엔 답변이 조회된다.
        listed = client.get("/chat/lives/12/answers")
        assert listed.status_code == 200
        assert [a["ticket"] for a in listed.json()["answers"]] == [ticket]
        assert client.get(f"/chat/answers/{ticket}").status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "payload",
    [
        {"live_id": 0, "message_id": 1, "user_id": 1, "content": "안녕"},  # live_id < 1
        {"live_id": 12, "message_id": 1, "user_id": 1, "content": ""},  # 빈 본문
        {"live_id": 12, "message_id": 1, "user_id": 1},  # 필드 누락
    ],
)
def test_api_422_invalid_payload(payload):
    client = _override(_service())
    try:
        assert client.post("/chat/moderate", json=payload).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_api_404_for_unknown_ticket():
    client = _override(_service())
    try:
        assert client.get("/chat/answers/a_12_ffffff").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_api_503_when_knowledge_base_not_ready():
    client = _override(_service(retriever=PgvectorRetriever()))
    try:
        resp = client.get("/chat/lives/12/answers")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "faq knowledge base not ready"
    finally:
        app.dependency_overrides.clear()
