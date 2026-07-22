"""반복질문 클러스터링(B-2) 임베딩 모델 후보군 비교 벤치마크 — 라이브러리 모듈.

Throwaway/spike code for AI/test/model_selection/ — NOT production code.

`chat_agent.ipynb` 5.2("B-2 — 유사 질문 클러스터링 임계치(≥0.8) 검증")는 kanana-nano-embedding
하나만 써서 임계치 0.8 자체의 타당성만 확인했고, 임베딩 "모델" 비교는 의도적으로 스킵했다.
이 모듈은 그 스킵된 부분 — 여러 임베딩 모델 후보를 실제로 로드해서 로드 시간/지연시간과,
5.1의 FAQ paraphrase 그룹 데이터에 대한 쌍별 코사인 유사도를 비교한다.

`classifier_benchmark.py`와 동일하게 스크립트가 아니라 노트북에서 import해서 쓰는 모듈이다:
어떤 후보 집합·어떤 샘플을 돌릴지는 호출부(ipynb)가 결정하고, 이 파일은 "모델 로딩 + 임베딩 +
쌍별 유사도/임계치 스윕 집계" 로직만 제공한다. import만 해서는 아무 것도 실행되지 않는다.

측정 항목
---------
- 로드 시간, 임베딩 1건당(배치 크기 1) 지연시간: mean / p95
- 쌍별 코사인 유사도 + 정답(같은 paraphrase 그룹 여부)
- 임계치 0.30~0.90 스윕에 따른 precision/recall — 0.8 고정이 아니라 0.8이 최적인지
  자체를 같이 들여다보는 게 목적이다.

스코프 밖: B-3(그라운딩 임계치)과 RAG 답변 생성 LLM은 다루지 않는다. 이 모듈/이 모듈이
만드는 결과 어디에도 "이 모델을 채택한다"는 결론은 내리지 않는다 — 정책 검증용 관찰이지
정식 지표가 아니며, 최종 판단은 사람 몫이다(`chat_agent.ipynb` 5.2와 동일한 스탠스).

CLI 진입점(`python embedding_benchmark.py`)은 선택 사항이다 — `DEFAULT_PARAPHRASE_GROUPS`와
`CANDIDATE_EMBEDDINGS`로 단독 실행할 때만 쓰고, 노트북에서 import할 때는 실행되지 않는다.
"""

from __future__ import annotations

import statistics
import time
import tracemalloc
from dataclasses import dataclass, field
from functools import partial
from itertools import combinations
from typing import Callable, Iterable

import torch
import torch.nn.functional as F

from loaders import (
    EmbeddingBundle,
    load_kanana_embedding,
    load_sentence_transformer,
    load_transformers_embedding,
)
from model_registry import EMBEDDING_MODELS

ParaphraseSample = tuple[str, str]  # (댓글, 그룹 라벨) — 같은 그룹 = 같은 질문의 다른 표현

# --------------------------------------------------------------------------
# 1. 평가 데이터 — 최소 예시만 남긴다. 실제 평가셋은 `chat_agent.ipynb` 5.1의
#    `FAQ_CANDIDATES`(paraphrase 그룹 라벨링된 데이터)를 그대로 재사용해서 넘긴다.
# --------------------------------------------------------------------------
DEFAULT_PARAPHRASE_GROUPS: list[ParaphraseSample] = [
    ("가격 좀 너무 비싼거 아니에요?", "가격"),
    ("이거 얼마예요?", "가격"),
    ("배송은 언제 오나요?", "배송"),
]

# 0.30 ~ 0.90, 0.05 간격 — B-2 제안값 0.8을 포함해서 그 주변이 실제로 최적인지 스윕한다.
DEFAULT_THRESHOLDS: tuple[float, ...] = tuple(round(0.30 + 0.05 * i, 2) for i in range(13))


