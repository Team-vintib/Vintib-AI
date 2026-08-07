"""품질 검수 백엔드 레지스트리 — SAM3 세그멘터의 유일한 스왑 지점.

설계: `.claude/plans/ai/005-quality-inspection-prototype.md`,
`.claude/plans/ai/CH006-sam3-quality-segmenter.md` (방식 B — 네이티브 경로).

SAM3는 **연속 확률 히트맵이 아니라 인스턴스(마스크+박스+score)를 직접 낸다** — 그래서
`SegmenterConfig`의 임계치 구성이 단일 `defect_threshold`가 아니라 `score_threshold`/
`mask_threshold`/`garment_score_threshold` 세 갈래다.

**`DEFECT_TAXONOMY`/점수 상수는 하자 유형 자체의 성격에 대한 정책이다** — "어느 모델이
찾았는가"가 아니라 그 하자 유형의 감점·신뢰도 취급 기준이므로, 나중에 다른 백엔드가
추가되더라도 이 값들은 동일하게 유지돼야 정책 일관성이 지켜진다.
"""

from typing import TypedDict

from .contracts import ConditionGrade, DefectType, FindingStatus, Severity


class SegmenterConfig(TypedDict):
    """세그멘터 한 종류의 모델 ID + 그 모델 기준으로 잡은 임계치."""

    model_id: str | None
    description: str
    score_threshold: float  # 하자 인스턴스 채택 임계 (SAM3 PCS 의 score)
    mask_threshold: float  # 인스턴스 마스크 이진화 임계(post_process_instance_segmentation)
    confident_threshold: float  # 이 점수 이상이어야 DETECTED. 미만은 SUSPECTED로 강등
    garment_score_threshold: float  # 의류 존재 확인 임계 — 하자 임계보다 훨씬 관대해야 한다
    garment_crop_pad_ratio: float  # 의류 bbox 크롭 여백 비율(경계 하자 잘림 방지)
    garment_overlap_min: float  # 하자 마스크가 의류 마스크에 겹쳐야 하는 최소 비율(사후 안전망)
    suppress_benign: bool  # 양성(주름·그림자·구조적 개구부) 억제 로직 on/off
    benign_containment: float  # 하자가 양성에 이만큼 잠기면 억제 후보로 본다
    dedupe_cross_type: bool  # 서로 다른 defect_type이 같은 실물 부위를 중복 검출했을 때 병합 on/off
    cross_type_iou_min: float  # 이 이상 겹치면 confidence 낮은 쪽을 버린다(findings.py 참고)
    dedupe_same_type: bool  # 같은 defect_type이 "박스 안에 박스"로 겹칠 때 병합 on/off
    same_type_containment_min: float  # 포함 비율(둘 중 큰 쪽)이 이 이상이면 병합(findings.py 참고)
    min_area_ratio: float  # 이 면적 비율 미달 인스턴스는 노이즈로 폐기
    max_defect_area_ratio: float  # 이 비율 초과 인스턴스는 세그멘테이션 실패로 보고 폐기


