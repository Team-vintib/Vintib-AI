"""파츠 프롬프트 — "옷 전체 크롭 후 하자 탐지" 대신 "파츠별로 조각낸 뒤 하자 탐지"를
테스트하기 위한 SAM3 파츠 프롬프트 세트.

프로덕션(`worker/models/sam3/prompts.py`)의 3×3 섹션 라벨은 **마스크 무게중심이 속한
그리드 칸**으로 정하는 기하학적 방식이다 — 실제 옷 구조(소매가 어디서 시작하는지 등)와는
무관하다. 이 스파이크는 그 대신 SAM3에게 파츠 자체를 프롬프트로 물어서 **실제 파츠
경계 마스크**를 얻고, 그 마스크로 잘라낸 좁은 영역 안에서 하자를 탐지하면 더 정확해지는지
확인한다(CH006 고도화 경로 #6 "타일 추론"과 같은 동기 — 입력이 좁을수록 미세 하자가
덜 뭉개질 것이라는 가설).

SAM3는 논문상 **짧은 명사구**로 학습돼 있어(`qc_shared.py` 참고) 파츠 이름도 최대한
짧게 유지한다. 아직 실측 전이라 이 어휘가 실제로 잘 잡히는지는 미검증이다 — 첫 시도다.
"""

# 카테고리 그룹. 프로덕션 GarmentSection이 상의/아웃터와 하의 두 그룹으로 나뉘는 것과
# 같은 구분이다(HEM은 두 그룹이 공유).
PART_PROMPTS_BY_GROUP: dict[str, dict[str, str]] = {
    "top": {
        "COLLAR": "a collar",
        "SLEEVE": "a sleeve",
        "TORSO": "a torso",
        "HEM": "a hem",
        "POCKET": "a pocket",
    },
    "bottom": {
        "WAISTBAND": "a waistband",
        "LEG": "a pant leg",
        "HEM": "a hem",
        "POCKET": "a pocket",
    },
}

_BOTTOM_CATEGORIES = {"BOTTOM_PANTS", "BOTTOM_SKIRT"}


def part_group_for(category: str) -> str:
    """카테고리 문자열(예: "TOP_KNIT") -> "top"/"bottom". 미등록 카테고리는 "top"으로 취급한다."""
    return "bottom" if category in _BOTTOM_CATEGORIES else "top"


# 파츠 탐지 점수 임계치. 하자 탐지(qc_shared.BACKEND_THRESHOLDS["sam3"]["score"]=0.30)보다
# 관대하게 잡는다 — 의류 존재 확인(garment_score=0.05)과 하자 정밀 판정(0.30)의 중간 성격:
# 파츠를 못 찾으면 그 파츠 안의 하자를 통째로 놓치므로, 존재 확인 쪽에 가깝게 관대해야 한다.
# ⚠️ 근거 없는 초기값 — qc_shared.BACKEND_THRESHOLDS와 같은 성격의 미확정 상수다.
PART_SCORE_THRESHOLD = 0.15

# 파츠 bbox를 넓힐 여유 비율. 프로덕션 GARMENT_CROP_PAD_RATIO와 같은 역할 — 파츠 경계
# 바로 위(소매 끝 실밥 등)의 하자가 크롭 경계에 잘리지 않게 한다.
PART_CROP_PAD_RATIO = 0.08
