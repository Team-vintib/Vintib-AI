"""필드별 autofill/suggest/none 임계값 — 자리만 잡아둔다.

CH012 §5.2: "카테고리 score(수백 라벨 softmax)와 색상 score(k-means 거리)는 스케일이 완전히
다르므로 공통 임계값 하나로 가를 수 없다." `AI/validation/CLASS/product-info-check/
REPORT.md` §V4도 같은 결론이다 — 소분류 30종 기준 실측 권장값(약 0.74, N=7이라 저신뢰
플래그 붙음)이 나왔지만, **실백엔드가 아직 없어 이 값을 쓸 데가 없다.** 실백엔드가 정해지고
정답셋이 40~60건 이상으로 확장된 뒤 여기 실제 값을 채운다.

지금은 구조만 잡아둔다 — mock 백엔드는 항상 `action="none"`을 반환하므로 이 값이 실제로
쓰이지 않는다(`classifier.py`/`color.py`의 `MockCategoryClassifier`/`MockColorExtractor`
참고).
"""

from typing import TypedDict

from .contracts import Action


class FieldThresholds(TypedDict):
    autofill_min_score: float  # 이 값 이상이면 자동 채움
    suggest_min_score: float  # 이 값 이상~autofill 미만이면 제안 칩만


# TODO(검증 후 채울 것): 실백엔드가 정해지면 REPORT.md의 V4 캘리브레이션 결과(정답셋 확장 후
# 재실측)로 아래 값을 채운다. 지금은 임의의 보수적 placeholder다 — mock 백엔드는 이 값을
# 참조하지 않는다(항상 action="none").
CATEGORY_THRESHOLDS: FieldThresholds = {"autofill_min_score": 0.9, "suggest_min_score": 0.5}
COLOR_THRESHOLDS: FieldThresholds = {"autofill_min_score": 0.9, "suggest_min_score": 0.5}


def resolve_action(score: float, thresholds: FieldThresholds) -> Action:
    if score >= thresholds["autofill_min_score"]:
        return "autofill"
    if score >= thresholds["suggest_min_score"]:
        return "suggest"
    return "none"