SEGMENTER_BACKENDS: dict[str, SegmenterConfig] = {
    # 기본 — 목업 시나리오로 결정적 인스턴스를 합성한다. torch 불필요, CI에서 전 경로가
    # 그대로 검증된다(하드코딩 응답이 아니라 실제 합성).
    "mock": {
        "model_id": None,
        "description": "목업 시나리오 기반 결정적 인스턴스 합성(의존성 없음)",
        "score_threshold": 0.30,
        "mask_threshold": 0.5,
        "confident_threshold": 0.55,
        "garment_score_threshold": 0.05,
        "garment_crop_pad_ratio": 0.06,
        "garment_overlap_min": 0.6,
        "suppress_benign": True,
        "benign_containment": 0.6,
        # ⚠️ 라벨링된 검증셋 없이 잡은 값(confident_threshold와 같은 한계) — 스윕 대상.
        # 실측 중복 쌍(scratch.jpg)은 bbox가 1px 이내로 거의 동일해 IoU가 0.9대로 매우
        # 높았다. 0.5보다 여유 있게 0.7로 잡아 "진짜 인접했지만 서로 다른 하자"까지
        # 잘못 합칠 위험을 줄인다.
        "dedupe_cross_type": True,
        "cross_type_iou_min": 0.7,
        # ⚠️ 라벨링된 검증셋 없이 잡은 값 — 스윕 대상. 실측 중복(small_pro.jpg)은 작은
        # STAIN 박스가 큰 STAIN 박스에 97~100% 포함돼 있었다(IoU는 낮아도 포함 비율은
        # 매우 높음) — 그래서 IoU가 아니라 포함 비율을 쓴다(findings.py 참고). 0.8로
        # 여유를 둬서 부분적으로만 겹치는 "진짜 다른 두 하자"까지 합치는 위험을 줄인다.
        "dedupe_same_type": True,
        "same_type_containment_min": 0.8,
        "min_area_ratio": 0.0015,
        "max_defect_area_ratio": 0.35,
    },
    # facebook/sam3 PCS(Promptable Concept Segmentation). AI/validation/QUAL/sam3-condition-check/
    # sam3_qc_test_masking.ipynb 스파이크의 마지막 실험값을 그대로 가져왔다.
    #
    # ⚠️ 이 임계치들은 **라벨링된 검증셋 없이 육안 판단으로 조정된 값**이다(007/CH006 계획의
    # 공통 한계). 특히 confident_threshold는 실측 근거가 없는 신규 값이다 —
    # 검증셋 확보 후 스윕 대상.
    #
    # gated 저장소다(HF 약관 동의 필요) — 배포 환경의 워커 실행 계정이 승인돼 있어야 한다.
    "sam3_pcs": {
        "model_id": "facebook/sam3",
        "description": "SAM3 Promptable Concept Segmentation. torch>=2.4/transformers>=5.0 필요",
        "score_threshold": 0.30,
        "mask_threshold": 0.5,
        "confident_threshold": 0.55,
        "garment_score_threshold": 0.05,
        "garment_crop_pad_ratio": 0.06,
        "garment_overlap_min": 0.6,
        "suppress_benign": True,
        "benign_containment": 0.6,
        # ⚠️ 라벨링된 검증셋 없이 잡은 값(confident_threshold와 같은 한계) — 스윕 대상.
        # 실측 중복 쌍(scratch.jpg)은 bbox가 1px 이내로 거의 동일해 IoU가 0.9대로 매우
        # 높았다. 0.5보다 여유 있게 0.7로 잡아 "진짜 인접했지만 서로 다른 하자"까지
        # 잘못 합칠 위험을 줄인다.
        "dedupe_cross_type": True,
        "cross_type_iou_min": 0.7,
        # ⚠️ 라벨링된 검증셋 없이 잡은 값 — 스윕 대상. 실측 중복(small_pro.jpg)은 작은
        # STAIN 박스가 큰 STAIN 박스에 97~100% 포함돼 있었다(IoU는 낮아도 포함 비율은
        # 매우 높음) — 그래서 IoU가 아니라 포함 비율을 쓴다(findings.py 참고). 0.8로
        # 여유를 둬서 부분적으로만 겹치는 "진짜 다른 두 하자"까지 합치는 위험을 줄인다.
        "dedupe_same_type": True,
        "same_type_containment_min": 0.8,
        "min_area_ratio": 0.0015,
        "max_defect_area_ratio": 0.35,
    },
}
# 기본값. 워커는 `QUALITY_BACKEND` 환경변수로 이 값을 덮어쓴다.
ACTIVE_SEGMENTER = "mock"


class DefectPolicy(TypedDict):
    """하자 유형 하나의 취급 정책. **모델이 못 하는 걸 잘하는 척하지 않기 위한 장치**다."""

    trusted: bool  # False면 확률이 높아도 DETECTED로 노출하지 않는다(항상 SUSPECTED)
    needs_seller_review: bool  # 판매자 확인이 필수인지
    statement_required: bool  # 판매자 소명 입력 대상인지(저장은 BE)
    weight: float  # 감점 가중치 — 미확정(아래 주석 참고)
    evidence: str  # 위 판단의 근거(LAB-12/LAB-46 실측 / 미검증)


