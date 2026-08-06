"""상품 정보 분류(카테고리+색상) 요청/응답 스키마.

**BE 계약이 바뀌면 이 파일만 고친다.** AI는 프리필용 제안만 하고, 실제 상품 등록 확정·저장은
BE가 한다 — 사용자가 폼에서 수정한 값이 최종값이다.

`measurement/schemas.py`와 같은 이유로 단일 `image_url`(presigned URL 1장)을 쓴다 — CH012
설계 초안은 `image_keys`(S3 key 목록, 다중 이미지)를 구상했지만, 이미 구현된 형제 기능
(`quality_check`/`garment_measurement`)이 전부 단일 URL 방식이라 일관성을 위해 그대로
맞췄다. 다중 이미지가 실제로 필요해지면 그때 확장한다.

**성별은 이 응답에 없다.** 사용자가 등록 폼에서 직접 고르기로 확정됐다(2026-08-01) —
`categoryId = f(성별, subcategory)` 조합은 BE/폼 통합 단계(이 스키마 밖)에서 이뤄진다.

설계: `.claude/plans/ai/CH012-~2.MD`
"""

from enum import Enum

from pydantic import BaseModel, Field


class Action(str, Enum):
    """필드별 자동채움/제안/미채움 판정. **임계값 판정은 워커가 한다**(CH012 §5.2) — FE는
    이 값만 보고 분기한다(자동 채움 vs 제안 칩 vs 아무 것도 안 함)."""

    autofill = "autofill"
    suggest = "suggest"
    none = "none"


# --- 요청 --------------------------------------------------------------------


class ProductClassifyRequest(BaseModel):
    """BE 상품 등록 흐름이 보내는 분류 요청."""

    product_id: int = Field(ge=1, description="BE가 채번한 상품 id. AI는 에코만 한다")
    image_url: str = Field(description="대표 상품 사진 1장. 1장 = 1 job")
    taxonomy_version: str = Field(
        default="v1",
        description="`worker/models/product_classifier/taxonomy.py`의 TAXONOMY_VERSION",
    )


# --- 접수 응답 -----------------------------------------------------------------


class ProductClassifyEnqueued(BaseModel):
    """`POST /product-classifier/classify`의 응답. **결과가 아니라 접수증이다.**

    실제 결과는 `GET /ai/jobs/{job_id}`로 폴링한다 — 품질검수·실측과 같은 형식이라 BE가
    폴링 로직을 하나만 유지하면 된다. `result` 필드에 아래 `ProductClassifyResult` 형태가
    담긴다.
    """

    job_id: str = Field(description="게이트웨이가 채번한 job id. 이 값으로 결과를 폴링한다")
    product_id: int = Field(description="요청에서 받은 값을 그대로 에코")


# --- job result 계약 ----------------------------------------------------------
# 아래 모델들은 **AI가 직접 생성하지 않는다.** 워커(worker/models/product_classifier/)가 만들어
# `JobResult.result`에 dict로 싣는 값의 형태를 문서화·고정하는 용도다. 둘이 어긋나지 않는지는
# `AI/test/product_classifier/test_product_classifier_contract.py`가 검사한다.


class FieldCandidate(BaseModel):
    value: str
    score: float = Field(ge=0.0, le=1.0)


class CategoryField(BaseModel):
    """카테고리 필드 1개. `value`는 소분류 코드(예: "CARDIGAN"), `path`는 표시용 한글 라벨."""

    value: str | None
    path: list[str]
    score: float = Field(ge=0.0, le=1.0)
    action: Action
    candidates: list[FieldCandidate] = Field(default_factory=list)


class ColorField(BaseModel):
    """색상 필드 1개(주색상 또는 보조색상). `value`는 팔레트 코드, `hex`는 표시용."""

    value: str | None
    hex: str | None
    score: float = Field(ge=0.0, le=1.0)
    action: Action
    candidates: list[FieldCandidate] = Field(default_factory=list)


class ProductClassifyFields(BaseModel):
    """세 필드 모두 **키는 항상 존재하고 값만 nullable**이다 — 워커가 해당 필드 추론에
    실패하면 키를 빼는 대신 값을 `null`로 채운다(`category`/`color_primary` 둘 다 실패하면
    job 자체가 `failed`이므로 여기까지 오지 않는다, CH012 §6.1)."""

    category: CategoryField | None
    color_primary: ColorField | None
    color_secondary: ColorField | None = None


class ModelInfo(BaseModel):
    """카테고리·색상이 독립적으로 스왑 가능해서(하나는 실백엔드, 하나는 mock 조합도 가능) 두
    필드로 나뉜다. `worker/models/product_classifier/registry.py`의 백엔드 키."""

    category_backend: str
    color_backend: str


class ProductClassifyResult(BaseModel):
    """분류 1건의 결과. `GET /ai/jobs/{job_id}` 응답의 `result` 필드에 담긴다."""

    product_id: int
    fields: ProductClassifyFields
    model: ModelInfo
    taxonomy_version: str
    latency_ms: float = Field(description="워커의 처리 소요 시간(큐 대기 제외)")
