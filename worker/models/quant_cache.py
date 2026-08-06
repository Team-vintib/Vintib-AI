"""4bit 양자화 가중치를 디스크에 캐싱하는 공용 헬퍼.

VLM(quality_vlm)과 FLUX 텍스트 인코더(tryon_flux) 둘 다 bitsandbytes 4bit로 로드하는데,
가중치 자체는 이미 로컬 HF 캐시에 있는데도 매 job마다 `BitsAndBytesConfig`로 런타임
양자화를 다시 계산하는 게 로딩 시간(job당 1~2분)의 실제 병목이었다.

최초 1회 양자화한 결과를 `model.save_pretrained()`로 저장해두면, 저장된 체크포인트의
`config.json`에 `quantization_config`가 함께 기록되어 이후 `from_pretrained()`가
재양자화 없이 그대로 로드한다.

설계: `docs/plans/AI/CH022-worker-quant-weight-cache.md`
"""

import os
from pathlib import Path

CACHE_ROOT = Path(
    os.getenv("WORKER_QUANT_CACHE_DIR", str(Path(__file__).resolve().parent.parent / ".cache" / "quantized"))
)


def cached_path(model_id: str, subfolder: str | None = None) -> Path:
    """model_id(+subfolder)별 캐시 디렉터리. '/' 는 파일시스템에 못 쓰니 '__'로 치환."""
    name = model_id.replace("/", "__")
    if subfolder:
        name = f"{name}__{subfolder}"
    return CACHE_ROOT / name


def is_cached(path: Path) -> bool:
    """save_pretrained()가 끝까지 성공했는지의 최소 확인 -- config.json 존재 여부."""
    return (path / "config.json").exists()
