"""Chat agent — 의도 분류 게이트 + 라우팅 스파이크 구현.

Throwaway/spike code for AI/test/model_selection/ — NOT production code.

Notion "라이브 댓글 관리 — 분산 Agent 아키텍처 설계" 문서에서 설계한 파이프라인
(도배 탐지 -> 의도 분류 게이트 -> 악성 댓글 관리 / 반복질문 RAG 응답)의 최소 구현.
downstream agent(악성 처리, RAG 응답)는 아직 스텁이며, 실제 서비스 연동은
S15P11A108-192(라이브 댓글 관리 서비스 구현)에서 진행한다.

실행: `python chat_agent.py` — model_registry.ACTIVE_INTENT의 두 전략을 모두
같은 샘플에 돌려서 라우팅 결과와 지연시간을 비교한다(모델 선정용 데모).
"""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Literal

from loaders import (
    CausalLMBundle,
    ClassifierBundle,
    generate_chat,
    load_causal_lm,
    load_sequence_classifier,
)
from model_registry import (
    ACTIVE_CLASSIFIER,
    ACTIVE_GENERATIVE,
    ACTIVE_INTENT,
    CLASSIFIER_MODELS,
    GENERATIVE_MODELS,
)

Intent = Literal["정상", "악성", "반복질문"]


# ---------------------------------------------------------------------------
# 1. 도배(스팸) 탐지 — 규칙 기반, 모델 불필요 (설계 문서 "모델 후보" 표 참고)
# ---------------------------------------------------------------------------


