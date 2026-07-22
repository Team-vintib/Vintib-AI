"""추천 알고리즘(방향 A: 콘텐츠 기반 상품 추천) 임베딩 모델 후보군 비교 벤치마크 — 라이브러리 모듈.

Throwaway/spike code for AI/test/model_selection/ — NOT production code.

실험실 Notion 문서 `[AI] 추천 알고리즘 방향성 및 모델 선정 리서치`(LAB-14)의 "5. 검증 절차 제안"을
코드로 옮긴 모듈이다. 기존 `recommendation.ipynb`(1~4번 섹션)는 텍스트(상품명) 임베딩 2종
(kanana-nano-embedding/bge-m3)만 비교했다. 이미 완료된 `[AI] 추천용 벡터 DB 후보 검증`(LAB-10)은
"CLIP 기반 이미지 임베딩"을 전제로 pgvector를 채택해뒀는데, 정작 그 이미지 임베딩은 어디서도
실측된 적이 없다 — 이 모듈은 그 간극을 메워서 텍스트 후보 2종 + CLIP 이미지 후보 1종을 같은
평가 절차로 비교한다.

`classifier_benchmark.py`/`embedding_benchmark.py`와 동일하게 스크립트가 아니라 노트북에서
import해서 쓰는 모듈이다: 어떤 후보 집합·코퍼스·쿼리를 돌릴지는 호출부(ipynb)가 결정하고,
이 파일은 "모델 로딩 + 임베딩 + 랭킹 집계" 로직만 제공한다. import만 해서는 아무 것도
실행되지 않는다 — `load_sample_corpus()`도 함수로만 정의돼 있어(모듈 최상단 상수가 아님)
명시적으로 호출해야 네트워크 I/O(HF datasets 다운로드)가 발생한다.

평가지표가 `embedding_benchmark.py`와 다른 이유
----------------------------------------------
`embedding_benchmark.py`(B-2 클러스터링)는 "쌍이 같은 그룹인가"를 임계치로 가르는 과제라
쌍별 precision/recall + 임계치 스윕을 썼다. 추천은 "쿼리 하나에 대해 코퍼스를 랭킹"하는
검색 과제라 성격이 다르다 — 여기서는 Recall@K/Precision@K를 쓴다(카테고리 일치 = 정답).

이미지 데이터 — 플레이스홀더
----------------------------
리포지토리에는 실제 상품 사진이 아직 없다(FE/BE 도메인 데이터 미구축). 공개 데이터셋
`ashraq/fashion-product-images-small`(HF `datasets`)에서 카테고리 라벨(`articleType`)이 붙은
이미지를 소량 샘플링해 코퍼스로 쓰고, 그 카테고리 라벨을 그대로 정답(relevant/irrelevant)으로
재사용한다. **실제 서비스 카탈로그가 아니다** — 실제 상품 이미지가 확보되면 `load_sample_corpus()`의
데이터 소스를 교체해야 한다. 카탈로그가 영어 상품명 기준이라, 한국어 쿼리는 언어가 섞인 비교가
된다는 점도 참고(텍스트 후보는 한국어 쿼리 대 영어 상품명 매칭이 되고, CLIP은 이미지 타워가
언어에 무관하므로 이 영향을 덜 받는다).

5단계 추천 아키텍처와의 관계
----------------------------
①데이터 수집 → ②피처스토어/벡터저장소(pgvector) → ③A/B/C 추천 로직 → ④서빙(ANN+LLM 재정렬)
→ ⑤노출 화면 중, 이 모듈은 **③-A만** 다룬다. 여기서 만드는 임베딩 벡터를 실제로 pgvector에
저장하거나(②) ANN 검색 서빙(④)으로 붙이는 코드는 포함하지 않는다 — 인프라가 아직 없다
(LAB-10에서 방향만 정함). `RecommendationCandidate.embed_corpus_fn`이 반환하는 벡터를 그대로
pgvector 삽입 파이프라인에 넘기면 되는 형태로 설계했다.

스코프 밖: 방향 B(라이브 방송 추천)의 규칙기반 재순위화는 `live_recommendation.py`에 별도로
있다. 방향 C(브랜드 그래프)는 코드 스파이크 없음(LAB-14 참고, 방향성 리서치만).

CLI 진입점(`python recommendation_benchmark.py`)은 선택 사항이다 — 노트북에서 import할 때는
실행되지 않는다.
"""

