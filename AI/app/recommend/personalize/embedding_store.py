"""상품 의류 임베딩 저장소(`postgres-vector`) — 저장/조회 DAO.

`app/chat/rag_store.py`와 같은 패턴(같은 AI 전용 pgvector 인스턴스, `app/core/db.py`의
`get_vector_engine()`)을 그대로 따른다 — 이 모듈은 **DB 왕복만** 한다. 임베딩 계산(torch
필요)은 `worker/models/sam3/garment_embedding.py`가 이미 끝내서 넘겨준다.

`rag_store.py`의 `ChatRagDocument`와 다른 점 — **여기는 upsert다.** 품질검수는 상품 하나에
대해 재검수(재촬영 등)로 여러 번 돌 수 있는데, 그때마다 새 행이 쌓이면 안 되고 상품당 최신
임베딩 1개만 유지해야 한다(추천은 "이 상품의 지금 임베딩"이 필요하지, 이력이 필요하지 않다).

`find_similar()`가 실제 조회·서빙 로직이다 — `app/recommend/similar/service.py`가 이걸 쓴다.
pgvector의 코사인 거리 연산자(`<=>`)를 이 프로젝트에서 처음 실시간 쿼리로 쓰는 곳이다(CH020은
"동일 상품" 판별에 이 방식이 안 맞아 의도적으로 안 썼다 — 여긴 다른 목적).

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
    # 품질검수 payload의 GarmentCategory 값(예: "TOP_KNIT"). nullable — 이 컬럼 추가 이전에
    # 저장된 행은 값이 없고, category 필터를 안 쓰는 조회엔 영향 없다.
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
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


@dataclass(frozen=True)
class SimilarGarmentMatch:
    """`find_similar()` 결과 한 건 — 코사인 유사도(거리의 역, 1에 가까울수록 유사)."""

    product_id: int
    score: float


def init_schema() -> None:
    """`CREATE EXTENSION vector` + 테이블 생성. 이미 있으면 아무 것도 안 한다(멱등).

    `rag_store.py`와 동일하게 앱 기동에 안 묶는다 — 배포/로컬 셋업 스크립트에서 명시적으로
    호출한다.
    """
    engine = get_vector_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(conn)


def save_garment_embedding(
    product_id: int,
    embedding: list[float],
    model_id: str,
    category: str | None = None,
) -> None:
    """상품 하나의 임베딩을 upsert한다 — 같은 `product_id`가 이미 있으면 덮어쓴다(재검수)."""
    with Session(get_vector_engine()) as session:
        stmt = insert(ProductGarmentEmbedding).values(
            product_id=product_id, embedding=embedding, model_id=model_id, category=category
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[ProductGarmentEmbedding.product_id],
            set_={
                "embedding": stmt.excluded.embedding,
                "model_id": stmt.excluded.model_id,
                "category": stmt.excluded.category,
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


def find_similar(product_id: int, k: int, category: str | None = None) -> list[SimilarGarmentMatch]:
    """`product_id` 상품과 코사인 거리가 가까운 순으로 최대 `k`개를 돌려준다.

    대상 상품 자체에 임베딩이 없으면(품질검수 미완료·옷 미검출) 빈 리스트 — 에러가 아니다,
    호출부(`app/recommend/similar/service.py`)가 "아직 추천 불가"로 정상 처리한다.
    `category`를 주면 그 값이 일치하는 상품으로만 후보를 좁힌다(카테고리 컬럼이 없던 시절에
    저장된 행은 `category is None`이라 이 필터에 걸리지 않는다 — 의도된 동작).
    """
    with Session(get_vector_engine()) as session:
        query_embedding = session.execute(
            select(ProductGarmentEmbedding.embedding).where(
                ProductGarmentEmbedding.product_id == product_id
            )
        ).scalar_one_or_none()
        if query_embedding is None:
            return []

        distance = ProductGarmentEmbedding.embedding.cosine_distance(query_embedding)
        stmt = (
            select(ProductGarmentEmbedding.product_id, distance.label("distance"))
            .where(ProductGarmentEmbedding.product_id != product_id)
            .order_by(distance)
            .limit(k)
        )
        if category is not None:
            stmt = stmt.where(ProductGarmentEmbedding.category == category)

        rows = session.execute(stmt).all()
        return [
            SimilarGarmentMatch(product_id=row.product_id, score=round(1 - row.distance, 4))
            for row in rows
        ]
