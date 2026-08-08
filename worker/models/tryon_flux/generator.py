"""worn-reference 생성기 — 교체 경계.

`sam3/segmenter.py`의 `DefectSegmenter(ABC)` + `build_segmenter()` 패턴을 그대로
미러링한다. `generate(reference_image, prompt)`는 참조 사진(고객 본인 사진) + 편집
프롬프트를 받아 "그 사람이 그 옷을 그 핏으로 입은" worn-reference 이미지를 돌려준다.
"""

from abc import ABC, abstractmethod

from PIL import Image

from .registry import FluxConfig, flux_config

WIDTH, HEIGHT = 768, 1024


class WornReferenceGenerator(ABC):
    name: str

    @abstractmethod
    def generate(self, person_image: Image.Image, cloth_image: Image.Image, prompt: str) -> Image.Image:
        ...


class MockWornReferenceGenerator(WornReferenceGenerator):
    """참조 이미지를 그대로 반환한다. torch 불필요 — 잡 왕복 전 경로를 GPU 없이
    검증하려는 용도다."""

    name = "mock"

    def generate(self, person_image: Image.Image, cloth_image: Image.Image, prompt: str) -> Image.Image:
        return person_image.copy()


class Flux2KleinGenerator(WornReferenceGenerator):
    """FLUX.2-Klein-4B, GGUF Q4_0 양자화. `__init__`에서 즉시 로드(워커 프로세스당 1회) —
    `generate()` 호출마다 다시 로드하면 너무 느리다.

    `image=[person_image, cloth_image]`로 두 장을 함께 참조 이미지로 준다(FLUX.2 계열이
    여러 참조 이미지를 조합하는 편집을 지원 — `Flux2KleinPipeline.__call__`의 `image`
    파라미터가 원래 리스트를 받게 설계돼 있음). 사람 사진 한 장만 주고 옷은 텍스트 캡션으로만
    설명하던 이전 방식(`tryon_worker_catvton_legacy.py`)보다 색상·로고·질감 재현이 훨씬
    정확하다 — CatVTON 없이도 이 결과를 그대로 최종본으로 쓸 수 있는 이유(`CH027`).
    """

    name = "flux2_klein"

    def __init__(self, config: FluxConfig):
        self._config = config
        self._pipe = None
        self._load()

    def _load(self):
        import torch
        from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
        from transformers import AutoModelForCausalLM

        # 텍스트 인코더 4bit 양자화도 매번 다시 계산하면 느리다 -- 최초 1회만 계산해
        # quant_cache에 저장해두고 그다음부터는 재계산 없이 로드한다(CH022, quality_vlm/
        # loader.py의 load_qwen_vl()과 동일 패턴). transformer(GGUF)는 이미 사전 양자화된
        # 포맷이라 이 최적화 대상이 아니다.
        from quant_cache import cached_path, is_cached

        text_encoder_cache = cached_path(self._config["model_id"], subfolder="text_encoder")
        if is_cached(text_encoder_cache):
            text_encoder = AutoModelForCausalLM.from_pretrained(
                str(text_encoder_cache), torch_dtype=torch.bfloat16
            )
        else:
            from transformers import BitsAndBytesConfig

            quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
            text_encoder = AutoModelForCausalLM.from_pretrained(
                self._config["model_id"],
                subfolder="text_encoder",
                quantization_config=quant_config,
                torch_dtype=torch.bfloat16,
            )
            text_encoder.save_pretrained(str(text_encoder_cache))
        transformer = Flux2Transformer2DModel.from_single_file(
            self._config["transformer_gguf_url"],
            config=self._config["model_id"],
            subfolder="transformer",
            quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
            torch_dtype=torch.bfloat16,
        )
        self._pipe = Flux2KleinPipeline.from_pretrained(
            self._config["model_id"],
            transformer=transformer,
            text_encoder=text_encoder,
            torch_dtype=torch.bfloat16,
        )
        self._pipe.enable_model_cpu_offload()

    def generate(self, person_image: Image.Image, cloth_image: Image.Image, prompt: str) -> Image.Image:
        import torch

        generator = torch.Generator(device="cpu").manual_seed(1)
        image = self._pipe(
            image=[person_image, cloth_image],
            prompt=prompt,
            height=HEIGHT,
            width=WIDTH,
            num_inference_steps=self._config["num_inference_steps"],
            guidance_scale=self._config["guidance_scale"],
            generator=generator,
        ).images[0]
        return image

    def unload(self):
        """스테이지 종료 후 VRAM을 CatVTON에 넘겨주기 위해 명시적으로 해제한다 —
        VLM+FLUX+CatVTON을 한 프로세스에서 순차로 돌리는 전제(동시 상주 아님,
        AI/docs/tryon-advancement-strategy.md §10 프로덕션 반영 절 참고).

        `enable_model_cpu_offload()`가 건 accelerate 훅이 파이프라인과 참조 순환을
        만들어서, gc.collect() 없이 empty_cache()만 부르면 VRAM이 실제로는 반환되지
        않는다(다음 단계 VLM 4bit 로딩이 그만큼 못 들어가 CPU/disk 오프로드 에러로
        이어짐 -- 실측으로 확인)."""
        import gc

        import torch

        self._pipe = None
        gc.collect()
        torch.cuda.empty_cache()


def build_generator(key: str) -> WornReferenceGenerator:
    config = flux_config(key)
    if key == "mock":
        return MockWornReferenceGenerator()
    if key == "flux2_klein":
        return Flux2KleinGenerator(config)
    raise ValueError(f"등록되지 않은 FLUX 백엔드입니다: {key!r}")
