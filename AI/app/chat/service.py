"""라이브 댓글 관리 파이프라인 오케스트레이션.

동기 판정 3단계를 우선순위대로 단락 평가한다: 스팸 → 악성 → 질문 게이트.
반복질문으로 판정되면 티켓만 즉시 돌려주고 **답변 생성은 응답 이후로 미룬다**
(라우터가 `BackgroundTasks`로 실행) — 생성 지연이 채팅을 막지 않게 하려는 것이다.

AI는 판정만 하고 실제 차단/숨김은 BE가 집행한다. 이유는 설계 문서의
"판정 위임 vs 직접 집행" 표 참고 — 1 RTT, 게시 전 판정이라 노출 없음, AI 장애가 격리됨.

**답변 생성은 게이트웨이가 직접 하지 않는다.** `rag_store.fetch_documents()`로 이 방송의 문서
후보를 가져와 `chat_rag` job으로 워커에 넘기고, 검색·그라운딩 판단·생성은 전부 워커가
처리한다(`worker/chat_rag_worker_example.py`, `S15P11A108-444`) — 게이트웨이(`ai` 컨테이너)엔
torch가 없어서다. `Retriever`/`AnswerGenerator`(`app/chat/faq.py`) 인터페이스는 이제 평가
파이프라인(`app/chat/evaluation.py`) 전용이고 이 서비스는 더 이상 참조하지 않는다.

`get_chat_service()`의 조립부가 **유일한 구현 스왑 지점**이다.

설계: .claude/plans/ai/003-live-comment-moderation-prototype.md,
.claude/plans/ai/009-chat-rag-generator.md
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime
from functools import lru_cache

from app.chat import rag_store, registry
from app.chat.answers import AnswerNotFound, AnswerStore, build_answer_store
from app.chat.classifier import AbuseClassifier, build_classifier
from app.chat.faq import Cluster, QuestionClusterer, QuestionDetector
from app.chat.schemas import (
    AnswerListResponse,
    FaqAnswer,
    ModerateRequest,
    ModerateResponse,
    ModerationAction,
    Scores,
    Verdict,
)
from app.chat.spam import SpamDetector, build_state_store
from app.gateway.router import enqueue_job

# 라우터가 import하기 쉽도록 재노출(404 매핑용).
__all__ = [
    "ChatModerationService",
    "AnswerNotFound",
    "get_chat_service",
]

logger = logging.getLogger(__name__)


class ChatModerationService:
    """댓글 한 건을 판정하고, 반복질문이면 `chat_rag` job을 큐에 넣는다."""

    def __init__(
        self,
        spam_detector: SpamDetector,
        classifier: AbuseClassifier,
        question_detector: QuestionDetector,
        clusterer: QuestionClusterer,
        answer_store: AnswerStore,
        *,
        abuse_threshold: float = registry.ABUSE_THRESHOLD,
        min_cluster_size: int = registry.MIN_CLUSTER_SIZE,
        candidate_limit: int = registry.CHAT_RAG_CANDIDATE_LIMIT,
    ) -> None:
        self._spam = spam_detector
        self._classifier = classifier
        self._questions = question_detector
        self._clusterer = clusterer
        self._answers = answer_store
        self._abuse_threshold = abuse_threshold
        self._min_cluster_size = min_cluster_size
        self._candidate_limit = candidate_limit
        # 이미 워커에 보내 결과를 기다리는 중인 티켓. 프로세스 인메모리라 다중 게이트웨이
        # 환경에서는 안 맞는다 — InMemoryAnswerStore와 같은 한계(S15P11A108-188).
        self._pending: set[str] = set()

    # -- 동기 판정 --------------------------------------------------------
    def moderate(
        self, request: ModerateRequest
    ) -> tuple[ModerateResponse, Callable[[], None] | None]:
        """판정 결과와, 있으면 지연 실행할 작업을 함께 돌려준다."""
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
                deferred = self._make_enqueue_job(cluster)
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

    # -- 답변 생성: chat_rag job 큐 -----------------------------------------
    def _make_enqueue_job(self, cluster: Cluster) -> Callable[[], None]:
        def job() -> None:
            self._try_enqueue_chat_rag(cluster)

        return job

    def _try_enqueue_chat_rag(self, cluster: Cluster) -> None:
        """이미 답변됐거나 이미 워커에 보낸 티켓이면 건너뛰고, 아니면 job을 큐에 넣는다.

        실제 검색·그라운딩 판단·생성은 워커가 한다(`worker/chat_rag_worker_example.py`) —
        여기선 이 방송의 후보 문서를 모아 job payload에 실어 보내기만 한다.
        """
        try:
            self._answers.get(cluster.ticket)
        except AnswerNotFound:
            pass
        else:
            return  # 이미 답변됨

        if cluster.ticket in self._pending:
            # 워커 처리가 poll 주기(수 초)만큼 걸리는 동안 같은 클러스터에 메시지가 더 들어와도
            # moderate()는 매번 cluster.size >= min_cluster_size를 다시 통과시킨다 — 이 가드가
            # 없으면 같은 질문에 대해 워커로 중복 job이 계속 쌓인다.
            return

        docs = rag_store.fetch_documents(cluster.live_id, limit=self._candidate_limit)
        if not docs:
            # 아직 이 방송에 대한 근거 문서(STT 전사문)가 하나도 없다 — 침묵.
            return

        self._pending.add(cluster.ticket)
        enqueue_job(
            "chat_rag",
            {
                "ticket": cluster.ticket,
                "live_id": cluster.live_id,
                "question": cluster.canonical,
                "cluster_size": cluster.size,
                "docs": [{"id": d.id, "content": d.content} for d in docs],
            },
        )

    def save_generated_answer(self, answer: FaqAnswer) -> None:
        """`chat_rag` job 결과가 근거 있음(`grounded`)일 때 게이트웨이가 호출한다."""
        self._answers.save(answer)
        self._pending.discard(answer.ticket)

    def mark_chat_rag_ungrounded(self, ticket: str) -> None:
        """`chat_rag` job 결과가 근거 부족(`grounded=false`)일 때 대기 상태만 해제한다."""
        self._pending.discard(ticket)

    # -- 답변 조회 --------------------------------------------------------
    def list_answers(self, live_id: int, since: datetime | None = None) -> AnswerListResponse:
        return AnswerListResponse(
            live_id=live_id,
            answers=self._answers.list_for_live(live_id, since),
        )

    def get_answer(self, ticket: str) -> FaqAnswer:
        """없으면 `AnswerNotFound` — 미생성이거나 근거 부족으로 생성되지 않은 경우."""
        return self._answers.get(ticket)


@lru_cache
def get_chat_service() -> ChatModerationService:
    """FastAPI 의존성 주입용 서비스 프로바이더(싱글턴).

    **여기가 유일한 스왑 지점이다.** `app/gateway/router.py`의 `chat_rag` 결과 처리도 이
    싱글턴을 재사용해 같은 `AnswerStore`/`_pending` 상태에 접근한다(같은 프로세스 안이라
    `lru_cache`로 보장됨 — 다중 게이트웨이 환경에서는 안 맞는 한계는 위 `_pending` 주석과 동일).
    """
    return ChatModerationService(
        spam_detector=SpamDetector(build_state_store()),
        classifier=build_classifier(),
        question_detector=QuestionDetector(),
        clusterer=QuestionClusterer(
            similarity_threshold=registry.embedder_config()["cluster_similarity"]
        ),
        answer_store=build_answer_store(),
    )
