"""반복질문 경로 — 질문 판별(B-1) / 유사질문 클러스터링(B-2) / RAG 검색(B-3, 평가 전용).

**`Retriever`는 이제 프로덕션이 아니라 평가 파이프라인(`app/chat/evaluation.py`,
`test/chat/test_chat_evaluation.py`, `S15P11A108-196`) 전용이다.** 실제 반복질문 답변 생성은
`chat_rag` 워커 job(`worker/chat_rag_worker_example.py`)이 `app/chat/rag_store.py`로 가져온
후보 문서를 그 안에서 직접 임베딩·랭킹·생성까지 처리한다(`S15P11A108-444`) — 검색·그라운딩
판단·생성을 왕복 1회로 합치기 위해서다. `Retriever`/`MockRetriever`는 클러스터링·그라운딩
임계치를 오프라인으로 검증할 때만 쓰인다.

임베딩은 문자 bigram을 해싱해 만든 **결정적 벡터**다(torch 불필요 — 서빙 경로는 경량 의존성만,
CI에서 클러스터링·검색 테스트가 그대로 돈다). 같은 착상을
`app/recommend/personalize/catalog.py`가 카탈로그 목업 벡터에 쓰고 있는데, 도메인 자체완결
규약(`AI/CLAUDE.md`)에 따라 import하지 않고 여기서 다시 정의한다. 두 도메인이 실제로 같은
임베더를 쓰게 되면 그때 `app/shared/`로 승격한다.

설계: .claude/plans/ai/003-live-comment-moderation-prototype.md
"""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.chat import registry
from app.chat.classifier import normalize

_DATA_DIR = Path(__file__).resolve().parent / "data"
_MOCK_FAQ_FILE = _DATA_DIR / "mock_faq.json"

# bigram 해싱은 무작위 투영이라 차원이 낮으면 무관한 문장끼리도 코사인이 뜬다(노이즈 ~1/√dim).
# 임계치 0.30~0.35와 충분히 벌어지도록 512로 잡았다.
_EMBED_DIM = 512


class KnowledgeBaseNotReady(Exception):
    """FAQ 지식베이스를 읽지 못함(라우터에서 503으로 매핑)."""


# --- 결정적 임베딩 ---------------------------------------------------------


