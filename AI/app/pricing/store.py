"""외부 검색 결과 관측 로그 — AI 소유 postgres-vector, BE DB와 무관(CH017).

BE 상시판매 데이터 연동(CH016)은 실데이터가 쌓이기 전까지 보류 중이다. 그런데 우리가 이미
갖고 있는 데이터가 있다 — **실제 GMS 웹검색으로 얻은 매물**이다. 지금은 응답 한 번 쓰고
버리는데, 이 모듈이 그걸 durable하게 적재한다.

`app/chat/rag_store.py`(007 계획)와 같은 패턴으로 `app.core.db.get_vector_engine()`(AI 전용
postgres-vector, BE 공유 DB `config.db_*`와는 별개 인스턴스)을 재사용한다. 벡터 컬럼은 쓰지
않는다 — 유사도 검색이 목적이 아니라 캐시·사후 검수용 원장이다.

효과: (1) 같은 쿼리 재검색 비용·지연 절감(캐시), (2) 파싱 실패·이상값 사후 검수(당근의
BigQuery 뷰 테이블과 같은 역할, BE 의존 없이), (3) CH016의 관측 저장소를 실데이터로 채우는
시작점.

**이 모듈의 함수는 예외를 던지지 않는 것이 호출부와의 계약이다** — 관측 로그 적재 실패가
가격 산정을 막으면 안 된다(`RetailSource.fetch()`와 같은 성격). 예외를 삼키는 책임은
호출부(`service.py`)가 진다 — 이 모듈 자체는 있는 그대로의 DB 예외를 올린다.

설계: .claude/plans/ai/CH017-pricing-cheap-wins.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.db import get_vector_engine
from app.pricing.schemas import CompItem

__all__ = ["fetch_recent", "init_schema", "save_observations"]


class Base(DeclarativeBase):
    pass


class PricingSearchObservation(Base):
    """실제 comps 검색 1건에서 나온 매물 1건. `CompItem`을 그대로 펼쳐 저장한다."""

    __tablename__ = "pricing_search_observation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    listed_at: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    is_used: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


@dataclass(frozen=True)
class Observation:
    """DAO 반환용 — `CompItem` 재구성 + 언제 관측됐는지."""

    item: CompItem
    fetched_at: datetime


def init_schema() -> None:
    """테이블 생성. 이미 있으면 아무 것도 안 한다(멱등). 앱 기동에 묶지 않는다 — `rag_store.py`
    와 같은 이유(마이그레이션을 배포/로컬 셋업 스크립트에서 명시적으로 호출한다)."""
    engine = get_vector_engine()
    with engine.begin() as conn:
        Base.metadata.create_all(conn)


def save_observations(query: str, source: str, items: list[CompItem]) -> int:
    """검색 결과 매물들을 적재하고 저장한 건수를 돌려준다. 빈 목록이면 아무 것도 안 한다."""
    if not items:
        return 0
    with Session(get_vector_engine()) as session:
        rows = [
            PricingSearchObservation(
                query=query[:300],
                source=source,
                title=item.title[:200],
                price=item.price,
                url=item.url[:500],
                listed_at=item.listed_at[:32],
                is_used=item.is_used,
            )
            for item in items
        ]
        session.add_all(rows)
        session.commit()
        return len(rows)


def fetch_recent(query: str, *, limit: int = 50) -> list[Observation]:
    """이 쿼리 문자열로 과거에 관측한 매물을 최신순으로 가져온다.

    지금은 쿼리 **완전 일치**만 본다 — 유사 쿼리 매칭(정규화·모델번호 추출)은 CH016의 몫이고,
    이 모듈은 원장 저장·조회만 책임진다.
    """
    with Session(get_vector_engine()) as session:
        rows = session.execute(
            select(PricingSearchObservation)
            .where(PricingSearchObservation.query == query[:300])
            # id를 보조 키로 쓴다 — 타임스탬프 정밀도가 낮으면(SQLite, 혹은 같은 밀리초에
            # 들어온 postgres 행) fetched_at만으로는 순서가 안정적이지 않다.
            .order_by(
                PricingSearchObservation.fetched_at.desc(), PricingSearchObservation.id.desc()
            )
            .limit(limit)
        ).scalars()
        return [
            Observation(
                item=CompItem(
                    title=row.title,
                    price=row.price,
                    source=row.source,
                    url=row.url,
                    listed_at=row.listed_at,
                    is_used=row.is_used,
                ),
                fetched_at=row.fetched_at,
            )
            for row in rows
        ]