# --------------------------------------------------------------------------
# 2. 후보 임베딩 모델
# --------------------------------------------------------------------------
def _embed_kanana(bundle: EmbeddingBundle, texts: list[str]) -> torch.Tensor:
    """kanana-nano-embedding 전용 `model.encode(texts, instruction=...)` 인터페이스를
    범용 시그니처로 감싼다. instruction은 비워둔다 — 질문끼리 대칭 비교하는 클러스터링이라
    (검색의 query/doc 비대칭과 다름) `chat_agent.ipynb` 5.2와 동일한 선택이다."""
    return torch.as_tensor(bundle.model.encode(texts, instruction="", max_length=512))


def _embed_sentence_transformers(bundle: EmbeddingBundle, texts: list[str]) -> torch.Tensor:
    """sentence-transformers 계열(ko-sroberta-multitask/KURE-v1/BGE-m3-ko) 공용 인터페이스."""
    return torch.as_tensor(bundle.model.encode(texts, convert_to_numpy=True))


def _embed_cls_pooling(bundle: EmbeddingBundle, texts: list[str]) -> torch.Tensor:
    """BM-K/KoSimCSE-roberta 전용 — sentence-transformers 래핑이 없어(HF Hub 기준
    library_name=transformers, 1_Pooling 설정 없음) 모델 카드 공식 사용법대로
    CLS 토큰(last_hidden_state의 첫 토큰)을 직접 뽑는다."""
    with torch.no_grad():
        inputs = bundle.tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(
            bundle.device
        )
        last_hidden_state, _ = bundle.model(**inputs, return_dict=False)
    return last_hidden_state[:, 0].cpu()


@dataclass
class EmbeddingCandidate:
    """벤치마크 대상 임베딩 모델 하나 — 로딩 방식과 범용 임베딩 함수를 함께 묶는다.

    `embed_fn`은 항상 "텍스트 리스트 -> 벡터(torch.Tensor, shape [N, dim])"라는 범용
    인터페이스를 따른다 — 클러스터링 전용 로직에 묶이지 않게 하기 위함이다. 나중에 RAG
    문서 검색(pgvector) 등 다른 용도로 같은 임베딩 모델을 재사용할 때도
    `candidate.embed_fn(bundle, texts)` 호출 하나로 그대로 쓸 수 있다.

    Attributes:
        name: 결과 표시용 이름(레지스트리 키).
        model_id: HF Hub 모델 ID(참고/표시용 — 실제 로딩은 `load`가 담당).
        note: 크기/특징/주의사항 메모(리포트에 그대로 노출).
        load: 인자 없이 호출해 `EmbeddingBundle`을 반환하는 콜러블.
        embed_fn: (bundle, texts) -> 임베딩 텐서.
    """

    name: str
    model_id: str
    note: str
    load: Callable[[], EmbeddingBundle]
    embed_fn: Callable[[EmbeddingBundle, list[str]], torch.Tensor]


