"""카테고리 매핑 엔진 — `(source_site, source_category_raw) -> subcategory_code`.

브리핑 §5의 5개 질문에 대한 이 저장소의 답이다:

1. **사이트별 카테고리 트리 조사** → 사이트 스펙 YAML의 `category_map`이 그 결과물을 담는
   자리다(`site_spec.py`). 조사해서 확정한 경로는 정확 일치로 1.0 신뢰도를 받는다.
2. **1:N / N:1 처리** → 자동으로 우겨넣지 않는다. 우리보다 뭉뚱그린 카테고리(예: 사이트의
   "니트/스웨터" 하나가 우리 `KNIT`/`SWEATSHIRT` 둘에 걸침)는 `needs_review`로 떨어져
   사람이 사진을 보고 정한다. 반대로 사이트가 더 세분화된 경우(N:1)는 키워드 규칙이
   자연스럽게 흡수한다.
3. **매핑 테이블을 코드/데이터로 관리** → 하드코딩 if문 없이, 사이트별 표(YAML) + 공용
   키워드 사전(`mapping_rules.py`) 2단으로 분리. taxonomy가 바뀌면 `labels.py`의
   `TAXONOMY_VERSION`과 함께 갱신하고, 수집 산출물에는 그 버전이 행마다 박힌다.
4. **신뢰도 표기** → `MappingResult.confidence` + `status`(mapped/needs_review/unmapped).
   검수 우선순위를 이 값으로 정렬한다.
5. **taxonomy에 없는 카테고리** → `unmapped`. 별도 파일로 모아서 taxonomy 확장 논의에 쓴다.

표준 라이브러리만 쓴다 — CI(`requirements-dev.txt`만 설치)에서 그대로 테스트된다.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from mapping_rules import (
    AMBIGUOUS_CONFIDENCE_CAP,
    CONFIDENCE_AUTO_THRESHOLD,
    PRODUCT_NAME_PENALTY,
    RULES,
    TIE_CONFIDENCE_CAP,
    MappingRule,
)

MappingStatus = Literal["mapped", "needs_review", "unmapped"]
MappingMethod = Literal["site_table", "keyword", "none"]

# 계층 구분자 — "아우터 > 자켓 > 블루종"의 ">". 사이트마다 표기가 다르다.
_PATH_SEPARATORS = re.compile(r"\s*(?:>{1,2}|\||»|›|→|-{2,})\s*")

# 병렬(형제) 구분자 — "숄더백/토트백"의 "/". 계층과 **다르게** 다뤄야 한다:
# 사이트가 우리보다 뭉뚱그린 1:N 카테고리라는 신호이기 때문이다(브리핑 §5.2).
# "상의/니트"처럼 계층 뜻으로 "/"를 쓰는 사이트도 있어서, 나열된 항목이 결국 같은 코드
# 하나로 수렴하면 그냥 매핑하고 서로 다른 코드로 갈리면 검수로 보낸다.
_ALTERNATIVE_SEPARATORS = re.compile(r"\s*[/,·ㆍ&]\s*")

# 정규화 시 지우는 문자 — 공백/구두점/괄호류. 한글·영숫자만 남긴다.
_STRIP_CHARS = re.compile(r"[^0-9a-z가-힣]+")


def normalize(text: str) -> str:
    """매칭용 정규화: NFKC → 소문자 → 한글/영숫자 외 전부 제거.

    "아우터 > Zip-up 후드!" -> "아우터zipup후드". 사이트마다 공백·하이픈·전각문자 사용이
    제각각이라, 키워드를 붙여쓴 형태 하나로 통일해두고 부분 문자열 포함으로 매칭한다.
    """
    folded = unicodedata.normalize("NFKC", text).lower()
    return _STRIP_CHARS.sub("", folded)


def split_path(raw_category: str) -> list[str]:
    """원본 카테고리 경로를 계층 세그먼트로 자른다. "아우터 > 자켓 > 블루종" -> 3개."""
    return [seg.strip() for seg in _PATH_SEPARATORS.split(raw_category.strip()) if seg.strip()]


def split_alternatives(segment: str) -> list[str]:
    """세그먼트 하나를 병렬 항목으로 자른다. "숄더백/토트백" -> 2개, "니트" -> 1개."""
    return [alt.strip() for alt in _ALTERNATIVE_SEPARATORS.split(segment.strip()) if alt.strip()]


@dataclass(frozen=True)
class RuleHit:
    code: str
    keyword: str
    ambiguous: bool

    @property
    def score(self) -> int:
        """매칭된 키워드의 길이 = 특이성 점수. 긴 키워드가 더 구체적이다."""
        return len(self.keyword)


@dataclass(frozen=True)
class MappingResult:
    subcategory_code: str | None
    status: MappingStatus
    confidence: float
    method: MappingMethod
    # 판정 근거 — 검수 화면/로그에서 "왜 이렇게 매핑됐는지" 바로 보이게 남긴다.
    matched_keyword: str | None = None
    matched_text: str | None = None
    runner_up_code: str | None = None
    reason: str = ""

    @property
    def needs_human(self) -> bool:
        return self.status != "mapped"


def _match_rule(rule: MappingRule, normalized: str) -> RuleHit | None:
    """규칙 하나를 정규화된 텍스트에 대고 본다. 배제어가 걸리면 후보에서 뺀다."""
    if any(bad in normalized for bad in rule.exclude):
        return None
    hits = [kw for kw in rule.keywords if kw in normalized]
    if not hits:
        return None
    # 같은 규칙 안에서도 가장 구체적인(긴) 키워드를 대표로 쓴다.
    best = max(hits, key=len)
    return RuleHit(code=rule.code, keyword=best, ambiguous=rule.ambiguous)


def _best_hits(normalized: str) -> list[RuleHit]:
    """코드별 최고 점수 hit 목록을 점수 내림차순으로."""
    per_code: dict[str, RuleHit] = {}
    for rule in RULES:
        hit = _match_rule(rule, normalized)
        if hit is None:
            continue
        current = per_code.get(hit.code)
        if current is None or hit.score > current.score:
            per_code[hit.code] = hit
    return sorted(per_code.values(), key=lambda h: h.score, reverse=True)


def _confidence(best: RuleHit, margin: int) -> float:
    """길이 점수 + 2위와의 격차로 신뢰도를 만든다.

    긴 키워드가 걸릴수록(`"후드집업"` 4자 > `"니트"` 2자) 우연 일치 가능성이 낮다.
    """
    value = 0.50 + 0.08 * best.score + 0.10 * margin
    return round(min(value, 0.95), 3)


def match_text(text: str) -> MappingResult:
    """자유 텍스트 한 덩어리에 키워드 규칙을 적용한다(경로 세그먼트 1개, 상품명 등)."""
    normalized = normalize(text)
    if not normalized:
        return MappingResult(None, "unmapped", 0.0, "none", reason="빈 텍스트")

    hits = _best_hits(normalized)
    if not hits:
        return MappingResult(
            None,
            "unmapped",
            0.0,
            "none",
            matched_text=text,
            reason="일치하는 키워드 규칙 없음(우리 taxonomy 밖일 수 있음 — §5.5)",
        )

    best = hits[0]
    runner_up = hits[1] if len(hits) > 1 else None
    margin = best.score - (runner_up.score if runner_up else 0)
    confidence = _confidence(best, margin)

    if best.ambiguous:
        confidence = min(confidence, AMBIGUOUS_CONFIDENCE_CAP)
        reason = "모호 규칙(사진을 봐야 확정 가능)"
    elif margin == 0 and runner_up is not None:
        # 두 코드가 같은 강도로 걸린 경우 — 사이트가 우리보다 뭉뚱그린 1:N 카테고리
        # ("숄더백/토트백")이거나 복합 아이템("니트 베스트")이다. 브리핑 §5.2가
        # "자동 매핑할지 사람이 재분류할지 판단이 필요하다"고 한 지점이라, 점수가
        # 높아도 자동 확정하지 않는다.
        confidence = min(confidence, TIE_CONFIDENCE_CAP)
        reason = f"{best.code}/{runner_up.code} 동점 — 어느 쪽인지 텍스트만으로 결정 불가"
    else:
        reason = f"키워드 '{best.keyword}' 일치"

    status: MappingStatus = "mapped" if confidence >= CONFIDENCE_AUTO_THRESHOLD else "needs_review"
    return MappingResult(
        subcategory_code=best.code,
        status=status,
        confidence=confidence,
        method="keyword",
        matched_keyword=best.keyword,
        matched_text=text,
        runner_up_code=runner_up.code if runner_up else None,
        reason=reason,
    )


def _match_segment(segment: str) -> MappingResult:
    """계층 세그먼트 1개를 본다. "숄더백/토트백"처럼 병렬 나열이면 항목별로 나눠서 비교한다.

    - 나열 항목이 전부 같은 코드로 수렴("니트/스웨터" → 둘 다 KNIT) → 그대로 매핑.
    - 서로 다른 코드로 갈림("숄더백/토트백") → **사이트가 우리보다 뭉뚱그린 1:N 카테고리**다.
      대표 이미지가 둘 중 어느 쪽인지 텍스트로는 알 수 없으므로 검수로 보낸다(§5.2).
    """
    alternatives = split_alternatives(segment)
    if len(alternatives) <= 1:
        return match_text(segment)

    results = [match_text(alt) for alt in alternatives]
    mapped = [r for r in results if r.subcategory_code is not None]
    codes = list(dict.fromkeys(r.subcategory_code for r in mapped))
    if not mapped:
        return match_text(segment)
    if len(codes) == 1:
        return max(mapped, key=lambda r: r.confidence)

    best = max(mapped, key=lambda r: r.confidence)
    others = [code for code in codes if code != best.subcategory_code]
    return MappingResult(
        subcategory_code=best.subcategory_code,
        status="needs_review",
        confidence=min(best.confidence, TIE_CONFIDENCE_CAP),
        method="keyword",
        matched_keyword=best.matched_keyword,
        matched_text=segment,
        runner_up_code=others[0],
        reason=(
            f"한 카테고리에 {'/'.join(codes)}가 함께 나열됨 — 사이트 분류가 우리보다 넓다(§5.2)"
        ),
    )


def map_category(
    raw_category: str,
    *,
    site_table: dict[str, str] | None = None,
    product_name: str | None = None,
) -> MappingResult:
    """원본 카테고리(+보조로 상품명)를 우리 소분류 코드로 매핑한다.

    판정 순서:
      1. `site_table` 정확 일치(정규화 후 비교) — 사람이 사이트 트리를 조사해 확정한 표라
         신뢰도 1.0.
      2. 카테고리 경로를 **깊은 세그먼트부터** 키워드 매칭. "아우터 > 자켓 > 블루종"이면
         "블루종" → "자켓" → "아우터" 순. 깊을수록 구체적이라 먼저 본다.
      3. 경로 전체를 한 덩어리로 매칭(세그먼트 경계에 걸친 표현 대비).
      4. 그래도 실패하면 `product_name`으로 한 번 더 — 단 신뢰도에 감쇠를 곱하고, 성공해도
         자동 확정 임계값을 넘지 못하면 검수로 간다.
    """
    site_table = site_table or {}

    normalized_raw = normalize(raw_category)
    for key, code in site_table.items():
        if normalize(key) == normalized_raw:
            return MappingResult(
                subcategory_code=code,
                status="mapped",
                confidence=1.0,
                method="site_table",
                matched_text=raw_category,
                reason="사이트 스펙의 category_map 정확 일치",
            )

    segments = split_path(raw_category)
    candidates: list[str] = list(reversed(segments))
    if len(segments) > 1:
        candidates.append(raw_category)

    fallback: MappingResult | None = None
    for candidate in candidates:
        result = _match_segment(candidate)
        if result.status == "mapped":
            return result
        if result.subcategory_code is not None and fallback is None:
            fallback = result  # needs_review 후보는 기억만 해두고 더 구체적인 세그먼트를 계속 본다

    if fallback is not None:
        return fallback

    if product_name:
        from_name = match_text(product_name)
        if from_name.subcategory_code is not None:
            confidence = round(from_name.confidence * PRODUCT_NAME_PENALTY, 3)
            status: MappingStatus = (
                "mapped" if confidence >= CONFIDENCE_AUTO_THRESHOLD else "needs_review"
            )
            return MappingResult(
                subcategory_code=from_name.subcategory_code,
                status=status,
                confidence=confidence,
                method="keyword",
                matched_keyword=from_name.matched_keyword,
                matched_text=product_name,
                runner_up_code=from_name.runner_up_code,
                reason=f"카테고리에서 실패, 상품명에서 '{from_name.matched_keyword}' 일치(감쇠 적용)",
            )

    return MappingResult(
        None,
        "unmapped",
        0.0,
        "none",
        matched_text=raw_category,
        reason="카테고리·상품명 어디서도 규칙 일치 없음 — taxonomy 확장 후보(§5.5)",
    )
