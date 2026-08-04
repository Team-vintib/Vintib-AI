"""수집 레버 구현 — 쿼리 생성·파싱은 순수 함수, 네트워크는 백엔드로 분리.

CH015의 L1~L5 / S1~S6을 플래그로 켜고 끌 수 있게 만든다. 순수 함수(쿼리 조립·파싱·
약라벨링)와 네트워크(백엔드)를 나눈 이유는 **전자를 CI에서 그대로 테스트하기 위해서**다
— GMS를 한 번도 호출하지 않고 레버 로직을 검증할 수 있어야 한다.

⛔ **GMS 백엔드는 Claude가 실행하지 않는다**(`AI/CLAUDE.md` 하드 룰). 기본 백엔드는
`mock`이고, 실호출은 사용자가 `--backend gemini`를 명시할 때만 일어난다.

`mock` 백엔드는 단순 더미가 아니다 — **순위와 가격에 일부러 상관을 넣는다.** 출력 A의
치명적 문제(순위검색 결과를 top-k로 자르면 분포가 왜곡됨, CH015 M9)를 GMS 호출 없이
재현해서, 축 D의 가격 중립성 지표가 실제로 그 왜곡을 잡아내는지 먼저 확인하기 위해서다.

설계: .claude/plans/ai/CH015-comps-price-distribution.md
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from histogram_registry import (
    CONDITION_KEYWORDS,
    PLATFORMS,
    PRICE_STRATA,
    RETAIL_RATIO_MAX,
    RETAIL_RATIO_MIN,
    SEED,
    HarvestConfig,
)

__all__ = [
    "GeminiSearchBackend",
    "HarvestItem",
    "HarvestOutcome",
    "MockSearchBackend",
    "SearchBackend",
    "build_condition_queries",
    "build_count_queries",
    "build_query_variants",
    "build_specificity_ladder",
    "build_stratum_queries",
    "classify_condition",
    "comps_prompt",
    "count_prompt",
    "dedup_items",
    "extract_json_array",
    "harvest",
    "normalize_title",
    "retail_gate_mask",
    "rows_to_items",
]

_TAG_RE = re.compile(r"<[^>]+>")
_NON_WORD_RE = re.compile(r"[^0-9a-z가-힣]+")

# S5 — 특이도 사다리. 위에서부터 시도하다 표본이 차면 멈춘다. 멈춘 단이 곧 "비교 수준"이다.
SPECIFICITY_LEVELS = ("모델 일치", "브랜드 유사", "카테고리 평균")


# --- 값 객체 ----------------------------------------------------------------


@dataclass
class HarvestItem:
    """수집된 매물 1건.

    `rank`가 있는 것이 프로덕션 `CompItem`과 다른 점이다 — **순위를 알아야 top-k 절단이
    분포를 얼마나 왜곡하는지 잴 수 있다**(축 D 가격 중립성). 프로덕션에는 필요 없다.
    """

    title: str
    price: int
    rank: int = 0
    url: str = ""
    listed_at: str = ""
    is_used: bool | None = None
    platform: str = ""
    stratum: str = ""
    grade: str = ""  # 약라벨링 결과(S/A/B/C). 판별 불가면 빈 문자열
    query: str = ""
    level: str = ""  # 어느 특이도 단에서 얻었는지


@dataclass
class HarvestOutcome:
    """한 쿼리에 대한 수집 결과 + 축 A/C 원지표."""

    query: str
    items: list[HarvestItem] = field(default_factory=list)
    counts_by_stratum: dict[str, int] = field(default_factory=dict)  # S1 카운트 쿼리 결과
    level: str = ""
    n_raw: int = 0
    n_dedup: int = 0
    search_calls: int = 0
    latency_ms: float = 0.0
    notes: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def n_valid(self) -> int:
        return len(self.items)


# --- 쿼리 조립 (순수) --------------------------------------------------------


def build_specificity_ladder(
    product_name: str, brand: str | None = None, category: str | None = None
) -> list[tuple[str, str]]:
    """S5 — `(비교 수준, 쿼리)` 사다리. 좁은 것부터 넓은 것 순.

    **핵심은 n 확보가 아니라 어느 단에서 멈췄는지를 기록하는 것이다.** 같은
    히스토그램이라도 "이 모델의 분포"와 "이 카테고리의 분포"는 판매자에게 완전히 다른
    의미인데, 지금 프로덕션은 그 구분 없이 한 장으로 뭉갠다.
    """
    name = product_name.strip()
    ladder: list[tuple[str, str]] = [(SPECIFICITY_LEVELS[0], name)]

    brand_term = (brand or "").strip()
    if brand_term and brand_term.lower() not in name.lower():
        ladder[0] = (SPECIFICITY_LEVELS[0], f"{brand_term} {name}")

    category_term = (category or "").strip()
    if brand_term:
        broader = f"{brand_term} {category_term}".strip() if category_term else brand_term
        ladder.append((SPECIFICITY_LEVELS[1], broader))
    if category_term:
        ladder.append((SPECIFICITY_LEVELS[2], f"중고 {category_term}"))
    return ladder


def build_query_variants(query: str, *, fanout: int = 1, platform_quota: bool = False) -> list[str]:
    """L1/M3 — 쿼리 팬아웃. 방법론적으로는 **할당표집**이다(CH015 M3).

    `platform_quota=True`면 플랫폼을 쿼리에 박아 한 곳에서 몰려 오는 것을 막는다.
    한 플랫폼의 가격대 특성이 시장 분포로 위장되는 것을 방지한다.
    """
    if fanout <= 1 and not platform_quota:
        return [query]
    if platform_quota:
        targets = list(PLATFORMS)[: max(1, fanout)] if fanout > 1 else list(PLATFORMS)
        return [f"{query} {platform}" for platform in targets]
    # 플랫폼 할당 없이 팬아웃만: 중고 표현을 바꿔 검색 표면을 넓힌다.
    suffixes = ["", " 중고", " 구제", " 빈티지"]
    return [f"{query}{suffix}".strip() for suffix in suffixes[:fanout]]


def build_stratum_queries(query: str) -> list[tuple[str, str]]:
    """S2 — 가격대별 층화 검색. top-k 절단이 전역이 아니라 **층 안에서** 일어나게 한다."""
    built: list[tuple[str, str]] = []
    for low, high in PRICE_STRATA:
        label = _stratum_label(low, high)
        band = (
            f"{low // 10_000}만원 이상" if high is None else f"{low // 10_000}~{high // 10_000}만원"
        )
        built.append((label, f"{query} {band}"))
    return built


def build_condition_queries(query: str) -> list[tuple[str, str]]:
    """S3 — 상태축 층화. top-10에 우연히 4등급이 다 나오길 기대하지 않는다."""
    terms = {"S": "미사용 새제품", "A": "A급 상태좋음", "B": "일반 중고 사용감", "C": "하자 있음"}
    return [(grade, f"{query} {term}") for grade, term in terms.items()]


def build_count_queries(query: str) -> list[tuple[str, str]]:
    """S1 — 매물이 아니라 **구간별 개수**를 물어본다.

    출력 A가 필요한 건 목록이 아니라 개수인데 지금은 매물을 긁어와서 센다. 순서를
    뒤집으면 **top-k 절단 편향이 원천적으로 사라진다** — 개수는 자르는 대상이 아니다.
    """
    built: list[tuple[str, str]] = []
    for low, high in PRICE_STRATA:
        built.append((_stratum_label(low, high), query))
    return built


def _stratum_label(low: int, high: int | None) -> str:
    return f"{low}-{high}" if high is not None else f"{low}+"


# --- 프롬프트 (순수) ---------------------------------------------------------


def comps_prompt(query: str, *, variant: str = "strict", max_comps: int = 10) -> str:
    """L2 — 프롬프트 변형.

    `strict`가 현행 프로덕션 문구다. LAB-47 §4.5가 표본 부족(평균 1.7건)의 원인 후보
    첫 번째로 `"가격을 확인할 수 없는 매물은 넣지 마라"`를 지목했으므로, `relaxed`는
    그 보수 문구를 빼고 **최소 건수를 명시**한다.
    """
    sites = "번개장터·중고나라·후르츠패밀리 등 중고 거래 매물을 우선한다."
    schema = (
        '형식: [{"title": "상품명", "price": 숫자(원, 쉼표 없이), "url": "링크", '
        '"platform": "플랫폼명", "listed_at": "YYYY-MM-DD 또는 빈 문자열", '
        '"is_used": true/false}]'
    )
    if variant == "relaxed":
        return (
            f"'{query}' 의 **중고** 거래 시세를 웹에서 검색해라. {sites}\n"
            f"**최소 {max_comps}건 이상** 찾아라. 가격대가 한쪽에 몰리지 않게 "
            "저가·중가·고가 매물을 고루 포함해라.\n"
            f"찾은 매물을 JSON 배열로만 답해라. 설명 문장은 쓰지 마라.\n{schema}\n"
            "가격이 명시된 매물만 넣어라."
        )
    return (
        f"'{query}' 의 **중고** 거래 시세를 웹에서 검색해라. {sites}\n"
        f"찾은 매물을 JSON 배열로만 답해라. 설명 문장은 쓰지 마라.\n{schema}\n"
        "가격을 확인할 수 없는 매물은 넣지 마라. 추측한 가격도 넣지 마라."
    )


def count_prompt(query: str, low: int, high: int | None) -> str:
    """S1 — 개수만 묻는다. 제목·URL·중고 여부를 다 맞힐 필요가 없어 **요구 정밀도가 낮다**."""
    band = f"{low:,}원 이상" if high is None else f"{low:,}원 이상 {high:,}원 미만"
    return (
        f"중고 거래 사이트(번개장터·중고나라·후르츠패밀리)에서 '{query}' 를 검색했을 때 "
        f"판매 가격이 {band}인 매물이 몇 건인지 확인해라.\n"
        "각 사이트의 가격 필터를 적용한 검색 결과 총 개수를 참고해라.\n"
        'JSON 하나로만 답해라: {"count": 숫자, "basis": "근거 사이트/필터"}\n'
        "확인할 수 없으면 count를 -1로 해라. 추측하지 마라."
    )


# --- 파싱·정규화 (순수) ------------------------------------------------------


def extract_json_array(text: str) -> list[dict]:
    """응답에서 첫 JSON 배열을 관대하게 건져낸다. 실패 자체가 지표(파싱 실패율)다."""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [row for row in parsed if isinstance(row, dict)]


def parse_count(text: str) -> tuple[int, str]:
    """S1 응답에서 `(개수, 근거)`. 확인 불가면 개수 -1."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return -1, ""
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return -1, ""
    if not isinstance(parsed, dict):
        return -1, ""
    raw = parsed.get("count")
    count = raw if isinstance(raw, int) and not isinstance(raw, bool) else -1
    return count, str(parsed.get("basis", ""))


