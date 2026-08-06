"""VLM 하자 설명 백엔드 레지스트리 — 유일한 모델 스왑 지점.

`worker/models/sam3/registry.py`의 `SegmenterConfig`/`segmenter_config()` 패턴을 그대로
따른다. 나중에 파인튜닝하거나 다른 모델로 바꾸려면 `VLM_BACKENDS`에 항목만 추가하고
`ACTIVE_VLM_BACKEND`(또는 `QUALITY_VLM_BACKEND` 환경변수)만 바꾸면 된다 — 코드 변경 없음.

설계: `.claude/plans/ai/CH011-quality-vlm-production-wiring.md`
"""

from typing import TypedDict


class VlmConfig(TypedDict):
    """VLM 백엔드 한 종류의 모델 ID + 생성 설정."""

    model_id: str | None
    description: str
    quantization: str  # "4bit" | "none" — loader.load_qwen_vl()의 quantization 인자
    max_new_tokens: int


VLM_BACKENDS: dict[str, VlmConfig] = {
    # 기본 — 정적 문구로 채운다. torch 불필요, CI에서 전 경로가 그대로 검증된다.
    "mock": {
        "model_id": None,
        "description": "정적 문구 기반 목업(의존성 없음)",
        "quantization": "none",
        "max_new_tokens": 0,
    },
    # Qwen/Qwen3-VL-4B-Instruct. AI/validation/QUAL/vlm-description-check/에서 검증한
    # 설정을 그대로 가져왔다 — 4bit 양자화, RTX 4070 Laptop(8GB) 기준 VRAM 약 2.7GB.
    # gated 저장소 아님(공개 체크포인트).
    "qwen3_vl": {
        "model_id": "Qwen/Qwen3-VL-4B-Instruct",
        "description": (
            "Qwen3-VL-4B-Instruct, bitsandbytes 4bit 양자화. "
            "torch>=2.4/transformers>=5.0/bitsandbytes 필요"
        ),
        "quantization": "4bit",
        "max_new_tokens": 80,
    },
}
# 기본값. 워커는 `QUALITY_VLM_BACKEND` 환경변수로 이 값을 덮어쓴다.
ACTIVE_VLM_BACKEND = "mock"


def vlm_config(key: str | None = None) -> VlmConfig:
    """활성 VLM 백엔드의 설정(모델 ID + 생성 옵션)을 돌려준다."""
    resolved = key or ACTIVE_VLM_BACKEND
    try:
        return VLM_BACKENDS[resolved]
    except KeyError as exc:
        raise ValueError(f"등록되지 않은 VLM 백엔드입니다: {resolved!r}") from exc
