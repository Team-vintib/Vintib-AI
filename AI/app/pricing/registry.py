"""가격 책정 백엔드 레지스트리 — 구현 교체의 유일한 스왑 지점.

`ACTIVE_*` 키 하나만 바꾸면 comps 수집기와 가격 산정기가 교체된다. `validation/` 코드를
프로덕션에서 import하지 않는 규약에 따라 모델 ID는 여기서 재선언한다(`app/chat/registry.py` 선례).

**임계치를 백엔드별로 묶어 둔 이유**: 백엔드마다 comps 수확량이 다르다. mock은 항상 5건을
만들지만 LLM 웹검색은 실측 평균 1.7건이었다(CH002 V2). 최소 표본을 전역 상수 3으로 잡으면
LLM 백엔드가 **항상** `INSUFFICIENT_COMPS`가 된다. 그래서 `min_comps_for_pricing`은
`COMPS_BACKENDS[key]` 안에 있다 — 백엔드를 갈아끼우면 임계치가 따라온다.

⚠️ **가격 계수·범위 폭·신뢰도 경계는 전부 근거 없는 임의값이다.** 실판매가 정답셋(30~50건)으로
캘리브레이션하기 전까지 이 값들로 산출한 가격의 정확도를 주장할 수 없다. LAB-32가
`condition_score` 가중치에 대해 남긴 것과 같은 성격의 부채다.

설계: .claude/plans/ai/CH003-pricing-service-prototype.md
"""

from typing import TypedDict

from app.pricing.schemas import ConditionGrade, ConfidenceLevel


class CompsSourceConfig(TypedDict):
    """comps 백엔드 하나의 모델 ID + 그 백엔드 기준으로 잡은 임계치."""

    model_id: str | None
    tool_types: tuple[str, ...]  # 웹검색 서버툴 규격. 앞에서부터 시도하고 400이면 폴백
    timeout_seconds: float
    max_comps: int  # 이보다 많이 오면 잘라낸다(토큰·응답 크기 방어)
    min_comps_for_pricing: int  # 이 미만이면 가격을 내지 않는다


COMPS_BACKENDS: dict[str, CompsSourceConfig] = {
    # 기본 — 상품명 해시 기반 결정적 매물 5건. 네트워크·키 불필요, CI에서 그대로 검증된다.
    "mock": {
        "model_id": None,
        "tool_types": (),
        "timeout_seconds": 0.0,
        "max_comps": 5,
        "min_comps_for_pricing": 3,
    },
    # CH002 V1에서 실동작이 확인된 조합. 평균 comps 1.7건이라 최소 표본을 1로 둔다 —
    # 3으로 잡으면 사실상 모든 요청이 INSUFFICIENT_COMPS가 된다.
    #
    # ⚠️ 상위 모델(sonnet 등)을 여기 추가하지 말 것. 같은 질문에도 검색 라운드를 훨씬 많이
    #    돌아 비용이 급증한다(CH002 V1 실측: haiku 20건 vs sonnet 81건). 바꿔야 하면
    #    사용자가 직접 model_id를 교체한다 — AI/CLAUDE.md 하드 룰.
    "llm_web_search": {
        "model_id": "claude-haiku-4-5-20251001",
        # haiku는 web_search_20260209(dynamic filtering)를 지원하지 않아 400이 난다.
        # 이 폴백이 없으면 "웹검색 미지원"으로 오판한다(CH002 V1 실측).
        "tool_types": ("web_search_20260209", "web_search_20250305"),
        "timeout_seconds": 90.0,
        "max_comps": 10,
        "min_comps_for_pricing": 1,
    },
}
ACTIVE_COMPS_SOURCE = "llm_web_search"  # <- 여기 키만 바꾸면 스왑
# llm_web_search / mock


class RetailSourceConfig(TypedDict):
    """신상품(정가) 백엔드 하나의 표시 정보 + 수확 상한."""

    display_name: str
    max_items: int  # "몇 가지"만 받으면 되므로 comps보다 작게 잡는다
    timeout_seconds: float


