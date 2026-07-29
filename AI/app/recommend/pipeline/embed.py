"""상품 이미지 CLIP 임베딩 (오프라인 전용).

무거운 의존성(torch, sentence-transformers, Pillow)은 함수 내부에서 지연 import 한다 —
서비스 런타임/CI가 이 모듈을 import 해도 무거운 라이브러리가 로드되지 않도록.
모델 후보는 test/model_selection/model_registry.py 의 CLIP 선택(clip-ViT-B-32)과 동일하다.
"""

from pathlib import Path

DEFAULT_CLIP_MODEL = "clip-ViT-B-32"


def embed_images(image_paths, model_name: str = DEFAULT_CLIP_MODEL, batch_size: int = 32):
    """이미지 경로 목록을 L2 정규화된 CLIP 임베딩 (M, D) 로 변환한다."""
    import numpy as np
    from PIL import Image
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    images = [Image.open(Path(p)).convert("RGB") for p in image_paths]
    embeddings = model.encode(
        images,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.astype(np.float32)