from __future__ import annotations

import statistics
import time
import tracemalloc
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Callable, Iterable, Literal

import torch
import torch.nn.functional as F

from loaders import EmbeddingBundle, load_bge_m3, load_kanana_embedding, load_sentence_transformer
from model_registry import EMBEDDING_MODELS

RecommendationQuery = tuple[str, str]  # (쿼리 텍스트, 정답 카테고리)

# --------------------------------------------------------------------------
# 1. 평가 데이터 — 쿼리는 순수 리터럴(I/O 없음). 코퍼스는 외부 데이터셋에서 가져와야 해서
#    함수(`load_sample_corpus`)로만 제공한다 — import 시점에 네트워크 호출이 생기면 안 된다.
# --------------------------------------------------------------------------
TARGET_CATEGORIES: dict[str, str] = {
    "빈티지 데님 자켓": "Jackets",
    "여성 여름 원피스": "Dresses",
    "남성 캐주얼 셔츠": "Shirts",
}
# 코퍼스에 함께 섞어 넣는 "정답이 아닌" 카테고리 — recall/precision 분모(오답 후보)로 쓰인다.
CONTROL_CATEGORIES: tuple[str, ...] = ("Watches", "Sunglasses")

DEFAULT_QUERIES: list[RecommendationQuery] = list(TARGET_CATEGORIES.items())

_FASHION_DATASET_ID = "ashraq/fashion-product-images-small"


@dataclass(frozen=True)
class CorpusItem:
    """코퍼스 아이템 하나. 텍스트 후보는 `text`를, 이미지 후보는 `image`를 사용한다."""

    text: str
    category: str
    image: Any = None  # PIL.Image.Image | None


def load_sample_corpus(*, items_per_category: int = 5, scan_rows: int = 3000) -> list[CorpusItem]:
    """공개 패션 이미지 데이터셋에서 `TARGET_CATEGORIES`/`CONTROL_CATEGORIES`에 해당하는
    아이템을 카테고리당 `items_per_category`개씩 모아 평가용 코퍼스를 만든다.

    **네트워크 I/O 발생** — HF `datasets`로 `scan_rows`행만큼 슬라이스를 내려받는다(전체
    데이터셋을 다운로드하지 않음). 명시적으로 호출해야만 실행되며 import 시점엔 실행되지 않는다.

    주의: 데이터셋의 정확한 컬럼명은 최초 실행 시 확인이 필요하다 — `articleType`/
    `productDisplayName`/`image`로 추정하고 작성했다. 컬럼명이 다르면 `KeyError`/빈 코퍼스로
    바로 드러나므로 이 함수의 `row.get(...)` 호출부만 고치면 된다.

    Args:
        items_per_category: 카테고리(정답+오답 통틀어)당 모을 아이템 수.
        scan_rows: 앞에서부터 몇 행을 훑을지. 목표 수량을 못 채우면 경고를 출력한다
            (`scan_rows`를 늘려서 재시도).

    Returns:
        `CorpusItem` 목록(정답 카테고리 + 오답 카테고리 아이템이 섞여 있음).
    """
    from datasets import load_dataset

    wanted_categories = set(TARGET_CATEGORIES.values()) | set(CONTROL_CATEGORIES)
    dataset = load_dataset(_FASHION_DATASET_ID, split=f"train[:{scan_rows}]")

    counts: dict[str, int] = {cat: 0 for cat in wanted_categories}
    corpus: list[CorpusItem] = []
    for row in dataset:
        category = row.get("articleType")
        if category not in wanted_categories or counts[category] >= items_per_category:
            continue
        corpus.append(
            CorpusItem(
                text=row.get("productDisplayName", ""),
                category=category,
                image=row.get("image"),
            )
        )
        counts[category] += 1
        if all(c >= items_per_category for c in counts.values()):
            break

    missing = [cat for cat, c in counts.items() if c < items_per_category]
    if missing:
        print(
            f"[load_sample_corpus] 경고: scan_rows={scan_rows} 내에서 목표 수량을 못 채운 "
            f"카테고리: {missing} (counts={counts}) — scan_rows를 늘려보세요."
        )
    return corpus