def rows_to_items(rows: Sequence[dict], *, query: str = "", level: str = "") -> list[HarvestItem]:
    """LLM이 준 dict 목록을 `HarvestItem`으로. **순위(등장 순서)를 보존한다.**"""
    items: list[HarvestItem] = []
    for index, row in enumerate(rows):
        price = _coerce_price(row.get("price"))
        if price is None or price <= 0:
            continue
        raw_used = row.get("is_used")
        title = _TAG_RE.sub("", str(row.get("title", "")))[:200]
        items.append(
            HarvestItem(
                title=title,
                price=price,
                rank=index,
                url=str(row.get("url", "") or ""),
                listed_at=str(row.get("listed_at", "") or ""),
                is_used=raw_used if isinstance(raw_used, bool) else None,
                platform=str(row.get("platform", "") or ""),
                grade=classify_condition(title),
                query=query,
                level=level,
            )
        )
    return items


def normalize_title(title: str) -> str:
    """중복 판정용 정규화 — 공백·기호를 걷어내고 소문자로."""
    return _NON_WORD_RE.sub("", title.lower())


def dedup_items(items: Sequence[HarvestItem]) -> list[HarvestItem]:
    """URL 우선, 없으면 정규화 제목 + 가격으로 중복 제거. **순위가 앞선 것을 남긴다.**"""
    seen: set[str] = set()
    kept: list[HarvestItem] = []
    for item in sorted(items, key=lambda i: i.rank):
        key = item.url.strip() or f"{normalize_title(item.title)}|{item.price}"
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return kept