# CH002 V2 실측: 네이버 쇼핑 API는 comps 평균 18건·지연 177ms로 빠르지만 중고 비율이 5%뿐이라
# 중고 시세로는 못 쓴다 — 대신 신상품(정가) 조회용으로 재배치한다. `RetailSource`는 실패해도
# 절대 예외를 던지지 않는다(comps.py의 `CompsUnavailable`과 계약이 다르다) — 부가 정보일 뿐
# 가격 산정의 필수 입력이 아니기 때문이다.
RETAIL_BACKENDS: dict[str, RetailSourceConfig] = {
    "mock": {
        "display_name": "mock",
        "max_items": 3,
        "timeout_seconds": 0.0,
    },
    "naver": {
        "display_name": "네이버 쇼핑",
        "max_items": 5,
        "timeout_seconds": 5.0,
    },
}
ACTIVE_RETAIL_SOURCE = "mock"  # <- 여기 키만 바꾸면 스왑. naver 전환은 사용자만(하드 룰)
# naver / mock

PRICER_BACKENDS: dict[str, str | None] = {
    "rule_baseline": None,  # 기본 — 중앙값 × 상태계수. 의존성 없음
    "llm": None,  # 미구현 스텁. 규칙 baseline을 이기는지 먼저 증명해야 한다(CH002 V4)
}
ACTIVE_PRICER = "rule_baseline"  # <- 여기 키만 바꾸면 스왑

# --- 상태 계수 -------------------------------------------------------------
# comps 자체가 **상태 불명의 중고**라 중앙값은 이미 "평균적 중고"의 가격이다. 그래서
# score/100을 그대로 곱하면 안 된다 — 70점짜리 평범한 물건이 30% 할인돼 버린다.
# 기준점(REFERENCE)에서 얼마나 벗어났는지로 보정한다.
REFERENCE_CONDITION_SCORE = 70.0
CONDITION_SENSITIVITY = 0.008  # 1점당 0.8%
CONDITION_COEF_MIN = 0.60
CONDITION_COEF_MAX = 1.25

# score가 결측이거나 범위를 벗어났을 때의 폴백. 등급만으로 계수를 정한다.
GRADE_COEFFICIENTS: dict[ConditionGrade, float] = {
    ConditionGrade.s: 1.15,
    ConditionGrade.a: 1.05,
    ConditionGrade.b: 0.92,
    ConditionGrade.c: 0.75,
}

# --- 범위·신뢰도 -----------------------------------------------------------
# range 폭은 신뢰도가 낮을수록 넓어진다. 상한을 두는 이유: 폭을 무한정 넓히면 "실제가가
# 범위 안에 들어갔는가(hit rate)"는 100%가 되지만 아무 쓸모가 없다(CH002 §V4).
BASE_RANGE_WIDTH = 0.12  # 신뢰도 1.0일 때 ±12%
MAX_RANGE_WIDTH = 0.35  # 신뢰도 0.0일 때 ±35%
PRICE_ROUNDING_UNIT = 1000  # 원 단위 반올림

CONFIDENCE_SATURATION_COMPS = 5  # 이 개수면 표본 항목 만점
CONFIDENCE_LEVEL_BOUNDS: dict[ConfidenceLevel, float] = {
    ConfidenceLevel.high: 0.70,
    ConfidenceLevel.medium: 0.40,
}

# --- 실행 제어 -------------------------------------------------------------
# 컨테이너 안에서 백그라운드 스레드로 도는데, 그 스레드풀을 게이트웨이 엔드포인트
# (`GET /ai/jobs/{id}` 폴링 포함)와 공유한다. 상한이 없으면 가격 job이 풀을 채워서
# 폴링 자체가 굶는다. 초과 요청은 대기시키지 않고 접수 단계에서 503으로 끊는다.
MAX_CONCURRENT_JOBS = 2

WORKER_ID = "ai-inprocess"  # 노트북 워커가 아니라 컨테이너가 처리했음을 결과에 남긴다


def comps_config(key: str | None = None) -> CompsSourceConfig:
    """활성 comps 백엔드의 설정(모델 ID + 임계치)을 돌려준다."""
    resolved = key or ACTIVE_COMPS_SOURCE
    try:
        return COMPS_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 comps 백엔드입니다: {resolved!r}") from exc


def retail_config(key: str | None = None) -> RetailSourceConfig:
    """활성 신상품가 백엔드의 설정(표시 정보 + 수확 상한)을 돌려준다."""
    resolved = key or ACTIVE_RETAIL_SOURCE
    try:
        return RETAIL_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 신상품가 백엔드입니다: {resolved!r}") from exc
