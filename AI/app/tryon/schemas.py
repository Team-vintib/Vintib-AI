"""가상 시착 추론 파라미터 계약.

**이 도메인에는 아직 `router.py`/`service.py`가 없다.** 시착은 비동기 큐 경유로 갈 기능이라
(`AI/docs/infra-architecture.md` §6 "AI 시착 = 비동기 큐 + 워커"), API 레이어는 비동기 전환
작업에서 함께 만든다. 지금 이 파일만 있는 이유는 아래와 같다.

`AI/tryon_service/`(`-189` 스캐폴딩)를 제거하면서 **대체되지 않은 설계 결정만 건져 왔다.**
그 패키지는 실행이 불가능했고(모든 import가 `from app.*` 로 박혀 있었고 `api/routes/tryon.py`는
스키마 파일이 복붙돼 있어 `router` 자체가 없었다) 채택된 아키텍처와도 충돌했다(Celery + 워커가
Redis에 직접 접속 — 인프라 문서 §2가 금지한다. 워커 노트북이 NAT 뒤라 애초에 불가능하다).

버린 것과 남긴 것:

| 원본 | 처리 |
| --- | --- |
| `TryOnStatus` | 버림 — 게이트웨이 `JobStatus`(queued/processing/success/failed)와 중복 |
| `TryOnRequestAccepted` | 버림 — `POST /ai/{feature}`가 돌려주는 `{job_id}`로 대체됨 |
| `TryOnResult` | 버림 — 게이트웨이 `JobResult`로 대체됨 |
| `MaskFitType`·추론 파라미터·업로드 정책 | **남김** — `-181`/`-182`에서 나온 결정이고 대체된 적이 없다 |

여기 값들은 워커(CatVTON)가 그대로 소비하므로, 비동기 전환 시
`POST /ai/tryon`의 job payload가 된다.
"""

from enum import Enum

from pydantic import BaseModel, Field


class MaskType(str, Enum):
    """마스킹할 의류 부위. CatVTON `AutoMasker`의 `mask_type`과 같은 값이다."""

    upper = "upper"
    lower = "lower"
    overall = "overall"
    inner = "inner"
    outer = "outer"


class MaskFitType(str, Enum):
    """빈티지 의류 핏 옵션. CatVTON `AutoMasker`의 `fit_type`과 같은 값이다."""

    regular = "regular"
    oversized = "oversized"
    cropped = "cropped"


# --- 업로드 검증 정책 (`-182` 이미지 생성 범위 정책) -------------------------
# 게이트웨이가 이미지를 받을 때 이 기준으로 거른다. 워커까지 흘려보낸 뒤 실패하면
# GPU 큐를 헛돌리게 되므로 접수 시점에서 막는다.
ALLOWED_IMAGE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_IMAGE_BYTES = 10 * 1024 * 1024

# CatVTON 입력 해상도. 워커가 원본을 이 크기로 resize/crop 한 뒤 추론한다.
TRYON_WIDTH = 768
TRYON_HEIGHT = 1024


class TryOnOptions(BaseModel):
    """시착 추론 파라미터(원본 `TryOnRequestCreate`).

    실제 이미지 파일은 이 모델에 담기지 않는다 — multipart로 따로 받아 저장하고,
    job payload에는 경로/URL만 싣는다.
    """

    mask_type: MaskType = Field(default=MaskType.upper, description="마스킹할 의류 부위")
    fit_type: MaskFitType = Field(default=MaskFitType.regular, description="핏 옵션")
    num_inference_steps: int = Field(
        default=30, ge=10, le=50, description="디퓨전 스텝 수. 클수록 품질↑ 속도↓"
    )
    guidance_scale: float = Field(
        default=2.5, ge=1.0, le=10.0, description="condition 이미지 반영 강도"
    )
