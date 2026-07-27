"""하자 세그멘터 — 프로토타입에서 **모델에 의존하는 유일한 지점**.

`DefectSegmenter` 구현체만 갈아끼우면 downstream(findings/scoring/overlay)과 API 계약은 그대로
유지된다. 활성 구현은 `registry.ACTIVE_SEGMENTER` 키 하나로 결정된다.

**목업이 하드코딩 응답이 아니라 실제 확률 마스크를 합성하는 이유**: 그래야 findings/scoring/
overlay 전 경로가 목업에서도 그대로 실행된다. 실모델로 갈아끼웠을 때 downstream이 이미 검증된
상태가 되는 게 이 프로토타입의 핵심 설계다.

**베이스 이미지를 마스크와 함께 돌려주는 이유**: Attention Map PNG는 원본 위에 히트맵을 얹어야
하는데, 목업의 `image_urls`는 가짜라 다운로드가 불가능하다. 그래서 이미지 확보 책임을 세그멘터가
지고, 목업은 결정적 플레이스홀더를 합성한다.

설계: .claude/plans/ai/005-quality-inspection-prototype.md
"""

from __future__ import annotations

import hashlib
import io
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from app.quality import registry
from app.quality.prompts import PromptSet
from app.quality.scenarios import MockBlob, MockScenario, get_scenarios
from app.quality.schemas import BaseColor

# 목업 마스크에 얹는 화이트 노이즈의 표준편차.
# 배경(0.06~0.09)에 3σ를 더해도 defect_threshold(0.35)에 한참 못 미치도록 작게 잡는다 —
# 노이즈가 유령 blob을 만들면 목업 시나리오의 기대 findings 개수가 흔들린다.
_NOISE_SIGMA = 0.02

# 목업 플레이스홀더 이미지의 기본색(RGB)과 텍스처 노이즈 진폭.
_PLACEHOLDER_COLORS: dict[BaseColor, tuple[int, int, int]] = {
    BaseColor.light: (232, 228, 220),
    BaseColor.dark: (46, 48, 54),
    BaseColor.patterned: (214, 206, 226),
}
_PLACEHOLDER_TEXTURE = 8
_PLACEHOLDER_STRIPE_PERIOD = 24  # PATTERNED 플레이스홀더의 줄무늬 주기(px)
_PLACEHOLDER_STRIPE_DEPTH = 26

# 실백엔드가 상품 이미지를 받아올 때의 제한. BE가 준 URL을 서버가 대신 가져오는 경로라
# 무한정 기다리거나 거대한 파일을 통째로 읽지 않게 막는다.
_FETCH_TIMEOUT_SECONDS = 10.0
_FETCH_MAX_BYTES = 20 * 1024 * 1024

# CLIPSeg 입력 해상도. 디코더 출력(352×352)과 별개로 인코더가 224×224를 받는다 —
# 미세 오염이 뭉개지는 원인이며, 타일 추론이 고도화 경로 6에 올라와 있는 이유다.
_CLIPSEG_INPUT_SIZE = 224

logger = logging.getLogger(__name__)


class SegmenterNotReady(Exception):
    """활성 백엔드가 준비되지 않음(라이브러리 미설치·워커 미연결) → 503."""


class ImageFetchFailed(Exception):
    """검수 대상 이미지를 가져오지 못함 → 502."""


@dataclass(frozen=True)
class InspectionTarget:
    """세그멘터에 넘기는 검수 대상 컨텍스트.

    실백엔드는 `image_urls`를, 목업은 `product_id`(시나리오 선택 키)를 쓴다. 백엔드마다 필요한
    입력이 달라도 ABC 시그니처가 갈리지 않게 하나로 묶는다.
    """

    product_id: int
    image_urls: tuple[str, ...]
    prompt_set: PromptSet


@dataclass(frozen=True)
class SegmentationResult:
    """이미지 한 장의 프롬프트별 확률 마스크 + 오버레이용 베이스 이미지.

    `masks`는 하자 프롬프트만 담고 `clean_mask`는 따로 둔다 — 대조 정규화의 감산항이라
    역할이 다르고, findings가 둘을 섞어 다루면 안 되기 때문이다.
    """

    image_index: int
    masks: dict[str, np.ndarray]  # 프롬프트 문구 -> (H, W) float32, [0,1]
    clean_mask: np.ndarray  # (H, W) float32, [0,1]
    base_image: Image.Image
    size: tuple[int, int]  # (height, width)


