"""의류 실측 백엔드 레지스트리 — 3단계(기준 물체 검출/원단 분할/랜드마크 검출) 각각의
유일한 스왑 지점.

`quality/registry.py`의 `ACTIVE_SEGMENTER` 패턴을 그대로 따르되, 이 기능은 독립적으로
스왑 가능한 단계가 3개라 레지스트리도 3개다 — 팀원이 예를 들어 "기준 물체 검출은 실제로,
랜드마크 검출은 아직 mock으로" 조합해서 테스트할 수 있어야 한다.

`test/` 코드를 프로덕션에서 import하지 않는 규약에 따라 모델 ID는 여기서 재선언한다
(`app/recommend/pipeline/embed_catalog.py` 선례).

설계: .claude/plans/ai/010-garment-measurement-scan.md
"""

from typing import TypedDict


class BackendConfig(TypedDict):
    model_id: str | None
    description: str


# --- 1단계: 기준 물체(A4 용지) 검출 -----------------------------------------
REFERENCE_BACKENDS: dict[str, BackendConfig] = {
    "mock": {
        "model_id": None,
        "description": "목업 시나리오 기반 결정적 결과(의존성 없음)",
    },
    # Phase 2: OpenCV 컨투어 + 종횡비(1:sqrt(2)) 필터. torch 불필요.
    "opencv_contour": {
        "model_id": None,
        "description": "OpenCV 컨투어 검출 + A4 종횡비 필터. torch 불필요, opencv-python-headless 필요",
    },
}
ACTIVE_REFERENCE_BACKEND = "mock"

# A4(ISO 216) 실제 규격(mm). 기준 물체 검출이 픽셀-실측 비율을 계산할 때 쓴다.
A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0
A4_ASPECT_RATIO = A4_HEIGHT_MM / A4_WIDTH_MM  # sqrt(2) ≈ 1.414

# --- 2단계: 원단 분할(배경 제거) ---------------------------------------------
SEGMENTATION_BACKENDS: dict[str, BackendConfig] = {
    "mock": {
        "model_id": None,
        "description": "목업 시나리오 기반 결정적 결과(의존성 없음)",
    },
    # Phase 3: GrabCut/색상 임계값. torch 불필요, 촬영 배경이 단색 매트/책상이라고 가정.
    "grabcut": {
        "model_id": None,
        "description": "OpenCV GrabCut 배경 제거. torch 불필요, 촬영 배경 통제 전제",
    },
    # 자리만 — GrabCut이 실측으로 부족하다고 판단되면 그때 구현(validation/ 비교 스파이크 선행).
    "yolo_seg": {
        "model_id": None,
        "description": "YOLOv8/v9-seg(DressCode 파인튜닝). 미구현 — GrabCut 정확도 부족 확인 후 착수",
    },
}
ACTIVE_SEGMENTATION_BACKEND = "mock"

# --- 3단계: 의류 랜드마크 검출 ------------------------------------------------
LANDMARK_BACKENDS: dict[str, BackendConfig] = {
    "mock": {
        "model_id": None,
        "description": "목업 시나리오 기반 결정적 결과(의존성 없음)",
    },
    # Phase 4 PoC(AI/validation/garment-landmark-check/) 통과 후에만 활성화.
    "hrnet_deepfashion2": {
        "model_id": "svip-lab/HRNet-for-Fashion-Landmark-Estimation.PyTorch",
        "description": "DeepFashion2 사전학습 HRNet. torch 필요 — validation/ PoC 결과 대기 중, 미구현",
    },
}
ACTIVE_LANDMARK_BACKEND = "mock"


def reference_backend_config(key: str | None = None) -> BackendConfig:
    resolved = key or ACTIVE_REFERENCE_BACKEND
    try:
        return REFERENCE_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 기준 물체 검출 백엔드입니다: {resolved!r}") from exc


def segmentation_backend_config(key: str | None = None) -> BackendConfig:
    resolved = key or ACTIVE_SEGMENTATION_BACKEND
    try:
        return SEGMENTATION_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 원단 분할 백엔드입니다: {resolved!r}") from exc


def landmark_backend_config(key: str | None = None) -> BackendConfig:
    resolved = key or ACTIVE_LANDMARK_BACKEND
    try:
        return LANDMARK_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 랜드마크 검출 백엔드입니다: {resolved!r}") from exc