def _seeded_vector(key: str, dim: int) -> np.ndarray:
    """키를 시드로 한 결정적 표준정규 벡터. 같은 키는 항상 같은 벡터를 준다."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()[:8]
    seed = int.from_bytes(digest, "little")
    return np.random.default_rng(seed).standard_normal(dim)


def _tokens(text: str) -> list[str]:
    """비교 단위 — 정규화된 문자열의 bigram(1글자면 그 글자 자체)."""
    plain = normalize(text)
    if len(plain) < 2:
        return [plain] if plain else []
    return [plain[i : i + 2] for i in range(len(plain) - 1)]


def embed(text: str, dim: int = _EMBED_DIM) -> np.ndarray:
    """bigram 해싱 임베딩. 코사인이 bigram 집합 유사도를 근사한다(L2 정규화)."""
    tokens = _tokens(text)
    if not tokens:
        return np.zeros(dim, dtype=np.float32)
    stacked = np.sum([_seeded_vector(token, dim) for token in tokens], axis=0)
    norm = np.linalg.norm(stacked)
    if norm == 0.0:
        return np.zeros(dim, dtype=np.float32)
    return (stacked / norm).astype(np.float32)


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    """두 정규화 벡터의 코사인(= 내적)."""
    return float(np.dot(left, right))


# --- B-1: 질문 판별 --------------------------------------------------------

# `test/model_selection/chat_agent.py`의 `_rule_based_faq_hint`에서 승격.
# 노트북 5.1이 지적한 대로 recall 한계가 있다 — 라벨 데이터가 쌓이면 모델로 교체 검토.
_QUESTION_PATTERN = re.compile(
    r"[?？]|얼마|언제|어디|어떻게|가능한가요|있나요|있어요|되나요|되요|되나|맞나요|"
    r"재고|사이즈|배송|교환|반품|결제"
)


class QuestionDetector:
    """상품/판매 관련 질문인지 가늠하는 값싼 규칙 필터."""

    def is_question(self, text: str) -> bool:
        return bool(_QUESTION_PATTERN.search(text))


# --- B-2: 유사질문 클러스터링 ----------------------------------------------


@dataclass
class Cluster:
    """한 방송 세션 안에서 같은 질문으로 묶인 발화 묶음."""

    ticket: str
    live_id: int
    canonical: str  # 클러스터를 처음 연 질문 문장
    vector: np.ndarray
    size: int = 1


@dataclass
class QuestionClusterer:
    """`live_id` 단위로만 누적한다 — 방송이 다르면 같은 질문이어도 별개 클러스터다."""

    similarity_threshold: float
    _clusters: dict[int, list[Cluster]] = field(default_factory=dict)

    def add(self, live_id: int, question: str) -> Cluster:
        """질문을 클러스터에 넣고(없으면 신규 생성) 갱신된 클러스터를 돌려준다."""
        vector = embed(question)
        buckets = self._clusters.setdefault(live_id, [])

        best: Cluster | None = None
        best_score = 0.0
        for cluster in buckets:
            score = cosine(cluster.vector, vector)
            if score > best_score:
                best, best_score = cluster, score

        if best is not None and best_score >= self.similarity_threshold:
            best.size += 1
            return best

        cluster = Cluster(
            ticket=_make_ticket(live_id, question),
            live_id=live_id,
            canonical=question,
            vector=vector,
        )
        buckets.append(cluster)
        return cluster

    def clear(self) -> None:
        self._clusters.clear()


def _make_ticket(live_id: int, question: str) -> str:
    """방송 + 질문 내용으로 결정되는 안정적인 티켓 id."""
    digest = hashlib.sha256(normalize(question).encode("utf-8")).hexdigest()[:6]
    return f"a_{live_id}_{digest}"


# --- B-3: 근거 검색 (RAG 비워둔 자리) --------------------------------------


@dataclass(frozen=True)
class RetrievedDoc:
    """검색된 근거 문서 한 건."""

    doc_id: str
    question: str
    answer: str
    score: float


class Retriever(ABC):
    """질문으로 근거 문서를 찾는 인터페이스. 평가 파이프라인 전용(모듈 docstring 참고)."""

    @abstractmethod
    def search(self, query: str, top_k: int) -> list[RetrievedDoc]:
        """유사도 내림차순 상위 top_k 문서. 없으면 빈 리스트."""
        raise NotImplementedError


class MockRetriever(Retriever):
    """목업 FAQ JSON + 결정적 bigram 임베딩 코사인 검색. 평가 파이프라인의 기준 구현."""

    def __init__(self, path: Path = _MOCK_FAQ_FILE) -> None:
        self._path = path
        self._docs: list[tuple[dict, np.ndarray]] | None = None

    def _load(self) -> list[tuple[dict, np.ndarray]]:
        if self._docs is None:
            try:
                rows = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise KnowledgeBaseNotReady(
                    f"목업 FAQ 지식베이스를 읽을 수 없습니다: {self._path}"
                ) from exc
            if not rows:
                raise KnowledgeBaseNotReady(f"목업 FAQ 지식베이스가 비어 있습니다: {self._path}")
            # 검색 대상 텍스트는 질문 + 태그 — 답변 본문까지 넣으면 무관한 문서가 딸려 온다.
            self._docs = [
                (row, embed(f"{row['question']} {' '.join(row.get('tags', []))}")) for row in rows
            ]
        return self._docs

    def search(self, query: str, top_k: int) -> list[RetrievedDoc]:
        query_vec = embed(query)
        scored = [
            RetrievedDoc(
                doc_id=row["doc_id"],
                question=row["question"],
                answer=row["answer"],
                score=round(cosine(query_vec, vec), 4),
            )
            for row, vec in self._load()
        ]
        scored.sort(key=lambda doc: doc.score, reverse=True)
        return scored[:top_k]


def build_retriever(key: str | None = None) -> Retriever:
    """평가 파이프라인 전용 조립 지점 — 프로덕션 서비스는 더 이상 이걸 안 쓴다."""
    resolved = key or registry.ACTIVE_RETRIEVER
    if resolved == "mock":
        return MockRetriever()
    raise ValueError(f"등록되지 않은 retriever 백엔드입니다: {resolved!r}")
