"""카테고리·색상 백엔드 레지스트리 — 유일한 모델 스왑 지점.

`worker/models/garment_measurement/registry.py`의 `BackendConfig`/`*_BACKENDS`/
`*_backend_config()` 패턴을 그대로 따른다. 카테고리·색상이 서로 다른 축으로 독립적으로
스왑 가능해야 해서(하나는 실백엔드로, 다른 하나는 mock으로 조합해 테스트할 수 있어야 함)
레지스트리도 2개다.

**`clip_finetuned`가 실백엔드다** — `AI/validation/CLASS/product-info-finetune/`에서
파인튜닝한 CLIP backbone + 선형 헤드 체크포인트를 쓴다(`classifier.py`/`color.py`의
`FineTunedClip*` 클래스). **커밋된 기본값은 여전히 `mock`이다** — 아래 `ACTIVE_*` 주석
참고. 로컬에서 실제로 테스트할 땐 워커 실행 시 환경변수로 켠다. 체크포인트 파일 경로는
`FINE_TUNED_*_CONFIG`(아래) — `app/pricing/registry.py::INTERNAL_CLIP_CONFIG`와 같은 패턴.

설계: `.claude/plans/ai/CH012-~2.MD`
"""

import os
from typing import TypedDict


class BackendConfig(TypedDict):
    model_id: str | None
    description: str


CATEGORY_BACKENDS: dict[str, BackendConfig] = {
    "mock": {
        "model_id": None,
        "description": "정적 결과 기반 목업(의존성 없음)",
    },
    "clip_finetuned": {
        "model_id": None,  # 체크포인트 자체에 model_id가 들어 있어 여기선 안 쓴다
        "description": "파인튜닝된 CLIP backbone + 선형 헤드(체크포인트 기반)",
    },
}
# 커밋된 기본값은 mock이다 — 실백엔드가 기본이면 CI(torch 미설치)에서 전 경로 테스트가
# 불가능해진다(`test/worker/product_classifier/test_product_classifier_registry.py`가 이
# 불변조건을 고정한다). 로컬에서 실제로 테스트하려면 워커 실행 시 환경변수로 켠다:
#   PRODUCT_CLASSIFIER_CATEGORY_BACKEND=clip_finetuned PRODUCT_CLASSIFIER_COLOR_BACKEND=clip_finetuned \
#       python product_classifier_worker_example.py
ACTIVE_CATEGORY_BACKEND = "mock"

COLOR_BACKENDS: dict[str, BackendConfig] = {
    "mock": {
        "model_id": None,
        "description": "정적 결과 기반 목업(의존성 없음)",
    },
    "clip_finetuned": {
        "model_id": None,
        "description": "파인튜닝된 CLIP backbone + 선형 헤드(체크포인트 기반)",
    },
}
# 커밋된 기본값은 mock이다 — 위 카테고리 백엔드와 같은 이유. 워커는
# `PRODUCT_CLASSIFIER_COLOR_BACKEND` 환경변수로 이 값을 덮어쓴다.
ACTIVE_COLOR_BACKEND = "mock"


def category_backend_config(key: str | None = None) -> BackendConfig:
    resolved = key or ACTIVE_CATEGORY_BACKEND
    try:
        return CATEGORY_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 카테고리 백엔드입니다: {resolved!r}") from exc


def color_backend_config(key: str | None = None) -> BackendConfig:
    resolved = key or ACTIVE_COLOR_BACKEND
    try:
        return COLOR_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 색상 백엔드입니다: {resolved!r}") from exc


# --- clip_finetuned 전용 설정 ------------------------------------------------
# `CATEGORY_BACKENDS`/`COLOR_BACKENDS`(`BackendConfig`)에 없는 필드(체크포인트 로컬 경로)라
# 별도 TypedDict로 뺐다 — `app/pricing/registry.py::InternalClipConfig`와 같은 이유.


class FineTunedClipConfig(TypedDict):
    checkpoint_path: str


# 저장소 루트의 /checkpoints/(1번째 줄부터 gitignore 처리됨)에 로컬로 둔다. 커밋된 기본값은
# 그 관례 경로 문자열이다(빈 문자열이 아니다) — 체크포인트 파일 자체가 없으면 빌드/기동은
# 그대로 되고, 실제로 분류를 시도하는 시점에야 ClassifierNotReady/ColorExtractorNotReady로
# 실패한다(파일 경로 자체는 비밀값이 아니라 커밋해도 안전하다). 다른 경로에 두고 싶으면
# 환경변수로 덮어쓴다.
FINE_TUNED_CATEGORY_CONFIG: FineTunedClipConfig = {
    "checkpoint_path": os.getenv(
        "PRODUCT_CLASSIFIER_CATEGORY_CHECKPOINT",
        "checkpoints/product_classifier/category/checkpoint.pt",
    ),
}
FINE_TUNED_COLOR_CONFIG: FineTunedClipConfig = {
    "checkpoint_path": os.getenv(
        "PRODUCT_CLASSIFIER_COLOR_CHECKPOINT", "checkpoints/product_classifier/color/checkpoint.pt"
    ),
}