# --------------------------------------------------------------------------
# 2. 후보 임베딩 모델
# --------------------------------------------------------------------------
_KANANA_QUERY_INSTRUCTION = "Given a question, retrieve passages that answer the question"
_KANANA_DOC_INSTRUCTION = ""


def _embed_kanana_query(bundle: EmbeddingBundle, texts: list[str]) -> torch.Tensor:
    """recommendation.ipynb 1번 섹션과 동일한 query instruction."""
    return torch.as_tensor(
        bundle.model.encode(texts, instruction=_KANANA_QUERY_INSTRUCTION, max_length=512)
    )


def _embed_kanana_corpus(bundle: EmbeddingBundle, texts: list[str]) -> torch.Tensor:
    """recommendation.ipynb 1번 섹션과 동일한 doc instruction(빈 문자열)."""
    return torch.as_tensor(
        bundle.model.encode(texts, instruction=_KANANA_DOC_INSTRUCTION, max_length=512)
    )


def _embed_bge_m3(bundle, texts: list[str]) -> torch.Tensor:
    """`loaders.load_bge_m3`는 EmbeddingBundle이 아니라 FlagEmbedding의 BGEM3FlagModel을
    그대로 반환한다(다른 라이브러리) — recommendation.ipynb 2번 섹션과 동일하게 dense_vecs만 쓴다."""
    return torch.as_tensor(bundle.encode(texts)["dense_vecs"])


def _load_clip_pair() -> tuple[EmbeddingBundle, EmbeddingBundle]:
    """CLIP은 텍스트/이미지를 한 모델로 못 돌린다 — `clip-vit-b32-multilingual`(텍스트 전용
    지식증류 모델)은 이미지 인코딩 자체를 지원하지 않는다("Modality 'image' is not supported"
    에러로 실측 확인됨). sentence-transformers 공식 사용법대로, **같은 벡터 공간을 공유하도록
    학습된** 원본 이미지 타워(`clip-vit-b32`)와 다국어 텍스트 타워(`clip-vit-b32-multilingual`)를
    각각 로드해 튜플로 묶는다 — `RecommendationCandidate.load`는 `Callable[[], Any]`라
    번들 하나 대신 튜플을 반환해도 나머지 벤치마크 로직은 그대로 재사용된다."""
    return (
        load_sentence_transformer(EMBEDDING_MODELS["clip-vit-b32-multilingual"]),  # [0] 텍스트 타워
        load_sentence_transformer(EMBEDDING_MODELS["clip-vit-b32"]),  # [1] 이미지 타워
    )


def _embed_clip_text(
    bundle: tuple[EmbeddingBundle, EmbeddingBundle], texts: list[str]
) -> torch.Tensor:
    """CLIP 텍스트 타워(`bundle[0]`) — sentence-transformers의 CLIPModel은 str 리스트를
    넣으면 자동으로 텍스트 인코딩 경로를 탄다."""
    text_bundle, _ = bundle
    return torch.as_tensor(text_bundle.model.encode(texts, convert_to_numpy=True))


def _embed_clip_images(
    bundle: tuple[EmbeddingBundle, EmbeddingBundle], images: list[Any]
) -> torch.Tensor:
    """CLIP 이미지 타워(`bundle[1]`) — PIL.Image 리스트를 넣으면 자동으로 이미지 인코딩
    경로를 탄다. 텍스트 타워(`_embed_clip_text`)와 같은 벡터 공간이라 코사인 유사도로 바로
    비교 가능하다(두 모델이 별개로 로드됐다는 사실은 여기서만 알면 되고, 호출부는 신경쓸
    필요 없다)."""
    _, image_bundle = bundle
    return torch.as_tensor(image_bundle.model.encode(images, convert_to_numpy=True))


