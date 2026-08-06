"""가격 분포 스파이크의 중앙 레지스트리 — 모델·레버·라운드·쿼리셋.

`model_selection/model_registry.py` 선례를 따른다. 키 하나만 바꾸면 스왑되는 패턴이고,
실행 라운드(R0~R3)도 여기서 조립한다.

⚠️ **고가 모델을 후보에 넣지 않는다**(`AI/CLAUDE.md` 하드 룰). 모델 등급이 오르면 검색
라운드가 같이 깊어져 비용이 곱으로 늘어난다(LAB-47 §4.3 — haiku 20건 vs sonnet 81건).
바꿔야 하면 사용자가 직접 `--model`로 지정한다.

설계: .claude/plans/ai/CH015-comps-price-distribution.md
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

__all__ = [
    "ACTIVE_BACKEND",
    "CONDITION_KEYWORDS",
    "DEFAULT_MODELS",
    "HarvestConfig",
    "PLATFORMS",
    "PRICE_STRATA",
    "QUERIES",
    "ROUNDS",
    "SEED",
    "round_config",
]

SEED = 20260803  # 재현성 — mock 백엔드와 부트스트랩이 공유한다

# --- 백엔드 ----------------------------------------------------------------

# 기본은 mock이다. 실백엔드 전환은 사용자만 한다(`--backend gemini`).
ACTIVE_BACKEND = "mock"

DEFAULT_MODELS: dict[str, str] = {
    # LAB-47 V1에서 grounding이 확인된 최저 등급 모델. 상위 모델을 여기 넣지 말 것.
    "gemini": "gemini-3.5-flash",
    "mock": "",
}

# --- 쿼리셋 ----------------------------------------------------------------

# LAB-21의 "카테고리별 정확도 차등"을 재현하려면 둘을 섞어야 한다. 앞 5건이 식별 쉬운
# 유명 라인, 뒤 5건이 니치·모델명 불명확 케이스다(LAB-47이 쓴 것과 같은 구성).
QUERIES: list[str] = [
    "리바이스 501 빅E 데님",
    "나이키 빈티지 스우시 후드 집업",
    "폴로 랄프로렌 옥스포드 셔츠 빈티지",
    "칼하트 디트로이트 자켓 빈티지",
    "스톤아일랜드 니트 가디건",
    "90년대 무지 워시드 데님 자켓",
    "빈티지 체크 플란넬 셔츠 오버핏",
    "구제 코듀로이 와이드 팬츠",
    "빈티지 카레지 니트 베스트",
    "구제 워크웨어 헤링본 코트",
]

NICHE_QUERY_OFFSET = 5  # 이 인덱스부터 니치. 축 A를 유명/니치로 나눠 집계할 때 쓴다

# M3 — 표집틀을 균형 있게 덮기 위한 플랫폼 할당 대상.
PLATFORMS: tuple[str, ...] = ("번개장터", "중고나라", "후르츠패밀리")

# S2 — 가격대 층. top-k 절단이 전역이 아니라 층 안에서 일어나게 한다.
# 상한 None은 "그 이상 전부".
PRICE_STRATA: tuple[tuple[int, int | None], ...] = (
    (0, 30_000),
    (30_000, 60_000),
    (60_000, 100_000),
    (100_000, 200_000),
    (200_000, None),
)

# S3 / M9 — 상태 약라벨링 키워드. 매물 제목에서 등급을 추정한다.
# **자기신고 텍스트라 신뢰도가 낮다** — 단조성 검증용이지 가격 보정용이 아니다.
CONDITION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "S": ("미사용", "새제품", "새상품", "택포", "택있음", "미착용"),
    "A": ("s급", "에스급", "a급", "상태좋음", "깨끗", "거의새것"),
    "B": ("b급", "사용감", "일반중고", "무난"),
    "C": ("c급", "하자", "오염", "수선", "찢어짐", "얼룩", "탈색"),
}

# S6 — 신품 정가 대비 중고가의 상식 범위. 벗어나면 다른 상품이 섞인 것으로 본다.
# ⚠️ 근거 없는 임의값이다. 실측으로 교정 대상.
RETAIL_RATIO_MIN = 0.05
RETAIL_RATIO_MAX = 1.50

# 축 A 판정 기준 — 히스토그램을 그려도 되는 최소 표본(CH015 "진짜 병목" 표).
HIST_MIN_SAMPLES = 12


# --- 레버 (L1~L5 / S1~S6) ---------------------------------------------------


@dataclass(frozen=True)
class HarvestConfig:
    """한 라운드의 수집 설정. **레버를 전부 플래그로 노출**해 조합을 비교한다."""

    name: str
    note: str = ""

    # L1 / M3 — 쿼리 팬아웃(= 할당표집). 1이면 현행과 같다.
    fanout: int = 1
    platform_quota: bool = False

    # L2 — 프롬프트 변형. "strict"가 현행(보수적 문구 포함).
    prompt_variant: str = "strict"

    # L3 — 서버툴 반복 한도로 끊긴 응답 이어받기(LAB-47 §5의 알려진 결함).
    follow_pause_turn: bool = False

    # L4 — 수확 상한. 현행 프로덕션은 10이고 히스토그램 목표(12)보다 낮다.
    max_comps: int = 10

    # L5 / S6 — 오탐 필터.
    mad_filter: bool = False
    retail_gate: bool = False

    # S1 — 매물이 아니라 구간별 **개수**를 물어본다. top-k 절단 편향이 사라진다.
    count_queries: bool = False

    # S2 — 가격대별 층화 검색.
    stratified: bool = False

    # S3 — 상태축 층화(출력 B 전용).
    condition_axis: bool = False

    # S4 — 1차 결과 어휘로 2차 쿼리를 만든다(유사 적합성 피드백).
    relevance_feedback: bool = False

    # S5 — 쿼리 특이도 사다리. 멈춘 단을 `비교 수준`으로 노출한다.
    specificity_ladder: bool = False

    # 재현성 축(B)용 반복 횟수. 캐시를 우회해야 의미가 있다(S7 주의).
    repeats: int = 1

    levers: tuple[str, ...] = field(default_factory=tuple)


# CH015 "실행 순서" — 격자 탐색을 하지 않는다. 목표에 닿는 라운드에서 멈춘다.
ROUNDS: dict[str, HarvestConfig] = {
    "R0": HarvestConfig(
        name="R0",
        note="베이스라인 — 현행 프로덕션과 같은 설정",
        levers=(),
    ),
    "R1": HarvestConfig(
        name="R1",
        note="비용 증가 없는 레버만 — pause_turn 이어받기 + 상한 상향 + MAD/정가 필터",
        follow_pause_turn=True,
        max_comps=30,
        mad_filter=True,
        retail_gate=True,
        levers=("L3", "L4", "L5", "S6"),
    ),
    "R2": HarvestConfig(
        name="R2",
        note="프롬프트 완화 + 특이도 사다리 — 비용 소폭",
        follow_pause_turn=True,
        max_comps=30,
        mad_filter=True,
        retail_gate=True,
        prompt_variant="relaxed",
        specificity_ladder=True,
        relevance_feedback=True,
        levers=("L2", "L3", "L4", "L5", "S4", "S5", "S6"),
    ),
    # ⚠️ 출력 A와 B는 표본 요구가 다르므로 **라운드를 나눈다**(CH015 M9). 한 라운드에서
    #    가격 층화와 상태축 층화를 동시에 켜면 비용이 곱해지고, 어느 축 때문에 n이 늘었는지
    #    구분도 안 된다.
    "R3": HarvestConfig(
        name="R3",
        note="출력 A — 팬아웃 + 가격 층화. 쿼리당 검색 약 6회(층 5 + 피드백 1)",
        follow_pause_turn=True,
        max_comps=30,
        mad_filter=True,
        retail_gate=True,
        prompt_variant="relaxed",
        specificity_ladder=True,
        relevance_feedback=True,
        fanout=2,
        platform_quota=True,
        stratified=True,
        levers=("L1", "L2", "L3", "L4", "L5", "M3", "S2", "S4", "S5", "S6"),
    ),
    "B": HarvestConfig(
        name="B",
        note="출력 B — 상태축 층화. 등급별 표본을 보장해 단조성(Spearman)을 판정한다",
        follow_pause_turn=True,
        max_comps=30,
        mad_filter=True,
        retail_gate=True,
        prompt_variant="relaxed",
        condition_axis=True,
        levers=("L2", "L3", "L4", "L5", "S3", "S6"),
    ),
    # S1은 라운드가 아니라 **선결 확인**이다. 검색이 플랫폼의 "총 N개"를 읽어 오는지
    # 부터 확인해야 하고, 되면 출력 A의 설계가 통째로 바뀐다(CH015 우선순위 표).
    "S1": HarvestConfig(
        name="S1",
        note="카운트 쿼리 실현 가능성 — 매물 대신 구간별 개수를 물어본다",
        count_queries=True,
        levers=("S1",),
    ),
}


def round_config(key: str, *, repeats: int = 1, max_comps: int | None = None) -> HarvestConfig:
    """라운드 설정을 꺼내고 실행 시점 오버라이드를 얹는다."""
    try:
        config = ROUNDS[key]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 라운드입니다: {key!r} (가능: {sorted(ROUNDS)})") from exc
    changes: dict[str, object] = {"repeats": max(1, repeats)}
    if max_comps is not None:
        changes["max_comps"] = max_comps
    return replace(config, **changes)
