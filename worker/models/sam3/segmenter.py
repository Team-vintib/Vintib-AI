"""SAM3 세그멘터 — 프로토타입에서 **모델에 의존하는 유일한 지점**.

CLIPSeg(`worker/models/clipseg/segmenter.py`)와 근본적으로 다른 점: SAM3 PCS(Promptable
Concept Segmentation)는 확률 히트맵이 아니라 **인스턴스**(마스크+박스+score)를 직접 낸다.
그래서 `SegmentationResult`도 CLIPSeg와 모양이 다르다 — `masks: dict[프롬프트, 히트맵]` 대신
`instances: tuple[Instance, ...]`이고, `clean_mask`(대조 정규화 감산항) 대신 `garment_mask`
(사후 겹침 필터용)를 들고 있다.

**마스킹 전처리가 여기 내장돼 있다.** `AI/validation/QUAL/sam3-condition-check/
sam3_qc_test_masking.ipynb` 스파이크에서 검증한 방식 그대로: 1) `clothing` 프롬프트로 의류
위치를 찾고 2) 그 bbox로 이미지를 자른 뒤 3) 마스크 밖(의류가 아닌 픽셀)을 검정(0)으로 채워
4) 그 안에서 하자·양성 프롬프트를 탐지한다. 배경(바닥·소품) 오탐을 구조적으로 차단한다.
의류를 못 찾으면 크롭·마스킹 없이 원본 그대로 탐지한다("하자 없음"과 "탐지 실패"를 뭉개지
않기 위한 안전장치, `clipseg`의 `filter_by_garment` None 처리와 같은 원칙).

설계: `.claude/plans/ai/CH006-sam3-quality-segmenter.md`
"""

from __future__ import annotations

import hashlib
import io
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from . import registry
from .contracts import DefectType
from .prompts import BENIGN_PROMPTS, GARMENT_PROMPT, PromptSet

_FETCH_TIMEOUT_SECONDS = 10.0
_FETCH_MAX_BYTES = 20 * 1024 * 1024

# 목업 전용 캔버스 크기(실 모델과 무관, 배경 없는 결정적 플레이스홀더).
_MOCK_IMAGE_SIZE = (768, 768)  # (height, width)

logger = logging.getLogger(__name__)


class SegmenterNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치·gated 접근 미승인) → 503."""


class ImageFetchFailed(Exception):
    """검수 대상 이미지를 가져오지 못함 → 502."""


@dataclass(frozen=True)
class InspectionTarget:
    """세그멘터에 넘기는 검수 대상 컨텍스트. `clipseg.segmenter.InspectionTarget`과 같은 모양."""

    product_id: int
    image_urls: tuple[str, ...]
    prompt_set: PromptSet


@dataclass(frozen=True)
class Instance:
    """SAM3가 낸 인스턴스 하나. 확률 히트맵이 아니라 마스크·박스·score를 직접 들고 있다.

    `defect_type`은 양성(benign) 후보 인스턴스면 `None`이다 — 양성 개념은 BE에 노출되는
    `DefectType`이 아니라 내부 억제 판단용이라서 별도 enum을 만들지 않는다.
    """

    defect_type: DefectType | None
    prompt: str
    confidence: float
    mask: np.ndarray  # (H, W) uint8, 0/1 — 항상 원본 이미지 좌표계
    bbox: tuple[float, float, float, float]  # 정규화 xyxy, 원본 이미지 좌표계


@dataclass(frozen=True)
class SegmentationResult:
    """이미지 한 장의 인스턴스 목록 + 오버레이용 베이스 이미지.

    `garment_mask`가 `None`이면 의류를 못 찾은 것이다 — `findings.py`는 이 경우 겹침 필터를
    건너뛴다.
    """

    image_index: int
    instances: tuple[Instance, ...]  # 하자 후보(전체 이미지 좌표)
    benign_instances: tuple[Instance, ...]  # 양성 후보(전체 이미지 좌표), 억제 꺼져 있으면 빈 튜플
    garment_mask: np.ndarray | None  # (H, W) uint8, 전체 이미지 좌표
    base_image: Image.Image
    size: tuple[int, int]  # (height, width), 원본 기준


class DefectSegmenter(ABC):
    """이미지 한 장 → 하자/양성 인스턴스 + 의류 마스크. **여기가 모델 교체 경계다.**"""

    @abstractmethod
    def segment(self, target: InspectionTarget, image_index: int) -> SegmentationResult:
        """준비되지 않았으면 `SegmenterNotReady`, 이미지를 못 읽으면 `ImageFetchFailed`."""
        raise NotImplementedError


# --- 좌표 유틸 (마스킹 전처리·좌표 복원 공용) --------------------------------


def _pad_bbox_clamped(
    bbox: tuple[float, float, float, float],
    pad_ratio: float,
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """bbox(xyxy, 절대 픽셀)를 pad_ratio 만큼 넓히고 이미지 경계 안으로 clamp.

    image_size = (width, height).
    """
    img_w, img_h = image_size
    x1, y1, x2, y2 = bbox
    pad_x = int((x2 - x1) * pad_ratio) + 1
    pad_y = int((y2 - y1) * pad_ratio) + 1
    return (
        max(0, int(x1) - pad_x),
        max(0, int(y1) - pad_y),
        min(img_w, int(x2) + pad_x),
        min(img_h, int(y2) + pad_y),
    )


def _remap_mask_to_full(
    mask: np.ndarray,
    crop_box: tuple[int, int, int, int],
    full_size: tuple[int, int],
) -> np.ndarray:
    """크롭 좌표계 마스크 1장을 원본 크기 캔버스로 되돌린다. full_size = (width, height)."""
    x1, y1, _, _ = crop_box
    full_w, full_h = full_size
    full_mask = np.zeros((full_h, full_w), dtype=np.uint8)
    crop_h, crop_w = mask.shape
    full_mask[y1 : y1 + crop_h, x1 : x1 + crop_w] = mask
    return full_mask


def _bbox_to_normalized(
    bbox_px: tuple[float, float, float, float], image_size: tuple[int, int]
) -> tuple[float, float, float, float]:
    """절대 픽셀 xyxy -> 정규화 xyxy. image_size = (width, height)."""
    width, height = image_size
    x1, y1, x2, y2 = bbox_px
    return (x1 / width, y1 / height, x2 / width, y2 / height)


def _mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    """마스크의 픽셀 bbox(x1,y1,x2,y2, 절대 픽셀, 상한 배타적). 마스크가 비면 None."""
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any():
        return None
    y_idx = np.where(rows)[0]
    x_idx = np.where(cols)[0]
    return int(x_idx[0]), int(y_idx[0]), int(x_idx[-1]) + 1, int(y_idx[-1]) + 1


# --- 목업 백엔드 -------------------------------------------------------------


def _seed_from(*parts: object) -> int:
    """키 조각들을 결정적 시드로 바꾼다(`clipseg` 목업과 같은 방식)."""
    key = "|".join(str(part) for part in parts)
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "little")


def _gaussian_disk(size: tuple[int, int], center: tuple[float, float], radius: float) -> np.ndarray:
    """정규화 좌표 중심의 원판 이진 마스크(반지름 안쪽만 1). size = (height, width)."""
    height, width = size
    ys = (np.arange(height, dtype=np.float32) + 0.5) / height
    xs = (np.arange(width, dtype=np.float32) + 0.5) / width
    dx = xs[None, :] - center[0]
    dy = ys[:, None] - center[1]
    return (np.sqrt(dx * dx + dy * dy) <= radius).astype(np.uint8)


class MockSegmenter(DefectSegmenter):
    """product_id 로 결정적 인스턴스를 합성한다(torch 불필요).

    CLIPSeg 목업처럼 named 시나리오 JSON을 쓰지 않는다 — SAM3 네이티브 경로는 확률 히트맵/
    clean 대조 개념이 없어 CLIPSeg 목업의 blob 합성 로직이 그대로 맞지 않는다. 대신
    `(product_id, image_index)` 해시로 0~2개의 하자 인스턴스를 직접 합성한다. 같은 입력은
    항상 같은 결과를 낸다(CI 재현성).
    """

    def __init__(self, config: registry.SegmenterConfig | None = None) -> None:
        self._config = config or registry.segmenter_config("mock")

    def segment(self, target: InspectionTarget, image_index: int) -> SegmentationResult:
        height, width = _MOCK_IMAGE_SIZE
        rng = np.random.default_rng(_seed_from("sam3:mock", target.product_id, image_index))

        # 의류 마스크 — 화면 중앙 84%를 의류로 본다(배경 없는 목업 플레이스홀더 기준).
        garment_mask = np.zeros((height, width), dtype=np.uint8)
        garment_mask[int(height * 0.08) : int(height * 0.92), int(width * 0.08) : int(width * 0.92)] = 1

        defect_prompts = list(target.prompt_set.defect_prompts)
        instances = []
        for _ in range(int(rng.integers(0, 3))):
            prompt, defect_type = defect_prompts[int(rng.integers(0, len(defect_prompts)))]
            center = (float(rng.uniform(0.25, 0.75)), float(rng.uniform(0.25, 0.75)))
            radius = float(rng.uniform(0.03, 0.09))
            mask = _gaussian_disk((height, width), center, radius) & garment_mask
            if not mask.any():
                continue
            box = _mask_bbox(mask)
            instances.append(
                Instance(
                    defect_type=defect_type,
                    prompt=prompt,
                    confidence=round(float(rng.uniform(0.35, 0.85)), 4),
                    mask=mask,
                    bbox=_bbox_to_normalized(box, (width, height)),
                )
            )

        base_image = Image.fromarray(np.full((height, width, 3), 220, dtype=np.uint8), mode="RGB")
        return SegmentationResult(
            image_index=image_index,
            instances=tuple(instances),
            benign_instances=(),
            garment_mask=garment_mask,
            base_image=base_image,
            size=(height, width),
        )


# --- 실 이미지 로딩 --------------------------------------------------------


def load_source_image(url: str) -> Image.Image:
    """검수 대상 이미지를 RGB로 읽는다. 실패는 전부 `ImageFetchFailed`로 모은다.

    HTTP(S) URL과 로컬 경로를 모두 받는다(clipseg와 동일한 규약).
    """
    try:
        if url.startswith(("http://", "https://")):
            request = urllib.request.Request(url, headers={"User-Agent": "vintib-ai-quality/0.1"})
            with urllib.request.urlopen(  # noqa: S310 - BE가 준 상품 이미지 URL을 대신 가져온다
                request, timeout=_FETCH_TIMEOUT_SECONDS
            ) as response:
                payload = response.read(_FETCH_MAX_BYTES + 1)
            if len(payload) > _FETCH_MAX_BYTES:
                raise ImageFetchFailed(f"이미지가 너무 큽니다(>{_FETCH_MAX_BYTES}B): {url}")
            return Image.open(io.BytesIO(payload)).convert("RGB")
        return Image.open(Path(url)).convert("RGB")
    except ImageFetchFailed:
        raise
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise ImageFetchFailed(f"이미지를 읽을 수 없습니다: {url} ({exc})") from exc


# --- SAM3 PCS 백엔드 --------------------------------------------------------


class Sam3PcsSegmenter(DefectSegmenter):
    """facebook/sam3 PCS(Promptable Concept Segmentation) 백엔드.

    `torch`/`transformers`는 함수 내부에서 지연 import한다(CI 미설치, `transformers>=5.0`
    필요 — `worker/models/sam3/requirements.txt` 참고). `facebook/sam3`는 gated 저장소라
    승인된 계정의 HF 토큰이 필요하다 — 미승인·미설치 시 **첫 호출에서 503**(목업이 기본값이라
    서비스 자체는 항상 뜬다).

    알려진 한계(LAB-46 실측): 뚜렷한 손상은 잘 잡지만, 애매한 손상에서 암홀·넥라인·밑단·
    소매끝 같은 구조적 개구부를 구멍으로 오인하는 **비유계** 오탐이 반복 확인됐다. 그래서
    ⑴ `hole_tear`는 `registry.DEFECT_TAXONOMY`에서 항상 SUSPECTED로 강등되고 ⑵ 이 클래스가
    구조적 개구부 프롬프트를 양성 억제 후보로 명시적으로 다룬다(`_detect_defects`/
    `findings.py`의 억제 로직 참고).
    """

    def __init__(self, model_id: str, config: registry.SegmenterConfig) -> None:
        self._model_id = model_id
        self._config = config
        self._model = None
        self._processor = None
        self._device = "cpu"
        self._dtype = None

    def _ensure_loaded(self) -> None:
        """모델을 지연 로드한다(프로세스당 1회). 라이브러리가 없으면 `SegmenterNotReady`."""
        if self._model is not None:
            return
        try:
            import torch
            from transformers import Sam3Model, Sam3Processor
        except ImportError as exc:
            raise SegmenterNotReady(
                "SAM3 백엔드에는 torch>=2.4/transformers>=5.0이 필요합니다 "
                "(worker/models/sam3/requirements.txt 참고)"
            ) from exc

        try:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._dtype = torch.float16 if self._device == "cuda" else torch.float32
            self._processor = Sam3Processor.from_pretrained(self._model_id)
            self._model = (
                Sam3Model.from_pretrained(self._model_id, dtype=self._dtype).to(self._device).eval()
            )
        except Exception as exc:
            message = str(exc).lower()
            if any(k in message for k in ("gated", "401", "403", "awaiting", "access to model")):
                raise SegmenterNotReady(
                    f"facebook/sam3 는 gated 저장소입니다 — 접근 승인 여부를 확인하세요: {exc}"
                ) from exc
            raise SegmenterNotReady(f"SAM3 모델을 불러오지 못했습니다: {exc}") from exc
        logger.info("SAM3 로드 완료 (model=%s, device=%s)", self._model_id, self._device)

    def _to_device(self, inputs):
        """텐서를 디바이스로 옮기고 pixel_values 만 모델 dtype 에 맞춘다."""
        inputs = inputs.to(self._device)
        if "pixel_values" in inputs and inputs["pixel_values"].dtype.is_floating_point:
            inputs["pixel_values"] = inputs["pixel_values"].to(self._dtype)
        return inputs

    def _detect(self, image: Image.Image, prompt: str, score_threshold: float, vision_embeds=None):
        """텍스트 프롬프트 1개로 PCS 추론. (scores, boxes, masks) 텐서를 반환한다.

        `vision_embeds` 를 주면 vision 인코더를 건너뛴다 — 같은 이미지에 프롬프트를 여러 개
        돌릴 때(하자 + 양성) 재사용한다.
        """
        import torch

        if vision_embeds is not None:
            text_inputs = self._to_device(self._processor(text=prompt, return_tensors="pt"))
            with torch.no_grad():
                outputs = self._model(vision_embeds=vision_embeds, **text_inputs)
            sizes = [[image.height, image.width]]
        else:
            inputs = self._to_device(self._processor(images=image, text=prompt, return_tensors="pt"))
            with torch.no_grad():
                outputs = self._model(**inputs)
            sizes = inputs["original_sizes"].tolist()

        result = self._processor.post_process_instance_segmentation(
            outputs,
            threshold=score_threshold,
            mask_threshold=self._config["mask_threshold"],
            target_sizes=sizes,
        )[0]
        return result["scores"], result["boxes"], result["masks"]

    def _vision_embeds(self, image: Image.Image):
        """이미지당 1회 계산해 프롬프트 여러 개(하자+양성)에 재사용. 실패하면 None(폴백)."""
        import torch

        try:
            inputs = self._to_device(self._processor(images=image, return_tensors="pt"))
            with torch.no_grad():
                return self._model.get_vision_features(pixel_values=inputs["pixel_values"])
        except Exception as exc:  # pragma: no cover - transformers 버전에 따른 방어적 폴백
            logger.warning("get_vision_features 실패(%s) -> 매 프롬프트 전체 호출로 폴백", exc)
            return None

    def _detect_garment(self, image: Image.Image):
        """의류 인스턴스 전체 중 가장 큰 것 하나. 못 찾으면 None."""
        scores, boxes, masks = self._detect(image, GARMENT_PROMPT, self._config["garment_score_threshold"])
        if len(scores) == 0:
            return None
        areas = [float(m.sum()) for m in masks]
        picked = int(np.argmax(areas))
        mask = masks[picked].detach().cpu().numpy().astype(np.uint8)
        bbox = tuple(float(v) for v in boxes[picked].tolist())
        return mask, bbox

    def _crop_and_mask_to_garment(self, image: Image.Image):
        """의류 영역을 찾아 bbox로 자른 뒤 마스크 밖을 검정으로 채운다.

        반환: (탐지에 쓸 이미지, crop_box 절대 픽셀 또는 None, 전체 좌표 의류 마스크 또는 None).
        의류를 못 찾으면 (원본, None, None).
        """
        picked = self._detect_garment(image)
        if picked is None:
            return image, None, None
        garment_mask_full, garment_bbox = picked

        crop_box = _pad_bbox_clamped(garment_bbox, self._config["garment_crop_pad_ratio"], image.size)
        x1, y1, x2, y2 = crop_box
        crop_image = image.crop((x1, y1, x2, y2))
        mask_in_crop = garment_mask_full[y1:y2, x1:x2]

        arr = np.array(crop_image)
        arr[mask_in_crop == 0] = 0
        masked_crop = Image.fromarray(arr)
        return masked_crop, crop_box, garment_mask_full

    def _instances_from(
        self,
        image: Image.Image,
        prompts: Sequence[tuple[str, DefectType | None]],
        score_threshold: float,
        vision_embeds,
    ) -> list[Instance]:
        """프롬프트 목록을 순회 탐지해 인스턴스 리스트로 합친다. 좌표는 `image` 기준(크롭 좌표일 수 있음)."""
        out: list[Instance] = []
        for prompt, defect_type in prompts:
            scores, boxes, masks = self._detect(image, prompt, score_threshold, vision_embeds)
            for score, box, mask in zip(scores.tolist(), boxes.tolist(), masks, strict=True):
                mask_np = mask.detach().cpu().numpy().astype(np.uint8)
                area_ratio = float(mask_np.mean())
                if area_ratio < self._config["min_area_ratio"]:
                    continue
                if area_ratio > self._config["max_defect_area_ratio"]:
                    logger.warning("인스턴스 과포화로 폐기 (prompt=%r, area_ratio=%.2f)", prompt, area_ratio)
                    continue
                out.append(
                    Instance(
                        defect_type=defect_type,
                        prompt=prompt,
                        confidence=round(float(score), 4),
                        mask=mask_np,
                        bbox=_bbox_to_normalized(tuple(box), image.size),
                    )
                )
        return out

    @staticmethod
    def _remap_instance(
        instance: Instance, crop_box: tuple[int, int, int, int], full_size: tuple[int, int]
    ) -> Instance:
        """크롭 좌표계 인스턴스를 원본 이미지 좌표계로 되돌린다. full_size = (width, height)."""
        x1, y1, x2, y2 = crop_box
        crop_w, crop_h = x2 - x1, y2 - y1
        full_w, full_h = full_size
        bx1, by1, bx2, by2 = instance.bbox  # 크롭 이미지 기준 정규화 좌표
        full_bbox = (
            (x1 + bx1 * crop_w) / full_w,
            (y1 + by1 * crop_h) / full_h,
            (x1 + bx2 * crop_w) / full_w,
            (y1 + by2 * crop_h) / full_h,
        )
        full_mask = _remap_mask_to_full(instance.mask, crop_box, full_size)
        return Instance(
            defect_type=instance.defect_type,
            prompt=instance.prompt,
            confidence=instance.confidence,
            mask=full_mask,
            bbox=full_bbox,
        )

    def segment(self, target: InspectionTarget, image_index: int) -> SegmentationResult:
        self._ensure_loaded()

        image = load_source_image(target.image_urls[image_index])
        full_size_wh = image.size  # (width, height)

        detect_image, crop_box, garment_mask = self._crop_and_mask_to_garment(image)
        cropped = crop_box is not None

        vision_embeds = self._vision_embeds(detect_image)
        defect_instances = self._instances_from(
            detect_image,
            list(target.prompt_set.defect_prompts),
            self._config["score_threshold"],
            vision_embeds,
        )

        benign_instances: list[Instance] = []
        if self._config["suppress_benign"]:
            benign_pairs = [(prompt, None) for prompt in BENIGN_PROMPTS]
            benign_instances = self._instances_from(
                detect_image, benign_pairs, self._config["score_threshold"], vision_embeds
            )

        if cropped:
            defect_instances = [self._remap_instance(i, crop_box, full_size_wh) for i in defect_instances]
            benign_instances = [self._remap_instance(i, crop_box, full_size_wh) for i in benign_instances]

        return SegmentationResult(
            image_index=image_index,
            instances=tuple(defect_instances),
            benign_instances=tuple(benign_instances),
            garment_mask=garment_mask,
            base_image=image,
            size=(full_size_wh[1], full_size_wh[0]),
        )


# --- 조립 -------------------------------------------------------------------


def build_segmenter(key: str | None = None) -> DefectSegmenter:
    """레지스트리 키에 맞는 세그멘터를 만든다. **여기가 유일한 모델 스왑 지점이다.**

    워커는 `QUALITY_BACKEND` 환경변수로 이 키를 넘긴다. GPU가 없는 환경에서도 `mock`으로
    전 경로를 그대로 돌려볼 수 있다.
    """
    resolved = key or registry.ACTIVE_SEGMENTER
    config = registry.segmenter_config(resolved)
    if resolved == "mock":
        return MockSegmenter(config=config)
    if resolved == "sam3_pcs":
        return Sam3PcsSegmenter(model_id=config["model_id"], config=config)
    raise SegmenterNotReady(f"아직 구현되지 않은 세그멘터 백엔드입니다: {resolved!r}")
