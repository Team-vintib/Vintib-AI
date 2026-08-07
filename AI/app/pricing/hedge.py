"""CH016 §3.3 — 내부 호가 편향 완화. 전부 순수 함수(네트워크·DB 없음).

호가(광고가)는 미판매 건도 포함해서, 과다호가로 남은 물건이 계속 조회되면 내부 중앙값이
위로 부풀고 시간이 지날수록 심해진다. 상태 enum이 `sale_type`(거래방식)·`sale_status`
(진행상태) 둘로 나뉘어 있어 필터를 하나만 걸면 경매 낙찰가가 상시판매 시세에 섞인다.

**이번 라운드(CH024)는 CH016 §3.3만 다룬다.** §3.4~3.6(자릿수 게이트·구간 겹침·연속 감쇠)은
외부 검색(`llm_web_search`)과 내부 결과를 비교(hedge)하는 로직이라 `internal` 단일 백엔드
배선 범위 밖이다 — 두 소스를 함께 쓰는 다음 라운드에서 다룬다. 이름은 `hedge.py`를 그대로
쓰되(CH016 설계 문서와의 연결을 위해), 지금 들어있는 건 정제(필터)뿐이다.

설계: docs/plans/AI/CH016-internal-comps-hedge.md §3.3, docs/plans/AI/CH024-*.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

__all__ = [
    "MAX_LISTING_AGE_DAYS",
    "MAX_SANE_PRICE",
    "MIN_SANE_PRICE",
    "InternalCandidate",
    "apply_hedge_filters",
    "filter_by_sale_type",
    "filter_sane_price",
    "filter_stale_listings",
]

# 임의값 — 근거 없는 부채(다른 registry.py 계수들과 같은 성격). 실측 전까지 보수적으로 넉넉히
# 잡는다. 실판매가 정답셋이 쌓이면 조정 대상이다.
MAX_LISTING_AGE_DAYS = 180
MIN_SANE_PRICE = 1_000
MAX_SANE_PRICE = 100_000_000


@dataclass(frozen=True)
class InternalCandidate:
    """내부 후보 매물 1건 — `CompItem`으로 정규화되기 전, 필터링에 필요한 원본 필드.

    BE 공개 API(`app.shared.be_client.BeProduct`)를 그대로 옮긴 것에 가깝다 — comps.py가
    변환해 넘긴다.
    """

    product_id: int
    title: str
    price: int | None
    sale_type: str | None
    sale_status: str | None
    created_at: str | None  # ISO8601 문자열, BE `createdAt`


def filter_by_sale_type(
    candidates: list[InternalCandidate], *, allowed: str = "DIRECT_SALE"
) -> tuple[list[InternalCandidate], list[str]]:
    """`sale_type`이 `allowed`가 아니면 제외한다(CH016 §3.3-1, 전제조건).

    경매 낙찰가가 상시판매 시세에 섞이는 걸 막는다. `sale_type`을 알 수 없는 후보(BE 조회
    실패 등)도 제외한다 — 판정 근거가 없으면 시세 근거로 쓰지 않는다.
    """
    kept = [c for c in candidates if c.sale_type == allowed]
    dropped = len(candidates) - len(kept)
    notes = [f"상시판매가 아니거나 판매방식을 확인할 수 없는 매물 {dropped}건을 제외했습니다."]
    return kept, notes if dropped else []


def filter_stale_listings(
    candidates: list[InternalCandidate],
    *,
    now: datetime,
    max_age_days: int = MAX_LISTING_AGE_DAYS,
) -> tuple[list[InternalCandidate], list[str]]:
    """`max_age_days`보다 오래된 매물을 제외한다(CH016 §3.3-3·4).

    오래 안 팔린 매물이 시세를 위로 부풀리는 편향을 완화한다. `created_at`을 파싱할 수
    없으면 배제하지 않는다 — 판단 근거가 없다고 표본을 줄이지 않는다(다른 필터들과 같은 원칙).
    """
    kept: list[InternalCandidate] = []
    dropped = 0
    for candidate in candidates:
        age_days = _age_days(candidate.created_at, now)
        if age_days is not None and age_days > max_age_days:
            dropped += 1
            continue
        kept.append(candidate)
    notes = [f"등록된 지 {max_age_days}일이 넘은 매물 {dropped}건을 제외했습니다."]
    return kept, notes if dropped else []


def filter_sane_price(
    candidates: list[InternalCandidate],
) -> tuple[list[InternalCandidate], list[str]]:
    """절대 방어(CH016 §3.5) — 1,000원 미만·1억 초과는 배송비·입력 오류 수준으로 본다."""
    kept = [
        c for c in candidates if c.price is not None and MIN_SANE_PRICE <= c.price <= MAX_SANE_PRICE
    ]
    dropped = len(candidates) - len(kept)
    notes = [f"가격이 비정상적인 매물 {dropped}건을 제외했습니다."]
    return kept, notes if dropped else []


def apply_hedge_filters(
    candidates: list[InternalCandidate], *, now: datetime
) -> tuple[list[InternalCandidate], list[str]]:
    """CH016 §3.3 필터를 순서대로 적용한다: 판매방식 → 최신성 → 가격 절대 방어."""
    kept, notes_sale_type = filter_by_sale_type(candidates)
    kept, notes_stale = filter_stale_listings(kept, now=now)
    kept, notes_price = filter_sane_price(kept)
    return kept, [*notes_sale_type, *notes_stale, *notes_price]


def _age_days(created_at: str | None, now: datetime) -> float | None:
    if not created_at:
        return None
    try:
        parsed = datetime.fromisoformat(created_at)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return (now - parsed).total_seconds() / 86400