@dataclass
class SpamDetector:
    """사용자별 rate-limit + 근접 중복 매칭. 인메모리 슬라이딩 윈도우 — 스파이크용.
    프로덕션에서는 Redis로 교체해야 한다(다중 워커 간 상태 공유 필요, -188 참고)."""

    window_seconds: float = 10.0
    max_messages_in_window: int = 4
    similarity_threshold: float = 0.85
    _history: dict[str, deque[tuple[float, str]]] = field(
        default_factory=lambda: defaultdict(deque)
    )

    def is_spam(self, user_id: str, comment: str, *, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        history = self._history[user_id]

        while history and now - history[0][0] > self.window_seconds:
            history.popleft()

        near_duplicate_count = sum(
            1
            for _, prev in history
            if SequenceMatcher(None, prev, comment).ratio() >= self.similarity_threshold
        )
        spam = len(history) >= self.max_messages_in_window or near_duplicate_count >= 2

        history.append((now, comment))
        return spam


# ---------------------------------------------------------------------------
# 2. 의도 분류 게이트 — 정상 / 악성 / 반복질문 (전략 스왑은 model_registry.ACTIVE_INTENT)
# ---------------------------------------------------------------------------

_FAQ_HINT_PATTERN = re.compile(
    r"[?？]|얼마|언제|어떻게|가능한가요|되나요|되요|되나|맞나요|재고|사이즈"
)


def _rule_based_faq_hint(comment: str) -> bool:
    """질문형 문장인지 가늠하는 값싼 휴리스틱. 정교한 판정은 아니고 후보 필터용."""
    return bool(_FAQ_HINT_PATTERN.search(comment))


def classify_intent_kor_unsmile_plus_rule(
    comment: str, classifier_bundle: ClassifierBundle
) -> Intent:
    """kor_unsmile로 악성 여부 먼저 판정, 아니면 규칙 기반으로 반복질문 후보 탐지."""
    import torch

    with torch.no_grad():
        inputs = classifier_bundle.tokenizer(comment, truncation=True, return_tensors="pt").to(
            classifier_bundle.device
        )
        logits = classifier_bundle.model(**inputs).logits
    scores = torch.sigmoid(logits)[0]
    id2label = classifier_bundle.model.config.id2label
    abuse_score = max(float(scores[i]) for i, label in id2label.items() if label != "clean")

    if abuse_score >= 0.5:
        return "악성"
    if _rule_based_faq_hint(comment):
        return "반복질문"
    return "정상"


_INTENT_PROMPT = (
    "다음은 라이브 커머스 방송 채팅 댓글이다. 아래 세 범주 중 하나로만 답하라:\n"
    "정상 / 악성 / 반복질문\n"
    "- 악성: 욕설, 혐오표현, 판매자에 대한 인신공격\n"
    "- 반복질문: 가격, 재고, 배송, 사이즈 등 상품/판매 관련 질문\n"
    "- 정상: 그 외 모든 댓글\n"
    "범주명 하나만 출력하라.\n\n댓글: {comment}"
)


def classify_intent_kanana_zero_shot(comment: str, gen_bundle: CausalLMBundle) -> Intent:
    """kanana-1.5-instruct 프롬프트로 3-way 분류. 별도 로딩/파인튜닝 불필요."""
    raw = generate_chat(gen_bundle, _INTENT_PROMPT.format(comment=comment), max_new_tokens=10)
    if "악성" in raw:
        return "악성"
    if "반복질문" in raw:
        return "반복질문"
    return "정상"


_INTENT_STRATEGY_FUNCS = {
    "kor_unsmile_plus_rule": classify_intent_kor_unsmile_plus_rule,
    "kanana_zero_shot": classify_intent_kanana_zero_shot,
}


def classify_intent(
    comment: str,
    *,
    classifier_bundle: ClassifierBundle | None = None,
    gen_bundle: CausalLMBundle | None = None,
    strategy: str = ACTIVE_INTENT,
) -> Intent:
    """model_registry.ACTIVE_INTENT로 전략을 스왑. 두 함수 시그니처가 달라(분류기 vs
    생성모델 번들) 여기서 필요한 번들만 골라 넘긴다."""
    fn = _INTENT_STRATEGY_FUNCS[strategy]
    if strategy == "kor_unsmile_plus_rule":
        if classifier_bundle is None:
            raise ValueError("kor_unsmile_plus_rule 전략은 classifier_bundle이 필요합니다")
        return fn(comment, classifier_bundle)
    if gen_bundle is None:
        raise ValueError("kanana_zero_shot 전략은 gen_bundle이 필요합니다")
    return fn(comment, gen_bundle)


# ---------------------------------------------------------------------------
# 3. 라우팅 — 설계 문서 다이어그램의 downstream agent 자리(현재는 스텁)
# ---------------------------------------------------------------------------


@dataclass
class RoutingDecision:
    comment: str
    intent: Intent | Literal["스팸"]
    action: str
    latency_ms: float


def handle_spam(comment: str) -> str:
    return "숨김/뮤트 (스팸 규칙 위반)"


def handle_abusive(comment: str) -> str:
    return "숨김/차단 (악성 판정)"


def handle_faq(comment: str) -> str:
    """실제로는 pgvector 유사도 검색 + RAG 생성(S15P11A108-184/-192). 스파이크에선 스텁."""
    return "RAG 응답 큐에 적재 (스텁 — pgvector 연동은 -184에서)"


def handle_normal(comment: str) -> str:
    return "통과 (액션 없음)"


_INTENT_HANDLERS = {
    "악성": handle_abusive,
    "반복질문": handle_faq,
    "정상": handle_normal,
}


def route_comment(
    comment: str,
    user_id: str,
    spam_detector: SpamDetector,
    *,
    classifier_bundle: ClassifierBundle | None = None,
    gen_bundle: CausalLMBundle | None = None,
    strategy: str = ACTIVE_INTENT,
) -> RoutingDecision:
    start = time.perf_counter()

    if spam_detector.is_spam(user_id, comment):
        action = handle_spam(comment)
        latency_ms = (time.perf_counter() - start) * 1000
        return RoutingDecision(comment=comment, intent="스팸", action=action, latency_ms=latency_ms)

    intent = classify_intent(
        comment, classifier_bundle=classifier_bundle, gen_bundle=gen_bundle, strategy=strategy
    )
    action = _INTENT_HANDLERS[intent](comment)
    latency_ms = (time.perf_counter() - start) * 1000
    return RoutingDecision(comment=comment, intent=intent, action=action, latency_ms=latency_ms)


# ---------------------------------------------------------------------------
# 4. 데모 — 두 전략 비교 (모델 선정용). `python chat_agent.py`로 직접 실행.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    SAMPLES = [
        ("user_1", "이 옷 진짜 예쁘네요 판매자님 감사합니다"),
        ("user_2", "가격 좀 너무 비싼거 아니에요?"),
        ("user_3", "이거 사이즈 M도 있나요?"),
        ("user_4", "저런 걸 옷이라고 파네 진짜 미친놈인가"),
        ("user_5", "여자가 무슨 명품을 입고 방송을 하냐 꼴값이네"),
        ("user_6", "품절이요 품절이요 품절이요"),
        ("user_6", "품절이요 품절이요 품절이요"),
        ("user_6", "품절이요 품절이요 품절이요"),
    ]

    for strategy in ("kor_unsmile_plus_rule", "kanana_zero_shot"):
        print(f"\n=== strategy={strategy} ===")
        detector = SpamDetector()
        classifier_bundle = (
            load_sequence_classifier(CLASSIFIER_MODELS[ACTIVE_CLASSIFIER])
            if strategy == "kor_unsmile_plus_rule"
            else None
        )
        gen_bundle = (
            load_causal_lm(GENERATIVE_MODELS[ACTIVE_GENERATIVE])
            if strategy == "kanana_zero_shot"
            else None
        )
        for user_id, comment in SAMPLES:
            decision = route_comment(
                comment,
                user_id,
                detector,
                classifier_bundle=classifier_bundle,
                gen_bundle=gen_bundle,
                strategy=strategy,
            )
            print(
                f"[{decision.intent:>4}] {decision.latency_ms:7.1f}ms  {comment!r} -> {decision.action}"
            )
