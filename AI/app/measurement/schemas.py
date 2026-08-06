"""의류 실측(cm) 측정 요청/응답 스키마.

**BE 계약이 바뀌면 이 파일만 고친다.** AI는 측정만 하고 상품 등록 확정·저장은 BE가 한다.

`category`는 **Phase 4 PoC에서 실제 사진 + DeepFashion2 공식 랜드마크 정의도로 눈으로 대조
검증한 3종만** 다룬다(`AI/validation/garment-landmark-check/verify_hrnet_landmarks.py`) —
DeepFashion2가 정의하는 나머지 10개 카테고리(긴팔상의/아우터 2종/조끼/슬링/반바지/치마/
반팔원피스/조끼원피스/슬링원피스)는 대조할 실제 사진이 없어 이번 범위에서 뺐다. 카테고리마다
294개 랜드마크 중 다른 구간을 쓰고 포인트 배치도 달라서, 검증 안 된 카테고리를 넣으면 조용히
틀린 값이 나올 위험이 있다 — 실제 사진이 확보되는 대로 하나씩 검증해 추가한다.

`quality/schemas.py`의 `GarmentCategory`와 이름이 겹치지만 값 집합이 달라 재사용하지 않고 이
도메인 전용으로 별도 선언한다(품질검수 쪽 관례와 동일한 이유 — BE 확정 전까지 AI 자체 enum으로
둔다).

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from enum import Enum

from pydantic import BaseModel, Field


class ReferenceObjectType(str, Enum):
    """스케일 기준으로 쓰는 기준 물체.

    v1은 A4 용지만 지원한다(ISO 216, 210x297mm, 비율 1:sqrt(2)). 신용카드(ISO/IEC 7810)도
    후보였지만, 판매자가 실물 카드를 촬영해 서버로 올리는 흐름이라 번호·명의 노출 등 개인정보
    위험이 있어 제외했다 — A4는 그런 위험이 없고 어디서나 구하기 쉽다. enum 값 + 워커 쪽 규격
    상수만 바꾸면 되는 구조라, 다른 기준 물체가 필요해지면 나중에 추가/교체하기 쉽다.
    """

    a4_paper = "A4_PAPER"


class GarmentCategory(str, Enum):
    """랜드마크 세트를 고르는 키 — DeepFashion2 13개 카테고리 중 실사진으로 검증된 3개만.

    각 값은 DeepFashion2의 294개 랜드마크 중 서로 다른 구간(카테고리별 고정 오프셋)을 쓴다.
    구간·포인트 배치 매핑은 `worker/models/garment_measurement/registry.py`의
    `DF2_CATEGORY_RANGES`/`DF2_LANDMARK_MAPPING` 참고.
    """

    short_sleeve_top = "SHORT_SLEEVE_TOP"
    trousers = "TROUSERS"
    long_sleeve_dress = "LONG_SLEEVE_DRESS"


class LandmarkType(str, Enum):
    """이번 기능에 필요한 랜드마크 서브셋.

    DeepFashion2 사전학습 모델(HRNet)은 294종을 예측하지만, cm 환산에 실제로 쓰는 건 이 중
    일부뿐이다 — Phase 4 PoC(`AI/validation/garment-landmark-check/`) 결과 보고 필요하면
    확장한다. 상의류(SHORT_SLEEVE_TOP/LONG_SLEEVE_DRESS)는 위쪽 6종을, 하의(TROUSERS)는
    아래쪽 항목을 쓴다 — 카테고리가 달라도 같은 이름을 재사용할 수 있으면 재사용한다(예:
    SHOULDER_LEFT는 상의든 원피스든 "어깨점"이라는 같은 의미).
    """

    # 상의/원피스 공통
    shoulder_left = "SHOULDER_LEFT"
    shoulder_right = "SHOULDER_RIGHT"
    sleeve_end_left = "SLEEVE_END_LEFT"
    sleeve_end_right = "SLEEVE_END_RIGHT"
    neckline_center = "NECKLINE_CENTER"
    hem_left = "HEM_LEFT"
    hem_center = "HEM_CENTER"
    hem_right = "HEM_RIGHT"

    # 하의(바지) 전용
    waist_left = "WAIST_LEFT"
    waist_center = "WAIST_CENTER"
    waist_right = "WAIST_RIGHT"
    hip_left = "HIP_LEFT"
    hip_right = "HIP_RIGHT"
    crotch = "CROTCH"
    hem_left_outer = "HEM_LEFT_OUTER"
    hem_left_inner = "HEM_LEFT_INNER"
    hem_right_outer = "HEM_RIGHT_OUTER"
    hem_right_inner = "HEM_RIGHT_INNER"


class MeasurementType(str, Enum):
    """산출하는 실측 항목. 가슴단면(pit-to-pit)은 겨드랑이 랜드마크가 아직 없어 범위 밖.

    상의/원피스: SHOULDER_WIDTH/SLEEVE_LENGTH/TOTAL_LENGTH/HEM_WIDTH.
    하의(바지): WAIST_WIDTH/INSEAM_LENGTH/OUTSEAM_LENGTH/LEG_OPENING_WIDTH.
    """

    shoulder_width = "SHOULDER_WIDTH"
    sleeve_length = "SLEEVE_LENGTH"
    total_length = "TOTAL_LENGTH"
    hem_width = "HEM_WIDTH"

    waist_width = "WAIST_WIDTH"
    inseam_length = "INSEAM_LENGTH"
    outseam_length = "OUTSEAM_LENGTH"
    leg_opening_width = "LEG_OPENING_WIDTH"


class RetakeReason(str, Enum):
    """재촬영이 필요한 이유. 실제 재촬영 유도 UX는 FE/BE 몫이고, AI는 이유만 알려준다."""

    reference_not_found = "REFERENCE_NOT_FOUND"
    garment_not_found = "GARMENT_NOT_FOUND"
    garment_not_flat = "GARMENT_NOT_FLAT"
    low_landmark_confidence = "LOW_LANDMARK_CONFIDENCE"


# --- 요청 --------------------------------------------------------------------


class MeasurementScanRequest(BaseModel):
    """BE 상품 등록 흐름이 보내는 실측 요청."""

    product_id: int = Field(ge=1, description="BE가 채번한 상품 id. AI는 에코만 한다")
    image_url: str = Field(
        description="기준 물체(A4 용지) + 평평하게 편 옷을 정면 위(bird's-eye)에서 찍은 사진 1장. "
        "1장 = 1 job — 재촬영은 새 job으로 처리한다"
    )
    category: GarmentCategory = Field(description="랜드마크 세트 선택 키")
    reference_object: ReferenceObjectType = Field(default=ReferenceObjectType.a4_paper)


# --- 접수 응답 -----------------------------------------------------------------


class MeasurementScanEnqueued(BaseModel):
    """`POST /measurement/scans`의 응답. **결과가 아니라 접수증이다.**

    실제 결과는 `GET /ai/jobs/{job_id}`로 폴링한다 — 품질검수·시착과 같은 형식이라 BE가 폴링
    로직을 하나만 유지하면 된다. `result` 필드에 아래 `MeasurementResult` 형태가 담긴다.
    """

    job_id: str = Field(description="게이트웨이가 채번한 job id. 이 값으로 결과를 폴링한다")
    product_id: int = Field(description="요청에서 받은 값을 그대로 에코")


# --- job result 계약 ----------------------------------------------------------
# 아래 모델들은 **AI가 직접 생성하지 않는다.** 워커(worker/models/garment_measurement/)가 만들어
# `JobResult.result`에 dict로 싣는 값의 형태를 문서화·고정하는 용도다. 워커 쪽 사본은
# `worker/models/garment_measurement/contracts.py`이며, 둘이 어긋나지 않는지는
# `AI/test/measurement/test_measurement_contract.py`가 검사한다.


class ModelInfo(BaseModel):
    """단계별로 어떤 백엔드로 처리했는지. 카드검출/원단분할/랜드마크검출이 독립적으로
    스왑 가능해서 하나가 아니라 세 개다."""

    reference_backend: str
    segmentation_backend: str
    landmark_backend: str


class Landmark(BaseModel):
    """랜드마크 1개의 픽셀 좌표. cm 값이 아니라 픽셀 값이다 — 실측 환산은 `measurements`에 있다."""

    type: LandmarkType
    pixel_x: float
    pixel_y: float
    confidence: float = Field(ge=0.0, le=1.0)


class Measurement(BaseModel):
    """실측 항목 1개."""

    type: MeasurementType
    value_cm: float
    confidence: float = Field(ge=0.0, le=1.0, description="이 값을 만든 랜드마크 쌍의 최소 신뢰도")


class MeasurementResult(BaseModel):
    """실측 1건의 결과. `GET /ai/jobs/{job_id}` 응답의 `result` 필드에 담긴다."""

    measurement_id: str
    product_id: int
    model: ModelInfo
    reference_object_found: bool
    pixel_to_cm_ratio: float | None = Field(
        default=None, description="기준 물체를 못 찾았으면 null"
    )
    landmarks: list[Landmark] = Field(default_factory=list)
    measurements: list[Measurement] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    needs_retake: bool = Field(description="이 값이 true면 measurements는 비어있거나 불완전하다")
    retake_reason: RetakeReason | None = None
    notes: list[str] = Field(
        default_factory=list, description="판매자·FE에 보일 주의 문구(모델 한계 안내 등)"
    )
    latency_ms: float = Field(description="워커의 처리 소요 시간(큐 대기 제외)")
