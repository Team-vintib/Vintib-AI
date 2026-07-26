"""1차 필터(욕설/스팸 분류기) 모델 후보군 비교 벤치마크 — 라이브러리 모듈.

Throwaway/spike code for AI/test/model_selection/ — NOT production code.

스크립트가 아니라 노트북에서 import해서 쓰는 모듈이다: 실제 평가 샘플(`samples`)과
어떤 모델 집합을 돌릴지는 호출부(ipynb)가 결정하고, 이 파일은 "모델 로딩 + 추론 +
지연시간/정확도 집계" 로직만 제공한다. import만 해서는 아무 것도 실행되지 않는다 —
`benchmark_model()` 또는 `run_all()`을 직접 호출해야 한다.

측정 항목
---------
- 지연시간: mean / p50 / p95 / p99 (콜드스타트 워밍업 제외)
- 클래스별 recall (전체 accuracy보다 중요 — 악성 미탐지가 정상 오탐지보다 비용이 큼)
- 모델 로드 시간 / 추론 중 피크 메모리

CLI 진입점(`python classifier_benchmark.py`)은 선택 사항이다 — `DEFAULT_SAMPLES`와
`CLASSIFIER_MODELS`/`CANDIDATE_MODELS`로 단독 실행할 때만 쓰고, 노트북에서 import할
때는 실행되지 않는다.
"""

from __future__ import annotations

import statistics
import time
import tracemalloc
from collections.abc import Iterable
from dataclasses import dataclass, field

import torch
from loaders import ClassifierBundle, load_sequence_classifier
from model_registry import CLASSIFIER_MODELS

Sample = tuple[str, str, str]  # (user_id, 댓글, 기대 라벨)

# --------------------------------------------------------------------------
# 1. 평가 데이터 — 최소 예시만 남긴다. 실제 대규모 평가셋(200건 이상, 실제 방송
#    채팅 로그 분포 반영, 초성체/띄어쓰기 우회 등 실제 우회 패턴 포함)은 노트북
#    쪽에서 구성해 benchmark_model()/run_all()의 samples 인자로 넘긴다.
#
#    "반복질문"/"스팸" 라벨은 의도적으로 넣지 않았다 — 이 모듈이 로드하는 건
#    순수 텍스트 분류기(정상/악성 2-way)라서 애초에 그 라벨을 낼 수 없다.
#    스팸은 규칙 기반 SpamDetector(chat_agent.py) 몫이고, 반복질문 여부는
#    별도 정책(실험실 "[AI] 반복질문 판정 정책 기준" 문서) 몫이다.
# --------------------------------------------------------------------------
DEFAULT_SAMPLES: list[Sample] = [
    ("user_1", "이 옷 진짜 예쁘네요 판매자님 감사합니다", "정상"),
    ("user_4", "저런 걸 옷이라고 파네 진짜 미친놈인가", "악성"),
    ("user_5", "여자가 무슨 명품을 입고 방송을 하냐 꼴값이네", "악성"),
]

# --------------------------------------------------------------------------
# 2. 후보 모델
# --------------------------------------------------------------------------
# 원래 후보였던 beomi/KcELECTRA-base, monologg/koelectra-small-v3-discriminator,
# klue/roberta-small은 셋 다 사전학습 베이스 체크포인트다(HF config 기준
# architectures가 각각 ElectraForPreTraining/ElectraForPreTraining/
# RobertaForMaskedLM이고 pipeline_tag도 text-classification이 아님 — 분류 헤드가
# 없다). AutoModelForSequenceClassification으로 불러오면 에러 없이 "로드는" 되지만
# 분류 헤드가 랜덤 초기화된 채로 붙어서 벤치마크 자체가 무의미해진다.
# 같은 크기대의 실제 파인튜닝된 한국어 혐오표현 분류기로 교체했다(HF Hub API로
# architectures=`*ForSequenceClassification`, id2label 존재 확인 완료):
CANDIDATE_MODELS: dict[str, str] = {
    # base(hidden 768/12L), 3-class(none/offensive/hate). 원래 beomi/KcELECTRA-base
    # 자리 — 같은 저자가 BEEP 혐오표현 데이터셋으로 파인튜닝한 버전으로 교체.
    "kcelectra_base_hate": "beomi/beep-KcELECTRA-base-hate",
    # small(hidden 256/12L), 2-class(Default/Spoiled). 원래
    # monologg/koelectra-small-v3-discriminator 자리 — APEACH 데이터셋으로
    # 파인튜닝된 KcELECTRA-small로 교체. 후보 중 가장 작아 지연시간 최우선 1순위.
    "kcelectra_small_apeach": "jason9693/KcELECTRA-small-v2022-apeach",
    # base(hidden 768/12L), 3-class(none/offensive/hate), RoBERTa 계열. 원래
    # klue/roberta-small 자리 — 공식적으로 파인튜닝된 klue-roberta-**small**
    # 혐오표현 분류기는 HF Hub에서 확인되지 않아, 같은 BEEP 데이터셋으로
    # 파인튜닝된 klue-roberta-base로 대체(Electra 계열과 다른 아키텍처 비교용).
    "klue_roberta_base_hate": "beomi/beep-klue-roberta-base-hate",
}
CANDIDATE_NOTES: dict[str, str] = {
    "kcelectra_base_hate": "KcELECTRA-base를 BEEP 혐오표현 데이터셋으로 파인튜닝. 구어체/댓글 특화, base급이라 다소 무거울 수 있음.",
    "kcelectra_small_apeach": "KcELECTRA-small을 APEACH 데이터셋으로 파인튜닝. hidden size 256으로 후보 중 가장 작음 — 지연시간 최우선 1순위 후보.",
    "klue_roberta_base_hate": "klue-roberta-base를 BEEP 혐오표현 데이터셋으로 파인튜닝. Electra 계열과 다른 아키텍처(RoBERTa) 비교용.",
}

