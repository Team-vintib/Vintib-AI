"""가격 책정 요청/응답 스키마.

**BE 계약이 바뀌면 이 파일만 고친다.**

상태 정보(`condition_score`/`condition_grade`)는 **요청 payload로 받는다.** AI에는 품질검수
결과를 조회할 저장소가 없다 — `app/quality/`는 큐 어댑터뿐이고 결과는 Redis `result:{job_id}`에
TTL 1시간으로만 남는다. 상품 등록 흐름에서 BE가 검수 결과를 들고 있으므로 그대로 실어 보낸다.

`ConditionGrade`·`GarmentCategory`는 `app.quality.schemas`에서 **import한다.** 값이
`InspectionResult`에서 그대로 넘어오는 것이라, 여기서 재정의하면 두 파일이 조용히 어긋난다.

설계: .claude/plans/ai/CH003-pricing-service-prototype.md
"""

from enum import Enum

from pydantic import BaseModel, Field

from app.quality.schemas import ConditionGrade, GarmentCategory

__all__ = [
    "CompItem",
    "CompsStats",
    "ConditionEcho",
    "ConditionGrade",
    "ConfidenceLevel",
    "GarmentCategory",
    "PriceRange",
    "PricingEnqueued",
    "PricingModelInfo",
    "PricingRequest",
    "PricingResult",
    "ReasonCode",
    "RetailSourceKey",
]


class ConfidenceLevel(str, Enum):
    """신뢰도 구간. 경계는 `registry.CONFIDENCE_LEVEL_BOUNDS` — 근거 없는 임의값이다."""

    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"


class ReasonCode(str, Enum):
    """가격을 냈는지, 못 냈다면 왜인지.

    **`PRICED`가 아닌 것들도 job은 `success`다.** 시세 근거를 못 찾은 것은 인프라 실패가
    아니라 정상적인 결과다 — 이걸 실패로 만들면 BE가 재시도 루프를 돌고 그대로 과금된다.
    """

    priced = "PRICED"
    insufficient_comps = "INSUFFICIENT_COMPS"  # comps가 백엔드별 최소 표본 미만
    no_search_performed = "NO_SEARCH_PERFORMED"  # 모델이 검색 없이 답함 → 응답 폐기
    parse_failed = "PARSE_FAILED"  # 검색은 했으나 결과를 구조화하지 못함
    no_image_provided = "NO_IMAGE_PROVIDED"  # internal_clip 활성인데 image_url이 없음


class CompsSourceKey(str, Enum):
    """어느 백엔드로 comps를 모았는지. `registry.COMPS_BACKENDS`의 키와 같다."""

    mock = "mock"
    llm_web_search = "llm_web_search"
    internal_clip = "internal_clip"
    internal = "internal"


class RetailSourceKey(str, Enum):
    """어느 백엔드로 신상품(정가) 가격을 모았는지. `registry.RETAIL_BACKENDS`의 키와 같다.

    `CompsSourceKey`와 별개다 — 중고 시세와 신상품가는 서로 다른 백엔드로 수집되고
    응답에서도 `comps_used`/`retail_items`로 분리 노출된다.
    """

    mock = "mock"
    naver = "naver"


# --- 요청 ------------------------------------------------------------------


class PricingRequest(BaseModel):
    """BE 상품 등록 흐름이 보내는 가격 산정 요청.

    브랜드·모델명 텍스트는 BE가 상품 등록 폼에서 이미 갖고 있다. `image_url`은
    `internal_clip` 백엔드(CLIP 이미지 유사도 기반 내부 RAG, CH020)만 쓴다 —
    mock/llm_web_search는 이 필드를 무시한다.
    """

    product_id: int = Field(ge=1, description="BE가 채번한 상품 id. AI는 에코만 한다")
    product_name: str = Field(
        min_length=1, max_length=200, description="검색 쿼리의 뼈대가 되는 상품명"
    )
    brand: str | None = Field(default=None, max_length=100, description="있으면 쿼리에 덧붙인다")
    category: GarmentCategory | None = Field(
        default=None, description="있으면 쿼리를 좁힌다. 없어도 동작한다"
    )
    condition_score: float = Field(
        ge=0.0, le=100.0, description="품질검수 InspectionResult.condition_score 를 그대로"
    )
    condition_grade: ConditionGrade = Field(
        description="품질검수 InspectionResult.condition_grade 를 그대로. score 결측 시 폴백에도 쓴다"
    )
    retail_price: int | None = Field(
        default=None, ge=0, description="신품 정가(원). 있으면 근거 문장에 할인율만 덧붙인다"
    )
    include_retail: bool = Field(
        default=False,
        description=(
            "신상품(정가) 참고가 조회 여부. 기본은 끔 — 백엔드가 naver로 전환되면 "
            "요청마다 쿼터가 소모되므로, 언제 켤지는 BE/FE와 트리거 기준을 정한 뒤 "
            "이 필드에 그 판단 결과만 담아 보낸다(임시 스위치, 트리거 기준 미정)"
        ),
    )
    image_url: str | None = Field(
        default=None,
        description=(
            "상품 대표 사진 presigned URL(단일). internal_clip 백엔드가 활성일 때만 쓰인다 — "
            "없으면 internal_clip은 reason_code=NO_IMAGE_PROVIDED로 빈 결과를 낸다"
        ),
    )


