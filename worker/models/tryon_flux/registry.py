"""FLUX worn-reference 생성 백엔드 레지스트리 — 유일한 모델 스왑 지점.

`worker/models/quality_vlm/registry.py`/`sam3/registry.py`와 같은 패턴. `FLUX_BACKENDS`에
항목만 추가하고 `ACTIVE_FLUX_BACKEND`(또는 `TRYON_FLUX_BACKEND` 환경변수)만 바꾸면 된다.
"""

from typing import TypedDict


class FluxConfig(TypedDict):
    model_id: str | None
    transformer_gguf_url: str | None
    description: str
    num_inference_steps: int
    guidance_scale: float


FLUX_BACKENDS: dict[str, FluxConfig] = {
    # 기본 — 참조 이미지를 그대로 반환한다. torch/다운로드 불필요, 파이프라인 왕복(잡 폴링
    # → CatVTON 합성까지)을 GPU 없이 전부 검증할 수 있다.
    "mock": {
        "model_id": None,
        "transformer_gguf_url": None,
        "description": "참조 이미지를 그대로 반환하는 목업(의존성 없음)",
        "num_inference_steps": 0,
        "guidance_scale": 0.0,
    },
    # black-forest-labs/FLUX.2-klein-4B, GGUF Q4_0 양자화. AI/validation/TRYON/AI_tryon/
    # CatVTON/generate_worn_reference_outer_fitaware.py에서 검증한 설정을 그대로 가져왔다 —
    # "image=" 참조 편집 모드(원본 사진 참조 + "이 사람에게 입혀라" 프롬프트), 8스텝(24스텝과
    # 품질 차이 없음을 실측 확인, AI/docs/tryon-advancement-strategy.md §10.3).
    "flux2_klein": {
        "model_id": "black-forest-labs/FLUX.2-klein-4B",
        "transformer_gguf_url": (
            "https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF/blob/main/"
            "flux-2-klein-4b-Q4_0.gguf"
        ),
        "description": (
            "FLUX.2-Klein-4B, GGUF Q4_0 트랜스포머 + 4bit 텍스트 인코더. "
            "torch/diffusers/transformers/bitsandbytes/gguf 필요, ~5-6GB VRAM"
        ),
        "num_inference_steps": 8,
        "guidance_scale": 4.0,
    },
}
# 기본값. 워커는 `TRYON_FLUX_BACKEND` 환경변수로 이 값을 덮어쓴다.
ACTIVE_FLUX_BACKEND = "mock"


def flux_config(key: str | None = None) -> FluxConfig:
    """활성 FLUX 백엔드의 설정을 돌려준다."""
    resolved = key or ACTIVE_FLUX_BACKEND
    try:
        return FLUX_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 FLUX 백엔드입니다: {resolved!r}") from exc
