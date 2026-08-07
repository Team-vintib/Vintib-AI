"""라이브 댓글 관리 요청/응답 스키마.

**BE 계약이 바뀌면 이 파일만 고친다.** AI는 판정만 하고 실제 차단/숨김 집행은 BE가 하므로
`action`은 강제가 아니라 권고다(설계 문서 "판정 위임 vs 직접 집행" 참고).

설계: .claude/plans/ai/003-live-comment-moderation-prototype.md
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    """댓글 판정 결과."""

    normal = "NORMAL"
    abusive = "ABUSIVE"  # 욕설·혐오·인신공격
    spam = "SPAM"  # 도배(rate-limit / 근접중복)
    repeated_question = "REPEATED_QUESTION"  # 같은 질문이 MIN_CLUSTER_SIZE 이상 반복


class ModerationAction(str, Enum):
    """BE에 권고하는 처리. 집행 주체는 BE(chat_message.is_blocked, CHAT-004)."""

    pass_ = "PASS"
    hide = "HIDE"
    block = "BLOCK"


class ModerateRequest(BaseModel):
    """BE가 메시지를 게시하기 **전에** 보내는 판정 요청."""

    live_id: int = Field(ge=1, description="라이브 방송 id (클러스터링 세션 단위)")
    message_id: int = Field(ge=1, description="BE가 채번한 메시지 id. AI는 에코만 함")
    user_id: int = Field(ge=1, description="작성자 id (스팸 윈도우 키)")
    content: str = Field(min_length=1, max_length=1000, description="댓글 본문")
    sent_at: datetime | None = Field(None, description="작성 시각. 없으면 서버 시각 사용")


class Scores(BaseModel):
    """판정 근거 점수(디버그/튜닝용. FE는 무시 가능)."""

    abuse: float
    spam: float


class ModerateResponse(BaseModel):
    message_id: int
    verdict: Verdict
    action: ModerationAction
    reason: str  # 어떤 규칙에 걸렸는지(예: rate_limit, abuse_term, question_repeated)
    scores: Scores
    answer_ticket: str | None = None  # 반복질문일 때만. 답변 조회용 키
    latency_ms: float


class AnswerSource(BaseModel):
    """답변의 근거가 된 FAQ 문서."""

    doc_id: str
    score: float


class FaqAnswer(BaseModel):
    """반복질문에 대해 생성된 답변. 근거가 없으면 애초에 만들어지지 않는다."""

    ticket: str
    live_id: int
    question: str
    cluster_size: int
    answer: str
    grounded: bool
    grounding_score: float
    sources: list[AnswerSource]
    created_at: datetime


class AnswerListResponse(BaseModel):
    live_id: int
    answers: list[FaqAnswer]


class SeedDocumentRequest(BaseModel):
    """STT 없이 반복질문 근거 문서를 채우는 경로(-571, CH024). BE가 상품 편성 시점에 호출한다."""

    content: str = Field(min_length=1, max_length=1000)
