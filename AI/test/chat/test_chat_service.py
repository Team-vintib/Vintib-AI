"""파이프라인 오케스트레이션 + API 계약.

목업 시나리오(`data/mock_comments.json`)를 실제 파이프라인에 그대로 흘려서
욕설·도배·반복질문·근거부족 네 경로를 한 번에 검증한다.

**`chat_rag` 큐는 진짜 Redis에 안 붙는다** — `_FakeRedis`로 `app.gateway.router.r`을 갈아끼워
job이 실제로 무엇이 실리는지만 본다(`test/quality/test_quality_router.py`와 같은 패턴). 워커의
응답은 `gateway_router._ingest_chat_rag_result()`를 직접 호출해 흉내 낸다 — 실제 검색·랭킹·
생성(KURE-v1/LangChain)은 워커 쪽 관심사라 여기서 검증하지 않는다.
"""

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.chat import rag_store, registry
from app.chat import service as chat_service_module
from app.chat.answers import AnswerNotFound, InMemoryAnswerStore
from app.chat.classifier import RuleBasedClassifier
from app.chat.faq import _DATA_DIR, QuestionClusterer, QuestionDetector
from app.chat.schemas import ModerateRequest, ModerationAction, Verdict
from app.chat.service import ChatModerationService, get_chat_service
from app.chat.spam import InMemoryStateStore, SpamDetector
from app.gateway import router as gateway_router
from app.gateway.schemas import Job
from app.main import app

# 테스트가 test/ 아래로 옮겨져 __file__ 기준 상대경로를 쓸 수 없다. 목업 데이터는 프로덕션
# 패키지(app/chat/data/)에 그대로 있으므로 그쪽 상수를 재사용한다.
_MOCK_COMMENTS = _DATA_DIR / "mock_comments.json"

GROUNDED_QUESTION = "이거 M 사이즈 있나요?"
UNGROUNDED_QUESTION = "매장 위치가 어디인가요?"


class _FakeRedis:
    """rpush/set만 흉내내는 최소 스텁 — `test/quality/test_quality_router.py`와 동일 패턴."""

    def __init__(self) -> None:
        self.pushed: list[tuple[str, str]] = []
        self.stored: dict[str, str] = {}

    def rpush(self, key: str, value: str) -> int:
        self.pushed.append((key, value))
        return len(self.pushed)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.stored[key] = value
        return True


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(gateway_router, "r", fake)
    return fake


def _doc(doc_id: int, content: str) -> rag_store.RagDocument:
    return rag_store.RagDocument(
        id=doc_id, live_id=12, content=content, created_at=datetime.now(UTC)
    )


def _stub_docs(monkeypatch, docs: list[rag_store.RagDocument]) -> None:
    """`rag_store.fetch_documents()`를 대체한다 — 실제 postgres-vector에 안 붙는다."""
    monkeypatch.setattr(rag_store, "fetch_documents", lambda *a, **k: docs)


def _pushed_job(fake_redis: _FakeRedis) -> Job:
    key, raw = fake_redis.pushed[-1]
    assert key == "queue:chat_rag"
    return Job(**json.loads(raw))


def _stub_singleton(monkeypatch, service: ChatModerationService) -> None:
    """`gateway_router._ingest_chat_rag_result()`는 DI가 아니라 `get_chat_service()`
    싱글턴을 직접 호출한다(같은 프로세스 안이라 프로덕션에선 문제없음, `service.py` 참고).
    테스트는 매번 새 `_service()` 인스턴스를 쓰므로, 싱글턴이 그 인스턴스를 돌려주도록
    바꿔치기해야 워커 결과가 같은 곳에 쌓인다."""
    monkeypatch.setattr(chat_service_module, "get_chat_service", lambda: service)