# 모델별 id2label 원문(소문자 정규화) → 이 벤치마크의 공통 라벨. 매핑에 없는
# 라벨(예: kor_unsmile/hatescore류의 세부 혐오 카테고리 "기타 혐오", "남성" 등)은
# 전부 "악성"으로 취급한다 — "정상(clean)"이 아니면 전부 악성 후보라는 뜻.
_LABEL_ALIASES: dict[str, str] = {
    "clean": "정상",
    "none": "정상",
    "default": "정상",
    "ok_sen": "정상",
    "bad_sen": "악성",
    "offensive": "악성",
    "hate": "악성",
    "spoiled": "악성",
}


def _predict_label(bundle: ClassifierBundle, text: str) -> str:
    """분류기 하나로 문장 하나를 판정해 "정상"/"악성" 중 하나로 정규화해 반환한다.

    kor_unsmile류(다중 라벨/sigmoid, "clean" 라벨 하나 + 혐오 카테고리 여러 개)와
    KcELECTRA/RoBERTa 계열 혐오표현 분류기(단일 라벨/softmax, 2~3 라벨)를 모두
    다룬다 — `model.config.problem_type`으로 분기하고, 모델마다 다른 id2label
    원문 문자열은 `_LABEL_ALIASES`로 정규화한다.
    """
    with torch.no_grad():
        inputs = bundle.tokenizer(text, truncation=True, return_tensors="pt").to(bundle.device)
        logits = bundle.model(**inputs).logits[0]

    id2label = bundle.model.config.id2label
    is_multi_label = bundle.model.config.problem_type == "multi_label_classification"

    if is_multi_label:
        scores = torch.sigmoid(logits)
        abuse_score = max(
            (
                float(scores[i])
                for i, label in id2label.items()
                if _LABEL_ALIASES.get(label.lower(), "악성") != "정상"
            ),
            default=0.0,
        )
        return "악성" if abuse_score >= 0.5 else "정상"

    pred_id = int(torch.argmax(logits).item())
    raw_label = id2label[pred_id].lower()
    return _LABEL_ALIASES.get(raw_label, "악성")


# --------------------------------------------------------------------------
# 3. 벤치마크 로직
# --------------------------------------------------------------------------
@dataclass
class BenchResult:
    """단일 모델 1회 벤치마크 실행 결과.

    Attributes:
        model_name: 결과 표시용 이름(호출부가 넘긴 레지스트리 키 등).
        load_time_s: `loaders.load_sequence_classifier` 호출에 걸린 시간(초).
        peak_mem_mb: 추론 구간(워밍업 제외) 동안의 피크 메모리(MB, `tracemalloc` 기준).
        latencies_ms: 샘플별 추론 지연시간(ms) 목록(워밍업 제외).
        correct: 정답과 일치한 샘플 수.
        total: 전체 샘플 수.
        per_class_correct: 라벨별 정답 수.
        per_class_total: 라벨별 전체 샘플 수.
    """

    model_name: str
    load_time_s: float
    peak_mem_mb: float = 0.0
    latencies_ms: list[float] = field(default_factory=list)
    correct: int = 0
    total: int = 0
    per_class_correct: dict[str, int] = field(default_factory=dict)
    per_class_total: dict[str, int] = field(default_factory=dict)

    @property
    def accuracy(self) -> float:
        """전체 정확도(0~1). 샘플이 없으면 0.0."""
        return self.correct / self.total if self.total else 0.0

    def latency_stats(self) -> dict[str, float]:
        """지연시간 mean/p50/p95/p99(ms)를 담은 dict. 샘플이 없으면 빈 dict."""
        if not self.latencies_ms:
            return {}
        s = sorted(self.latencies_ms)
        n = len(s)
        return {
            "mean": statistics.mean(s),
            "p50": s[int(n * 0.5)],
            "p95": s[min(int(n * 0.95), n - 1)],
            "p99": s[min(int(n * 0.99), n - 1)],
        }

    def class_recall(self, label: str) -> float:
        """특정 라벨(예: "악성")에 대한 recall. 해당 라벨 샘플이 없으면 0.0."""
        total = self.per_class_total.get(label, 0)
        correct = self.per_class_correct.get(label, 0)
        return correct / total if total else 0.0