@dataclass
class RecommendationCandidate:
    """벤치마크 대상 임베딩 모델 하나.

    `embedding_benchmark.EmbeddingCandidate`와 달리 `embed_query_fn`/`embed_corpus_fn`을
    분리했다 — 검색 과제는 쿼리(텍스트)와 코퍼스(텍스트 또는 이미지)의 입력 형태가 다를 수
    있어서다(비대칭 인코딩). `corpus_modality`로 코퍼스 아이템에서 `text`/`image` 중 뭘 뽑아
    넘길지 결정한다.

    Attributes:
        name: 결과 표시용 이름(레지스트리 키).
        model_id: HF Hub 모델 ID(참고/표시용).
        note: 후보 선정 이유/주의사항 메모(리포트에 노출).
        corpus_modality: 코퍼스 아이템을 텍스트로 볼지 이미지로 볼지.
        load: 인자 없이 호출해 모델 번들을 반환하는 콜러블.
        embed_query_fn: (bundle, texts) -> 쿼리 임베딩 텐서.
        embed_corpus_fn: (bundle, texts_or_images) -> 코퍼스 임베딩 텐서.
    """

    name: str
    model_id: str
    note: str
    corpus_modality: Literal["text", "image"]
    load: Callable[[], Any]
    embed_query_fn: Callable[[Any, list[str]], torch.Tensor]
    embed_corpus_fn: Callable[[Any, list[Any]], torch.Tensor]


CANDIDATE_RECOMMENDATIONS: dict[str, RecommendationCandidate] = {
    "kanana_nano_embedding": RecommendationCandidate(
        name="kanana_nano_embedding",
        model_id=EMBEDDING_MODELS["kanana-nano-embedding"],
        note="현재 baseline(model_registry.ACTIVE_EMBEDDING). recommendation.ipynb 1번 섹션과 동일한 로더/instruction.",
        corpus_modality="text",
        load=partial(load_kanana_embedding, EMBEDDING_MODELS["kanana-nano-embedding"]),
        embed_query_fn=_embed_kanana_query,
        embed_corpus_fn=_embed_kanana_corpus,
    ),
    "bge_m3": RecommendationCandidate(
        name="bge_m3",
        model_id=EMBEDDING_MODELS["bge-m3"],
        note="recommendation.ipynb 2번 섹션과 동일. FlagEmbedding 라이브러리, dense_vecs만 검증(lexical/colbert 미검증).",
        corpus_modality="text",
        load=partial(load_bge_m3, EMBEDDING_MODELS["bge-m3"]),
        embed_query_fn=_embed_bge_m3,
        embed_corpus_fn=_embed_bge_m3,
    ),
    "clip_vit_b32_multilingual": RecommendationCandidate(
        name="clip_vit_b32_multilingual",
        model_id=(
            f"{EMBEDDING_MODELS['clip-vit-b32-multilingual']} (text) + "
            f"{EMBEDDING_MODELS['clip-vit-b32']} (image)"
        ),
        note=(
            "신규 후보 — LAB-10이 전제한 'CLIP 기반 이미지 임베딩'을 실제로 검증하는 첫 후보. "
            "2-모델 조합이다: 원본 openai/clip-vit-base-patch32는 텍스트 타워가 영어 전용이라 "
            "한국어 쿼리에 약할 수 있어, 멀티링구얼 지식증류로 텍스트 타워만 다국어로 확장한 "
            "sentence-transformers 공식 변형(clip-vit-b32-multilingual)으로 쿼리를 인코딩하고, "
            "이미지는 그 변형이 지원하지 않아(텍스트 전용 모델) 원본 이미지 타워(clip-vit-b32)로 "
            "인코딩한다 — 두 모델이 같은 벡터 공간을 공유하도록 학습됐기 때문에 가능한 조합."
        ),
        corpus_modality="image",
        load=_load_clip_pair,
        embed_query_fn=_embed_clip_text,
        embed_corpus_fn=_embed_clip_images,
    ),
}


# --------------------------------------------------------------------------
# 3. 벤치마크 로직
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class QueryRanking:
    """쿼리 하나에 대한 코퍼스 랭킹 결과(유사도 내림차순으로 정렬된 카테고리 목록)."""

    query: str
    target_category: str
    ranked_categories: list[str]


