"""STT 워커 — 라이브 발언 전사(Whisper) + 임베딩(KURE-v1) 계산.

전사 텍스트를 pgvector에 저장하려면 임베딩이 필요한데, 게이트웨이(`ai` 컨테이너)엔 torch가
없어 계산을 못 한다(`AI/docs/chat-rag-storage.md`). 이 워커는 이미 Whisper 때문에 torch를
들고 있으므로, 같은 프로세스 안에서 KURE-v1 임베딩까지 끝내서 게이트웨이엔 텍스트+벡터를
그대로 넘긴다 — 게이트웨이는 계산 없이 저장만 한다(`app/gateway/router.py`의 `submit_result`).

**GPU 없이도 돌릴 수 있다.** `STT_BACKEND=mock`(기본값)이면 오디오를 실제로 내려받지도
전사하지도 않고 결정적인 더미 텍스트+임베딩을 반환한다 — job 등록→워커 처리→게이트웨이
적재까지 전체 경로를 검증하는 데 쓴다(품질검수 워커의 `QUALITY_BACKEND=mock`과 같은 목적).

```bash
STT_BACKEND=mock python stt_worker_example.py             # GPU 불필요, 기본값
STT_BACKEND=faster_whisper python stt_worker_example.py   # 실제 모델
```

**아직 실제 방송 오디오로는 검증할 수 없다** — OpenVidu(방송 녹화)가 로드맵상 미설치라
`audio_url`을 채워줄 곳이 없다. 로컬 오디오 파일을 올려서 URL로 넘기는 식으로만 확인 가능.

설계: .claude/plans/ai/008-stt-worker.md
"""

import hashlib
import io
import os

import numpy as np

from base_worker import BaseWorker
from storage_utils import download_bytes

STT_BACKEND = os.getenv("STT_BACKEND", "mock")

# nlpai-lab/KURE-v1 출력 차원. app/chat/rag_store.py의 EMBEDDING_DIM과 반드시 같아야 한다 —
# 워커와 게이트웨이가 별도 코드베이스라 상수를 공유하지 못해 주석으로 동기화한다.
EMBEDDING_DIM = 1024


def _mock_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """실 모델 없이도 검증 가능한 결정적 벡터(`app/chat/faq.py`의 bigram 해싱과 같은 착상)."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()[:8]
    seed = int.from_bytes(digest, "little")
    vector = np.random.default_rng(seed).standard_normal(dim)
    return (vector / np.linalg.norm(vector)).astype(np.float32).tolist()


class SttWorker(BaseWorker):
    feature = "stt"

    def __init__(self):
        super().__init__()
        self._whisper_model = None
        self._embed_model = None

    def _ensure_loaded(self):
        """모델은 워커 프로세스당 한 번만 로드한다. mock 백엔드는 로드할 게 없다."""
        if STT_BACKEND == "mock" or self._whisper_model is not None:
            return
        print(f"[{self.worker_id}] STT/임베딩 모델 로딩 중... (backend={STT_BACKEND})")
        from faster_whisper import WhisperModel
        from sentence_transformers import SentenceTransformer

        self._whisper_model = WhisperModel("small", device="cuda", compute_type="float16")
        self._embed_model = SentenceTransformer("nlpai-lab/KURE-v1")
        print(f"[{self.worker_id}] 로딩 완료")

    def run_inference(self, payload: dict) -> dict:
        """
        payload 예:
        {
            "audio_url": "https://.../chunk.mp4",
            "live_id": 42
        }
        """
        live_id = int(payload["live_id"])

        if STT_BACKEND == "mock":
            text = f"[mock STT] live_id={live_id} 오디오 전사 결과"
            return {"text": text, "embedding": _mock_embedding(text), "live_id": live_id}

        self._ensure_loaded()

        # faster-whisper는 내부적으로 ffmpeg로 디코딩하므로 MP4를 그대로 넘겨도 오디오
        # 트랙만 읽는다 — 별도 오디오 추출 스텝이 필요 없다.
        audio_bytes = download_bytes(payload["audio_url"])
        segments, _ = self._whisper_model.transcribe(io.BytesIO(audio_bytes), language="ko")
        text = "".join(segment.text for segment in segments).strip()

        embedding = self._embed_model.encode(text, normalize_embeddings=True).tolist()
        return {"text": text, "embedding": embedding, "live_id": live_id}


if __name__ == "__main__":
    SttWorker().loop()