def benchmark_model(
    model_name: str,
    model_id: str,
    samples: Iterable[Sample],
    *,
    warmup: int = 3,
) -> BenchResult:
    """모델 하나를 로드해 `samples` 전체를 추론하고 지연시간/정확도를 집계한다.

    Args:
        model_name: 결과에 붙일 표시용 이름(레지스트리 키 등). 로딩에는 쓰이지 않는다.
        model_id: `loaders.load_sequence_classifier`에 넘길 HF Hub 모델 ID.
        samples: (user_id, 댓글, 기대 라벨) 튜플들. 기대 라벨은 "정상"/"악성"이어야
            `_predict_label()`의 정규화 결과와 비교가 성립한다.
        warmup: 지연시간 통계에서 제외할 콜드스타트 워밍업 추론 횟수.

    Returns:
        BenchResult: 로드 시간, 피크 메모리, 지연시간 목록, 정확도/클래스별 recall.
    """
    tracemalloc.start()

    t0 = time.perf_counter()
    bundle = load_sequence_classifier(model_id)
    load_time = time.perf_counter() - t0

    samples = list(samples)
    # 콜드스타트(그래프 최적화/캐시) 제외를 위한 워밍업 — 지연시간 통계에서 제외
    for _, text, _ in samples[:warmup]:
        _predict_label(bundle, text)

    result = BenchResult(model_name=model_name, load_time_s=load_time)

    for _, text, label in samples:
        t0 = time.perf_counter()
        pred = _predict_label(bundle, text)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        result.latencies_ms.append(elapsed_ms)
        result.total += 1
        result.per_class_total[label] = result.per_class_total.get(label, 0) + 1
        if pred == label:
            result.correct += 1
            result.per_class_correct[label] = result.per_class_correct.get(label, 0) + 1

    _, peak = tracemalloc.get_traced_memory()
    result.peak_mem_mb = peak / (1024 * 1024)
    tracemalloc.stop()
    return result


def run_all(
    models: dict[str, str],
    samples: Iterable[Sample],
    *,
    warmup: int = 3,
) -> list[BenchResult]:
    """`models`의 각 (이름, model_id) 쌍에 대해 `benchmark_model()`을 실행한다.

    한 후보가 실패해도(다운로드 실패, OOM 등) 나머지 후보는 계속 진행하고
    실패 사실만 출력한다 — 스파이크 코드라 전체 실행이 한 후보 때문에
    중단되지 않는 쪽을 택했다.

    노트북에서 호출할 때는 어떤 후보 집합을 돌릴지 직접 구성해서 넘긴다, 예:
    `run_all({**CLASSIFIER_MODELS, **CANDIDATE_MODELS}, my_samples)`.

    Args:
        models: {표시용 이름: HF Hub 모델 ID} 매핑.
        samples: `benchmark_model()`과 동일 — (user_id, 댓글, 기대 라벨) 목록.
        warmup: 후보마다 적용할 워밍업 추론 횟수.

    Returns:
        성공한 후보들의 BenchResult 목록(실패한 후보는 제외).
    """
    samples = list(samples)
    results: list[BenchResult] = []
    for name, model_id in models.items():
        try:
            results.append(benchmark_model(name, model_id, samples, warmup=warmup))
        except Exception as exc:
            print(f"[{name}] 벤치마크 실패: {exc}")
    return results


def print_report(results: list[BenchResult]) -> None:
    """`run_all()`/`benchmark_model()` 결과를 표 형태로 출력한다.

    CLI 단독 실행과 노트북 양쪽에서 재사용하는 리포트 포매터일 뿐, 데이터를
    직접 다루려면 `results`의 `BenchResult` 객체를 그대로 쓰면 된다.
    """
    header = f"{'모델':30s} {'로드(s)':>8s} {'메모리(MB)':>10s} {'평균(ms)':>10s} {'p95(ms)':>10s} {'정확도':>8s}"
    print(header)
    print("-" * len(header))
    for r in results:
        stats = r.latency_stats()
        print(
            f"{r.model_name:30s} {r.load_time_s:8.2f} {r.peak_mem_mb:10.1f} "
            f"{stats.get('mean', 0):10.1f} {stats.get('p95', 0):10.1f} {r.accuracy:8.1%}"
        )
        for label in r.per_class_total:
            print(
                f"    - {label:8s} recall: {r.class_recall(label):.0%} "
                f"({r.per_class_correct.get(label, 0)}/{r.per_class_total[label]})"
            )
    print()
    print(
        f"주의: 현재 샘플 수({len(results[0].latencies_ms) if results else 0}건)로는 p95/p99가 통계적으로 무의미합니다."
    )
    print("      최소 200~300건, 실제 채팅 분포에 맞춘 클래스 비율로 재실행하세요.")


# --------------------------------------------------------------------------
# 4. CLI 단독 실행 (선택 사항) — `python classifier_benchmark.py`로 직접 돌릴 때만
#    쓰인다. 노트북에서 이 모듈을 import할 때는 실행되지 않는다.
# --------------------------------------------------------------------------
if __name__ == "__main__":
    all_models = {**CLASSIFIER_MODELS, **CANDIDATE_MODELS}
    results = run_all(all_models, DEFAULT_SAMPLES)
    print()
    print_report(results)