# 크기 비교(HF Hub config.json 기준 hidden_size/레이어 수 — 2026-07 확인):
#   - kanana_nano_embedding: 1792d/32L(2.1B)  — 현재 baseline, 후보 중 가장 무거움
#   - kosimcse_roberta / ko_sroberta_multitask: 768d/12L(~110M) — 가볍고 빠름
#   - kure_v1 / bge_m3_ko: 1024d/24L(~568M, 둘 다 BAAI/bge-m3 기반) — kanana 다음으로
#     무거움. 원래 "무거운 참고용"으로 지목된 건 bge_m3_ko뿐이지만 kure_v1도 같은
#     크기라 마찬가지로 속도 이슈가 있을 수 있다.
CANDIDATE_EMBEDDINGS: dict[str, EmbeddingCandidate] = {
    "kanana_nano_embedding": EmbeddingCandidate(
        name="kanana_nano_embedding",
        model_id=EMBEDDING_MODELS["kanana-nano-embedding"],
        note="현재 baseline(model_registry.ACTIVE_EMBEDDING). 1792d/32L, 2.1B — 후보 중 가장 무거움.",
        load=partial(load_kanana_embedding, EMBEDDING_MODELS["kanana-nano-embedding"]),
        embed_fn=_embed_kanana,
    ),
    "kosimcse_roberta": EmbeddingCandidate(
        name="kosimcse_roberta",
        model_id="BM-K/KoSimCSE-roberta",
        note="768d/12L(~110M). sentence-transformers 래핑 없음(CLS 토큰 직접 사용). 가볍고 빠른 후보.",
        load=partial(load_transformers_embedding, "BM-K/KoSimCSE-roberta"),
        embed_fn=_embed_cls_pooling,
    ),
    "ko_sroberta_multitask": EmbeddingCandidate(
        name="ko_sroberta_multitask",
        model_id="jhgan/ko-sroberta-multitask",
        note="768d/12L(~110M). sentence-transformers 표준 pooling. 널리 쓰이는 한국어 baseline.",
        load=partial(load_sentence_transformer, "jhgan/ko-sroberta-multitask"),
        embed_fn=_embed_sentence_transformers,
    ),
    "kure_v1": EmbeddingCandidate(
        name="kure_v1",
        model_id="nlpai-lab/KURE-v1",
        note=(
            "1024d/24L(~568M), BAAI/bge-m3 기반 한국어 파인튜닝. bge_m3_ko와 크기가 같아 "
            "마찬가지로 속도 이슈가 있을 수 있음."
        ),
        load=partial(load_sentence_transformer, "nlpai-lab/KURE-v1"),
        embed_fn=_embed_sentence_transformers,
    ),
    "bge_m3_ko": EmbeddingCandidate(
        name="bge_m3_ko",
        model_id="dragonkue/BGE-m3-ko",
        note="1024d/24L(~568M), BAAI/bge-m3 기반. 무거운 참고용 후보 — 속도 이슈가 있을 수 있음.",
        load=partial(load_sentence_transformer, "dragonkue/BGE-m3-ko"),
        embed_fn=_embed_sentence_transformers,
    ),
}


# --------------------------------------------------------------------------
# 3. 벤치마크 로직
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class PairSimilarity:
    """샘플 쌍 하나의 코사인 유사도와 정답(같은 paraphrase 그룹 여부)."""

    a: str
    b: str
    same_group: bool
    cosine_sim: float


@dataclass
class EmbeddingResult:
    """단일 임베딩 모델 1회 벤치마크 실행 결과.

    Attributes:
        model_name: 결과 표시용 이름(`CANDIDATE_EMBEDDINGS`의 키 등).
        load_time_s: 모델 로드에 걸린 시간(초).
        peak_mem_mb: 실행 구간(워밍업 포함) 피크 메모리(MB, `tracemalloc` 기준).
        embed_latencies_ms: 문장 1건당(배치 크기 1) 임베딩 지연시간(ms) 목록(워밍업 제외).
        pair_similarities: 입력 샘플의 모든 쌍에 대한 코사인 유사도 + 정답(같은 그룹 여부).
    """

    model_name: str
    load_time_s: float
    peak_mem_mb: float = 0.0
    embed_latencies_ms: list[float] = field(default_factory=list)
    pair_similarities: list[PairSimilarity] = field(default_factory=list)

    def latency_stats(self) -> dict[str, float]:
        """임베딩 지연시간 mean/p95(ms). 샘플이 없으면 빈 dict."""
        if not self.embed_latencies_ms:
            return {}
        s = sorted(self.embed_latencies_ms)
        n = len(s)
        return {
            "mean": statistics.mean(s),
            "p95": s[min(int(n * 0.95), n - 1)],
        }

    def precision_recall_at(self, threshold: float) -> dict[str, float]:
        """`threshold` 이상이면 "같은 그룹(클러스터링됨)"으로 예측했다고 볼 때의 precision/recall.

        임계치 하나만 고정해서 보여주는 게 아니라 `threshold_sweep()`과 함께 써서 0.8이
        실제로 최적인지를 스스로 판단하기 위한 재료일 뿐이다 — 이 메서드는 "이 임계치가
        맞다/틀리다"는 결론을 내리지 않는다.
        """
        tp = fp = fn = 0
        for pair in self.pair_similarities:
            predicted_same = pair.cosine_sim >= threshold
            if predicted_same and pair.same_group:
                tp += 1
            elif predicted_same and not pair.same_group:
                fp += 1
            elif not predicted_same and pair.same_group:
                fn += 1
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        return {"threshold": threshold, "precision": precision, "recall": recall}

    def threshold_sweep(
        self, thresholds: Iterable[float] = DEFAULT_THRESHOLDS
    ) -> list[dict[str, float]]:
        """`thresholds` 각각에 대해 precision/recall을 계산한다.

        B-2 제안값 0.8을 고정값으로 검증하는 대신, 0.30~0.90 구간 전체를 스윕해서
        0.8이 실제로 최적 근방인지 자체를 같이 드러내는 게 목적이다.
        """
        return [self.precision_recall_at(t) for t in thresholds]


