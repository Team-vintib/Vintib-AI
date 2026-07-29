"""chat_rag 워커 — 반복질문 답변 생성(검색+랭킹+그라운딩+생성을 한 번에).

게이트웨이는 이 방송(`live_id`)의 문서 후보를 벡터 검색 없이 그대로 job payload에 실어
보낸다(`app/chat/rag_store.py`). 이 워커가 KURE-v1로 질문·후보를 그 자리에서 임베딩·랭킹하고,
그라운딩 임계치를 넘으면 LangChain + `LiquidAI/LFM2.5-230M`으로 답변까지 생성해서 돌려준다.
검색·그라운딩 판단·생성을 왕복 1회로 합친 이유는 방송 하나당 문서 수가 많지 않아서다
(`AI/docs/chat-rag-storage.md`) — pgvector의 ANN 검색이 굳이 필요 없는 규모다.

**GPU 없이도 돌릴 수 있다.** `CHAT_RAG_BACKEND=mock`(기본값)이면 실제 모델 없이 결정적인
임베딩과 "최상위 후보 문서를 그대로 반환"(환각 없음, `TemplateAnswerGenerator`와 같은 안전한
기본값)으로 job 큐 왕복 전체를 검증한다.

```bash
CHAT_RAG_BACKEND=mock python chat_rag_worker_example.py             # GPU 불필요, 기본값
CHAT_RAG_BACKEND=lfm2_langchain python chat_rag_worker_example.py   # 실제 모델
```

설계: .claude/plans/ai/009-chat-rag-generator.md
"""

import hashlib
import os

import numpy as np

from base_worker import BaseWorker

CHAT_RAG_BACKEND = os.getenv("CHAT_RAG_BACKEND", "mock")

# nlpai-lab/KURE-v1 출력 차원. app/chat/rag_store.py, stt_worker_example.py의 같은 이름 상수와
# 반드시 같아야 한다(별도 코드베이스라 주석으로만 동기화된다).
EMBEDDING_DIM = 1024

# app/chat/registry.py의 EMBEDDER_BACKENDS["kure_v1"]["grounding_threshold"]와 같은 값을 쓰고
# 싶지만, 워커는 AI/ 코드를 import하지 않는 원칙(worker/README.md)이라 여기 재선언한다. 실측
# 전까지는 정책 제안치(registry.py의 POLICY_GROUNDING_THRESHOLD)를 그대로 쓴다.
GROUNDING_THRESHOLD = 0.35


def _mock_embedding(text: str, dim: int = EMBEDDING_DIM) -> np.ndarray:
    """실 모델 없이도 검증 가능한 결정적 벡터(`stt_worker_example.py`와 같은 착상)."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()[:8]
    seed = int.from_bytes(digest, "little")
    vector = np.random.default_rng(seed).standard_normal(dim)
    return (vector / np.linalg.norm(vector)).astype(np.float32)


class ChatRagWorker(BaseWorker):
    feature = "chat_rag"

    def __init__(self):
        super().__init__()
        self._embed_model = None
        self._llm = None

    def _ensure_loaded(self):
        """모델은 워커 프로세스당 한 번만 로드한다. mock 백엔드는 로드할 게 없다."""
        if CHAT_RAG_BACKEND == "mock" or self._embed_model is not None:
            return
        print(f"[{self.worker_id}] 임베딩/생성 모델 로딩 중... (backend={CHAT_RAG_BACKEND})")
        from langchain_huggingface import HuggingFacePipeline
        from sentence_transformers import SentenceTransformer
        from transformers import pipeline

        self._embed_model = SentenceTransformer("nlpai-lab/KURE-v1")
        text_gen = pipeline(
            "text-generation", model="LiquidAI/LFM2.5-230M", device="cuda", max_new_tokens=200
        )
        self._llm = HuggingFacePipeline(pipeline=text_gen)
        print(f"[{self.worker_id}] 로딩 완료")

    def _embed(self, text: str) -> np.ndarray:
        if CHAT_RAG_BACKEND == "mock":
            return _mock_embedding(text)
        vector = self._embed_model.encode(text, normalize_embeddings=True)
        return np.asarray(vector, dtype=np.float32)

    def run_inference(self, payload: dict) -> dict:
        """
        payload 예:
        {
            "ticket": "a_42_ab12cd",
            "live_id": 42,
            "question": "이거 프리사이즈인가요?",
            "cluster_size": 2,
            "docs": [{"id": 1, "content": "이 니트는 프리사이즈이며..."}, ...]
        }

        반환:
        - 근거 부족: {"grounded": False}
        - 근거 있음: {"grounded": True, "answer": ..., "grounding_score": ..., "sources": [...]}
        """
        docs = payload["docs"]
        if not docs:
            return {"grounded": False}

        self._ensure_loaded()
        query_vec = self._embed(payload["question"])

        scored = [(float(np.dot(query_vec, self._embed(doc["content"]))), doc) for doc in docs]
        scored.sort(key=lambda item: item[0], reverse=True)
        top_score, top_doc = scored[0]

        if top_score < GROUNDING_THRESHOLD:
            # "근거 있는 경우에만 응답" — 근거가 약하면 침묵한다(app/chat/faq.py의 기존 원칙과 동일).
            return {"grounded": False}

        answer = self._generate(payload["question"], top_doc["content"])
        return {
            "grounded": True,
            "answer": answer,
            "grounding_score": round(top_score, 4),
            "sources": [{"doc_id": str(top_doc["id"]), "score": round(top_score, 4)}],
        }

    def _generate(self, question: str, context: str) -> str:
        if CHAT_RAG_BACKEND == "mock":
            # 생성 없이 근거 문단을 그대로 반환 — 환각 없음. TemplateAnswerGenerator와 같은 안전한 기본값.
            return context

        prompt = (
            "다음은 라이브 방송에서 판매자가 한 말입니다. 이 내용만 근거로 질문에 짧게 답하세요.\n"
            f"방송 발언: {context}\n질문: {question}\n답변:"
        )
        return self._llm.invoke(prompt).strip()


if __name__ == "__main__":
    ChatRagWorker().loop()
