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
    def generate(self, reference_image: Image.Image, prompt: str) -> Image.Image:
        ...


class MockWornReferenceGenerator(WornReferenceGenerator):
    """참조 이미지를 그대로 반환한다. torch 불필요 — 잡 왕복/CatVTON 합성 단계까지
    GPU 없이 전 경로를 검증하려는 용도다."""

    name = "mock"

    def generate(self, reference_image: Image.Image, prompt: str) -> Image.Image:
        return reference_image.copy()


class Flux2KleinGenerator(WornReferenceGenerator):
    """FLUX.2-Klein-4B, GGUF Q4_0 양자화. `__init__`에서 즉시 로드(워커 프로세스당 1회) —
    `generate()` 호출마다 다시 로드하면 너무 느리다.

    AI/validation/TRYON/AI_tryon/CatVTON/generate_worn_reference_outer_fitaware.py에서
    검증한 "image=" 참조 편집 모드를 그대로 쓴다: 원본(고객) 사진을 참조로 주고 "이 사람에게
    이 옷을 이 핏으로 입혀라"는 프롬프트로 생성하면, 포즈/스케일/프레이밍은 참조 사진에서
    그대로 상속되고 옷만 바뀐다(§10.3).
    """

    name = "flux2_klein"

    def __init__(self, config: FluxConfig):
        self._config = config
        self._pipe = None
        self._load()

    def _load(self):
        import torch
        from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel, GGUFQuantizationConfig
        from transformers import AutoModelForCausalLM, BitsAndBytesConfig

        quant_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
        text_encoder = AutoModelForCausalLM.from_pretrained(
            self._config["model_id"],
            subfolder="text_encoder",
            quantization_config=quant_config,
            torch_dtype=torch.bfloat16,
        )
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

    def generate(self, reference_image: Image.Image, prompt: str) -> Image.Image:
        import torch

        generator = torch.Generator(device="cpu").manual_seed(1)
        image = self._pipe(
            image=[reference_image],
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
        AI/docs/tryon-advancement-strategy.md §10 프로덕션 반영 절 참고)."""
        import torch

        self._pipe = None
        torch.cuda.empty_cache()


def build_generator(key: str) -> WornReferenceGenerator:
    config = flux_config(key)
    if key == "mock":
        return MockWornReferenceGenerator()
    if key == "flux2_klein":
        return Flux2KleinGenerator(config)
    raise ValueError(f"등록되지 않은 FLUX 백엔드입니다: {key!r}")