def benchmark_embedding(
    candidate: EmbeddingCandidate,
    groups: Iterable[ParaphraseSample],
    *,
    warmup: int = 1,
) -> EmbeddingResult:
    """임베딩 모델 하나를 로드해 `groups`의 모든 문장을 임베딩하고, 문장 1건당
    지연시간과 쌍별 코사인 유사도를 집계한다.

    Args:
        candidate: 로딩 방식(`load`)과 범용 임베딩 함수(`embed_fn`)를 담은 후보 정의.
        groups: (댓글, 그룹 라벨) 목록. 같은 그룹 라벨 = 같은 질문의 다른 표현
            (paraphrase)이라는 뜻이다. `chat_agent.ipynb` 5.1의 `FAQ_CANDIDATES`를
            그대로 넘기면 된다.
        warmup: 지연시간 측정에서 제외할 콜드스타트 워밍업 횟수(문장 개수 기준).

    Returns:
        EmbeddingResult: 로드 시간, 피크 메모리, 문장별 지연시간, 쌍별 유사도.
    """
    tracemalloc.start()

    t0 = time.perf_counter()
    bundle = candidate.load()
    load_time = time.perf_counter() - t0

    groups = list(groups)
    texts = [text for text, _ in groups]
    group_labels = [label for _, label in groups]

    # 콜드스타트(그래프 최적화/캐시) 제외를 위한 워밍업 — 지연시간 통계에서 제외
    for text in texts[:warmup]:
        candidate.embed_fn(bundle, [text])

    # "임베딩 1건당" 지연시간 — 배치로 한꺼번에 인코딩하면 건당 비용이 묻히므로
    # 문장 하나씩(배치 크기 1) 개별 호출해서 잰다.
    embed_latencies_ms: list[float] = []
    for text in texts:
        t0 = time.perf_counter()
        candidate.embed_fn(bundle, [text])
        embed_latencies_ms.append((time.perf_counter() - t0) * 1000)

    # 유사도 계산용 벡터는 배치로 한 번에 다시 인코딩한다 — 위 개별 호출은 지연시간
    # 측정 전용이라 그 결과(벡터)는 버린다.
    vectors = candidate.embed_fn(bundle, texts)

    pair_similarities: list[PairSimilarity] = []
    for i, j in combinations(range(len(texts)), 2):
        cosine_sim = float(F.cosine_similarity(vectors[i : i + 1], vectors[j : j + 1]))
        pair_similarities.append(
            PairSimilarity(
                a=texts[i],
                b=texts[j],
                same_group=group_labels[i] == group_labels[j],
                cosine_sim=cosine_sim,
            )
        )

    _, peak = tracemalloc.get_traced_memory()
    peak_mem_mb = peak / (1024 * 1024)
    tracemalloc.stop()

    return EmbeddingResult(
        model_name=candidate.name,
        load_time_s=load_time,
        peak_mem_mb=peak_mem_mb,
        embed_latencies_ms=embed_latencies_ms,
        pair_similarities=pair_similarities,
    )


