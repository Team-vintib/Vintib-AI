"""악성(욕설/혐오/인신공격) 분류기 — 인터페이스 + 규칙 기반 기본 구현 + HF 어댑터.

**CH030부터 기본(`registry.ACTIVE_CLASSIFIER`)은 `kcelectra_base_hate`다.** 규칙 기반은
recall 16.7%로 실서비스엔 너무 낮아서(욕설 10건 중 8건 이상 놓침) KcELECTRA-base-hate
(accuracy 99.5%/recall 98.8%, CPU 추론 p95 253ms 실측 — `AI/requirements.txt`에 이제
torch/transformers 포함)로 교체했다. `RuleBasedClassifier`는 삭제하지 않고 그대로
남겨뒀다 — `registry.ACTIVE_CLASSIFIER = "rule_based"`로 한 줄만 되돌리면 원복된다.

규칙 기반이 커버하는 우회 패턴: 공백/문장부호 삽입, 같은 글자 반복 패딩, 초성체.
(모음 늘이기 "시이이발" 같은 변형은 커버하지 않는다.)

설계: .claude/plans/ai/003-live-comment-moderation-prototype.md,
docs/plans/AI/CH030-chat-hate-classifier-swap.md
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
            # low_cpu_mem_usage=False로 명시 -- accelerate가 설치돼 있으면 transformers가
            # 기본으로 meta 디바이스에 지연 초기화(low_cpu_mem_usage=True)를 켜는데, 이
            # 조합에서 일부 텐서가 실제 디바이스로 안 옮겨지고 meta에 남아
            # "Tensor on device cpu is not on the expected device meta!"로 터지는 걸
            # 프로덕션에서 실측했다. 이 모델은 작아서(base급) 메모리 절약형 로딩이 애초에
            # 필요 없다.
            model = AutoModelForSequenceClassification.from_pretrained(
                self._model_id, low_cpu_mem_usage=False
            )
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


# --- 하이브리드(사전 + 모델) -------------------------------------------------


_MODEL_MIN_LENGTH = 5  # 이 미만이면(반복 접힌 정규화 기준) 모델을 안 태운다 -- 아래 클래스독스트링 참고

# 명백히 정상인 질문/관리요청 문장은 모델을 안 태운다(정규화된 문자열 대상, 공백 없음).
# "-나요"/"-까요"로 끝나는 정중한 질문형과, 도배/광고/소음 항의처럼 흔한 관리 요청 문구만
# 좁게 잡았다 -- 반말 의문형("~하냐")이나 서술형은 안 걸리므로 은근한 모욕 탐지(모델 경로)는
# 그대로 유지된다. 실측(2026-08-09): "이거 M 사이즈 있나요"(0.5041)/"그만 좀 하세요"(0.7442)/
# "도배 하지 마세요"(0.8118)가 전부 모델 단독으로 ABUSIVE 판정됐는데, 같은 모델에서 진짜
# 은근한 모욕인 "저 사람은 옷 고르는 안목이 부족한 편이다"도 0.8115로 점수가 거의 같아서
# 임계값 조정으로는 구분이 안 된다(임계값을 올리면 이것도 같이 놓친다) -- 그래서 임계값
# 대신 이 문장들이 안전하다고 알려진 패턴 자체를 화이트리스트로 우회시킨다.
# 알려진 한계(사용자 확인 후 채택): 이 패턴을 흉내 낸 모욕("그렇게 못생겼나요?", "그만 좀
# 죽어주세요")은 사전에도 안 걸리고 이 화이트리스트에도 걸려서 빠져나갈 수 있다 -- 새 우회
# 패턴이 발견되면 여기 추가하는 식으로 계속 다듬어야 한다(whack-a-mole, 근본 해결 아님).
_SAFE_QUESTION_SUFFIX_PATTERN = re.compile(r"(나요|까요)$")
_SAFE_MODERATION_REQUEST_PATTERN = re.compile(
    r"(그만좀?(해주세요|하세요)|도배하지(말아주세요|마세요)|광고(그만하세요|하지마세요)|조용히좀?해주세요)"
)


class HybridClassifier(AbuseClassifier):
    """사전(RuleBasedClassifier)과 모델(HuggingFaceClassifier)을 OR로 결합한다.

    실측(로컬, 2026-08-09): KcELECTRA 단독으로는 "병신같은 방송이네"(명백한 욕설)조차
    0.3185로 임계값(0.5)을 못 넘기고, "ㅂㅅ 이게 뭐야"도 0.4991로 아슬아슬하게 놓쳤다 --
    문맥이 짧으면 모델 확신도가 애매해지는 것으로 보인다. 반면 rule_based는 사전 단어를
    항상 확정적으로(0.9/0.75) 잡는다. 그래서 rule_based가 먼저 걸러보고(빠르고 확실한
    경우), 안 걸리면 모델로 넘겨서(사전에 없는 은근한 모욕/혐오까지) 서로의 약점을
    메운다. rule_based가 이미 걸렸으면 모델 호출(느림, ~30-250ms) 자체를 생략한다.

    **추가 실측(같은 날): 모델이 짧은 입력에서 훨씬 심하게 오탐한다.** "ㅇ"(0.8482),
    "ㅋㅋ"(0.7865), "넵"(0.8536) 전부 ABUSIVE로 잘못 판정했다 -- 실시간 채팅에서 가장
    흔한 반응들이라 이대로면 채팅 자체가 못 쓰게 된다. 그래서 반복 문자를 접은 뒤 길이가
    `_MODEL_MIN_LENGTH` 미만이면 모델을 아예 안 태우고 clean으로 본다 -- 그만큼 짧은
    욕설은 이미 rule_based 사전/초성체 목록이 커버한다(예: "씹"/"좆"은 1글자, "지랄"/
    "닥쳐"/"꺼져"는 2글자로 전부 사전에 있음). 반복 문자를 접는 이유: "ㅋㅋㅋㅋㅋ"(정규화
    길이 5)처럼 접기 전 길이만 보면 게이트를 피해가는 도배성 반복 문자가 있었다 -- 실제
    내용은 "ㅋ" 하나뿐인데 모델까지 태워져 똑같이 오탐(0.8645)했다.

    **세 번째 실측(같은 날): 모델이 정중한 질문/관리요청 문장까지 공격적으로 오인식한다.**
    위 `_SAFE_*_PATTERN` 독스트링 참고.
    """

    def __init__(self, rule_classifier: AbuseClassifier, model_classifier: AbuseClassifier) -> None:
        self._rule = rule_classifier
        self._model = model_classifier

    def score(self, text: str) -> AbuseResult:
        rule_result = self._rule.score(text)
        if rule_result.score >= registry.ABUSE_THRESHOLD:
            return rule_result

        normalized = normalize(text)
        if len(_collapse_repeats(normalized)) < _MODEL_MIN_LENGTH:
            return rule_result
        if _SAFE_QUESTION_SUFFIX_PATTERN.search(normalized):
            return rule_result
        if _SAFE_MODERATION_REQUEST_PATTERN.search(normalized):
            return rule_result

        return self._model.score(text)


def build_classifier(key: str | None = None) -> AbuseClassifier:
    """레지스트리 키로 분류기를 만든다. 미등록 키는 조립 시점에 바로 실패시킨다.

    모델 기반 백엔드는 항상 rule_based와 하이브리드로 묶는다(위 HybridClassifier 참고) --
    모델 단독으로는 사전에 있는 뻔한 욕설도 놓치는 게 실측으로 확인됐다.
    """
    resolved = key or registry.ACTIVE_CLASSIFIER
    try:
        model_id = registry.CLASSIFIER_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 분류기 백엔드입니다: {resolved!r}") from exc
    if model_id is None:
        return RuleBasedClassifier()
    return HybridClassifier(RuleBasedClassifier(), HuggingFaceClassifier(model_id))
