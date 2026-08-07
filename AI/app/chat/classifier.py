"""악성(욕설/혐오/인신공격) 분류기 — 인터페이스 + 규칙 기반 기본 구현 + HF 어댑터.

기본값이 규칙 기반인 이유: CI는 `requirements-dev.txt`만 설치해서 torch/transformers가 없다
(`AI/CLAUDE.md` CI 규칙). 규칙 기반을 기본으로 두면 전체 파이프라인 테스트가 CI에서 **스킵 없이**
그대로 돌고, 실모델은 `registry.ACTIVE_CLASSIFIER` 키 하나로 바꿔 끼운다.

규칙 기반이 커버하는 우회 패턴: 공백/문장부호 삽입, 같은 글자 반복 패딩, 초성체.
(모음 늘이기 "시이이발" 같은 변형은 커버하지 않는다 — 실모델 전환 시 해소 대상.)
`classifier_benchmark.ipynb` 실측에서 현 baseline `kor_unsmile`이 이런 우회를 절반 가까이
놓쳤기 때문에(악성 recall 58.3%), 목업 단계에서도 정규화 전처리는 넣어 둔다.

설계: .claude/plans/ai/003-live-comment-moderation-prototype.md
"""

from __future__ import annotations

import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.chat import registry


@dataclass(frozen=True)
class AbuseResult:
    """악성 점수와 그 근거 라벨."""

    score: float
    label: str  # 매칭된 규칙/모델 라벨. 정상이면 "clean"


class AbuseClassifier(ABC):
    """댓글 한 건의 악성 점수를 매기는 인터페이스."""

    @abstractmethod
    def score(self, text: str) -> AbuseResult:
        """0.0~1.0 악성 점수. `registry.ABUSE_THRESHOLD` 이상이면 악성으로 처리된다."""
        raise NotImplementedError


# --- 규칙 기반 기본 구현 ---------------------------------------------------

# 욕설/혐오/인신공격 사전. 목업 수준의 최소 셋이다 — 실서비스는 모델로 교체하는 것이 전제다.
# 인접 중복 글자가 있는 표제어는 넣지 않는다(정규화가 중복을 접기 때문).
_ABUSE_TERMS: tuple[str, ...] = (
    "시발",
    "씨발",
    "시팔",
    "씨팔",
    "씹",
    "좆",
    "개새끼",
    "개새",
    "새끼",
    "병신",
    "븅신",
    "등신",
    "미친놈",
    "미친년",
    "지랄",
    "닥쳐",
    "꺼져",
    "꺼지",
    "멍청이",
    "쓰레기",
    "꼴값",
    "죽어라",
    "찌질",
)

# 초성체 우회. 사용자가 **낱자 자모를 직접 입력한** 경우에만 검사한다.
# 일반 음절을 초성으로 환원해서 비교하면 "소백산"→"ㅅㅂㅅ"처럼 오탐이 폭증한다.
#
# "ㅄ"(U+3144)은 "ㅂ"+"ㅅ"를 붙여 쓴 게 아니라 유니코드에 이미 합쳐진 별개의 호환 자모
# 코드포인트다 — 문자열로는 "ㅂㅅ"(두 글자)와 전혀 다르다. 그래서 "ㅂㅅ"만 사전에 있으면
# 띄어 쓴 "ㅂ ㅅ"/"ㅂㅅ"는 걸리는데 붙여 쓴 "ㅄ"은 빠져나간다 — 둘 다 등록해야 한다.
# 표준 겹자모 중 이렇게 조합형 코드포인트가 따로 있는 건 "ㅂㅅ"→"ㅄ"뿐이라(ㄳ/ㄵ/ㄶ/ㄺ/ㄻ/
# ㄼ/ㄽ/ㄾ/ㄿ/ㅀ/ㅄ), 나머지 항목들은 해당 없다.
_ABUSE_JAMO: tuple[str, ...] = (
    "ㅅㅂ",
    "ㅆㅂ",
    "ㅂㅅ",
    "ㅄ",
    "ㄱㅅㄲ",
    "ㅁㅊ",
    "ㅈㄹ",
    "ㄷㅊ",
    "ㄲㅈ",
)

_KEEP_PATTERN = re.compile(r"[^0-9a-z가-힣ㄱ-ㅎㅏ-ㅣ]+")
_JAMO_PATTERN = re.compile(r"[ㄱ-ㅎㅏ-ㅣ]+")

