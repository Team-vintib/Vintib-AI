"""SAM3 의류 크롭 → zero-shot CLIP 임베딩 (유사 상품 추천용).

**원본(zero-shot) `patrickjohncyh/fashion-clip`만 쓴다** — 카테고리/색상 파인튜닝 체크포인트는
쓰지 않는다. `aihub_embedding_quality_check.py`(AI/validation/CLASS/product-info-finetune/)로
실측한 결과, 분류 파인튜닝은 카테고리 간 관계 정보를 거의 파괴했다(카테고리 내부/카테고리 간
평균 코사인 유사도 차이가 zero-shot 0.066 → 파인튜닝 0.553, 대부분 카테고리 간 유사도가
0.585→0.002로 붕괴한 것에서 옴) — 분류 정확도엔 좋아도 일반적인 시각적 유사도(추천 용도)엔
나쁘다. 그래서 체크포인트 로딩 코드 자체가 없다 — `app/pricing/clip_embed.py`(파인튜닝
체크포인트 지원)보다 훨씬 단순하다.

`SegmentationResult.garment_crop`(SAM3가 하자 탐지 전에 이미 만들어 둔, 배경 제거된 의류
크롭)을 그대로 입력으로 받는다 — 새 세그멘테이션을 하지 않는다.

torch/transformers는 함수 내부에서 지연 import한다(`worker/models/quality_vlm/loader.py`와
같은 관례) — mock 세그멘터 경로는 이 모듈을 아예 안 건드린다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

EMBEDDING_DIM = 512  # fashion-clip / CLIP ViT-B/32 projection_dim
EMBEDDING_MODEL_ID = "patrickjohncyh/fashion-clip"


class GarmentEmbeddingNotReady(Exception):
    """torch/transformers 미설치 등 — 호출부가 무시하고 넘어갈 수 있게 구분한다."""


@dataclass
class _Bundle:
    model: Any
    processor: Any
    device: str


_bundle: _Bundle | None = None


def _ensure_loaded() -> _Bundle:
    """모델을 지연 로드한다(프로세스당 1회) — `Qwen3VlDescriber._ensure_loaded()`와 같은
    지연-싱글턴 패턴. 체크포인트가 없으니 로딩은 `AutoModel.from_pretrained() 하나뿐이다."""
    global _bundle
    if _bundle is not None:
        return _bundle

    try:
        import torch
        from transformers import AutoModel, AutoProcessor
    except ImportError as exc:
        raise GarmentEmbeddingNotReady(
            "임베딩 계산에는 torch/transformers가 필요합니다"
        ) from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModel.from_pretrained(EMBEDDING_MODEL_ID).to(device).eval()
    processor = AutoProcessor.from_pretrained(EMBEDDING_MODEL_ID, use_fast=True)
    _bundle = _Bundle(model=model, processor=processor, device=device)
    return _bundle


def embed_garment(image: Any) -> list[float]:
    """의류 크롭(PIL 이미지) → L2 정규화된 `EMBEDDING_DIM`차원 벡터."""
    import torch

    bundle = _ensure_loaded()
    inputs = bundle.processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = bundle.model.get_image_features(
            pixel_values=inputs["pixel_values"].to(bundle.device)
        )
        # transformers 버전에 따라 get_image_features()가 이미 투영된 텐서를 바로 주기도
        # 하고(구버전), BaseModelOutputWithPooling으로 감싸 주기도 한다(신버전, 5.x 실측) —
        # 이땐 .pooler_output이 실제 projection_dim 텐서다(last_hidden_state는 투영 전
        # 768차원이라 다르다). 둘 다 받아낸다.
        if hasattr(features, "pooler_output"):
            features = features.pooler_output
        features = features / features.norm(dim=-1, keepdim=True)
    return features[0].cpu().tolist()