def classify_condition(title: str) -> str:
    """M9 — 제목의 상태 키워드로 등급을 **약하게** 라벨링한다.

    ⚠️ 판매자 자기신고 텍스트라 신뢰도가 낮다. **단조성 검증(출력 B)에만 쓰고 가격
    보정에는 쓰지 않는다.** 단조성이 깨지면 결론은 "가격이 틀렸다"가 아니라
    "우리 상태 신호가 잡음이다"이다.

    여러 등급이 걸리면 더 나쁜 쪽을 택한다 — "A급이지만 오염 있음"은 C로 본다.
    """
    lowered = title.lower()
    for grade in ("C", "B", "A", "S"):
        if any(keyword in lowered for keyword in CONDITION_KEYWORDS[grade]):
            return grade
    return ""


def retail_gate_mask(items: Sequence[HarvestItem], retail_price: int | None) -> list[bool]:
    """S6 — 신품 정가 대비 비율이 상식 범위 밖이면 True(탈락).

    리바이스 501을 검색했는데 키즈 제품이 섞이면 가격대가 통째로 어긋나는데, 지금
    프로덕션에는 그걸 걸러낼 기준이 없다. 추가 API 호출이 0건이다 — 정가는 CH004가
    이미 수집한다. M1의 ② 사례 적격성 심사에 해당한다.
    """
    if not retail_price or retail_price <= 0:
        return [False] * len(items)
    return [
        not (RETAIL_RATIO_MIN <= item.price / retail_price <= RETAIL_RATIO_MAX) for item in items
    ]