# --- 접수 응답 --------------------------------------------------------------


class PricingEnqueued(BaseModel):
    """`POST /pricing/estimates`의 응답. **결과가 아니라 접수증이다.**

    결과는 `GET /ai/jobs/{job_id}`로 폴링한다 — 품질검수·시착과 같은 형식이라 BE가 폴링
    로직을 하나만 유지하면 된다. `result` 필드에 아래 `PricingResult` 형태가 담긴다.
    """

    job_id: str = Field(description="이 값으로 결과를 폴링한다")
    product_id: int = Field(description="요청에서 받은 값을 그대로 에코")


# --- job result 계약 --------------------------------------------------------


class CompItem(BaseModel):
    """비교 매물 1건. 어느 백엔드에서 왔든 같은 모양으로 정규화된다."""

    title: str = Field(max_length=200)
    price: int = Field(ge=0, description="원 단위")
    source: str = Field(description="수집 백엔드 키")
    url: str = Field(default="", description="원본 매물 링크. 백엔드가 못 주면 빈 문자열")
    listed_at: str = Field(default="", description="등록·판매일(YYYY-MM-DD). 없으면 빈 문자열")
    is_used: bool | None = Field(
        default=None,
        description="중고 여부. **판별 불가면 None이다** — False로 뭉개면 신품과 구별이 사라진다",
    )


class PriceRange(BaseModel):
    """제안 가격대. 단일 숫자가 아니라 range로 내는 것이 업계 표준(LAB-21)."""

    min: int = Field(ge=0)
    mid: int = Field(ge=0)
    max: int = Field(ge=0)


class CompsStats(BaseModel):
    """근거의 두께를 숫자로 노출한다. LAB-15의 "설득력을 결정하는 지표"에 대응."""

    count: int = Field(ge=0, description="가격 산정에 실제로 쓴 매물 수")
    median: int = Field(ge=0)
    p25: int = Field(ge=0)
    p75: int = Field(ge=0)
    used_ratio: float = Field(
        ge=0.0, le=1.0, description="중고로 확인된 비율. 판별 불가(None)는 분자에서 뺀다"
    )


class ConditionEcho(BaseModel):
    """받은 상태 값과 그것이 가격에 반영된 계수. 근거 표시용."""

    score: float = Field(ge=0.0, le=100.0)
    grade: ConditionGrade
    coefficient: float = Field(description="중앙값에 곱한 상태 계수")


class PricingModelInfo(BaseModel):
    """어떤 백엔드로 산정했는지. 스왑 결과를 응답으로 확인하는 용도."""

    comps_source: CompsSourceKey
    comps_model_id: str | None
    pricer: str
    retail_source: RetailSourceKey


class PricingResult(BaseModel):
    """가격 산정 1건의 결과. `GET /ai/jobs/{job_id}` 응답의 `result` 필드에 담긴다."""

    estimate_id: str
    product_id: int
    priced: bool = Field(
        description="가격을 냈는지. **false여도 job은 success다** — ReasonCode 참고"
    )
    reason_code: ReasonCode
    price_range: PriceRange | None = Field(default=None, description="priced=false면 null")
    currency: str = Field(default="KRW")
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    rationale: list[str] = Field(
        default_factory=list, description="판매자에게 보여줄 한국어 근거 문장"
    )
    comps_used: list[CompItem] = Field(default_factory=list)
    comps_stats: CompsStats | None = Field(default=None)
    condition: ConditionEcho
    model: PricingModelInfo
    notes: list[str] = Field(
        default_factory=list, description="한계·주의 문구(검색 미호출, 파싱 실패 등)"
    )
    retail_items: list[CompItem] = Field(
        default_factory=list,
        description="신상품(정가) 참고용 매물. comps_used와 별개 — 가격 산정에는 아직 반영되지 않는다",
    )
    retail_notes: list[str] = Field(
        default_factory=list, description="신상품가 조회 한계·주의 문구. notes(comps용)와 분리"
    )
    latency_ms: float = Field(description="comps 수집 + 산정 소요 시간")