_TERM_SCORE = 0.9
_JAMO_SCORE = 0.75


def _collapse_repeats(text: str) -> str:
    """같은 글자가 연달아 나오면 하나로 접는다 ("ㅋㅋㅋ"→"ㅋ", "시발!!!"→"시발!")."""
    if not text:
        return text
    out = [text[0]]
    for ch in text[1:]:
        if ch != out[-1]:
            out.append(ch)
    return "".join(out)


def normalize(text: str) -> str:
    """공백·문장부호를 걷어내고 소문자화한 비교용 문자열."""
    folded = unicodedata.normalize("NFC", text).lower()
    return _KEEP_PATTERN.sub("", folded)


def jamo_runs(text: str) -> str:
    """사용자가 직접 입력한 낱자 자모만 이어 붙인 문자열(초성체 검사용)."""
    folded = unicodedata.normalize("NFC", text)
    return _collapse_repeats("".join(_JAMO_PATTERN.findall(folded)))


class RuleBasedClassifier(AbuseClassifier):
    """사전 + 우회패턴 정규화 기반 기본 분류기. 외부 의존성이 없다."""

    def __init__(
        self,
        terms: tuple[str, ...] = _ABUSE_TERMS,
        jamo_terms: tuple[str, ...] = _ABUSE_JAMO,
    ) -> None:
        self._terms = terms
        self._jamo_terms = jamo_terms

    def score(self, text: str) -> AbuseResult:
        plain = normalize(text)
        collapsed = _collapse_repeats(plain)
        for term in self._terms:
            if term in plain or term in collapsed:
                return AbuseResult(score=_TERM_SCORE, label=term)

        runs = jamo_runs(text)
        for term in self._jamo_terms:
            if term in runs:
                return AbuseResult(score=_JAMO_SCORE, label=term)

        return AbuseResult(score=0.0, label="clean")


# --- HuggingFace 어댑터 (지연 import) --------------------------------------

# 모델마다 "정상"을 가리키는 라벨명이 다르다(classifier_benchmark.py의 _LABEL_ALIASES와 같은 취지).
_NORMAL_LABELS = frozenset({"clean", "none", "default", "ok_sen", "label_0", "not_hate"})


class HuggingFaceClassifier(AbuseClassifier):
    """HF 시퀀스 분류기 어댑터. transformers/torch는 `requirements-pipeline.txt`(CI 미설치).

    multi-label(sigmoid, 예: kor_unsmile)과 single-label(softmax, 예: beep-KcELECTRA)을
    `model.config.problem_type`으로 분기해서 "정상이 아닌 라벨의 최대 확률"을 점수로 쓴다.
    """

    def __init__(self, model_id: str) -> None:
        self._model_id = model_id
        self._bundle: tuple[object, object] | None = None

    def _load(self) -> tuple[object, object]:
        if self._bundle is None:
            # 지연 import — 모듈 최상단에 두면 서빙 경로가 torch에 묶인다.
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(self._model_id)
            model = AutoModelForSequenceClassification.from_pretrained(self._model_id)
            model.eval()
            self._bundle = (tokenizer, model)
        return self._bundle

    def score(self, text: str) -> AbuseResult:
        import torch

        tokenizer, model = self._load()
        with torch.no_grad():
            inputs = tokenizer(text, truncation=True, return_tensors="pt")
            logits = model(**inputs).logits

        if getattr(model.config, "problem_type", None) == "multi_label_classification":
            probs = torch.sigmoid(logits)[0]
        else:
            probs = torch.softmax(logits, dim=-1)[0]

        id2label = model.config.id2label
        abusive = [
            (float(probs[i]), str(label))
            for i, label in id2label.items()
            if str(label).lower() not in _NORMAL_LABELS
        ]
        if not abusive:
            return AbuseResult(score=0.0, label="clean")
        score, label = max(abusive)
        return AbuseResult(score=round(score, 4), label=label)


def build_classifier(key: str | None = None) -> AbuseClassifier:
    """레지스트리 키로 분류기를 만든다. 미등록 키는 조립 시점에 바로 실패시킨다."""
    resolved = key or registry.ACTIVE_CLASSIFIER
    try:
        model_id = registry.CLASSIFIER_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 분류기 백엔드입니다: {resolved!r}") from exc
    if model_id is None:
        return RuleBasedClassifier()
    return HuggingFaceClassifier(model_id)
