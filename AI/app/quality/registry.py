"""품질 검수 백엔드 레지스트리 — 세그멘테이션 모델의 유일한 스왑 지점.

`ACTIVE_SEGMENTER` 키 하나만 바꾸면 구현이 교체되고, downstream(findings/scoring/overlay)과
API 계약은 그대로 유지된다. `app/chat/registry.py`의 프로덕션 패턴을 그대로 따른다.

**임계치를 백엔드별로 묶어 둔 이유**: 003(라이브 댓글)에서 얻은 교훈이 "임베딩 모델마다
유사도 스케일이 달라 고정 임계치를 모델 무관하게 재사용하면 안 된다"였고, 여기도 같다 —
CLIPSeg의 sigmoid 확률 스케일은 프롬프트·체크포인트·입력 해상도마다 달라진다. 그래서 임계치는
전역 상수가 아니라 `SEGMENTER_BACKENDS[key]` 안에 함께 둔다. 백엔드를 바꾸면 임계치가 따라온다.

`test/` 코드를 프로덕션에서 import하지 않는 규약에 따라 모델 ID는 여기서 재선언한다
(`app/recommend/pipeline/embed_catalog.py` 선례).

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from typing import TypedDict

from app.quality.schemas import DefectType


class SegmenterConfig(TypedDict):
    """세그멘터 한 종류의 모델 ID + 그 모델 기준으로 잡은 임계치."""

    model_id: str | None
    description: str
    mask_size: int  # 확률 마스크 한 변 길이(px). CLIPSeg 디코더 출력이 352×352다
    defect_threshold: float  # 이 확률 이상을 하자 영역으로 이진화
    confident_threshold: float  # 이 확률 이상이어야 DETECTED. 미만은 SUSPECTED로 강등
    clean_margin: float  # p_norm = p_defect - clean_margin * p_clean (0이면 정규화 없음)
    min_area_ratio: float  # 이 면적 비율 미달 blob은 노이즈로 폐기


SEGMENTER_BACKENDS: dict[str, SegmenterConfig] = {
    # 기본 — 목업 시나리오 정의(data/mock_inspections.json)를 읽어 결정적 확률 마스크를
    # numpy로 합성한다. torch 불필요, CI에서 전 경로가 그대로 검증된다.
    #
    # clean_margin 0.8: 프린트 오탐 방어 시나리오(printed_design)가 성립하는 값이다.
    # 프린트 영역은 defect 프롬프트(0.66)와 clean 프롬프트(0.80)가 함께 높게 나오도록
    # 목업이 합성하는데, 정규화하면 0.66 - 0.8*0.80 = 0.02 로 상쇄돼 하자로 잡히지 않는다.
    # 0으로 두면 같은 시나리오가 오탐이 된다 — WinCLIP이 프린트·솔기를 손상으로 오인했던
    # LAB-12 실패 케이스의 회귀 테스트가 이 값에 걸려 있다.
    "mock": {
        "model_id": None,
        "description": "목업 시나리오 기반 결정적 가우시안 확률 마스크 합성(의존성 없음)",
        "mask_size": 352,
        "defect_threshold": 0.35,
        "confident_threshold": 0.60,
        "clean_margin": 0.8,
        "min_area_ratio": 0.0015,
    },
    # LAB-12 채택 모델. 오염은 의류 특성을 반영해 잘 분리하지만 찢어짐·훼손 판단은 약하고,
    # 미세 오염은 탐지되나 뚜렷하지 않다(→ 하자 분류 체계 / confident_threshold로 반영).
    #
    # ⚠️ 아래 임계치는 **CLIPSeg 기준 미검증 임의값**이다. 라벨링된 오염 유/무 검증셋을
    # 확보한 뒤 스윕으로 확정해야 한다(설계 문서 §고도화 경로 4).
    # clean_margin은 0으로 둔다 — 대조 정규화 자체가 CLIPSeg 기준 미검증이라, 정규화 없음이
    # 안전한 기본값이고 스윕 대상이다.
    "clipseg_rd64_refined": {
        "model_id": "CIDAS/clipseg-rd64-refined",
        "description": "CLIPSeg 텍스트 프롬프트 세그멘테이션(LAB-12 채택). torch/transformers 필요",
        "mask_size": 352,
        "defect_threshold": 0.45,
        "confident_threshold": 0.60,
        "clean_margin": 0.0,
        "min_area_ratio": 0.0015,
    },
    # 게이트웨이 큐(POST /ai/quality_check) 경유 — 동기 REST가 한계에 닿을 때 쓸 비동기 전환용
    # 스텁. 실제로는 로컬 GPU 워커가 위 CLIPSeg를 돌리므로 임계치를 그대로 물려받는다.
    "remote_worker": {
        "model_id": None,
        "description": "게이트웨이 Redis 큐 경유 원격 GPU 워커(미구현 스텁)",
        "mask_size": 352,
        "defect_threshold": 0.45,
        "confident_threshold": 0.60,
        "clean_margin": 0.0,
        "min_area_ratio": 0.0015,
    },
}
ACTIVE_SEGMENTER = "mock"  # <- 여기 키만 바꾸면 스왑


class DefectPolicy(TypedDict):
    """하자 유형 하나의 취급 정책. **모델이 못 하는 걸 잘하는 척하지 않기 위한 장치**다."""

    trusted: bool  # False면 확률이 높아도 DETECTED로 노출하지 않는다(항상 SUSPECTED)
    needs_seller_review: bool  # 판매자 확인이 필수인지
    statement_required: bool  # 판매자 소명 입력 대상인지(저장은 BE)
    weight: float  # 감점 가중치 — 미확정(아래 주석 참고)
    evidence: str  # 위 판단의 근거(LAB-12 실측 / 미검증)


# LAB-12 검증 결론을 그대로 코드에 넣는다.
#
# ⚠️ `weight`는 **근거 없는 임의값**이다. 라벨링된 검증셋이 없어 정량 지표가 없는 상태이고,
# 가격책정(에픽 밖)이 `condition_score`를 소비하게 되므로 값 확정은 검증셋 확보 이후의 별도
# 작업이다. 지금은 "찢어짐이 오염보다 아프다" 정도의 순서만 담고 있다.
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
        "evidence": "LAB-12 실측 약함 — 찢어짐·훼손은 잘 판단하지 못함. 항상 SUSPECTED",
    },
    DefectType.discoloration: {
        "trusted": False,
        "needs_seller_review": True,
        "statement_required": True,
        "weight": 7.0,
        "evidence": "미검증 프롬프트 — LAB-12 대상이 아니었다",
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
        "evidence": "미검증 프롬프트 — LAB-12 대상이 아니었다",
    },
}


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
