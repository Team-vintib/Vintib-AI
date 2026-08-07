"""검수 attention map 로그 저장소(`postgres-vector`) — 저장/조회 DAO.

`app/recommend/personalize/embedding_store.py`와 같은 패턴(같은 AI 전용 pgvector 인스턴스,
`app/core/db.py`의 `get_vector_engine()`)을 그대로 따른다.

임베딩 저장소와 달리 **여기는 upsert가 아니라 append-only 로그**다 — attention map은 "이 상품의
최신 상태"가 아니라 "이 job이 그 순간 이렇게 판단했다"는 기록 자체가 목적(모델 임계치·프롬프트
튜닝 시 판단 근거로 다시 들여다보기 위함, CH008 `log_inspection_result`의 로컬 파일 로그와 같은
목적이지만 여러 팀원이 공유 조회할 수 있는 DB에 남긴다). 그래서 같은 상품을 재검수해도 이전
행을 덮어쓰지 않고 계속 쌓인다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.db import get_vector_engine


class Base(DeclarativeBase):
    pass


class QualityAttentionMapLog(Base):
    """검수 job 하나가 낸 attention map 한 장의 기록. 상품당 여러 job·여러 장이 계속 쌓인다."""

    __tablename__ = "quality_attention_map_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    inspection_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    image_index: Mapped[int] = mapped_column(Integer, nullable=False)
    defect_type: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


@dataclass(frozen=True)
class AttentionMapLogRecord:
    """DAO 반환용 — 순수 데이터."""

    product_id: int
    inspection_id: str
    image_index: int
    defect_type: str
    url: str
    created_at: datetime


def init_schema() -> None:
    """테이블 생성. 이미 있으면 아무 것도 안 한다(멱등).

    `embedding_store.init_schema()`와 동일하게 앱 기동에 안 묶는다 — 배포/로컬 셋업 스크립트에서
    명시적으로 호출한다.
    """
    engine = get_vector_engine()
    with engine.begin() as conn:
        Base.metadata.create_all(conn)


def save_attention_maps(product_id: int, inspection_id: str, attention_maps: list[dict]) -> None:
    """job 결과의 `attention_maps[]`를 그대로 로그 테이블에 append한다. 빈 리스트면 아무 것도 안 한다."""
    if not attention_maps:
        return
    with Session(get_vector_engine()) as session:
        session.add_all(
            QualityAttentionMapLog(
                product_id=product_id,
                inspection_id=inspection_id,
                image_index=int(m["image_index"]),
                defect_type=str(m["defect_type"]),
                url=str(m["url"]),
            )
            for m in attention_maps
        )
        session.commit()


def fetch_by_product(product_id: int) -> list[AttentionMapLogRecord]:
    """상품 하나에 쌓인 모든 attention map 로그를 최신순으로 돌려준다(여러 job 걸쳐 누적)."""
    with Session(get_vector_engine()) as session:
        rows = session.execute(
            select(QualityAttentionMapLog)
            .where(QualityAttentionMapLog.product_id == product_id)
            .order_by(QualityAttentionMapLog.created_at.desc())
        ).scalars()
        return [
            AttentionMapLogRecord(
                product_id=row.product_id,
                inspection_id=row.inspection_id,
                image_index=row.image_index,
                defect_type=row.defect_type,
                url=row.url,
                created_at=row.created_at,
            )
            for row in rows
        ]
