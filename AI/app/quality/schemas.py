"""품질 검수 요청/응답 스키마.

**BE 계약이 바뀌면 이 파일만 고친다.** AI는 판정과 산출물 생성만 하고, 판매자 소명 저장·상품
등록 확정은 BE가 한다 — 그래서 finding에는 소명 본문이 아니라 `key`와 `statement_required`
플래그만 있다(설계 문서 "서비스 흐름과 AI/BE 경계" 참고).

`category`/`base_color`는 BE 상품 등록 스키마가 어떤 이름으로 갖고 있는지 아직 확정되지 않아
**AI 자체 enum**으로 둔다. BE 확정 시 이 파일에서만 매핑한다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from enum import Enum

from pydantic import BaseModel, Field


class GarmentCategory(str, Enum):
    """프롬프트 세트와 3×3 부위 라벨을 고르는 키.

    설계 문서의 부위 라벨 표가 정의한 두 그룹(상의·아웃터 / 하의)에만 대응한다 — 원피스처럼
    라벨 세트가 없는 카테고리는 이번 범위 밖이다.
    """

    top_knit = "TOP_KNIT"
    top_shirt = "TOP_SHIRT"
    outer_jacket = "OUTER_JACKET"
    outer_coat = "OUTER_COAT"
    bottom_pants = "BOTTOM_PANTS"
    bottom_skirt = "BOTTOM_SKIRT"


class BaseColor(str, Enum):
    """의류 기본색. 프롬프트 문구 보정에 쓴다(밝은 옷/어두운 옷/프린트)."""

    light = "LIGHT"
    dark = "DARK"
    patterned = "PATTERNED"


class DefectType(str, Enum):
    """하자 유형. 신뢰도(검증 여부)는 `registry.DEFECT_TAXONOMY`가 갖는다."""

    stain = "STAIN"
    dirt_mark = "DIRT_MARK"
    hole_tear = "HOLE_TEAR"
    discoloration = "DISCOLORATION"
    pilling = "PILLING"
    fray = "FRAY"


class FindingStatus(str, Enum):
    """하자 항목의 확신 수준.

    `SUSPECTED`는 "AI가 의심하는 부분 — 확인해 주세요"로 표현되며 감점 가중치가 낮다.
    LAB-12에서 약점이 확인된 유형은 확률이 높아도 `SUSPECTED`로만 노출된다.
    """

    detected = "DETECTED"
    suspected = "SUSPECTED"


class Severity(str, Enum):
    """`area_ratio × peak_confidence` 3구간. 경계는 `registry.SEVERITY_BOUNDS`."""

    minor = "MINOR"
    moderate = "MODERATE"
    major = "MAJOR"


class ConditionGrade(str, Enum):
    """컨디션 등급. 경계는 `registry.GRADE_THRESHOLDS` — 근거 없는 임의값이라 미확정이다."""

    s = "S"
    a = "A"
    b = "B"
    c = "C"


class GarmentSection(str, Enum):
    """3×3 그리드 부위 라벨. 상의/하의가 `HEM_LEFT`/`HEM_RIGHT`를 공유한다."""

    # 상의·아웃터
    shoulder_left = "SHOULDER_LEFT"
    collar = "COLLAR"
    shoulder_right = "SHOULDER_RIGHT"
    sleeve_left = "SLEEVE_LEFT"
    chest_center = "CHEST_CENTER"
    sleeve_right = "SLEEVE_RIGHT"
    hem_left = "HEM_LEFT"
    hem_center = "HEM_CENTER"
    hem_right = "HEM_RIGHT"
    # 하의 (HEM_LEFT / HEM_RIGHT 는 위와 공유)
    waist_left = "WAIST_LEFT"
    waist_center = "WAIST_CENTER"
    waist_right = "WAIST_RIGHT"
    thigh_left = "THIGH_LEFT"
    crotch = "CROTCH"
    thigh_right = "THIGH_RIGHT"
    shin_center = "SHIN_CENTER"


# --- 요청 ------------------------------------------------------------------


class InspectionRequest(BaseModel):
    """BE 상품 등록 흐름이 보내는 동기 검수 요청."""

    product_id: int = Field(
        ge=1,
        description="BE가 채번한 상품 id. AI는 에코만 한다(목업 백엔드에서는 시나리오 선택 키)",
    )
    image_urls: list[str] = Field(
        min_length=1,
        max_length=8,
        description="검수 대상 상품 이미지 URL. 순서가 곧 image_index",
    )
    category: GarmentCategory = Field(description="프롬프트 세트·부위 라벨 선택 키")
    base_color: BaseColor = Field(
        default=BaseColor.light, description="기본색. 프롬프트 문구를 보정한다"
    )
    include_attention_maps: bool = Field(
        default=False,
        description=(
            "히트맵 오버레이 PNG 생성 여부. 기본 off — 상품 등록 흐름에서 쓰지 않을 수 있고, "
            "켜면 이미지·하자유형마다 PNG를 만들어 응답이 느려진다"
        ),
    )
    include_descriptions: bool = Field(
        default=False,
        description=(
            "하자 한 줄 설명(sVLM, finding.description) 생성 여부. 기본 off — finding당 "
            "수 초가 걸려 이미지당 수십 초~수 분까지 늘어날 수 있다(CH011). 켜지 않으면 "
            "description은 계속 None"
        ),
    )


# --- 접수 응답 --------------------------------------------------------------


class InspectionEnqueued(BaseModel):
    """`POST /quality/inspections`의 응답. **결과가 아니라 접수증이다.**

    실제 결과는 `GET /ai/jobs/{job_id}`로 폴링한다 — 시착과 같은 형식이라 BE가 폴링 로직을
    하나만 유지하면 된다. `result` 필드에 아래 `InspectionResult` 형태가 담긴다.
    """

    job_id: str = Field(description="게이트웨이가 채번한 job id. 이 값으로 결과를 폴링한다")
    product_id: int = Field(description="요청에서 받은 값을 그대로 에코")


# --- job result 계약 --------------------------------------------------------
# 아래 모델들은 **AI가 직접 생성하지 않는다.** 워커(worker/models/sam3/)가 만들어
# `JobResult.result`에 dict로 싣는 값의 형태를 문서화·고정하는 용도다. 워커 쪽 사본은
# `worker/models/sam3/contracts.py`이며, 둘이 어긋나지 않는지는
# `AI/test/quality/test_quality_contract.py`가 검사한다.


class ModelInfo(BaseModel):
    """어떤 백엔드로 판정했는지. 모델 스왑을 응답으로 확인하는 용도."""

    backend: str
    model_id: str | None
    prompt_set: str


class Finding(BaseModel):
    """하자 항목 1건 = 마스크에서 뽑은 연결요소 1개."""

    key: str = Field(description="안정 키. BE가 판매자 소명을 이 키에 매핑한다")
    defect_type: DefectType
    status: FindingStatus
    image_index: int = Field(ge=0, description="요청 image_urls의 인덱스")
    section_no: int = Field(ge=1, le=9, description="3×3 부위 넘버링(행 우선)")
    section: GarmentSection
    confidence: float = Field(ge=0.0, le=1.0, description="정규화 마스크의 blob 내 최대 확률")
    area_ratio: float = Field(ge=0.0, le=1.0, description="blob 면적 / 이미지 면적")
    bbox: tuple[float, float, float, float] = Field(
        description="정규화 좌표 (x1, y1, x2, y2). FE가 원본 해상도에 매핑한다"
    )
    severity: Severity
    matched_prompt: str = Field(description="이 항목을 잡아낸 프롬프트")
    statement_required: bool = Field(description="판매자 소명 입력 대상인지(저장은 BE)")
    needs_seller_review: bool = Field(description="모델 신뢰도가 낮아 판매자 확인이 필수인지")
    no: int | None = Field(
        default=None,
        description=(
            "같은 image_index 안에서의 표시 번호(1부터). annotated_images의 bbox 숫자와 "
            "일치한다 — FE가 이 값으로 이미지 위 숫자와 리스트 항목을 매칭한다. 이 필드를 "
            "아직 채우지 않는 백엔드는 None"
        ),
    )
    label: str | None = Field(
        default=None, description="하자 유형의 한글 태그(오염/얼룩/구멍·찢어짐 등). 미채움 시 None"
    )
    description: str | None = Field(
        default=None,
        description=(
            "하자에 대한 sVLM 생성 한 줄 설명(CH011). 요청의 include_descriptions가 "
            "True이고 status가 DETECTED일 때만 채워진다 — 그 외(옵트인 안 함, SUSPECTED, "
            "개별 생성 실패)에는 None"
        ),
    )


class SectionScore(BaseModel):
    """부위별 하자 확률. LAB-30의 "각 부위 넘버링 / 확률값" 요구에 대응한다.

    이미지 1장당 9개씩 나온다(CH020) — `image_urls`가 여러 장이면 총 개수는
    `9 × len(image_urls)`다. 이미지 간 확률을 합치지 않고 완전히 독립적으로 낸다."""

    image_index: int = Field(ge=0, description="요청 image_urls의 인덱스")
    section_no: int = Field(ge=1, le=9)
    section: GarmentSection
    score: float = Field(ge=0.0, le=1.0)


class ImageSummary(BaseModel):
    """이미지 1장에 대한 한 줄 요약(CH020).

    `InspectionResult.summary`는 전체 이미지를 합산한 요약이고, 이건 이미지별 상세다 —
    앞/뒤 캐러셀에서 넘길 때마다 설명이 그 이미지 것으로 바뀌어야 하는 요구
    (`docs/requests/BE/019-product-quality-multi-image.md`)에 대응한다. 하자가 없는
    이미지도 빠짐없이 포함된다("확인된 하자가 없습니다")."""

    image_index: int = Field(ge=0)
    summary: str


class AttentionMap(BaseModel):
    """서버가 생성한 히트맵 오버레이 PNG의 공개 URL."""

    image_index: int = Field(ge=0)
    defect_type: DefectType
    url: str


class AnnotatedImage(BaseModel):
    """숫자만 넘버링된 bbox 오버레이 PNG의 공개 URL. 이미지 1장당 최대 1개(하자가 있을 때만).

    `attention_maps`(하자유형별 연속 히트맵, 여러 장)와는 다른 산출물이다 — 이건 원본 위에
    박스 + 숫자만 그린 이미지 1장이고, 숫자는 같은 image_index의 `Finding.no`와 일치한다.
    """

    image_index: int = Field(ge=0)
    url: str


class InspectionResult(BaseModel):
    """검수 1건의 결과. `GET /ai/jobs/{job_id}` 응답의 `result` 필드에 담긴다."""

    inspection_id: str
    product_id: int
    model: ModelInfo
    condition_score: float = Field(ge=0.0, le=100.0)
    condition_grade: ConditionGrade
    summary: str = Field(
        description="전체 이미지를 합산한 한 줄 요약. 이미지별 요약은 image_summaries"
    )
    image_summaries: list[ImageSummary] = Field(
        default_factory=list,
        description="이미지별 한 줄 요약(CH020). image_urls 개수만큼, 순서대로 채워진다",
    )
    findings: list[Finding]
    section_scores: list[SectionScore]
    attention_maps: list[AttentionMap]
    annotated_images: list[AnnotatedImage] = Field(
        default_factory=list,
        description="숫자 넘버링 bbox 이미지(이미지당 최대 1장, 하자 있는 이미지만). 미구현 백엔드는 빈 리스트",
    )
    notes: list[str] = Field(
        default_factory=list, description="판매자·FE에 보일 주의 문구(모델 한계 안내 등)"
    )
    latency_ms: float = Field(description="워커의 추론+후처리 소요 시간(큐 대기 제외)")


# 활성 설정 노출용 스키마(`GET /quality/prompt-sets`)는 제거했다 — 프롬프트·임계치·하자 분류
# 체계가 전부 워커(`worker/models/sam3/registry.py`)로 옮겨가서 게이트웨이가 그 값을 알지
# 못한다. 설정을 확인하려면 워커 쪽 파일을 보거나, 필요해지면 워커가 job result에 실어 보내는
# 방식으로 되살린다(`ModelInfo`가 이미 백엔드·프롬프트 세트를 담고 있다).