@dataclass
class RecommendationResult:
    """단일 임베딩 모델 1회 벤치마크 실행 결과.

    Attributes:
        model_name: 결과 표시용 이름.
        load_time_s: 모델 로드에 걸린 시간(초).
        peak_mem_mb: 실행 구간 피크 메모리(MB, `tracemalloc` 기준).
        query_latencies_ms: 쿼리 1건당 임베딩 지연시간(ms) 목록(워밍업 제외).
        query_rankings: 쿼리별 코퍼스 랭킹 결과.
    """

    model_name: str
    load_time_s: float
    peak_mem_mb: float = 0.0
    query_latencies_ms: list[float] = field(default_factory=list)
    query_rankings: list[QueryRanking] = field(default_factory=list)

    def latency_stats(self) -> dict[str, float]:
        """쿼리 임베딩 지연시간 mean/p95(ms). 샘플이 없으면 빈 dict."""
        if not self.query_latencies_ms:
            return {}
        s = sorted(self.query_latencies_ms)
        n = len(s)
        return {"mean": statistics.mean(s), "p95": s[min(int(n * 0.95), n - 1)]}

    def recall_at_k(self, k: int) -> float:
        """쿼리별 recall(top-K 안에 정답 카테고리 아이템이 얼마나 포함됐는지)의 macro-average.

        코퍼스에 정답 카테고리 아이템이 하나도 없는 쿼리는 분모가 0이라 계산에서 제외한다
        (코퍼스 구성이 잘못됐다는 신호이지, 모델 문제가 아니다).
        """
        per_query = []
        for qr in self.query_rankings:
            total_relevant = qr.ranked_categories.count(qr.target_category)
            if total_relevant == 0:
                continue
            hit = qr.ranked_categories[:k].count(qr.target_category)
            per_query.append(hit / total_relevant)
        return statistics.mean(per_query) if per_query else 0.0

    def precision_at_k(self, k: int) -> float:
        """top-K 중 정답 카테고리 비율의 macro-average."""
        per_query = [
            qr.ranked_categories[:k].count(qr.target_category) / min(k, len(qr.ranked_categories))
            for qr in self.query_rankings
            if qr.ranked_categories
        ]
        return statistics.mean(per_query) if per_query else 0.0


def benchmark_recommendation(
    candidate: RecommendationCandidate,
    corpus: Iterable[CorpusItem],
    queries: Iterable[RecommendationQuery],
    *,
    warmup: int = 1,
) -> RecommendationResult:
    """임베딩 모델 하나를 로드해 코퍼스 전체를 임베딩하고, 쿼리마다 코퍼스를 랭킹한다.

    Args:
        candidate: 로딩 방식과 쿼리/코퍼스 임베딩 함수를 담은 후보 정의.
        corpus: 평가용 코퍼스(`load_sample_corpus()` 결과 등).
        queries: (쿼리 텍스트, 정답 카테고리) 목록.
        warmup: 지연시간 측정에서 제외할 콜드스타트 워밍업 쿼리 수.

    Returns:
        RecommendationResult: 로드 시간, 피크 메모리, 쿼리별 지연시간·랭킹.
    """
    tracemalloc.start()

    t0 = time.perf_counter()
    bundle = candidate.load()
    load_time = time.perf_counter() - t0

    corpus = list(corpus)
    if candidate.corpus_modality == "image":
        corpus_inputs: list[Any] = [item.image for item in corpus]
        if any(img is None for img in corpus_inputs):
            raise ValueError(
                f"[{candidate.name}] corpus_modality='image'인데 image가 없는 CorpusItem이 있습니다."
            )
    else:
        corpus_inputs = [item.text for item in corpus]
    corpus_categories = [item.category for item in corpus]
    corpus_vectors = candidate.embed_corpus_fn(bundle, corpus_inputs)

    queries = list(queries)
    query_texts = [q for q, _ in queries]

    # 콜드스타트 제외를 위한 워밍업 — 지연시간 통계에서 제외
    for text in query_texts[:warmup]:
        candidate.embed_query_fn(bundle, [text])

    query_latencies_ms: list[float] = []
    query_vectors: list[torch.Tensor] = []
    for text in query_texts:
        t0 = time.perf_counter()
        vec = candidate.embed_query_fn(bundle, [text])
        query_latencies_ms.append((time.perf_counter() - t0) * 1000)
        query_vectors.append(vec)

    query_rankings: list[QueryRanking] = []
    for (query_text, target_category), query_vec in zip(queries, query_vectors):
        sims = F.cosine_similarity(query_vec, corpus_vectors)
        ranked_idx = torch.argsort(sims, descending=True).tolist()
        query_rankings.append(
            QueryRanking(
                query=query_text,
                target_category=target_category,
                ranked_categories=[corpus_categories[i] for i in ranked_idx],
            )
        )

    _, peak = tracemalloc.get_traced_memory()
    peak_mem_mb = peak / (1024 * 1024)
    tracemalloc.stop()

    return RecommendationResult(
        model_name=candidate.name,
        load_time_s=load_time,
        peak_mem_mb=peak_mem_mb,
        query_latencies_ms=query_latencies_ms,
        query_rankings=query_rankings,
    )


