"""카테고리·색상 백엔드 레지스트리 — 유일한 모델 스왑 지점.

`worker/models/garment_measurement/registry.py`의 `BackendConfig`/`*_BACKENDS`/
`*_backend_config()` 패턴을 그대로 따른다. 카테고리·색상이 서로 다른 축으로 독립적으로
스왑 가능해야 해서(하나는 실백엔드로, 다른 하나는 mock으로 조합해 테스트할 수 있어야 함)
레지스트리도 2개다.

**둘 다 현재 `mock`만 등록돼 있다.** 카테고리(CLIP 파인튜닝 예정)·색상(방식 미정) 실백엔드는
`AI/validation/CLASS/product-info-check/`에서 검증이 끝난 뒤에 여기 추가한다(2026-08-02
판단 — 검증 안 된 걸 프로덕션에 먼저 심지 않는다).

설계: `.claude/plans/ai/CH012-~2.MD`
"""

from typing import TypedDict


class BackendConfig(TypedDict):
    model_id: str | None
    description: str


CATEGORY_BACKENDS: dict[str, BackendConfig] = {
    "mock": {
        "model_id": None,
        "description": "정적 결과 기반 목업(의존성 없음)",
    },
    # 검증 후 여기 추가 예정. 후보: CLIP 파인튜닝
    # (AI/validation/CLASS/product-info-check/REPORT.md 참고 — zero-shot 단계는
    # en_clip_style 프롬프트로 top1 0.71, 파인튜닝은 아직 미검증).
}
# 워커는 `PRODUCT_CLASSIFIER_CATEGORY_BACKEND` 환경변수로 이 값을 덮어쓴다.
ACTIVE_CATEGORY_BACKEND = "mock"

COLOR_BACKENDS: dict[str, BackendConfig] = {
    "mock": {
        "model_id": None,
        "description": "정적 결과 기반 목업(의존성 없음)",
    },
    # 검증 후 여기 추가 예정. 원래 설계안(k-means+팔레트 스냅)은 검증 스파이크에서 0%로
    # 실패했다(REPORT.md §V3) — "CLIP 임베딩+분류 헤드" 등 대체 방식을 검증 중이며,
    # 아직 어떤 방식으로 갈지 결정되지 않았다.
}
# 워커는 `PRODUCT_CLASSIFIER_COLOR_BACKEND` 환경변수로 이 값을 덮어쓴다.
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
