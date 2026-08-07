"""필드별 autofill/suggest/none 임계값.

CH012 §5.2: "카테고리 score(수백 라벨 softmax)와 색상 score(k-means 거리)는 스케일이 완전히
다르므로 공통 임계값 하나로 가를 수 없다." — 그래서 필드별로 분리돼 있다. mock 백엔드는
항상 `action="none"`을 반환하므로 이 값을 안 쓴다(`classifier.py`/`color.py`의
`MockCategoryClassifier`/`MockColorExtractor` 참고) — 아래는 `clip_finetuned` 실백엔드용.

**둘 다 여전히 근거가 얕은 값이다** — `report_fashion_compare.json`(N=17, 2026-08-03,
현재 35종 taxonomy 기준)이 유일한 실측 근거이고, 그 리포트 자체가 N<30이면 하드 라인으로
읽지 말라고 명시한다. 실판매 정답셋이 쌓이면 재조정 대상이다(다른 도메인의 임의 계수들과
같은 성격의 부채).

- **카테고리**: score-정답 분리가 양호했다(zero-shot 기준 ECE≈0.05). suggest 임계를 그
  리포트의 권장값(0.743)보다 낮춰 0.55로 잡아 더 자주 제안이 뜨게 하고, autofill은 보수적으로
  0.9 유지.
- **색상**: `fashion_clip` 체크포인트가 primary accuracy 0.882(N=17)로 준수하지만 ECE가
  0.209로 카테고리보다 훨씬 나쁘다 — 권장 임계값(0.977)에서도 커버리지가 17건 중 4건뿐이라
  신뢰도 점수 자체가 카테고리만큼 믿을 만하지 않다. **autofill을 카테고리보다 보수적으로
  0.95로 올려 위험을 줄이고**, suggest는 0.5로 낮게 잡아 대부분 "제안"으로만 노출되게 한다.
"""

from typing import TypedDict

from .contracts import Action


class FieldThresholds(TypedDict):
    autofill_min_score: float  # 이 값 이상이면 자동 채움
    suggest_min_score: float  # 이 값 이상~autofill 미만이면 제안 칩만


CATEGORY_THRESHOLDS: FieldThresholds = {"autofill_min_score": 0.9, "suggest_min_score": 0.55}
COLOR_THRESHOLDS: FieldThresholds = {"autofill_min_score": 0.95, "suggest_min_score": 0.5}


def resolve_action(score: float, thresholds: FieldThresholds) -> Action:
    if score >= thresholds["autofill_min_score"]:
        return "autofill"
    if score >= thresholds["suggest_min_score"]:
        return "suggest"
    return "none"
