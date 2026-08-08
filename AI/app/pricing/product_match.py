"""동일 상품(브랜드+상품명+카테고리) 텍스트 매칭 — 순수 함수(CH030).

이미지 임베딩(CH024 `internal` 백엔드)이 아니라 텍스트만으로 "동일 상품"을 판정한다.
정규화된 제목 토큰 + 브랜드로 1차 키(엄격), 표본이 부족하면 브랜드+카테고리만의 2차 키
(완화)로 재조회한다 — 사용자가 지정한 폴백 순서 그대로다.

브랜드 별칭 사전(`GET /api/brands` 캐시)은 이 모듈이 직접 조회하지 않는다 — 네트워크 호출이
섞이면 순수 함수로 테스트할 수 없다. 호출부(`product_corpus.py`)가 사전을 만들어 인자로
넘긴다.

설계: docs/plans/AI/CH030-pricing-text-match.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "MatchKeys",
    "build_match_keys",
    "normalize_title",
    "resolve_brand_id",
]

# 매칭에 도움이 안 되는 공통 수식어. 사이즈·컨디션·마케팅 문구는 "동일 상품"을 가리는 데
# 방해만 된다(거의 모든 제목에 등장) — 정규화 시 제거한다. 실측 없이 잡은 목록이라(CH030
# 문서 "확인 필요" 참고) 매칭 정확도를 보면서 늘리거나 줄일 대상이다.
_NOISE_TOKENS = frozenset(
    {
        "빈티지",
        "미착용",
        "새제품",
        "새상품",
        "정품",
        "한정판",
        "데드스탁",
        "급처",
        "저렴이",
        "s",
        "m",
        "l",
        "xl",
        "xs",
        "xxl",
        "free",
        "one",
        "size",
    }
)

_TOKEN_SPLIT_RE = re.compile(r"[^0-9a-zA-Z가-힣]+")


def normalize_title(title: str) -> list[str]:
    """제목을 소문자화하고 특수문자를 걷어낸 뒤, 노이즈 토큰을 뺀 유의미 토큰 목록으로 만든다.

    정렬은 호출부(`build_match_keys`)가 한다 — 이 함수는 "무엇을 유의미한 토큰으로 볼지"만
    책임진다.
    """
    lowered = title.strip().lower()
    tokens = [tok for tok in _TOKEN_SPLIT_RE.split(lowered) if tok]
    return [tok for tok in tokens if tok not in _NOISE_TOKENS]


def resolve_brand_id(
    *, brand_id: int | None, product_name: str, brand_alias_map: dict[str, int]
) -> int | None:
    """브랜드 id를 결정한다. 요청에 이미 `brand_id`가 있으면 그대로 쓴다(가장 신뢰도 높음).

    없으면 상품명에서 브랜드 별칭(`brand_alias_map` — `GET /api/brands`의 name/nameEn을
    소문자로 정규화한 키)이 부분 문자열로 등장하는지 검사한다. 실데이터의 `brand_id`가
    거의 항상 비어 있어서(CH030 조사) 이 폴백이 없으면 브랜드 매칭 자체가 거의 항상 실패한다.
    긴 별칭부터 검사한다 — 짧은 별칭이 다른 브랜드명 안에 부분 문자열로 우연히 섞여 있을 때
    오매칭을 줄이기 위해서다.
    """
    if brand_id is not None:
        return brand_id

    lowered = product_name.strip().lower()
    for alias in sorted(brand_alias_map, key=len, reverse=True):
        if alias and alias in lowered:
            return brand_alias_map[alias]
    return None


@dataclass(frozen=True)
class MatchKeys:
    """ "동일 상품" 판정에 쓸 키 2개. `strict`가 1차(정확), `relaxed`가 2차(완화) 후보다."""

    strict: str
    relaxed: str


def build_match_keys(
    *,
    product_name: str,
    brand_id: int | None,
    category: str,
    brand_alias_map: dict[str, int],
) -> MatchKeys:
    """1차(브랜드+정규화 토큰+카테고리)·2차(브랜드+카테고리) 매칭 키를 만든다.

    호출부(`comps.py`)는 `strict`로 먼저 조회하고, 표본이 `min_comps` 미만이면 `relaxed`로
    재조회한다(사용자가 지정한 순서). `product.match_key` 컬럼에는 `strict`를 저장한다 —
    구매자 화면의 동일 상품 조회 기준이 된다.

    `category`는 호출부가 결정한 문자열 식별자다 — BE의 categoryId(성별별로 최대 3개가 같은
    이름을 가질 수 있음, 126개 taxonomy)와 AI의 `GarmentCategory`(6종, 성별 무관) 사이의
    변환은 이 함수의 책임이 아니다(`product_corpus.py`가 캐시 적재 시 통일해서 넣는다).
    """
    resolved_brand = resolve_brand_id(
        brand_id=brand_id, product_name=product_name, brand_alias_map=brand_alias_map
    )
    brand_token = str(resolved_brand) if resolved_brand is not None else "unknown"
    tokens = sorted(set(normalize_title(product_name)))
    strict = f"{brand_token}:{'-'.join(tokens)}:{category}"
    relaxed = f"{brand_token}:{category}"
    return MatchKeys(strict=strict, relaxed=relaxed)
