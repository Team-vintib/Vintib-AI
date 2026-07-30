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

from .contracts import GarmentCategory, LandmarkType


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

# DeepFashion2는 294개 랜드마크를 13개 카테고리에 나눠 정의한다(카테고리마다 포인트 개수·배치가
# 다름) — 모델은 항상 294개를 전부 예측하지만, 실제로 의미 있는 건 해당 카테고리 구간뿐이다.
# 순서는 DeepFashion2 공식 category_id 순(1~13)과 같다: short_sleeve_top(25), long_sleeve_top(33),
# short_sleeve_outwear(31), long_sleeve_outwear(39), vest(15), sling(15), shorts(10), trousers(14),
# skirt(8), short_sleeve_dress(29), long_sleeve_dress(37), vest_dress(19), sling_dress(19).
# 실사진으로 검증한 3개만 채운다 — 나머지는 검증 전까지 오프셋을 몰라도 되니 안 둔다.
_DF2_CATEGORY_SIZES = [25, 33, 31, 39, 15, 15, 10, 14, 8, 29, 37, 19, 19]


def _df2_offset(category_index_1based: int) -> int:
    """category_id(1~13) 앞에 오는 카테고리들의 랜드마크 개수 합 — 이 카테고리 구간의 시작 인덱스."""
    return sum(_DF2_CATEGORY_SIZES[: category_index_1based - 1])


# (DF2 category_id, 이 카테고리의 랜드마크 개수). `AI/validation/garment-landmark-check/`에서
# 실제 사진 + `verify_hrnet_landmarks.py`로 인덱스를 찍어 눈으로 확인한 값이다.
DF2_CATEGORY_RANGES: dict[GarmentCategory, tuple[int, int]] = {
    GarmentCategory.short_sleeve_top: (_df2_offset(1), _DF2_CATEGORY_SIZES[0]),
    GarmentCategory.trousers: (_df2_offset(8), _DF2_CATEGORY_SIZES[7]),
    GarmentCategory.long_sleeve_dress: (_df2_offset(11), _DF2_CATEGORY_SIZES[10]),
}

# 카테고리별 "이 로컬 인덱스(DeepFashion2 표기, 1-based)가 어떤 LandmarkType인지".
# 값이 없는 로컬 인덱스(예: short_sleeve_top의 10~13, 19~22)는 겨드랑이 부근에 몰린 세부
# 포인트라 지금 쓰는 4가지 실측 항목엔 안 쓴다 — 필요해지면(가슴단면 등) 여기 추가한다.
DF2_LANDMARK_MAPPING: dict[GarmentCategory, dict[int, LandmarkType]] = {
    GarmentCategory.short_sleeve_top: {
        4: LandmarkType.neckline_center,
        7: LandmarkType.shoulder_left,
        25: LandmarkType.shoulder_right,
        9: LandmarkType.sleeve_end_left,
        23: LandmarkType.sleeve_end_right,
        15: LandmarkType.hem_left,
        16: LandmarkType.hem_center,
        17: LandmarkType.hem_right,
    },
    GarmentCategory.trousers: {
        1: LandmarkType.waist_left,
        2: LandmarkType.waist_center,
        3: LandmarkType.waist_right,
        4: LandmarkType.hip_left,
        14: LandmarkType.hip_right,
        9: LandmarkType.crotch,
        6: LandmarkType.hem_left_outer,
        7: LandmarkType.hem_left_inner,
        11: LandmarkType.hem_right_inner,
        12: LandmarkType.hem_right_outer,
    },
    GarmentCategory.long_sleeve_dress: {
        4: LandmarkType.neckline_center,
        7: LandmarkType.shoulder_left,
        37: LandmarkType.shoulder_right,
        11: LandmarkType.sleeve_end_left,  # 손목 쪽 커프 바깥 모서리
        32: LandmarkType.sleeve_end_right,
        21: LandmarkType.hem_left,
        22: LandmarkType.hem_center,
        23: LandmarkType.hem_right,
    },
}


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