def run_all_embeddings(
    candidates: dict[str, EmbeddingCandidate],
    groups: Iterable[ParaphraseSample],
    *,
    warmup: int = 1,
) -> list[EmbeddingResult]:
    """`candidates`의 각 후보에 대해 `benchmark_embedding()`을 실행한다.

    한 후보가 실패해도(다운로드 실패, OOM 등) 나머지 후보는 계속 진행하고 실패
    사실만 출력한다 — `classifier_benchmark.run_all()`과 동일한 정책.

    노트북에서 호출할 때는 어떤 후보 집합을 돌릴지 직접 구성해서 넘긴다, 예:
    `run_all_embeddings(CANDIDATE_EMBEDDINGS, FAQ_CANDIDATES)`.

    Args:
        candidates: {표시용 이름: `EmbeddingCandidate`} 매핑.
        groups: `benchmark_embedding()`과 동일 — (댓글, 그룹 라벨) 목록.
        warmup: 후보마다 적용할 워밍업 횟수.

    Returns:
        성공한 후보들의 `EmbeddingResult` 목록(실패한 후보는 제외).
    """
    groups = list(groups)
    results: list[EmbeddingResult] = []
    for name, candidate in candidates.items():
        try:
            results.append(benchmark_embedding(candidate, groups, warmup=warmup))
        except (
            Exception
        ) as exc:  # noqa: BLE001 — 스파이크 코드: 한 후보 실패해도 나머지는 계속 돈다
            print(f"[{name}] 임베딩 벤치마크 실패: {exc}")
    return results


def print_report(results: list[EmbeddingResult], *, threshold: float = 0.8) -> None:
    """`run_all_embeddings()` 결과를 표로 출력한다.

    `threshold`는 리포트에 대표로 보여줄 임계치 하나일 뿐 — 스윕 결과 전체는
    `EmbeddingResult.threshold_sweep()`을 따로 호출해서 봐야 한다. 이 함수는 "어떤
    모델/임계치가 맞다"는 결론을 내리지 않는다 — 최종 판단은 사람이 한다.
    """
    header = (
        f"{'모델':25s} {'로드(s)':>8s} {'메모리(MB)':>10s} {'평균(ms)':>10s} {'p95(ms)':>10s} "
        f"{'precision@' + str(threshold):>14s} {'recall@' + str(threshold):>12s}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        stats = r.latency_stats()
        pr = r.precision_recall_at(threshold)
        print(
            f"{r.model_name:25s} {r.load_time_s:8.2f} {r.peak_mem_mb:10.1f} "
            f"{stats.get('mean', 0):10.1f} {stats.get('p95', 0):10.1f} "
            f"{pr['precision']:14.1%} {pr['recall']:12.1%}"
        )
    print()
    print("주의: 이 표는 정책 검증용 관찰이지 정식 벤치마크 결론이 아닙니다.")
    print("      최적 임계치·최종 채택 모델은 threshold_sweep() 결과를 보고 사람이 판단하세요.")


# --------------------------------------------------------------------------
# 4. CLI 단독 실행 (선택 사항) — `python embedding_benchmark.py`로 직접 돌릴 때만
#    쓰인다. 노트북에서 이 모듈을 import할 때는 실행되지 않는다.
# --------------------------------------------------------------------------
if __name__ == "__main__":
    results = run_all_embeddings(CANDIDATE_EMBEDDINGS, DEFAULT_PARAPHRASE_GROUPS)
    print()
    print_report(results)
