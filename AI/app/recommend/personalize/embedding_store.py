"""상품 의류 임베딩 저장소(`postgres-vector`) — 저장/조회 DAO.

`app/chat/rag_store.py`와 같은 패턴(같은 AI 전용 pgvector 인스턴스, `app/core/db.py`의
`get_vector_engine()`)을 그대로 따른다 — 이 모듈은 **DB 왕복만** 한다. 임베딩 계산(torch
필요)은 `worker/models/sam3/garment_embedding.py`가 이미 끝내서 넘겨준다.

`rag_store.py`의 `ChatRagDocument`와 다른 점 — **여기는 upsert다.** 품질검수는 상품 하나에
대해 재검수(재촬영 등)로 여러 번 돌 수 있는데, 그때마다 새 행이 쌓이면 안 되고 상품당 최신
임베딩 1개만 유지해야 한다(추천은 "이 상품의 지금 임베딩"이 필요하지, 이력이 필요하지 않다).

이번 라운드 범위는 저장까지다 — 추천 API가 이 벡터를 실제로 조회·서빙하는 로직은 여기 없다
(`fetch_garment_embedding()`은 다음 단계가 바로 쓸 수 있게 미리 추가해 둔 것).

설계: `docs/plans/AI/CH020-internal-clip-price-comps.md`(zero-shot 선택 근거),
`worker/models/sam3/garment_embedding.py`(임베딩 계산)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.db import get_vector_engine

# fashion-clip / CLIP ViT-B/32 projection_dim. worker/models/sam3/garment_embedding.py의
# EMBEDDING_DIM과 반드시 같아야 한다.
EMBEDDING_DIM = 512


class Base(DeclarativeBase):
    pass


class ProductGarmentEmbedding(Base):
    """상품(`product_id`) 하나의 최신 의류 임베딩. `product_id`는 유니크 — 재검수 시 덮어쓴다."""

    __tablename__ = "product_garment_embedding"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


@dataclass(frozen=True)
class GarmentEmbeddingRecord:
    """DAO 반환용 — 순수 데이터."""

    product_id: int
    embedding: list[float]
    model_id: str
    updated_at: datetime


def init_schema() -> None:
    """`CREATE EXTENSION vector` + 테이블 생성. 이미 있으면 아무 것도 안 한다(멱등).

    `rag_store.py`와 동일하게 앱 기동에 안 묶는다 — 배포/로컬 셋업 스크립트에서 명시적으로
    호출한다.
    """
    engine = get_vector_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(conn)


def save_garment_embedding(product_id: int, embedding: list[float], model_id: str) -> None:
    """상품 하나의 임베딩을 upsert한다 — 같은 `product_id`가 이미 있으면 덮어쓴다(재검수)."""
    with Session(get_vector_engine()) as session:
        stmt = insert(ProductGarmentEmbedding).values(
            product_id=product_id, embedding=embedding, model_id=model_id
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[ProductGarmentEmbedding.product_id],
            set_={
                "embedding": stmt.excluded.embedding,
                "model_id": stmt.excluded.model_id,
                "updated_at": func.now(),
            },
        )
        session.execute(stmt)
        session.commit()


def fetch_garment_embedding(product_id: int) -> GarmentEmbeddingRecord | None:
    """상품 하나의 최신 임베딩을 가져온다. 없으면 `None`."""
    with Session(get_vector_engine()) as session:
        row = session.execute(
            select(ProductGarmentEmbedding).where(ProductGarmentEmbedding.product_id == product_id)
        ).scalar_one_or_none()
        if row is None:
            return None
        return GarmentEmbeddingRecord(
            product_id=row.product_id,
            embedding=list(row.embedding),
            model_id=row.model_id,
            updated_at=row.updated_at,
        )
