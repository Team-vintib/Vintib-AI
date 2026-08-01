"""V3 — 색상 추출 백엔드 4종 비교.

  (a) kmeans_palette  — 경량 마스크(중앙 크롭+배경색 추정+saturation 필터) + k-means(k=3)
                        + 팔레트 스냅  [설계안, CH012 §6.2 그대로]
  (b) mean_color      — 마스크 없이 전체 이미지 평균색 + 팔레트 스냅              [baseline]
  (c) vlm              — Qwen3-VL에 직접 질의(vlm_control.query_color 위임)        [대조군]
  (d) clip_vit_b32/clip_vit_l14/siglip_so400m — CLIP/SigLIP zero-shot(색상 라벨 텍스트와
                        이미지 임베딩 코사인 유사도). classify.py의 카테고리 zero-shot과
                        같은 메커니즘을 색상에 적용 — 2026-08-02 추가, "CLIP 파인튜닝으로
                        색상까지 처리" 결정 전에 먼저 zero-shot 신호부터 본다.

설계: `.claude/plans/ai/CH012-~2.MD`(파일명이 이렇게 커밋돼 있다 — 원래 의도한 이름은
`CH012-product-info-classify.md`로 보인다, 정리 필요).

model_selection/model_registry.py 관례와 동일: 레지스트리 dict + `ACTIVE_COLOR_BACKEND`
상수 한 줄로 스왑. 환경변수 `PRODUCT_INFO_COLOR_BACKEND`로 덮어쓸 수 있다(CH012 §6 워커
설계의 환경변수 이름과 동일하게 맞춤).

**PALETTE는 잠정값이다.** CH012 §12가 "색상 팔레트 정의 주체"를 미결정 사항으로 명시했고,
2026-08-01 기준 BE/FE 어디에도 실제 코드+hex 정의가 없다 — 이 스파이크가 임시로 정의했다.
FE가 실제 팔레트를 확정하면 이 dict만 갱신하면 나머지 로직(스냅/평가)은 그대로 재사용된다.
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# 잠정 색상 팔레트 (코드 -> hex). FE 확정 전 placeholder.
# --------------------------------------------------------------------------
PALETTE: dict[str, str] = {
    "BLACK": "#1A1A1A",
    "WHITE": "#FFFFFF",
    "GRAY": "#9B9B9B",
    "IVORY": "#F1EEE3",
    "BEIGE": "#D8C7A8",
    "BROWN": "#7B5B3A",
    "KHAKI": "#8C8560",
    "NAVY": "#22304A",
    "BLUE": "#3B6FB6",
    "SKYBLUE": "#8FC1E3",
    "GREEN": "#4F7942",
    "YELLOW": "#E8D44D",
    "ORANGE": "#E08A2E",
    "RED": "#C43D3D",
    "PINK": "#E6A9C0",
    "PURPLE": "#7D5BA6",
    "WINE": "#6E2A3A",
    "SILVER": "#C7C9CC",
    "GOLD": "#C9A646",
}

# 팔레트 색 하나로 스냅하면 오히려 오도하는 경우(프린트/멀티컬러)를 위한 특수 라벨.
# 정답셋에는 쓸 수 있지만, PALETTE의 실제 hex 항목은 아니다 — 평가 시 별도 취급한다.
MULTI_LABEL = "MULTI"


def _hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    hex_code = hex_code.lstrip("#")
    return tuple(int(hex_code[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def nearest_palette_color_with_distance(rgb: tuple[float, float, float]) -> tuple[str, float]:
    """가장 가까운 팔레트 색 코드 + 정규화된 거리(0~1, 0이면 정확히 일치)."""
    best_code, best_dist = None, float("inf")
    for code, hex_code in PALETTE.items():
        pr, pg, pb = _hex_to_rgb(hex_code)
        dist = (rgb[0] - pr) ** 2 + (rgb[1] - pg) ** 2 + (rgb[2] - pb) ** 2
        if dist < best_dist:
            best_code, best_dist = code, dist
    assert best_code is not None
    # RGB 채널당 최대 편차는 255 -> 최대 가능 거리는 3*255^2. 그 값으로 나눠 0~1로 정규화.
    max_dist = 3 * 255**2
    return best_code, (best_dist / max_dist) ** 0.5


def nearest_palette_color(rgb: tuple[float, float, float]) -> str:
    """RGB 값에 가장 가까운 팔레트 색 코드를 유클리드 거리로 스냅한다."""
    return nearest_palette_color_with_distance(rgb)[0]


@dataclass
class ColorResult:
    primary: str
    secondary: str | None = None
    is_multicolor: bool = False
    backend: str = ""
    # 필드 의미가 백엔드마다 다르다(V4는 반드시 백엔드별로 따로 봐야 한다):
    #   mean_color      — 1 - 팔레트까지의 정규화 거리(가까울수록 확신)
    #   kmeans_palette  — 1등 클러스터의 픽셀 비중(지배적일수록 확신)
    #   vlm             — 파싱/매칭 성공 여부(1.0 성공 / 0.0 실패, 진짜 확률 아님)
    #   mock            — 의미 없는 난수
    confidence: float = 0.0
    raw: dict = field(default_factory=dict)  # 백엔드별 부가정보(클러스터 비율 등, 리포트용)


class ColorExtractor(ABC):
    """색상 추출 백엔드 교체 경계. evaluate.py는 이 인터페이스로만 백엔드를 호출한다."""

    name: str

    @abstractmethod
    def extract(self, image_path: Path) -> ColorResult: ...


# --------------------------------------------------------------------------
# mock — torch/cv2/sklearn 없이도 전 경로가 끝까지 돌게 하는 기본 백엔드.
# 파일명 해시로 팔레트에서 결정적으로 골라 반환한다(무작위지만 재현 가능).
# --------------------------------------------------------------------------
class MockColorExtractor(ColorExtractor):
    name = "mock"

    def extract(self, image_path: Path) -> ColorResult:
        digest = hashlib.sha256(str(image_path).encode("utf-8")).hexdigest()
        codes = list(PALETTE)
        primary = codes[int(digest[:8], 16) % len(codes)]
        secondary = codes[int(digest[8:16], 16) % len(codes)]
        if secondary == primary:
            secondary = codes[(codes.index(secondary) + 1) % len(codes)]
        confidence = int(digest[16:24], 16) / 0xFFFFFFFF
        return ColorResult(
            primary=primary, secondary=secondary, confidence=confidence, backend=self.name
        )


# --------------------------------------------------------------------------
# (b) baseline — 마스크 없이 전체 이미지 평균색 + 스냅. 보조색은 정의상 없음(None).
# --------------------------------------------------------------------------
class MeanColorExtractor(ColorExtractor):
    name = "mean_color"

    def extract(self, image_path: Path) -> ColorResult:
        import numpy as np
        from PIL import Image

        with Image.open(image_path) as img:
            arr = np.asarray(img.convert("RGB"), dtype=np.float64)
        mean_rgb = tuple(arr.reshape(-1, 3).mean(axis=0))
        primary, distance = nearest_palette_color_with_distance(mean_rgb)
        return ColorResult(
            primary=primary,
            secondary=None,
            confidence=1.0 - distance,
            backend=self.name,
            raw={"mean_rgb": [round(c, 1) for c in mean_rgb]},
        )


# --------------------------------------------------------------------------
# (a) 설계안 — 경량 마스크 + k-means(k=3) + 팔레트 스냅.
#
# 마스크 방식은 CH012 §6.2가 명시한 그대로다: "중앙 크롭 + 배경색 추정 + saturation 필터".
# SAM3 마스크를 재사용하지 않는 이유도 §6.2에 있다 — classify 워커가 quality(SAM3) 완료에
# 의존하게 되면 두 파이프라인의 병렬성이 무너지기 때문에, 정확도를 조금 포기하고 완전히
# 독립적인 경량 방법을 쓰기로 한 "의도된 트레이드오프"다. 이 스파이크는 그 트레이드오프가
# 실제로 감당할 만한지(V3) 확인하는 게 목적이라, 여기서 다른 마스크 알고리즘(GrabCut 등)으로
# 대체하면 검증 대상 자체가 바뀌어 버린다 — 반드시 이 세 단계로 구현한다.
#
# opencv 없이 PIL+numpy만으로 구현한다(설계 취지인 "경량"에 더 맞고, 이 스파이크의 다른
# 백엔드도 이미 opencv 없이 도니 새 무거운 의존성을 추가하지 않아도 된다).
# --------------------------------------------------------------------------
def _rgb_to_saturation(rgb: "object") -> "object":
    """HSV의 S 채널만 벡터화 계산(0~1). rgb: (H, W, 3) float 배열, 0~255 스케일."""
    maxc = rgb.max(axis=-1)
    minc = rgb.min(axis=-1)
    sat = (maxc - minc) / maxc.clip(min=1e-6)
    return sat


class KMeansPaletteColorExtractor(ColorExtractor):
    name = "kmeans_palette"

    # CH012 §6.2는 정확한 임계값까지는 정하지 않았다 — 이 스파이크가 정하는 몫이다(V4와 별개로
    # 마스크 자체의 재현성을 위해 상수로 노출해 둔다).
    CROP_MARGIN = 0.1  # 중앙 크롭: 가장자리 10%는 무조건 배경 취급
    BORDER_BAND = 0.05  # 배경색 추정에 쓰는 테두리 띠 두께(원본 기준)
    SAT_THRESHOLD = 0.15  # 이보다 채도가 낮고
    BG_DIST_THRESHOLD = (
        40.0  # 배경 추정색과 이만큼(RGB 유클리드, 0~255 스케일) 가까우면 배경으로 본다
    )

    def __init__(self, k: int = 3, min_cluster_share: float = 0.2):
        self.k = k
        self.min_cluster_share = min_cluster_share

    def _foreground_mask(self, rgb: "object") -> "object":
        import numpy as np

        h, w = rgb.shape[:2]
        band_h, band_w = int(h * self.BORDER_BAND), int(w * self.BORDER_BAND)
        border_pixels = np.concatenate(
            [
                rgb[:band_h].reshape(-1, 3),
                rgb[-band_h:].reshape(-1, 3),
                rgb[:, :band_w].reshape(-1, 3),
                rgb[:, -band_w:].reshape(-1, 3),
            ]
        )
        bg_color = np.median(border_pixels, axis=0)  # 배경색 추정

        sat = _rgb_to_saturation(rgb.astype(np.float64))  # saturation 필터
        dist_from_bg = np.linalg.norm(rgb.astype(np.float64) - bg_color, axis=-1)
        is_background = (sat < self.SAT_THRESHOLD) & (dist_from_bg < self.BG_DIST_THRESHOLD)

        fg_mask = ~is_background
        margin_y, margin_x = int(h * self.CROP_MARGIN), int(w * self.CROP_MARGIN)
        fg_mask[:margin_y, :] = False  # 중앙 크롭: 가장자리는 배경으로 강제
        fg_mask[-margin_y:, :] = False
        fg_mask[:, :margin_x] = False
        fg_mask[:, -margin_x:] = False
        return fg_mask

    def extract(self, image_path: Path) -> ColorResult:
        import numpy as np
        from PIL import Image
        from sklearn.cluster import KMeans

        with Image.open(image_path) as img:
            rgb = np.asarray(img.convert("RGB"))

        fg_mask = self._foreground_mask(rgb)
        fg_ratio = float(fg_mask.mean())
        pixels = rgb[fg_mask].reshape(-1, 3)
        mask_degenerate = len(pixels) < self.k
        if mask_degenerate:
            pixels = rgb.reshape(-1, 3)  # 마스크가 거의 다 날아간 경우 전체 픽셀로 폴백

        km = KMeans(n_clusters=self.k, n_init=4, random_state=0).fit(pixels)
        labels, counts = np.unique(km.labels_, return_counts=True)
        order = np.argsort(-counts)  # 픽셀 수 많은 순
        shares = counts[order] / counts.sum()
        centers = km.cluster_centers_[labels[order]]

        primary = nearest_palette_color(tuple(centers[0]))
        secondary = nearest_palette_color(tuple(centers[1])) if len(centers) > 1 else None
        # 상위 클러스터들이 비슷한 비중으로 갈리면(어느 하나가 지배적이지 않으면) 멀티컬러로 본다.
        is_multicolor = bool((shares >= self.min_cluster_share).sum() >= 3)

        return ColorResult(
            primary=primary,
            secondary=secondary,
            is_multicolor=is_multicolor,
            confidence=float(shares[0]),  # 1등 클러스터 픽셀 비중 — 지배적일수록 확신
            backend=self.name,
            raw={
                "cluster_shares": [round(float(s), 3) for s in shares],
                "foreground_ratio": round(fg_ratio, 3),
                "mask_degenerate": mask_degenerate,
            },
        )


# --------------------------------------------------------------------------
# (c) 대조군 — VLM(Qwen3-VL)에 직접 질의. 무거운 모델 로딩은 vlm_control로 위임하고
# 여기서는 import를 지연시켜(함수 내부) mock 경로가 vlm_control조차 건드리지 않게 한다.
# --------------------------------------------------------------------------
class VLMColorExtractor(ColorExtractor):
    name = "vlm"

    def extract(self, image_path: Path) -> ColorResult:
        from vlm_control import query_color  # 지연 import — 무거운 의존성

        primary, secondary, raw = query_color(image_path)
        confidence = 0.0 if primary == "UNKNOWN" else 1.0  # VLM은 네이티브 확률을 안 준다
        return ColorResult(
            primary=primary, secondary=secondary, confidence=confidence, backend=self.name, raw=raw
        )


# --------------------------------------------------------------------------
# (d) CLIP zero-shot — 카테고리(classify.py)와 완전히 같은 메커니즘(이미지-텍스트 코사인
# 유사도 + temperature softmax)을 색상 라벨에 그대로 적용한다. 지금까지 색상은 (a)/(b)
# 고전 CV, (c) VLM만 있었고 CLIP 자체가 색상을 얼마나 "이해"하는지는 검증한 적이 없었다.
#
# 파인튜닝(100~200건)에 들어가기 전에 이 zero-shot 결과부터 본다 — 카테고리도 en_clip_style
# 프롬프트 하나로 71%까지 나왔던 전례가 있어서, 색상도 프롬프트만으로 어느 정도 나오는지가
# "파인튜닝이 꼭 필요한가"를 가르는 첫 번째 신호다.
# --------------------------------------------------------------------------
EN_COLOR_LABELS: dict[str, str] = {
    "BLACK": "black",
    "WHITE": "white",
    "GRAY": "gray",
    "IVORY": "ivory",
    "BEIGE": "beige",
    "BROWN": "brown",
    "KHAKI": "khaki",
    "NAVY": "navy blue",
    "BLUE": "blue",
    "SKYBLUE": "sky blue",
    "GREEN": "green",
    "YELLOW": "yellow",
    "ORANGE": "orange",
    "RED": "red",
    "PINK": "pink",
    "PURPLE": "purple",
    "WINE": "wine red",
    "SILVER": "silver",
    "GOLD": "gold",
    MULTI_LABEL: "multicolored patterned",
}
assert set(EN_COLOR_LABELS) == set(PALETTE) | {MULTI_LABEL}


class ClipZeroShotColorExtractor(ColorExtractor):
    """CLIP/SigLIP 임베딩에 색상 라벨 텍스트를 직접 물어본다(합성 — `EmbeddingZeroShotClassifier`를
    상속하지 않고 내부에 들고 쓴다. `ColorExtractor` ABC와 `CategoryClassifier` ABC는 반환
    타입이 달라서 상속으로 엮으면 타입이 꼬인다)."""

    # 2등 후보가 이 정도 확률 이상이어야 보조색상으로 인정한다 — 안 그러면 항상 2등 답까지
    # 억지로 보조색상으로 채워서 정확도를 스스로 깎아먹는다.
    SECONDARY_MIN_SCORE = 0.15

    def __init__(self, model_id: str, name: str = "clip_zeroshot"):
        self._model_id = model_id
        self.name = name
        self._backend = None

    def _get_backend(self) -> "EmbeddingZeroShotClassifier":  # noqa: F821 — 지연 import
        if self._backend is None:
            from classify import EmbeddingZeroShotClassifier

            self._backend = EmbeddingZeroShotClassifier(self._model_id)
        return self._backend

    def extract(self, image_path: Path) -> ColorResult:
        codes = list(PALETTE) + [MULTI_LABEL]
        texts = [f"a photo of {EN_COLOR_LABELS[code]} clothing" for code in codes]
        scores = self._get_backend().score_labels(image_path, texts)

        order = sorted(range(len(codes)), key=lambda i: -scores[i])
        primary_code = codes[order[0]]
        primary_score = scores[order[0]]
        secondary_code = (
            codes[order[1]]
            if len(order) > 1 and scores[order[1]] >= self.SECONDARY_MIN_SCORE
            else None
        )

        return ColorResult(
            primary=primary_code,
            secondary=secondary_code,
            is_multicolor=primary_code == MULTI_LABEL,
            confidence=float(primary_score),
            backend=self.name,
            raw={
                "scores": {code: round(float(s), 3) for code, s in zip(codes, scores, strict=True)}
            },
        )


COLOR_BACKENDS: dict[str, "callable[[], ColorExtractor]"] = {
    "mock": MockColorExtractor,
    "mean_color": MeanColorExtractor,
    "kmeans_palette": KMeansPaletteColorExtractor,
    "vlm": VLMColorExtractor,
    # (d) CLIP/SigLIP zero-shot. model_id는 classify.py의 CATEGORY_MODELS와 동일 후보를 쓴다 —
    # 카테고리·색상에 같은 체크포인트를 쓰면 나중에 임베딩 공유(인코더 1회 호출)로 합칠 수 있다.
    "clip_vit_b32": lambda: _make_clip_color("clip_vit_b32"),
    "clip_vit_l14": lambda: _make_clip_color("clip_vit_l14"),
    "siglip_so400m": lambda: _make_clip_color("siglip_so400m"),
}
ACTIVE_COLOR_BACKEND = os.environ.get("PRODUCT_INFO_COLOR_BACKEND", "mock")


def _make_clip_color(model_key: str) -> ClipZeroShotColorExtractor:
    from classify import CATEGORY_MODELS  # 지연 import — 무거운 의존성 체인 회피

    return ClipZeroShotColorExtractor(CATEGORY_MODELS[model_key], name=model_key)


def get_color_extractor(name: str | None = None) -> ColorExtractor:
    """이름 생략 시 `ACTIVE_COLOR_BACKEND`(환경변수 `PRODUCT_INFO_COLOR_BACKEND`로 덮어쓰기 가능)."""
    key = name or ACTIVE_COLOR_BACKEND
    try:
        return COLOR_BACKENDS[key]()
    except KeyError as exc:
        raise ValueError(
            f"unknown color backend: {key!r} (choices: {list(COLOR_BACKENDS)})"
        ) from exc