def _coerce_price(value: object) -> int | None:
    """`45000` / `"45,000원"` / `45000.0` 을 정수 원 단위로."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = re.sub(r"[^0-9]", "", value)
        return int(digits) if digits else None
    return None


# --- 백엔드 ----------------------------------------------------------------


class SearchBackend(ABC):
    """검색 1회 = 텍스트 응답 1개. 파싱은 호출부가 한다."""

    key: str

    @abstractmethod
    def search(self, prompt: str) -> tuple[str, bool]:
        """`(응답 텍스트, 검색 수행 여부)`. 검색을 안 했으면 응답을 신뢰하지 않는다."""
        raise NotImplementedError


class MockSearchBackend(SearchBackend):
    """키 없이 전 경로를 도는 결정적 백엔드.

    **순위와 가격에 일부러 상관을 넣는다**(`rank_bias`). 실제 순위검색이 표준적·인기
    매물을 앞에 놓는 성질을 흉내 낸 것으로, 이걸 top-k로 자르면 분포가 왜곡된다
    (CH015 M9). 축 D의 가격 중립성 지표가 이 왜곡을 잡아내는지 **GMS 호출 없이**
    확인하는 것이 이 백엔드의 존재 이유다. `rank_bias=0.0`이면 중립 대조군이 된다.
    """

    key = "mock"

    def __init__(self, *, pool_size: int = 40, rank_bias: float = 0.7) -> None:
        self._pool_size = pool_size
        self._rank_bias = rank_bias

    def search(self, prompt: str) -> tuple[str, bool]:
        if '"count"' in prompt:
            return json.dumps(self._counts(prompt), ensure_ascii=False), True
        return json.dumps(self._listings(prompt), ensure_ascii=False), True

    def _listings(self, prompt: str) -> list[dict]:
        rng = _seeded_rng(prompt)
        center = 40_000 + rng.randrange(60_000)
        rows: list[dict] = []
        for index in range(self._pool_size):
            # 로그정규 표본 — 가격은 하한 0·우측 꼬리가 길다(CH015 M4).
            price = int(center * math.exp(rng.gauss(0.0, 0.45)))
            rows.append({"price": max(1_000, price), "index": index, "rng": rng.random()})

        # 순위 편향: 중앙값에 가까운(=표준적인) 매물일수록 앞에 온다.
        prices = sorted(row["price"] for row in rows)
        middle = prices[len(prices) // 2]
        for row in rows:
            closeness = abs(math.log(row["price"] / middle))
            row["score"] = self._rank_bias * closeness + (1.0 - self._rank_bias) * row["rng"]
        rows.sort(key=lambda r: r["score"])

        grades = ("미사용 새제품", "A급 상태좋음", "일반 중고 사용감", "하자 있음")
        platforms = list(PLATFORMS)
        return [
            {
                "title": f"목업 매물 {i + 1} {grades[i % len(grades)]}",
                "price": row["price"],
                "url": f"https://example.invalid/mock/{i + 1}",
                "platform": platforms[i % len(platforms)],
                "listed_at": "",
                "is_used": True,
            }
            for i, row in enumerate(rows)
        ]

    def _counts(self, prompt: str) -> dict:
        rng = _seeded_rng(prompt)
        return {"count": 3 + rng.randrange(40), "basis": "mock"}


class GeminiSearchBackend(SearchBackend):
    """GMS 경유 Gemini `google_search` 그라운딩.

    ⛔ **Claude가 실행하지 않는다.** 검색 라운드당 별도 과금이고 팬아웃은 그 배수다
    (`AI/CLAUDE.md` 하드 룰). 사용자가 `--backend gemini`를 명시해야만 생성된다.

    `follow_pause_turn`은 LAB-47 §5가 남긴 "서버툴 반복 한도로 끊긴 응답을 그대로
    파싱한다"는 결함에 대응한다. 원문의 `pause_turn`은 Anthropic 서버툴 개념이고,
    Gemini에서 대응되는 신호는 `finishReason == "MAX_TOKENS"`다 — 끊긴 것이 확인되면
    이어받기 요청을 한 번 더 보낸다.
    """

    key = "gemini"
    _BASE = "https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta"

    def __init__(
        self, model: str, *, timeout: float = 90.0, follow_pause_turn: bool = False
    ) -> None:
        self._model = model
        self._timeout = timeout
        self._follow = follow_pause_turn
        self._api_key = _gms_key()
        if not self._api_key:
            raise RuntimeError("GMS_API_KEY가 없습니다 — AI/.env 또는 환경변수에 넣으세요")

    def search(self, prompt: str) -> tuple[str, bool]:
        text, searched, truncated = self._once(prompt)
        if truncated and self._follow:
            more, _, _ = self._once(f"{prompt}\n\n이어서 계속 답해라. 이미 answer한 것은 빼라.")
            text = f"{text}\n{more}"
        return text, searched

    def _once(self, prompt: str) -> tuple[str, bool, bool]:
        import httpx

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
        }
        response = httpx.post(
            f"{self._BASE}/models/{self._model}:generateContent",
            headers={"x-goog-api-key": self._api_key, "Content-Type": "application/json"},
            json=body,
            timeout=self._timeout,
        )
        if response.status_code != 200:
            raise RuntimeError(f"GMS 응답 오류({response.status_code})")

        candidates = response.json().get("candidates") or []
        if not candidates:
            return "", False, False
        candidate = candidates[0]
        grounding = candidate.get("groundingMetadata") or {}
        searched = bool(grounding.get("groundingChunks") or grounding.get("webSearchQueries"))
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        return text, searched, candidate.get("finishReason") == "MAX_TOKENS"


def _seeded_rng(prompt: str):
    """프롬프트로 결정되는 난수기. `hash()`는 프로세스마다 시드가 달라 쓰지 않는다."""
    import random

    digest = hashlib.sha256(prompt.encode("utf-8")).digest()
    return random.Random(SEED ^ int.from_bytes(digest[:8], "big"))


_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


def _gms_key() -> str:
    """AI/.env 또는 환경변수에서 키를 읽는다(`gms_client.py`에서 필요한 부분만 복사).

    형제 스파이크 폴더를 import하지 않는다 — 한쪽 수정이 다른 쪽을 조용히 깨뜨린다.
    """
    key = os.environ.get("GMS_API_KEY", "").strip()
    if key or not _ENV_PATH.exists():
        return key
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("GMS_API_KEY=") and "=" in line:
            return line.partition("=")[2].strip().strip("\"'")
    return ""


# --- 수집 오케스트레이션 ------------------------------------------------------


def harvest(
    backend: SearchBackend,
    config: HarvestConfig,
    query: str,
    *,
    retail_price: int | None = None,
    brand: str | None = None,
    category: str | None = None,
) -> HarvestOutcome:
    """설정대로 레버를 켜고 한 쿼리를 수집한다.

    호출 횟수가 곧 비용이므로 `search_calls`를 정확히 세어 축 C로 올린다.
    """
    started = time.perf_counter()
    outcome = HarvestOutcome(query=query)

    try:
        if config.count_queries:
            _harvest_counts(backend, query, outcome)
        else:
            _harvest_listings(backend, config, query, outcome, brand=brand, category=category)
    except Exception as exc:  # noqa: BLE001 — 한 쿼리 실패가 스윕 전체를 죽이면 안 된다
        outcome.error = f"{type(exc).__name__}: {exc}"

    if outcome.items:
        _apply_filters(config, outcome, retail_price)
    outcome.latency_ms = round((time.perf_counter() - started) * 1000, 1)
    return outcome


def _harvest_counts(backend: SearchBackend, query: str, outcome: HarvestOutcome) -> None:
    """S1 — 구간별 개수를 물어본다. 매물을 파싱하지 않는다."""
    for label, base in build_count_queries(query):
        low, high = _stratum_bounds(label)
        text, searched = backend.search(count_prompt(base, low, high))
        outcome.search_calls += 1
        if not searched:
            outcome.notes.append(f"{label}: 웹검색 미수행")
            continue
        count, basis = parse_count(text)
        if count < 0:
            outcome.notes.append(f"{label}: 개수 확인 불가")
            continue
        outcome.counts_by_stratum[label] = count
        if basis:
            outcome.notes.append(f"{label}: {basis}")


def _harvest_listings(
    backend: SearchBackend,
    config: HarvestConfig,
    query: str,
    outcome: HarvestOutcome,
    *,
    brand: str | None,
    category: str | None,
) -> None:
    """매물 수집. 특이도 사다리 → 층화/팬아웃 → 적합성 피드백 순으로 레버를 적용한다."""
    ladder = (
        build_specificity_ladder(query, brand, category)
        if config.specificity_ladder
        else [(SPECIFICITY_LEVELS[0], query)]
    )

    collected: list[HarvestItem] = []
    for level, ladder_query in ladder:
        collected.extend(_collect_one_level(backend, config, ladder_query, level, outcome))
        outcome.level = level
        if len(dedup_items(collected)) >= config.max_comps:
            break  # 표본이 찼다 — 더 넓히면 "이 모델"이 아니라 "이 카테고리"가 된다

    # S4 — 피드백은 **단일 쿼리 1회**다. 층화 계획 전체를 재실행하면 비용이 배가 되는데,
    # 여기서 얻으려는 건 "시장 어휘로 다시 물으면 새 매물이 나오는가" 하나뿐이다.
    if config.relevance_feedback and collected:
        extra = _feedback_query(collected)
        if extra:
            collected.extend(_search_once(backend, config, extra, outcome.level, "", outcome))

    outcome.n_raw = len(collected)
    deduped = dedup_items(collected)
    outcome.n_dedup = len(deduped)
    outcome.items = deduped


def _collect_one_level(
    backend: SearchBackend,
    config: HarvestConfig,
    query: str,
    level: str,
    outcome: HarvestOutcome,
) -> list[HarvestItem]:
    """한 특이도 단에서 층화·팬아웃·상태축을 모두 적용해 수집한다."""
    plans: list[tuple[str, str]] = []
    if config.stratified:
        plans.extend(build_stratum_queries(query))
    if config.condition_axis:
        plans.extend(build_condition_queries(query))
    if not plans:
        plans = [
            ("", variant)
            for variant in build_query_variants(
                query, fanout=config.fanout, platform_quota=config.platform_quota
            )
        ]

    gathered: list[HarvestItem] = []
    for tag, planned in plans:
        gathered.extend(_search_once(backend, config, planned, level, tag, outcome))
    return gathered


def _search_once(
    backend: SearchBackend,
    config: HarvestConfig,
    query: str,
    level: str,
    tag: str,
    outcome: HarvestOutcome,
) -> list[HarvestItem]:
    """검색 1회 = 비용 1건. **호출 지점을 여기 하나로 모아 `search_calls`를 정확히 센다.**"""
    text, searched = backend.search(
        comps_prompt(query, variant=config.prompt_variant, max_comps=config.max_comps)
    )
    outcome.search_calls += 1
    if not searched:
        outcome.notes.append(f"{query}: 웹검색 미수행(응답 폐기)")
        return []
    rows = extract_json_array(text)
    if not rows:
        outcome.notes.append(f"{query}: 파싱 실패")
        return []
    items = rows_to_items(rows, query=query, level=level)[: config.max_comps]
    for item in items:
        item.stratum = tag
    return items


def _apply_filters(
    config: HarvestConfig, outcome: HarvestOutcome, retail_price: int | None
) -> None:
    """L5(MAD) + S6(정가 게이트). M1의 ② 사례 적격성 심사에 해당한다."""
    from hist_metrics import outlier_mask

    items = outcome.items
    if config.retail_gate and retail_price:
        dropped = retail_gate_mask(items, retail_price)
        kept = [item for item, drop in zip(items, dropped, strict=True) if not drop]
        if len(kept) != len(items):
            outcome.notes.append(f"정가 게이트로 {len(items) - len(kept)}건 제외")
        items = kept

    if config.mad_filter and len(items) >= 4:
        flags = outlier_mask([item.price for item in items])
        kept = [item for item, bad in zip(items, flags, strict=True) if not bad]
        if len(kept) != len(items):
            outcome.notes.append(f"MAD 이상치 {len(items) - len(kept)}건 제외")
        items = kept

    outcome.items = items


def _feedback_query(items: Sequence[HarvestItem]) -> str:
    """S4 — 1차 결과 제목에서 시장이 실제로 쓰는 어휘를 뽑아 2차 쿼리를 만든다.

    판매자의 표현과 시장의 표기가 다른 것이 니치 검색 실패의 주원인이다
    (LAB-47 §3.2 — `"구제 워크웨어 헤링본 코트"` 네이버 0건).
    """
    counts: dict[str, int] = {}
    for item in items[:10]:
        for token in item.title.split():
            cleaned = normalize_title(token)
            if len(cleaned) < 2:
                continue
            counts[cleaned] = counts.get(cleaned, 0) + 1
    frequent = [
        token for token, count in sorted(counts.items(), key=lambda kv: -kv[1]) if count >= 2
    ]
    return " ".join(frequent[:4])


def _stratum_bounds(label: str) -> tuple[int, int | None]:
    if label.endswith("+"):
        return int(label[:-1]), None
    low, _, high = label.partition("-")
    return int(low), int(high)