def run_all_recommendations(
    candidates: dict[str, RecommendationCandidate],
    corpus: Iterable[CorpusItem],
    queries: Iterable[RecommendationQuery],
    *,
    warmup: int = 1,
) -> list[RecommendationResult]:
    """`candidates`의 각 후보에 대해 `benchmark_recommendation()`을 실행한다.

    한 후보가 실패해도(다운로드 실패, OOM 등) 나머지 후보는 계속 진행하고 실패 사실만
    출력한다 — `classifier_benchmark.run_all()`/`embedding_benchmark.run_all_embeddings()`와
    동일한 정책.

    Args:
        candidates: {표시용 이름: `RecommendationCandidate`} 매핑.
        corpus: `benchmark_recommendation()`과 동일.
        queries: `benchmark_recommendation()`과 동일.
        warmup: 후보마다 적용할 워밍업 쿼리 수.

    Returns:
        성공한 후보들의 `RecommendationResult` 목록(실패한 후보는 제외).
    """
    corpus = list(corpus)
    queries = list(queries)
    results: list[RecommendationResult] = []
    for name, candidate in candidates.items():
        try:
            results.append(benchmark_recommendation(candidate, corpus, queries, warmup=warmup))
        except (
            Exception
        ) as exc:  # noqa: BLE001 — 스파이크 코드: 한 후보 실패해도 나머지는 계속 돈다
            print(f"[{name}] 추천 벤치마크 실패: {exc}")
    return results


def print_report(
    results: list[RecommendationResult], *, k_values: tuple[int, ...] = (3, 5)
) -> None:
    """`run_all_recommendations()` 결과를 표로 출력한다.

    이 함수는 "어떤 모델이 맞다"는 결론을 내리지 않는다 — 최종 판단은 사람이 한다(다른 두
    벤치마크 모듈과 동일한 스탠스). 코퍼스가 실제 카탈로그가 아니라 플레이스홀더라는 점도
    항상 함께 봐야 한다.
    """
    header_parts = [
        f"{'모델':28s}",
        f"{'로드(s)':>8s}",
        f"{'메모리(MB)':>10s}",
        f"{'평균(ms)':>10s}",
    ]
    header_parts += [f"{'recall@' + str(k):>10s}" for k in k_values]
    header_parts += [f"{'precision@' + str(k):>12s}" for k in k_values]
    header = " ".join(header_parts)
    print(header)
    print("-" * len(header))
    for r in results:
        stats = r.latency_stats()
        row_parts = [
            f"{r.model_name:28s}",
            f"{r.load_time_s:8.2f}",
            f"{r.peak_mem_mb:10.1f}",
            f"{stats.get('mean', 0):10.1f}",
        ]
        row_parts += [f"{r.recall_at_k(k):10.1%}" for k in k_values]
        row_parts += [f"{r.precision_at_k(k):12.1%}" for k in k_values]
        print(" ".join(row_parts))
    print()
    print("주의: 코퍼스는 실제 상품 카탈로그가 아니라 공개 데이터셋 플레이스홀더입니다.")
    print("      최종 채택 모델은 사람이 판단하세요 — 이 표는 참고 자료일 뿐입니다.")


# --------------------------------------------------------------------------
# 4. CLI 단독 실행 (선택 사항) — `python recommendation_benchmark.py`로 직접 돌릴 때만
#    쓰인다. 노트북에서 이 모듈을 import할 때는 실행되지 않는다.
# --------------------------------------------------------------------------
if __name__ == "__main__":
    sample_corpus = load_sample_corpus()
    results = run_all_recommendations(CANDIDATE_RECOMMENDATIONS, sample_corpus, DEFAULT_QUERIES)
    print()
    print_report(results)