class DefectSegmenter(ABC):
    """이미지 한 장 → 프롬프트별 확률 마스크. **여기가 모델 교체 경계다.**"""

    @abstractmethod
    def segment(self, target: InspectionTarget, image_index: int) -> SegmentationResult:
        """준비되지 않았으면 `SegmenterNotReady`, 이미지를 못 읽으면 `ImageFetchFailed`."""
        raise NotImplementedError


# --- 목업 백엔드 -----------------------------------------------------------


def _seed_from(*parts: object) -> int:
    """키 조각들을 결정적 시드로 바꾼다(`catalog.py`의 `_seeded_vector`와 같은 방식)."""
    key = "|".join(str(part) for part in parts)
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "little")


def _gaussian(size: int, center: tuple[float, float], radius: float) -> np.ndarray:
    """정규화 좌표 기준 가우시안. 거리 `radius`에서 약 0.135까지 떨어진다."""
    axis = (np.arange(size, dtype=np.float32) + 0.5) / size
    dx = axis[None, :] - center[0]
    dy = axis[:, None] - center[1]
    return np.exp(-2.0 * (dx * dx + dy * dy) / (radius * radius)).astype(np.float32)


def _blend(mask: np.ndarray, weight: np.ndarray, value: float) -> np.ndarray:
    """`weight`(0~1)만큼 `value` 쪽으로 끌어당긴다.

    최댓값 합성이 아니라 보간이라서 값이 배경보다 **낮은** 경우(clean 마스크 위의 오염 자리)도
    같은 코드로 처리된다.
    """
    return mask * (1.0 - weight) + value * weight


class MockSegmenter(DefectSegmenter):
    """목업 시나리오 정의로 결정적 확률 마스크를 합성한다(torch 불필요).

    같은 (product_id, image_index, 프롬프트)는 항상 같은 마스크를 준다 — 노이즈까지 시드
    기반이라 CI에서 재현된다.
    """

    def __init__(self, mask_size: int | None = None) -> None:
        self._mask_size = mask_size or registry.segmenter_config("mock")["mask_size"]

    def segment(self, target: InspectionTarget, image_index: int) -> SegmentationResult:
        scenario = get_scenarios().for_product(
            target.product_id,
            target.prompt_set.category,
            target.prompt_set.base_color,
        )
        blobs = scenario.blobs_for(image_index)

        masks = {
            prompt: self._defect_mask(scenario, blobs, defect_type, target, image_index, prompt)
            for prompt, defect_type in target.prompt_set.defect_prompts
        }
        return SegmentationResult(
            image_index=image_index,
            masks=masks,
            clean_mask=self._clean_mask(scenario, blobs, target, image_index),
            base_image=self._placeholder_image(scenario, target, image_index),
            size=(self._mask_size, self._mask_size),
        )

    def _defect_mask(
        self,
        scenario: MockScenario,
        blobs: tuple[MockBlob, ...],
        defect_type,
        target: InspectionTarget,
        image_index: int,
        prompt: str,
    ) -> np.ndarray:
        mask = np.full(
            (self._mask_size, self._mask_size), scenario.background_defect, dtype=np.float32
        )
        for blob in blobs:
            # 다른 유형의 blob은 cross_talk 비율만큼만 번진다. 0이면 아예 반응하지 않는다 —
            # 실제 CLIPSeg가 하나의 오염에 여러 프롬프트로 반응하는 걸 재현하기 위한 값이다.
            value = blob.peak if blob.defect_type is defect_type else blob.peak * blob.cross_talk
            if value <= scenario.background_defect:
                continue
            mask = _blend(mask, _gaussian(self._mask_size, blob.center, blob.radius), value)
        return self._finish(mask, target.product_id, image_index, prompt)

    def _clean_mask(
        self,
        scenario: MockScenario,
        blobs: tuple[MockBlob, ...],
        target: InspectionTarget,
        image_index: int,
    ) -> np.ndarray:
        mask = np.full(
            (self._mask_size, self._mask_size), scenario.background_clean, dtype=np.float32
        )
        for blob in blobs:
            # 하자 자리에서는 clean 확률이 배경보다 **낮고**(진짜 오염), 프린트 자리에서는
            # 오히려 높다 — 그 차이가 대조 정규화의 작동 원리다.
            mask = _blend(
                mask, _gaussian(self._mask_size, blob.center, blob.radius), blob.clean_overlap
            )
        return self._finish(mask, target.product_id, image_index, target.prompt_set.clean_prompt)

    def _finish(
        self, mask: np.ndarray, product_id: int, image_index: int, prompt: str
    ) -> np.ndarray:
        """시드 기반 노이즈를 얹고 [0,1]로 자른다."""
        rng = np.random.default_rng(_seed_from("quality:mask", product_id, image_index, prompt))
        noise = rng.normal(0.0, _NOISE_SIGMA, size=mask.shape).astype(np.float32)
        return np.clip(mask + noise, 0.0, 1.0)

    def _placeholder_image(
        self, scenario: MockScenario, target: InspectionTarget, image_index: int
    ) -> Image.Image:
        """오버레이가 얹힐 결정적 플레이스홀더 이미지.

        실제 상품 사진이 아니라 "옷감처럼 보이는 배경"일 뿐이다. 목업에서도 Attention Map이
        실제 PNG로 렌더되는지 확인하는 게 목적이다.
        """
        size = self._mask_size
        base_color = target.prompt_set.base_color
        rgb = np.array(_PLACEHOLDER_COLORS[base_color], dtype=np.float32)
        canvas = np.broadcast_to(rgb, (size, size, 3)).copy()

        if base_color is BaseColor.patterned:
            # 프린트 방어 시나리오를 눈으로 확인할 수 있도록 줄무늬를 넣는다.
            stripe = ((np.arange(size) // _PLACEHOLDER_STRIPE_PERIOD) % 2).astype(np.float32)
            canvas -= (stripe[None, :, None] * _PLACEHOLDER_STRIPE_DEPTH).astype(np.float32)

        rng = np.random.default_rng(
            _seed_from("quality:placeholder", scenario.scenario, target.product_id, image_index)
        )
        canvas += rng.normal(0.0, _PLACEHOLDER_TEXTURE, size=canvas.shape)
        return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), mode="RGB")