def _service(**overrides) -> ChatModerationService:
    """매번 새 상태로 조립한다(싱글턴 @lru_cache를 우회해 테스트 간 간섭을 없앰)."""
    kwargs = {
        "spam_detector": SpamDetector(InMemoryStateStore()),
        "classifier": RuleBasedClassifier(),
        "question_detector": QuestionDetector(),
        "clusterer": QuestionClusterer(
            similarity_threshold=registry.embedder_config()["cluster_similarity"]
        ),
        "answer_store": InMemoryAnswerStore(),
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
    # registry 기본값(-571 후속으로 10까지 올라감)과 무관하게 이 테스트는 근접중복 경로
    # 자체를 보는 거라 작은 임계로 고정한다.
    service = _service(spam_detector=SpamDetector(InMemoryStateStore(), duplicate_count=2))
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


def test_repeated_violations_trigger_timeout():
    # registry 기본값(임계 3회)을 그대로 쓴다 — 서로 다른 욕설이라 스팸(근접중복)엔 안 걸리고
    # 매번 악성 판정으로 위반이 쌓인다.
    service = _service()
    abusive_texts = ["시발 진짜", "병신 아니냐", "지랄하네"]
    for text in abusive_texts:
        response, _ = service.moderate(_request(content=text))
        assert response.verdict is Verdict.abusive

    response, deferred = service.moderate(_request(content="안녕하세요"))

    assert response.verdict is Verdict.timed_out
    assert response.action is ModerationAction.block
    assert response.mute_remaining_seconds is not None
    assert response.mute_remaining_seconds > 0
    assert deferred is None


def test_timeout_is_scoped_per_live():
    service = _service()
    for text in ["시발 진짜", "병신 아니냐", "지랄하네"]:
        service.moderate(_request(live_id=12, content=text))

    # 같은 사용자라도 다른 방송에서는 음소거가 적용되지 않는다.
    response, _ = service.moderate(_request(live_id=99, content="안녕하세요"))
    assert response.verdict is Verdict.normal


def test_normal_comment_passes():
    response, _ = _service().moderate(_request(content="이 옷 진짜 예쁘네요"))
    assert response.verdict is Verdict.normal
    assert response.action is ModerationAction.pass_


# --- 답변 생성: chat_rag job 큐 ---------------------------------------------


def test_grounded_question_produces_an_answer(monkeypatch, fake_redis):
    _stub_docs(monkeypatch, [_doc(1, "이 니트는 M 사이즈로도 나왔습니다.")])
    service = _service()
    _stub_singleton(monkeypatch, service)
    service.moderate(_request(content=GROUNDED_QUESTION))
    response, deferred = service.moderate(_request(content="M 사이즈도 있나요?"))
    deferred()  # 이 시점엔 job만 큐에 실린다 — 생성은 아직 안 끝남

    assert len(fake_redis.pushed) == 1
    job = _pushed_job(fake_redis)
    assert job.payload["ticket"] == response.answer_ticket
    assert job.payload["docs"] == [{"id": 1, "content": "이 니트는 M 사이즈로도 나왔습니다."}]

    # 워커가 결과를 보냈다고 가정
    gateway_router._ingest_chat_rag_result(
        job,
        {
            "grounded": True,
            "answer": "네, M 사이즈 있습니다.",
            "grounding_score": 0.9,
            "sources": [{"doc_id": "1", "score": 0.9}],
        },
    )

    answer = service.get_answer(response.answer_ticket)
    assert answer.grounded is True
    assert answer.answer == "네, M 사이즈 있습니다."
    assert answer.sources[0].doc_id == "1"


def test_ungrounded_question_stays_silent(monkeypatch, fake_redis):
    _stub_docs(monkeypatch, [_doc(1, "무관한 내용")])
    service = _service()
    _stub_singleton(monkeypatch, service)
    service.moderate(_request(content=UNGROUNDED_QUESTION))
    response, deferred = service.moderate(_request(content=UNGROUNDED_QUESTION + "?"))
    deferred()

    job = _pushed_job(fake_redis)
    gateway_router._ingest_chat_rag_result(job, {"grounded": False})

    # 반복질문으로는 잡히지만 워커가 근거 부족으로 판단하면 답변이 안 만들어진다.
    assert response.verdict is Verdict.repeated_question
    with pytest.raises(AnswerNotFound):
        service.get_answer(response.answer_ticket)


def test_answer_is_generated_only_once_per_cluster(monkeypatch, fake_redis):
    _stub_docs(monkeypatch, [_doc(1, "근거 내용")])
    service = _service()
    _stub_singleton(monkeypatch, service)
    service.moderate(_request(content=GROUNDED_QUESTION))
    _, first = service.moderate(_request(content="M 사이즈도 있나요?"))
    first()
    job = _pushed_job(fake_redis)
    gateway_router._ingest_chat_rag_result(
        job, {"grounded": True, "answer": "A", "grounding_score": 0.9, "sources": []}
    )
    created_at = service.get_answer(job.payload["ticket"]).created_at

    _, second = service.moderate(_request(content="혹시 M 사이즈 있나요??"))
    second()
    assert len(fake_redis.pushed) == 1  # 이미 답변된 티켓이라 새 job이 안 쌓인다
    assert service.get_answer(job.payload["ticket"]).created_at == created_at


def test_does_not_enqueue_duplicate_job_while_pending(monkeypatch, fake_redis):
    """워커 응답을 기다리는 동안(poll 주기만큼) 같은 클러스터에 메시지가 더 들어와도
    job이 중복으로 쌓이면 안 된다 — 동기 시절엔 없던, 큐로 전환하며 새로 생긴 문제다."""
    _stub_docs(monkeypatch, [_doc(1, "근거 내용")])
    service = _service()
    service.moderate(_request(content=GROUNDED_QUESTION))
    _, first = service.moderate(_request(content="M 사이즈도 있나요?"))
    first()
    assert len(fake_redis.pushed) == 1

    _, second = service.moderate(_request(content="사이즈 M 있어요?"))
    second()  # 아직 워커 응답 전(pending) — 또 enqueue하면 안 된다
    assert len(fake_redis.pushed) == 1


def test_no_candidate_docs_skips_enqueue_but_moderation_still_completes(monkeypatch, fake_redis):
    """이 방송에 대한 근거 문서(STT 전사문)가 아직 하나도 없으면 조용히 스킵한다.
    판정 자체(반복질문 검출)는 그대로 완료돼야 한다 — 답변 기능 장애가 채팅을 막으면 안 된다."""
    _stub_docs(monkeypatch, [])
    service = _service()
    service.moderate(_request(content=GROUNDED_QUESTION))
    response, deferred = service.moderate(_request(content="M 사이즈도 있나요?"))
    assert response.verdict is Verdict.repeated_question
    deferred()  # 예외를 내지 않고 조용히 넘어간다
    assert fake_redis.pushed == []


# --- 목업 시나리오 E2E (판정 경로만 — 생성 결과는 워커 쪽 관심사) -----------


def test_mock_scenario_matches_expected_verdicts(monkeypatch, fake_redis):
    monkeypatch.setattr(rag_store, "fetch_documents", lambda *a, **k: [])
    # 이 목업 시나리오의 "도배 3회차" 케이스는 근접중복 2건에서 임계 도달을 전제로 적혀
    # 있다 — registry 기본값(-571 후속으로 10까지 올라감)과 무관하게 그 임계로 고정한다.
    service = _service(spam_detector=SpamDetector(InMemoryStateStore(), duplicate_count=2))
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


def test_api_timed_out_response_includes_remaining_seconds():
    client = _override(_service())
    try:
        for text in ["시발 진짜", "병신 아니냐", "지랄하네"]:
            client.post(
                "/chat/moderate",
                json={"live_id": 12, "message_id": 1, "user_id": 1, "content": text},
            )
        resp = client.post(
            "/chat/moderate",
            json={"live_id": 12, "message_id": 2, "user_id": 1, "content": "안녕하세요"},
        )
        body = resp.json()
        assert body["verdict"] == "TIMED_OUT"
        assert body["mute_remaining_seconds"] > 0
    finally:
        app.dependency_overrides.clear()


def test_api_enqueues_chat_rag_job_in_background(monkeypatch, fake_redis):
    _stub_docs(monkeypatch, [_doc(1, "근거 내용")])
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

        # TestClient는 응답 후 백그라운드 작업을 실행한다 — 그 시점에 job이 큐에 실린다.
        assert len(fake_redis.pushed) == 1
        assert json.loads(fake_redis.pushed[0][1])["payload"]["ticket"] == ticket

        # 워커가 아직 응답 안 했으니 답변은 아직 없다.
        assert client.get(f"/chat/answers/{ticket}").status_code == 404
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


def test_api_seed_document_saves_as_seed_source(monkeypatch):
    # STT 없이 반복질문 근거 문서를 채우는 경로(-571, CH024) — 실제 postgres-vector엔 안 붙는다.
    saved = []
    monkeypatch.setattr(
        rag_store,
        "save_document",
        lambda live_id, source_type, content, embedding=None: saved.append(
            (live_id, source_type, content)
        ),
    )
    client = _override(_service())
    try:
        resp = client.post(
            "/chat/lives/12/documents",
            json={"content": "빈티지 데님 재킷, 브랜드 리바이스, 가격은 89000원입니다."},
        )
        assert resp.status_code == 204
        assert saved == [(12, "seed", "빈티지 데님 재킷, 브랜드 리바이스, 가격은 89000원입니다.")]
    finally:
        app.dependency_overrides.clear()