# LAB-12·LAB-46 검증 결론을 그대로 코드에 넣는다. 정책은 모델이 아니라 하자 유형에 대한
# 것이다.
#
# ⚠️ `weight`는 **근거 없는 임의값**이다(라벨링된 검증셋이 없다).
DEFECT_TAXONOMY: dict[DefectType, DefectPolicy] = {
    DefectType.stain: {
        "trusted": True,
        "needs_seller_review": False,
        "statement_required": True,
        "weight": 8.0,
        "evidence": "LAB-12 실측 양호 — 오염을 의류 특성 반영해 잘 분리",
    },
    DefectType.dirt_mark: {
        "trusted": True,
        "needs_seller_review": False,
        "statement_required": True,
        "weight": 6.0,
        "evidence": "LAB-12 실측 양호 — stain과 같은 프롬프트 계열",
    },
    DefectType.hole_tear: {
        "trusted": False,
        "needs_seller_review": True,
        "statement_required": True,
        "weight": 15.0,
        "evidence": (
            "LAB-46 실측 — SAM3가 뚜렷한 손상은 잘 잡지만 애매한 손상에서 구조적 개구부"
            "(암홀·넥라인·밑단·소매끝)를 구멍으로 오인하는 비유계 오탐이 반복 확인됨. 항상 SUSPECTED"
        ),
    },
    DefectType.discoloration: {
        "trusted": False,
        "needs_seller_review": True,
        "statement_required": True,
        "weight": 7.0,
        "evidence": "미검증 프롬프트 — SAM3 스파이크 대상이 아니었다",
    },
    DefectType.pilling: {
        "trusted": False,
        "needs_seller_review": True,
        "statement_required": False,
        "weight": 4.0,
        "evidence": "미검증 프롬프트 — 보풀은 경미해 소명 대상에서 제외",
    },
    DefectType.fray: {
        "trusted": False,
        "needs_seller_review": True,
        "statement_required": True,
        "weight": 5.0,
        "evidence": "미검증 프롬프트 — SAM3 스파이크 대상이 아니었다",
    },
}


# --- 점수·등급 (전부 미확정 임의값) -----------------------------------------

SEVERITY_FACTORS: dict[Severity, float] = {
    Severity.minor: 0.5,
    Severity.moderate: 1.0,
    Severity.major: 1.8,
}

# SUSPECTED는 확신이 낮으니 감점도 낮다 — 오탐이 가격을 깎는 걸 막는 완충이다.
STATUS_FACTORS: dict[FindingStatus, float] = {
    FindingStatus.detected: 1.0,
    FindingStatus.suspected: 0.4,
}

# severity 구간 경계: (area_ratio × peak_confidence) 가 [0] 미만이면 MINOR,
# [1] 미만이면 MODERATE, 그 이상이면 MAJOR.
SEVERITY_BOUNDS: tuple[float, float] = (0.004, 0.02)

# 등급 하한. 위에서부터 처음 만족하는 등급을 쓰고, 전부 미달이면 C다.
GRADE_THRESHOLDS: tuple[tuple[float, ConditionGrade], ...] = (
    (90.0, ConditionGrade.s),
    (75.0, ConditionGrade.a),
    (55.0, ConditionGrade.b),
)

# 경미하면서 확신도 낮은 항목까지 소명을 요구하면 판매자 입력 부담만 커진다 — 면제한다.
EXEMPT_MINOR_SUSPECTED_FROM_STATEMENT = True


def segmenter_config(key: str | None = None) -> SegmenterConfig:
    """활성 세그멘터의 설정(모델 ID + 임계치)을 돌려준다."""
    resolved = key or ACTIVE_SEGMENTER
    try:
        return SEGMENTER_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 세그멘터 백엔드입니다: {resolved!r}") from exc


def defect_policy(defect_type: DefectType) -> DefectPolicy:
    """하자 유형의 취급 정책을 돌려준다."""
    try:
        return DEFECT_TAXONOMY[defect_type]
    except KeyError as exc:  # pragma: no cover - enum이라 도달 불가, 방어용
        raise ValueError(f"분류 체계에 없는 하자 유형입니다: {defect_type!r}") from exc
