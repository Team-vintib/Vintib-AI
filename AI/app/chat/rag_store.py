"""RAG 지식베이스 저장소(`postgres-vector`, S15P11A108-375) — 저장/조회 DAO.

이 모듈은 **DB 왕복만** 한다. 임베딩 계산(torch 필요)은 여기서 하지 않는다 — `embedding`은
호출부가 이미 계산해서 넘겨준다(2단계 STT 워커가 KURE-v1로 계산). 검색·랭킹·그라운딩 판단·
생성은 3단계 `chat_rag` 워커가 `fetch_documents()`로 받은 후보 텍스트를 가지고 처리한다 —
여기서 벡터 유사도 연산(`<=>`)을 하지 않는 이유는 게이트웨이(`ai` 컨테이너)에 torch가 없고
(`mem_limit: 1g`), 방송 하나당 문서 수가 적어(수십~수백 건) 워커 쪽 인메모리 비교로 충분하기
때문이다.

`embedding` 컬럼은 지금 당장 검색에 쓰이지 않지만, 나중에 대규모(여러 방송을 넘나드는) 검색이
필요해지면 pgvector의 `<=>` 검색으로 바로 전환할 수 있도록 미리 채워 둔다.

설계: .claude/plans/ai/007-pgvector-rag-storage.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text, func, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.db import get_vector_engine

# nlpai-lab/KURE-v1은 BAAI/bge-m3 파인튜닝이라 출력 차원이 1024다. 3단계에서 실제 모델을
# 로드해 재확인하기 전까지는 이 값을 가정한다(TODO: 007 계획 "미결정 사항" 참고).
EMBEDDING_DIM = 1024

SourceType = Literal["stt", "seed"]


class Base(DeclarativeBase):
    pass


class ChatRagDocument(Base):
    """방송(`live_id`) 하나에 속한 RAG 근거 문서 한 건 — 지금은 STT 전사문만 채운다."""

    __tablename__ = "chat_rag_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    live_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


@dataclass(frozen=True)
class RagDocument:
    """DAO 반환용 — 워커에 그대로 넘길 수 있는 순수 데이터."""

    id: int
    live_id: int
    content: str
    created_at: datetime


def init_schema() -> None:
    """`CREATE EXTENSION vector` + 테이블 생성. 이미 있으면 아무 것도 안 한다(멱등).

    앱 기동 시 자동으로 불리지 않는다 — 다른 도메인(품질검수 등)도 DB 마이그레이션을 앱
    시작에 묶어 두지 않는 것과 같은 이유로, 배포/로컬 셋업 스크립트에서 명시적으로 호출한다.
    """
    engine = get_vector_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(conn)


def save_document(
    live_id: int,
    source_type: SourceType,
    content: str,
    embedding: list[float] | None = None,
) -> int:
    """문서 한 건을 저장하고 id를 돌려준다."""
    with Session(get_vector_engine()) as session:
        row = ChatRagDocument(
            live_id=live_id, source_type=source_type, content=content, embedding=embedding
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def fetch_documents(live_id: int, limit: int = 200) -> list[RagDocument]:
    """이 방송(`live_id`)의 문서 후보를 최신순으로 가져온다. 벡터 연산 없음 — 랭킹은 호출부(워커) 몫."""
    with Session(get_vector_engine()) as session:
        rows = session.execute(
            select(ChatRagDocument)
            .where(ChatRagDocument.live_id == live_id)
            .order_by(ChatRagDocument.created_at.desc())
            .limit(limit)
        ).scalars()
        return [
            RagDocument(id=r.id, live_id=r.live_id, content=r.content, created_at=r.created_at)
            for r in rows
        ]
