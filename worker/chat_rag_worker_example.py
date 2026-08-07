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
# 싶지만, 워커는 AI/ 코드를 import하지 않는 원칙(worker/README.md)이라 여기 재선언한다.
# 0.35는 bigram 임베딩 기준 정책 제안치였는데, KURE-v1로 실측해보니(S15P11A108-444) 무관한
# 질문끼리도 코사인이 ~0.42까지 나와서 너무 낮았다 — bigram과 KURE-v1은 유사도 분포 자체가
# 다르다(무관한 문장의 "기본 유사도"가 다르다). 정확한 값은 실데이터로 다시 스윕해야 하고,
# 그 전까지는 오탐(그라운딩 오판)을 줄이는 쪽으로 넉넉히 잡는다.
GROUNDING_THRESHOLD = 0.70


def _load_preferring_cache(loader, *args, **kwargs):
    """로컬 HF 캐시에 가중치가 있으면 그걸 바로 쓰고, 없을 때만 온라인으로 받는다.

    `HF_HUB_OFFLINE`을 안 켜두면 캐시가 있어도 매번 Hub에 최신 리비전인지 확인하러
    나간다 — 그 사이 upstream 리비전이 바뀌어 있으면(실측: LFM2.5-230M) 이미 받아둔
    가중치가 그대로 있는데도 통째로 다시 받는다. 여기서 오프라인 로드를 먼저 시도해
    그 왕복 자체를 건너뛰고, 캐시에 없는 것만(최초 1회) 온라인으로 받는다.
    """
    previous = os.environ.get("HF_HUB_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    try:
        return loader(*args, **kwargs)
    except Exception:
        pass
    finally:
        if previous is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = previous

    print("[chat_rag] 로컬 캐시에 없어 온라인으로 새로 받습니다...")
    return loader(*args, **kwargs)


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
        from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
        from sentence_transformers import SentenceTransformer
        from transformers import pipeline

        self._embed_model = _load_preferring_cache(SentenceTransformer, "nlpai-lab/KURE-v1")
        text_gen = _load_preferring_cache(
            pipeline,
            "text-generation",
            model="LiquidAI/LFM2.5-230M",
            device="cuda",
            max_new_tokens=200,
            return_full_text=False,  # 기본값(True)이면 입력 프롬프트까지 답변에 그대로 섞여 나온다
        )
        # LFM2.5-230M은 채팅용으로 튜닝된 모델(자체 chat_template 보유)이다. 맨 문자열을
        # 그대로 이어쓰기시키면(HuggingFacePipeline 단독 사용) 모델이 학습 때 본 채팅 형식과
        # 안 맞아 엉뚱한 대화를 이어가는 문제가 있었다(실측: "자켓 얼마에요?"에 "받았네요!"라고
        # 답함) — ChatHuggingFace로 감싸 system/user 역할이 있는 채팅 템플릿을 제대로 태운다.
        self._llm = ChatHuggingFace(llm=HuggingFacePipeline(pipeline=text_gen))
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

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(
                content=(
                    "당신은 라이브 방송 채팅에서 시청자 질문에 답하는 친절한 안내 도우미입니다. "
                    "주어진 판매자 발언 내용만 근거로 답하세요. 내용에 없는 정보는 절대 지어내지 "
                    "마세요. 존댓말로, 친근하고 상냥하게, 한두 문장으로 간결하게 답하세요. "
                    "'45000원'처럼 단답으로 끝내지 말고 자연스러운 문장으로 답하세요."
                )
            ),
            HumanMessage(content=f"방송 발언: {context}\n질문: {question}"),
        ]
        return self._llm.invoke(messages).content.strip()


if __name__ == "__main__":
    ChatRagWorker().loop()
