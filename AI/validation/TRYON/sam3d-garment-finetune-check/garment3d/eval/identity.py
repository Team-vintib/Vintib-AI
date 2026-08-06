"""identity — 얼굴 임베딩의 프레임 간 / 원본 대비 코사인 유사도.

**측정 대상**: 회전하는 동안 같은 사람으로 보이는가. I2V 는 뒤 프레임에서 얼굴을 새로
생성하므로 정체성이 흐트러지기 쉽다.

⚠️ **의류 단독 크롭에는 얼굴이 없다.** 그 케이스에서는 `EvalConfig.measure_identity=False` 로
끄고, 지표를 `None` 으로 남긴다 — 0 으로 채우면 "정체성이 완전히 무너졌다"로 오독된다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


class FaceEmbedder(ABC):
    """프레임 → 얼굴 임베딩. 얼굴을 못 찾으면 None."""

    name: str = "abstract"

    @abstractmethod
    def embed(self, frame: np.ndarray) -> np.ndarray | None: ...

    def embed_sequence(self, frames: np.ndarray) -> list[np.ndarray | None]:
        return [self.embed(frames[t]) for t in range(len(frames))]


class PatchFaceEmbedder(FaceEmbedder):
    """상단 중앙 패치를 축소해 L2 정규화한 **프록시 임베딩.**

    얼굴 검출을 하지 않는다 — 상단 중앙에 얼굴이 있다고 가정한다. 실제 얼굴 인식이 아니므로
    사람 판별에는 쓸 수 없지만, **"프레임 간 그 영역이 얼마나 변하는가"** 라는 질문에는 답한다.
    턴테이블/I2V 에 같은 프록시를 적용하므로 비교는 성립한다.

    실측에는 `insightface`(ArcFace) 백엔드를 써야 한다.
    """

    name = "dummy"

    def __init__(self, patch: tuple[float, float, float, float] = (0.05, 0.35, 0.3, 0.7)) -> None:
        """
        Args:
            patch: `(top, bottom, left, right)` 상대 좌표. 기본값은 상단 중앙 영역.
        """
        self.patch = patch

    def embed(self, frame: np.ndarray) -> np.ndarray | None:
        frame = np.asarray(frame, dtype=np.float64)
        height, width = frame.shape[:2]
        top, bottom, left, right = self.patch
        region = frame[
            int(top * height) : int(bottom * height), int(left * width) : int(right * width)
        ]
        if region.size == 0:
            return None
        # 8x8 그리드로 평균 풀링해 저차원 기술자로. 영역이 8px 보다 작으면 그리드를 줄인다 —
        # 그냥 8 로 두면 빈 블록의 mean() 이 nan 을 만들어 코사인이 조용히 0 이 된다.
        grid = int(min(8, region.shape[0], region.shape[1]))
        if grid < 1:
            return None
        cells = [
            np.asarray([block.mean() for block in np.array_split(row, grid, axis=1)])
            for row in np.array_split(region, grid, axis=0)
        ]
        vector = np.concatenate(cells).astype(np.float64)
        norm = float(np.linalg.norm(vector))
        if norm < 1e-12:
            return None
        return vector / norm


class InsightFaceEmbedder(FaceEmbedder):
    """ArcFace(insightface) 백엔드. 설치돼 있을 때만."""

    name = "insightface"

    def __init__(self, model_name: str = "buffalo_l") -> None:
        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise RuntimeError(
                "insightface 가 없습니다: pip install insightface " "(또는 eval.face_backend=dummy)"
            ) from exc
        self._app = FaceAnalysis(name=model_name)
        self._app.prepare(ctx_id=-1)

    def embed(self, frame: np.ndarray) -> np.ndarray | None:
        faces = self._app.get(np.asarray(frame, dtype=np.uint8)[..., ::-1])  # RGB -> BGR
        if not faces:
            return None
        # 가장 큰 얼굴 하나만.
        face = max(faces, key=lambda f: float(np.prod(f.bbox[2:] - f.bbox[:2])))
        embedding = np.asarray(face.normed_embedding, dtype=np.float64)
        norm = float(np.linalg.norm(embedding))
        return embedding / norm if norm > 1e-12 else None


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """코사인 유사도. 영벡터는 0."""
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator < 1e-12:
        return 0.0
    return float(np.dot(a, b) / denominator)


@dataclass(frozen=True)
class IdentityMetrics:
    """정체성 일관성. **높을수록 좋다** (`detect_ratio` 제외 — 그건 신뢰도 지표다)."""

    #: 인접 프레임 임베딩 코사인 유사도 평균
    consecutive_cosine_mean: float
    #: 그 최솟값 — 최악 프레임
    consecutive_cosine_min: float
    #: 첫 프레임(=원본 입력) 대비 평균 유사도. I2V 는 뒤로 갈수록 떨어진다.
    reference_cosine_mean: float
    #: 마지막 프레임의 원본 대비 유사도 — 단조 붕괴를 직접 본다
    reference_cosine_last: float
    #: 임베딩을 얻은 프레임 비율. 낮으면 위 숫자를 신뢰하지 말 것
    detect_ratio: float
    backend: str
    num_frames: int

    def as_row(self) -> dict[str, float]:
        return {
            "identity_cosine_mean": self.consecutive_cosine_mean,
            "identity_cosine_min": self.consecutive_cosine_min,
            "identity_vs_reference_mean": self.reference_cosine_mean,
            "identity_vs_reference_last": self.reference_cosine_last,
            "identity_detect_ratio": self.detect_ratio,
        }


def identity_metrics(
    frames: np.ndarray,
    *,
    embedder: FaceEmbedder | None = None,
    reference: np.ndarray | None = None,
) -> IdentityMetrics | None:
    """정체성 지표. 임베딩을 하나도 못 얻으면 **None** 을 돌려준다(0 으로 채우지 않는다).

    Args:
        reference: 원본 입력 이미지. None 이면 첫 프레임을 기준으로 쓴다.
    """
    frames = np.asarray(frames)
    if len(frames) < 2:
        raise ValueError("identity 지표는 프레임이 2장 이상이어야 계산됩니다")

    embedder = embedder or PatchFaceEmbedder()
    embeddings = embedder.embed_sequence(frames)
    detected = [e for e in embeddings if e is not None]
    if len(detected) < 2:
        return None

    reference_embedding = embedder.embed(reference) if reference is not None else embeddings[0]

    consecutive = [
        cosine(embeddings[t - 1], embeddings[t])
        for t in range(1, len(embeddings))
        if embeddings[t - 1] is not None and embeddings[t] is not None
    ]
    against_reference = (
        [cosine(reference_embedding, e) for e in embeddings if e is not None]
        if reference_embedding is not None
        else []
    )

    return IdentityMetrics(
        consecutive_cosine_mean=float(np.mean(consecutive)) if consecutive else 0.0,
        consecutive_cosine_min=float(np.min(consecutive)) if consecutive else 0.0,
        reference_cosine_mean=float(np.mean(against_reference)) if against_reference else 0.0,
        reference_cosine_last=float(against_reference[-1]) if against_reference else 0.0,
        detect_ratio=float(len(detected) / len(embeddings)),
        backend=embedder.name,
        num_frames=int(len(frames)),
    )


def build_face_embedder(backend: str) -> FaceEmbedder:
    if backend == "dummy":
        return PatchFaceEmbedder()
    if backend == "insightface":
        return InsightFaceEmbedder()
    raise ValueError(f"알 수 없는 face 백엔드: {backend!r}")
