import torch
from diffusers import Flux2KleinPipeline, Flux2Transformer2DModel
from diffusers import GGUFQuantizationConfig
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

print("=== Step 1: 텍스트 인코더 로드 (4bit 양자화) ===")
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

text_encoder = AutoModelForCausalLM.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    subfolder="text_encoder",
    quantization_config=quant_config,
    torch_dtype=torch.bfloat16,
)
print("텍스트 인코더 로드 완료")

print("=== Step 2: Diffusion 트랜스포머 로드 (GGUF Q4_0) ===")
transformer = Flux2Transformer2DModel.from_single_file(
    "https://huggingface.co/unsloth/FLUX.2-klein-4B-GGUF/blob/main/flux-2-klein-4b-Q4_0.gguf",
    config="black-forest-labs/FLUX.2-klein-4B",
    subfolder="transformer",
    quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
    torch_dtype=torch.bfloat16,
)
print("트랜스포머 로드 완료")

print("=== Step 3: 파이프라인 조립 ===")
pipe = Flux2KleinPipeline.from_pretrained(
    "black-forest-labs/FLUX.2-klein-4B",
    transformer=transformer,
    text_encoder=text_encoder,
    torch_dtype=torch.bfloat16,
)
# pipe.enable_sequential_cpu_offload()
pipe.enable_model_cpu_offload() 
print("파이프라인 조립 완료, VRAM 오프로딩 활성화")

print("=== Step 4: 이미지 생성 (저해상도 테스트) ===")
prompt = "a photo of a cat holding a sign that says hello world"
image = pipe(
    prompt=prompt,
    height=512,
    width=512,
    num_inference_steps=4,
    guidance_scale=4.0,
    generator=torch.Generator(device="cpu").manual_seed(0),
).images[0]

image.save("test_output.png")
print("완료! test_output.png 저장됨")