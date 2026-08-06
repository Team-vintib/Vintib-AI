"""SAM3 PCS 모델 최소 호출 래퍼 — 이 스파이크 전용.

프로덕션(`worker/models/sam3/segmenter.py`)의 `Sam3PcsSegmenter._ensure_loaded`/`_detect`/
`_vision_embeds`와 로딩 방식은 같지만, 프로덕션 클래스의 private 메서드에 기대지 않고
독립적으로 둔다 — 스파이크는 프로덕션과 별도로 모델을 호출하는 관례를 따른다
(`AI/validation/QUAL/sam3-condition-check/`의 노트북들과 같은 방식). 여기서 검증되면
프로덕션에 붙일지 말지는 별도 계획 문서에서 결정한다.

인스턴스는 `qc_shared.py`의 딕셔너리 스키마(`{"type", "prompt", "bbox", "confidence",
"mask"}`, bbox는 **절대 픽셀** xyxy)를 그대로 따른다 — `qc_shared`의 `filter_by_garment`/
`suppress_benign`/`dedupe_cross_type`/`remap_instances_to_full`을 그대로 재사용하기 위해서다.

무거운 라이브러리(torch/transformers)는 함수 내부에서 지연 import한다(레포 관례) — 이 파일을
import하는 것만으로 torch가 로딩되면 안 된다.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

MODEL_ID = "facebook/sam3"

# post_process_instance_segmentation의 mask 이진화 임계치. 하자/파츠/의류 탐지 전부 공유—
# 이 값은 "인스턴스로 인정할 확률"이 아니라 "인스턴스 마스크 픽셀 경계를 어디로 볼지"라
# score_threshold(호출부마다 다름)와 성격이 다르다.
_MASK_THRESHOLD = 0.5


class Sam3Caller:
    """SAM3 모델·프로세서를 프로세스당 1회 로드하고 재사용한다."""

    def __init__(self, model_id: str = MODEL_ID) -> None:
        self._model_id = model_id
        self._model = None
        self._processor = None
        self._device = "cpu"
        self._dtype = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import Sam3Model, Sam3Processor

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._dtype = torch.float16 if self._device == "cuda" else torch.float32
        print(f"[Sam3Caller] 로딩 중... (model={self._model_id}, device={self._device})")
        self._processor = Sam3Processor.from_pretrained(self._model_id)
        self._model = (
            Sam3Model.from_pretrained(self._model_id, dtype=self._dtype).to(self._device).eval()
        )
        print("[Sam3Caller] 로드 완료")

    def _to_device(self, inputs):
        inputs = inputs.to(self._device)
        if "pixel_values" in inputs and inputs["pixel_values"].dtype.is_floating_point:
            inputs["pixel_values"] = inputs["pixel_values"].to(self._dtype)
        return inputs

    def vision_embeds(self, image: Image.Image):
        """이미지 1장에 프롬프트를 여러 개(파츠 여러 개, 하자+양성 등) 돌릴 때 재사용한다 —
        프로덕션과 같은 최적화(`segmenter.py:_vision_embeds`). 실패하면 None(매 프롬프트
        전체 재계산으로 자동 폴백, `detect()`가 `vision_embeds=None`을 그대로 받아준다)."""
        self._ensure_loaded()
        import torch

        try:
            inputs = self._to_device(self._processor(images=image, return_tensors="pt"))
            with torch.no_grad():
                return self._model.get_vision_features(pixel_values=inputs["pixel_values"])
        except Exception as exc:  # pragma: no cover - transformers 버전에 따른 방어적 폴백
            print(f"[Sam3Caller] vision_embeds 실패({exc}) -> 폴백")
            return None

    def detect(
        self,
        image: Image.Image,
        tag: str,
        prompt: str,
        score_threshold: float,
        vision_embeds=None,
    ) -> list[dict]:
        """텍스트 프롬프트 1개로 탐지. `qc_shared` 인스턴스 dict 리스트를 반환한다(절대 픽셀 bbox).

        `tag`는 이 프롬프트가 무엇을 뜻하는지(하자 유형/파츠 이름/"GARMENT" 등) — 호출부가
        정한다. `qc_shared.py`의 `{"type": ...}` 필드와 같은 자리다.
        """
        self._ensure_loaded()
        import torch

        if vision_embeds is not None:
            text_inputs = self._to_device(self._processor(text=prompt, return_tensors="pt"))
            with torch.no_grad():
                outputs = self._model(vision_embeds=vision_embeds, **text_inputs)
            sizes = [[image.height, image.width]]
        else:
            inputs = self._to_device(
                self._processor(images=image, text=prompt, return_tensors="pt")
            )
            with torch.no_grad():
                outputs = self._model(**inputs)
            sizes = inputs["original_sizes"].tolist()

        result = self._processor.post_process_instance_segmentation(
            outputs,
            threshold=score_threshold,
            mask_threshold=_MASK_THRESHOLD,
            target_sizes=sizes,
        )[0]
        scores, boxes, masks = result["scores"], result["boxes"], result["masks"]

        out = []
        for score, box, mask in zip(scores.tolist(), boxes.tolist(), masks, strict=True):
            mask_np = mask.detach().cpu().numpy().astype(np.uint8)
            out.append(
                {
                    "type": tag,
                    "prompt": prompt,
                    "bbox": [float(v) for v in box],
                    "confidence": round(float(score), 4),
                    "mask": mask_np,
                }
            )
        return out


def crop_and_mask_to(image: Image.Image, bbox_abs, mask_full: np.ndarray, pad_ratio: float):
    """bbox 영역을 pad_ratio만큼 넓혀 자르고, 마스크 밖(대상이 아닌 픽셀)을 검정으로 채운다.

    프로덕션 `segmenter.py:_crop_and_mask_to_garment`와 같은 패턴이다 — 의류 크롭에도,
    파츠 크롭에도 그대로 쓴다(대상이 의류 전체냐 파츠 1개냐만 다르다).
    반환: (마스킹된 크롭 이미지, crop_box 절대 픽셀).
    """
    from qc_shared import pad_bbox_clamped  # noqa: E402 - sys.path는 호출부(스크립트)가 잡는다

    crop_box = pad_bbox_clamped(bbox_abs, pad_ratio, image.size)
    x1, y1, x2, y2 = crop_box
    crop_image = image.crop((x1, y1, x2, y2))
    mask_in_crop = mask_full[y1:y2, x1:x2]

    arr = np.array(crop_image)
    arr[mask_in_crop == 0] = 0
    return Image.fromarray(arr), crop_box
