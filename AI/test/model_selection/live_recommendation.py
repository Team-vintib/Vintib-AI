"""라이브 방송 추천(방향 B) 규칙기반 실시간 재순위화 프로토타입 — 라이브러리 모듈.

Throwaway/spike code for AI/test/model_selection/ — NOT production code.

실험실 Notion 문서 `[AI] 추천 알고리즘 방향성 및 모델 선정 리서치`(LAB-14) 방향 B의 제안을
코드로 옮긴 모듈이다: "지금 볼 방송/다음 볼 방송을 추천"은 상품 추천과 추천 대상 자체가
다르다(아이템 = 방송, 상품이 아님). 방송이 끝나면 후보가 사라지고(휘발성), 방송 시작
시점엔 상호작용 로그가 전혀 없어 콜드스타트가 상품보다 심하다 — 그래서 LAB-14는 별도
모델을 학습하는 대신 2단계를 제안했다:

1. 배치 후보 생성: 방송 대표 벡터(방송에 걸린 대표 상품들의 임베딩 평균) — 이건 방향 A
   (`recommendation_benchmark.py`)에서 확정할 상품 임베딩을 그대로 재사용하는 것을 전제로
   하며, 이 모듈에서 새로 만들지 않는다.
2. 실시간 재순위화: 동시 시청자 수·최근 좋아요 증가율·팔로우한 판매자 여부를 **규칙 기반
   가중합 스코어링**으로 프로토타입한다 — 이 모듈이 담당하는 부분.

가중치(`DEFAULT_WEIGHTS`)는 임의 초기값이다. 실제 서비스 데이터가 쌓이기 전까진 조정 여지가
크다(LAB-14 "리스크/이슈" 섹션 참고) — 이 모듈은 "이 가중치가 맞다"는 결론을 내리지 않는다.

5단계 추천 아키텍처와의 관계
----------------------------
①데이터 수집 → ②피처스토어/벡터저장소 → ③A/B/C 추천 로직 → ④서빙(ANN+LLM 재정렬) → ⑤노출
화면 중, 이 모듈은 **③-B의 실시간 재순위화 부분만** 다룬다. 실시간 시청자 수 등 스트리밍
인프라 지표를 어떻게 받을지(Kafka/Redis 등, ①/④ 경계)는 BE 스트리밍 설계와 맞물려 있어
스코프 밖이다 — `LiveSessionSignal`을 어디서 채워 넣을지는 호출부가 결정한다.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------
# 1. 실시간 신호 + 가중치
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LiveSessionSignal:
    """방송 하나의 실시간 재순위화 입력 신호.

    Attributes:
        broadcast_id: 방송 식별자.
        viewer_count: 동시 시청자 수.
        recent_like_rate: 최근 N분간 좋아요 증가율. 0~1로 정규화됐다고 가정한다
            (정규화 방식은 호출부/BE 스트리밍 설계에 달려 있어 이 모듈은 관여하지 않는다).
        is_followed_seller: 사용자가 이 방송의 판매자를 팔로우하고 있는지 여부.
    """

    broadcast_id: str
    viewer_count: int
    recent_like_rate: float
    is_followed_seller: bool


# 임의 초기값 — LAB-14 참고. 실데이터로 검증된 값이 아니다.
DEFAULT_WEIGHTS: dict[str, float] = {
    "viewer_count": 0.4,
    "recent_like_rate": 0.4,
    "is_followed_seller": 0.2,
}


# --------------------------------------------------------------------------
# 2. 스코어링 로직
# --------------------------------------------------------------------------
def score_session(
    signal: LiveSessionSignal,
    *,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
    max_viewer_count: int = 1000,
) -> float:
    """방송 하나의 재순위화 점수(0~1 근방)를 계산한다.

    `viewer_count`는 `max_viewer_count`로 min-max 정규화한다 — 방송마다 규모 차이가 커서
    원값을 그대로 가중합에 섞으면 시청자 수가 다른 신호를 압도한다.

    Args:
        signal: 방송 하나의 실시간 신호.
        weights: 신호별 가중치. 합이 1일 필요는 없다(상대 비교용 점수라 스케일은 무의미).
        max_viewer_count: 시청자 수 정규화 기준값.

    Returns:
        가중합 점수. 값 자체보다 방송 간 상대적인 순서가 의미 있다.
    """
    normalized_viewers = min(signal.viewer_count / max_viewer_count, 1.0)
    followed_score = 1.0 if signal.is_followed_seller else 0.0
    return (
        weights["viewer_count"] * normalized_viewers
        + weights["recent_like_rate"] * signal.recent_like_rate
        + weights["is_followed_seller"] * followed_score
    )


def rerank_sessions(
    signals: list[LiveSessionSignal],
    *,
    weights: dict[str, float] = DEFAULT_WEIGHTS,
    max_viewer_count: int = 1000,
) -> list[tuple[LiveSessionSignal, float]]:
    """`signals`를 `score_session()` 점수 내림차순으로 정렬해 반환한다.

    배치 후보 생성(콘텐츠 기반 방송 대표 벡터 유사도)은 이 함수 호출 전에 이미 끝났다고
    가정한다 — 여기 들어오는 `signals`는 이미 "후보로 뽑힌" 방송들이다.
    """
    scored = [(s, score_session(s, weights=weights, max_viewer_count=max_viewer_count)) for s in signals]
    return sorted(scored, key=lambda x: x[1], reverse=True)
