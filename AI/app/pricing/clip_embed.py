"""CLIP 이미지 임베딩 — 파인튜닝된 fashion-clip 카테고리 백본에서 뽑는다.

`internal_clip` comps 백엔드(CH020) 전용. 무거운 의존성(torch/transformers/httpx)은
함수 내부에서 지연 import한다 — `gms.py`의 지연 `httpx` import와 같은 이유로,
comps 백엔드가 mock/llm_web_search면 이 모듈이 로드돼도 아무 것도 안 당겨온다.

⚠️ **이 백엔드는 torch가 필요하다.** `ai` 게이트웨이 컨테이너는 GPU도 torch도 없다
(`docs/infra-architecture.md` §6, `mem_limit: 1g`) — 다른 torch 필요 기능(품질검수·시착·
분류)은 전부 큐+워커 구조를 쓰는데 가격책정만 컨테이너 내부 동기 처리라 예외다. 이 모듈은
로컬/개발 환경에서 메커니즘을 검증하는 용도이고, EC2 배포는 품질검수처럼 큐+워커로
재배선해야 한다(CH020 범위 밖).

체크포인트 로딩은 `aihub_finetune_vit.py`의 `--init-checkpoint` 경로(`backbone_state_dict`
+ `drop_incompatible_keys()`)와 같은 로직이다 — `validation/`을 프로덕션에서 import하지
않는 규약이라 그 판단 로직만 복사한다.

설계: `.claude/plans/ai/CH020-internal-clip-price-comps.md`
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

EMBEDDING_DIM = 512  # fashion-clip / CLIP ViT-B/32 projection_dim


class ClipEmbedNotReady(Exception):
    """torch/transformers 미설치, 체크포인트 파일 없음 등 — 호출부에서 CompsUnavailable로
    승격한다."""


@dataclass
class ClipBundle:
    model: Any
    processor: Any
    device: str


def _select_device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _drop_incompatible_keys(checkpoint_state: dict, model: Any) -> dict:
    """`aihub_finetune_vit.drop_incompatible_keys()`와 같은 판단(키 존재 + shape 일치)만
    프로덕션 쪽에 복사한 것 — `strict=False`는 shape가 다른 키까지 봐주지 않아 RuntimeError가
    나므로 미리 걸러야 한다."""
    model_state = model.state_dict()
    return {
        key: value
        for key, value in checkpoint_state.items()
        if key in model_state and model_state[key].shape == value.shape
    }


@lru_cache
def _load_bundle(checkpoint_path: str, model_id: str) -> ClipBundle:
    """체크포인트를 프로세스당 1회만 로드한다(torch 모델 로드는 비싸다)."""
    import torch
    from transformers import AutoModel, AutoProcessor

    device = _select_device()
    try:
        model = AutoModel.from_pretrained(model_id)
        model.to(device)
        checkpoint = torch.load(checkpoint_path, map_location=device)
        compatible = _drop_incompatible_keys(checkpoint["backbone_state_dict"], model)
        model.load_state_dict(compatible, strict=False)
        model.eval()
        processor = AutoProcessor.from_pretrained(model_id, use_fast=True)
    except (ImportError, FileNotFoundError, KeyError) as exc:
        raise ClipEmbedNotReady(f"CLIP 임베딩 백엔드를 불러오지 못했습니다: {exc}") from exc
    return ClipBundle(model=model, processor=processor, device=device)


def embed_image(image: Any, *, checkpoint_path: str, model_id: str) -> list[float]:
    """PIL 이미지 1장 → L2 정규화된 임베딩 벡터(`EMBEDDING_DIM`차원)."""
    import torch

    bundle = _load_bundle(checkpoint_path, model_id)
    inputs = bundle.processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = bundle.model.get_image_features(
            pixel_values=inputs["pixel_values"].to(bundle.device)
        )
        # transformers 버전에 따라 get_image_features()가 이미 투영된 텐서를 바로 주기도
        # 하고(구버전), BaseModelOutputWithPooling으로 감싸 주기도 한다(신버전, 5.x 실측,
        # worker/models/sam3/garment_embedding.py에서 같은 문제로 먼저 발견) — 이땐
        # .pooler_output이 실제 projection_dim 텐서다. requirements-pipeline.txt가
        # transformers>=4.44로 상한이 없어 5.x가 설치될 수 있다.
        if hasattr(features, "pooler_output"):
            features = features.pooler_output
        features = features / features.norm(dim=-1, keepdim=True)
    return features[0].cpu().tolist()


def embed_image_from_url(image_url: str, *, checkpoint_path: str, model_id: str) -> list[float]:
    """presigned URL → 다운로드 → `embed_image()`.

    이미지 다운로드를 게이트웨이가 직접 하는 유일한 경우다 — 다른 도메인(품질검수·분류)은
    전부 워커가 이미 로드된 이미지를 받아 처리한다. `internal_clip`은 컨테이너 내부 동기
    처리(§ 모듈 docstring)라 여기서 직접 받는다.
    """
    import io

    import httpx
    from PIL import Image

    try:
        response = httpx.get(image_url, timeout=10.0)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001 — 원인이 다양해(네트워크/디코드) 전부 승격
        raise ClipEmbedNotReady(f"이미지를 받지 못했습니다: {exc}") from exc
    return embed_image(image, checkpoint_path=checkpoint_path, model_id=model_id)
