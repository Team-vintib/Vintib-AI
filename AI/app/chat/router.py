"""라이브 댓글 관리 API 레이어.

요청 검증·응답 변환만 담당하고 로직은 service에 위임한다. 판정(`POST /moderate`)은 동기,
답변 생성은 `BackgroundTasks`로 응답 이후에 돌려서 채팅 지연 예산을 지킨다.

`action`은 **권고**다 — 실제 차단/숨김(`chat_message.is_blocked`, CHAT-004) 집행은 BE가 한다.

설계: .claude/plans/ai/003-live-comment-moderation-prototype.md
"""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.chat.schemas import (
    AnswerListResponse,
    FaqAnswer,
    ModerateRequest,
    ModerateResponse,
    SeedDocumentRequest,
)
from app.chat.service import AnswerNotFound, ChatModerationService, get_chat_service

router = APIRouter()


@router.post("/moderate", response_model=ModerateResponse)
def moderate_message(
    request: ModerateRequest,
    background: BackgroundTasks,
    service: ChatModerationService = Depends(get_chat_service),
) -> ModerateResponse:
    response, deferred = service.moderate(request)
    if deferred is not None:
        background.add_task(deferred)
    return response


@router.get("/lives/{live_id}/answers", response_model=AnswerListResponse)
def list_live_answers(
    live_id: int,
    since: datetime | None = Query(None, description="이 시각 이후 생성된 답변만"),
    service: ChatModerationService = Depends(get_chat_service),
) -> AnswerListResponse:
    return service.list_answers(live_id, since)


@router.post("/lives/{live_id}/documents", status_code=status.HTTP_204_NO_CONTENT)
def seed_document(
    live_id: int,
    request: SeedDocumentRequest,
    service: ChatModerationService = Depends(get_chat_service),
) -> None:
    """STT 없이 반복질문 근거 문서를 채운다(-571, CH024) — BE가 상품 편성 시점에 호출한다."""
    service.seed_document(live_id, request.content)


@router.delete("/lives/{live_id}/documents", status_code=status.HTTP_204_NO_CONTENT)
def clear_documents(
    live_id: int,
    service: ChatModerationService = Depends(get_chat_service),
) -> None:
    """방송 종료 시 근거 문서를 전부 지운다(CH026 후속) — BE가 방송 종료 훅에서 호출한다."""
    service.clear_documents(live_id)


@router.get("/answers/{ticket}", response_model=FaqAnswer)
def get_answer(
    ticket: str,
    service: ChatModerationService = Depends(get_chat_service),
) -> FaqAnswer:
    try:
        return service.get_answer(ticket)
    except AnswerNotFound as exc:
        # 티켓이 없거나, 근거 부족으로 답변이 생성되지 않은 경우 둘 다 404다.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "answer not found") from exc
