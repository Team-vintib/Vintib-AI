"""라이브 댓글 관리 파이프라인 오케스트레이션.

동기 판정 3단계를 우선순위대로 단락 평가한다: 스팸 → 악성 → 질문 게이트.
반복질문으로 판정되면 티켓만 즉시 돌려주고 **답변 생성은 응답 이후로 미룬다**
(라우터가 `BackgroundTasks`로 실행) — 생성 지연이 채팅을 막지 않게 하려는 것이다.

AI는 판정만 하고 실제 차단/숨김은 BE가 집행한다. 이유는 설계 문서의
"판정 위임 vs 직접 집행" 표 참고 — 1 RTT, 게시 전 판정이라 노출 없음, AI 장애가 격리됨.

`get_chat_service()`의 조립부가 **유일한 구현 스왑 지점**이다.

설계: .claude/plans/ai/003-live-comment-moderation-prototype.md
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache

from app.chat import registry
from app.chat.answers import AnswerNotFound, AnswerStore, build_answer_store
from app.chat.classifier import AbuseClassifier, build_classifier
from app.chat.faq import (
    AnswerGenerator,
    Cluster,
    KnowledgeBaseNotReady,
    QuestionClusterer,
    QuestionDetector,
    Retriever,
    build_generator,
    build_retriever,
)
from app.chat.schemas import (
    AnswerListResponse,
    AnswerSource,
    FaqAnswer,
    ModerateRequest,
    ModerateResponse,
    ModerationAction,
    Scores,
    Verdict,
)
from app.chat.spam import SpamDetector, build_state_store

# 라우터가 import하기 쉽도록 재노출(503/404 매핑용).
__all__ = [
    "ChatModerationService",
    "KnowledgeBaseNotReady",
    "AnswerNotFound",
    "get_chat_service",
]

logger = logging.getLogger(__name__)


class ChatModerationService:
    """댓글 한 건을 판정하고, 반복질문이면 답변 생성 작업을 만들어 돌려준다."""

    def __init__(
        self,
        spam_detector: SpamDetector,
        classifier: AbuseClassifier,
        question_detector: QuestionDetector,
        clusterer: QuestionClusterer,
        retriever: Retriever,
        generator: AnswerGenerator,
        answer_store: AnswerStore,
        *,
        abuse_threshold: float = registry.ABUSE_THRESHOLD,
        min_cluster_size: int = registry.MIN_CLUSTER_SIZE,
        grounding_threshold: float | None = None,
        top_k: int = registry.RETRIEVE_TOP_K,
    ) -> None:
        self._spam = spam_detector
        self._classifier = classifier
        self._questions = question_detector
        self._clusterer = clusterer
        self._retriever = retriever
        self._generator = generator
        self._answers = answer_store
        self._abuse_threshold = abuse_threshold
        self._min_cluster_size = min_cluster_size
        self._grounding_threshold = (
            grounding_threshold
            if grounding_threshold is not None
            else registry.embedder_config()["grounding_threshold"]
        )
        self._top_k = top_k

    # -- 동기 판정 --------------------------------------------------------
    def moderate(
        self, request: ModerateRequest
    ) -> tuple[ModerateResponse, Callable[[], None] | None]:
        """판정 결과와, 있으면 지연 실행할 답변 생성 작업을 함께 돌려준다.

        지식베이스가 깨져 있어도 여기서 예외를 내지 않는다 — 답변 기능 장애가 채팅 자체를
        막으면 안 되기 때문이다. 그 상황은 답변 조회 엔드포인트에서 503으로 드러난다.
        """
        started = time.perf_counter()
        moment = request.sent_at.timestamp() if request.sent_at else time.time()

        spam = self._spam.check(request.user_id, request.content, now=moment)
        if spam.is_spam:
            return (
                self._response(
                    request,
                    Verdict.spam,
                    ModerationAction.hide,
                    spam.reason,
                    abuse=0.0,
                    spam_score=spam.score,
                    started=started,
                ),
                None,
            )

        abuse = self._classifier.score(request.content)
        if abuse.score >= self._abuse_threshold:
            return (
                self._response(
                    request,
                    Verdict.abusive,
                    ModerationAction.block,
                    f"abuse:{abuse.label}",
                    abuse=abuse.score,
                    spam_score=spam.score,
                    started=started,
                ),
                None,
            )

        if self._questions.is_question(request.content):
            cluster = self._clusterer.add(request.live_id, request.content)
            if cluster.size >= self._min_cluster_size:
                deferred = self._make_answer_job(cluster)
                return (
                    self._response(
                        request,
                        Verdict.repeated_question,
                        ModerationAction.pass_,
                        "question_repeated",
                        abuse=abuse.score,
                        spam_score=spam.score,
                        started=started,
                        ticket=cluster.ticket,
                    ),
                    deferred,
                )
            # 처음 나온 질문은 아직 "반복"이 아니다 — 통과시키고 클러스터만 열어 둔다.

        return (
            self._response(
                request,
                Verdict.normal,
                ModerationAction.pass_,
                "clean",
                abuse=abuse.score,
                spam_score=spam.score,
                started=started,
            ),
            None,
        )

    def _response(
        self,
        request: ModerateRequest,
        verdict: Verdict,
        action: ModerationAction,
        reason: str,
        *,
        abuse: float,
        spam_score: float,
        started: float,
        ticket: str | None = None,
    ) -> ModerateResponse:
        return ModerateResponse(
            message_id=request.message_id,
            verdict=verdict,
            action=action,
            reason=reason,
            scores=Scores(abuse=round(abuse, 4), spam=round(spam_score, 4)),
            answer_ticket=ticket,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
        )

    # -- 비동기 답변 생성 --------------------------------------------------
    def _make_answer_job(self, cluster: Cluster) -> Callable[[], None]:
        def job() -> None:
            self.generate_answer(cluster)

        return job

    def generate_answer(self, cluster: Cluster) -> FaqAnswer | None:
        """근거를 찾아 답변을 만들어 저장한다. 근거가 약하면 **아무것도 만들지 않는다**.

        클러스터당 1회만 생성한다(이미 저장돼 있으면 그대로 둔다).
        """
        try:
            self._answers.get(cluster.ticket)
        except AnswerNotFound:
            pass
        else:
            return None

        try:
            docs = self._retriever.search(cluster.canonical, self._top_k)
        except (KnowledgeBaseNotReady, NotImplementedError):
            logger.warning(
                "답변 생성 실패 — 지식베이스를 읽을 수 없습니다 (ticket=%s)", cluster.ticket
            )
            return None

        if not docs or docs[0].score < self._grounding_threshold:
            # "근거 있는 경우에만 응답" (CHAT-02/03) — 근거가 약하면 침묵한다.
            logger.info(
                "근거 부족으로 답변 생략 (ticket=%s, top=%.4f < %.4f)",
                cluster.ticket,
                docs[0].score if docs else 0.0,
                self._grounding_threshold,
            )
            return None

        answer = FaqAnswer(
            ticket=cluster.ticket,
            live_id=cluster.live_id,
            question=cluster.canonical,
            cluster_size=cluster.size,
            answer=self._generator.generate(cluster.canonical, docs),
            grounded=True,
            grounding_score=docs[0].score,
            sources=[AnswerSource(doc_id=d.doc_id, score=d.score) for d in docs],
            created_at=datetime.now(UTC),
        )
        self._answers.save(answer)
        return answer

    # -- 답변 조회 --------------------------------------------------------
    def list_answers(self, live_id: int, since: datetime | None = None) -> AnswerListResponse:
        self._ensure_knowledge_base()
        return AnswerListResponse(
            live_id=live_id,
            answers=self._answers.list_for_live(live_id, since),
        )

    def get_answer(self, ticket: str) -> FaqAnswer:
        """없으면 `AnswerNotFound` — 미생성이거나 근거 부족으로 생성되지 않은 경우."""
        return self._answers.get(ticket)

    def _ensure_knowledge_base(self) -> None:
        """답변 기능이 살아 있는지 확인한다(빈 질의로 검색 경로를 한 번 태운다)."""
        try:
            self._retriever.search("", 1)
        except NotImplementedError as exc:
            raise KnowledgeBaseNotReady(str(exc)) from exc


@lru_cache
def get_chat_service() -> ChatModerationService:
    """FastAPI 의존성 주입용 서비스 프로바이더(싱글턴).

    **여기가 유일한 스왑 지점이다.** 실모델/실 RAG로 갈아끼울 때는 `registry.ACTIVE_*` 키만
    바꾸면 되고, 이 함수는 그대로 둔다.
    """
    embedder = registry.embedder_config()
    return ChatModerationService(
        spam_detector=SpamDetector(build_state_store()),
        classifier=build_classifier(),
        question_detector=QuestionDetector(),
        clusterer=QuestionClusterer(similarity_threshold=embedder["cluster_similarity"]),
        retriever=build_retriever(),
        generator=build_generator(),
        answer_store=build_answer_store(),
        grounding_threshold=embedder["grounding_threshold"],
    )