# --- 실 이미지 로딩 --------------------------------------------------------


def load_source_image(url: str) -> Image.Image:
    """검수 대상 이미지를 RGB로 읽는다. 실패는 전부 `ImageFetchFailed`로 모은다.

    HTTP(S) URL과 로컬 경로를 모두 받는다 — 후자는 발표자료용 배치 렌더 스크립트가 이미지
    폴더를 그대로 흘려보낼 수 있게 하려는 것이다.
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


# --- CLIPSeg 백엔드 --------------------------------------------------------


class ClipSegSegmenter(DefectSegmenter):
    """LAB-12가 채택한 CLIPSeg 백엔드.

    `torch`/`transformers`는 **함수 내부에서 지연 import**한다(`requirements-pipeline` 계열,
    CI 미설치). 미설치 환경에서도 앱은 정상 기동하고 **첫 호출에서 503**이 나는 게 의도된
    동작이다 — 목업이 기본값이라 서비스 자체는 항상 뜬다.

    알려진 한계(LAB-12 실측): ⑴ 찢어짐·훼손 판단이 약하다 ⑵ 미세 오염은 탐지되나 뚜렷하지
    않다. ⑴은 `registry.DEFECT_TAXONOMY`가 SUSPECTED 강등으로 흡수하고, ⑵는 입력 해상도
    224×224가 유력한 원인이라 타일 추론(고도화 경로 6)이 후보다.
    """

    def __init__(self, model_id: str, mask_size: int) -> None:
        self._model_id = model_id
        self._mask_size = mask_size
        self._model = None
        self._processor = None
        self._device = "cpu"

    def _ensure_loaded(self) -> None:
        """모델을 지연 로드한다(프로세스당 1회). 라이브러리가 없으면 `SegmenterNotReady`."""
        if self._model is not None:
            return
        try:
            import torch
            from transformers import CLIPSegForImageSegmentation, CLIPSegProcessor
        except ImportError as exc:
            raise SegmenterNotReady(
                "CLIPSeg 백엔드에는 torch/transformers가 필요합니다 "
                "(pip install -r requirements-pipeline.txt)"
            ) from exc

        try:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._processor = CLIPSegProcessor.from_pretrained(self._model_id)
            self._model = (
                CLIPSegForImageSegmentation.from_pretrained(self._model_id).to(self._device).eval()
            )
        except Exception as exc:  # 체크포인트 다운로드 실패·손상 등
            raise SegmenterNotReady(f"CLIPSeg 모델을 불러오지 못했습니다: {exc}") from exc
        logger.info("CLIPSeg 로드 완료 (model=%s, device=%s)", self._model_id, self._device)

    def segment(self, target: InspectionTarget, image_index: int) -> SegmentationResult:
        self._ensure_loaded()
        import torch

        image = load_source_image(target.image_urls[image_index])
        prompts = list(target.prompt_set.all_prompts)

        # 통합 processor(...) 호출 대신 tokenizer/image_processor를 분리 호출한다 —
        # 한 번에 넘기면 텍스트/이미지 kwarg가 서로 섞여 에러가 난다.
        # (test/clipseg-condition-check/verify_clipseg.py에서 이미 밟은 문제라 여기로 승격했다.
        #  test/ 코드를 프로덕션에서 import하지 않는 규약에 따라 복사한다.)
        text_inputs = self._processor.tokenizer(prompts, return_tensors="pt", padding=True)
        image_inputs = self._processor.image_processor(
            [image] * len(prompts),
            size={"height": _CLIPSEG_INPUT_SIZE, "width": _CLIPSEG_INPUT_SIZE},
            return_tensors="pt",
        )
        inputs = {**text_inputs, "pixel_values": image_inputs["pixel_values"]}
        inputs = {key: value.to(self._device) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)

        logits = outputs.logits
        if logits.ndim == 2:
            # 프롬프트가 1개면 배치 축이 사라진다 — 항상 (N, H, W)로 맞춘다.
            logits = logits.unsqueeze(0)
        probs = torch.sigmoid(logits).float().cpu().numpy()

        masks = {
            prompt: self._to_mask_size(probs[i])
            for i, (prompt, _) in enumerate(target.prompt_set.defect_prompts)
        }
        return SegmentationResult(
            image_index=image_index,
            masks=masks,
            clean_mask=self._to_mask_size(probs[-1]),  # all_prompts의 마지막이 clean 대조항
            base_image=image,
            size=(self._mask_size, self._mask_size),
        )

    def _to_mask_size(self, mask: np.ndarray) -> np.ndarray:
        """디코더 출력이 설정된 마스크 크기와 다르면 맞춘다(체크포인트별로 달라질 수 있다)."""
        if mask.shape == (self._mask_size, self._mask_size):
            return np.clip(mask.astype(np.float32), 0.0, 1.0)
        resized = Image.fromarray((np.clip(mask, 0.0, 1.0) * 255).astype(np.uint8)).resize(
            (self._mask_size, self._mask_size), Image.BILINEAR
        )
        return (np.asarray(resized, dtype=np.float32) / 255.0).astype(np.float32)


# --- 원격 워커 백엔드(스텁) ------------------------------------------------


class RemoteWorkerSegmenter(DefectSegmenter):
    """게이트웨이 Redis 큐를 경유해 로컬 GPU 워커에 추론을 맡기는 경로(미구현).

    동기 REST가 한계에 닿으면(EC2에 GPU가 없어 CLIPSeg 추론이 느려지면) 여기로 넘어간다.
    **그때도 API 계약과 downstream은 그대로다** — 바뀌는 건 `ACTIVE_SEGMENTER` 한 줄뿐이다.

    TODO(-299): `app/gateway/router.py`의 큐 규약을 그대로 쓴다.
      1. `enqueue_job("quality_check", {image_url, prompts})` 로 job 등록
      2. `result:{job_id}` 를 폴링해 워커가 올린 마스크를 회수
      3. 마스크는 배열 그대로 넘기기엔 크므로 워커가 `/ai/workers/upload-json` 으로 올린
         URL을 받아 내려받는 형태가 될 가능성이 높다
    동기 엔드포인트 안에서 큐를 기다리게 할지, 검수 API 자체를 비동기(job id 반환)로 바꿀지는
    BE와 협의가 필요하다 — 상품 등록이 판매자가 화면에서 기다리는 인터랙티브 흐름이라
    이번 라운드는 동기 REST를 택했다.
    """

    def segment(self, target: InspectionTarget, image_index: int) -> SegmentationResult:
        # NotImplementedError가 아니라 SegmenterNotReady를 던진다 — 라우터가 이걸 503으로
        # 매핑하고, "워커 미연결"은 500(버그)이 아니라 가용성 문제이기 때문이다.
        raise SegmenterNotReady(
            "원격 워커 세그멘터는 아직 구현되지 않았습니다 (S15P11A108-299). "
            "registry.ACTIVE_SEGMENTER 를 'mock' 또는 'clipseg_rd64_refined' 로 두십시오."
        )


# --- 조립 ------------------------------------------------------------------


def build_segmenter(key: str | None = None) -> DefectSegmenter:
    """레지스트리 키에 맞는 세그멘터를 만든다. **여기가 유일한 스왑 지점이다.**"""
    resolved = key or registry.ACTIVE_SEGMENTER
    config = registry.segmenter_config(resolved)
    if resolved == "mock":
        return MockSegmenter(mask_size=config["mask_size"])
    if resolved == "clipseg_rd64_refined":
        return ClipSegSegmenter(model_id=config["model_id"], mask_size=config["mask_size"])
    if resolved == "remote_worker":
        return RemoteWorkerSegmenter()
    raise SegmenterNotReady(f"아직 구현되지 않은 세그멘터 백엔드입니다: {resolved!r}")
