"""V3 — 색상 추출 백엔드 비교.

  (a) kmeans_palette  — 경량 마스크(중앙 크롭+배경색 추정+saturation 필터) + k-means(k=3)
                        + 팔레트 스냅  [설계안, CH012 §6.2 그대로]
  (b) mean_color      — 마스크 없이 전체 이미지 평균색 + 팔레트 스냅              [baseline]
  (c) vlm              — Qwen3-VL에 직접 질의(vlm_control.query_color 위임)        [대조군]
  (d) clip_vit_b32/clip_vit_l14/siglip_so400m — CLIP/SigLIP zero-shot(색상 라벨 텍스트와
                        이미지 임베딩 코사인 유사도). classify.py의 카테고리 zero-shot과
                        같은 메커니즘을 색상에 적용 — 2026-08-02 추가, "CLIP 파인튜닝으로
                        색상까지 처리" 결정 전에 먼저 zero-shot 신호부터 본다.
  (e) *_ensemble(예: clip_vit_b32_ensemble) — (d)와 모델은 같고, 단일 문구 대신 템플릿 x
                        동의어 프롬프트 앙상블로 스코어링(2026-08-03 추가, 색상 개선안
                        1·2번). `EN_COLOR_SYNONYMS`/`_COLOR_ENSEMBLE_TEMPLATES` 참고.
                        **실측 결과 (d)보다 나쁘다(N=10: 0.20 -> 0.10, `REPORT.md` §11)** —
                        코드는 회귀 사례 재현용으로 남겨뒀을 뿐 권장 백엔드가 아니다.
  (f) *_wb/*_debias/*_wb_debias(예: clip_vit_b32_wb_debias) — (d)에 화이트밸런스
                        전처리(`gray_world_white_balance`)와 content-free 편향 보정
                        (`use_debias`, 혼동행렬로 확인된 GRAY/NAVY/SILVER 쏠림 상쇄)을
                        각각/함께 적용. **실측상 가장 좋은 CLIP 조합**(N=10: 0.20 ->
                        0.50, `REPORT.md` §17) — 그래도 VLM(0.90)에는 못 미친다.

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


def gray_world_white_balance(image: "object") -> "object":
    """gray-world 가정 화이트밸런스 보정: 이미지 평균이 중성회색이 되도록 채널별로
    스케일링한다(입력·반환 모두 PIL.Image, RGB로 변환됨).

    실측(2026-08-03, N=10, `REPORT.md` §13): VLM 색상 primary 정확도를 0.60~0.70 ->
    **0.90**(3회 반복 다수결)으로 올렸다 — 프롬프트 엔지니어링(§10~§12)이 못 올린 걸
    입력 전처리가 해결했다. 조명의 색 편향(warm/cool cast)이 WHITE->IVORY, BLACK->GRAY/NAVY
    같은 오답의 실제 원인이었다는 뜻이다. 카테고리(§10 v4, 10/10 유지)엔 부작용이 없었다.
    한계: 장면 전체 평균이 실제로 무채색에 가깝다는 가정이 전제라, 어둡고 단일 색이 화면
    대부분을 차지하는 사진(예: `black_stain.png`)에서는 가정이 깨져 여전히 오답이 남는다."""
    import numpy as np

    arr = np.asarray(image.convert("RGB"), dtype=np.float64)
    channel_means = arr.reshape(-1, 3).mean(axis=0)
    gray = channel_means.mean()
    scale = gray / np.clip(channel_means, 1e-6, None)
    corrected = np.clip(arr * scale, 0, 255).astype(np.uint8)

    from PIL import Image

    return Image.fromarray(corrected)


def build_swatch_reference(
    product_image: "object", codes: list[str], swatch_size: int = 64, cols: int = 5
) -> "object":
    """상품 사진 아래에 팔레트 스와치(hex 사각형 + 코드 라벨) 그리드를 합성한 이미지를
    만든다(색상 개선안 4번, 2026-08-03). 색 이름을 텍스트로만 지시하면 VLM이 자기 내부
    "색 이름 감각"에 의존하게 되는데(예: IVORY라는 단어가 실제로 어떤 hex를 가리키는지는
    프롬프트에 전혀 안 알려줌), 실제 hex 사각형을 같은 이미지에 넣어주면 VLM이 이미지 대
    이미지로 비교 판단할 수 있다. `MULTI_LABEL`은 특정 hex가 없어 스와치를 그리지 않는다
    (프롬프트 쪽에서 "스와치는 없지만 코드로는 답할 수 있다"고 안내).

    입력·반환 모두 PIL.Image(RGB)."""
    from PIL import Image, ImageDraw

    label_h = 20
    cell = swatch_size + label_h
    rows = -(-len(codes) // cols)  # ceil division
    grid_w = cols * swatch_size
    grid_h = rows * cell

    product_resized = product_image.copy()
    product_resized.thumbnail((grid_w, grid_w * 2))

    canvas_w = max(grid_w, product_resized.width)
    canvas = Image.new("RGB", (canvas_w, product_resized.height + grid_h + 10), "white")
    canvas.paste(product_resized, (0, 0))

    draw = ImageDraw.Draw(canvas)
    grid_top = product_resized.height + 10
    for i, code in enumerate(codes):
        col, row = i % cols, i // cols
        x = col * swatch_size
        y = grid_top + row * cell
        hex_code = PALETTE[code]
        draw.rectangle(
            [x + 2, y + 2, x + swatch_size - 2, y + swatch_size - 2], fill=hex_code, outline="black"
        )
        draw.text((x + 2, y + swatch_size + 2), code, fill="black")
    return canvas


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

# --------------------------------------------------------------------------
# 프롬프트 앙상블(색상 개선안 1·2번, 2026-08-03 추가) — 단일 템플릿/단일 단어의 어휘
# 노이즈를 줄이려고 여러 템플릿 x 여러 동의어 조합의 임베딩을 평균 낸다(원조 CLIP zero-shot
# 앙상블 레시피). 동의어는 실제로 헷갈렸던 코드에만 추가한다 — 정답셋 라벨링 정정 이력
# (logo_test.jpg BEIGE->WHITE, small_pro.jpg SKYBLUE->WHITE)이 근거다. 나머지는 원래
# 단어 하나로 충분하다(과설계 방지).
# --------------------------------------------------------------------------
_COLOR_ENSEMBLE_TEMPLATES: tuple[str, ...] = (
    "a photo of {color} clothing",
    "{color} colored clothing",
    "clothing in {color}",
    "a {color} garment",
)

EN_COLOR_SYNONYMS: dict[str, tuple[str, ...]] = {
    code: (word,) for code, word in EN_COLOR_LABELS.items()
}
EN_COLOR_SYNONYMS.update(
    {
        "IVORY": ("ivory", "off-white", "cream"),
        "BEIGE": ("beige", "tan", "sand"),
        "NAVY": ("navy blue", "dark blue", "deep blue"),
        "GRAY": ("gray", "grey"),
        "SILVER": ("silver", "metallic gray"),
        "BROWN": ("brown", "chocolate brown"),
        "KHAKI": ("khaki", "olive tan"),
        "SKYBLUE": ("sky blue", "light blue"),
    }
)
assert set(EN_COLOR_SYNONYMS) == set(EN_COLOR_LABELS)


class ClipZeroShotColorExtractor(ColorExtractor):
    """CLIP/SigLIP 임베딩에 색상 라벨 텍스트를 직접 물어본다(합성 — `EmbeddingZeroShotClassifier`를
    상속하지 않고 내부에 들고 쓴다. `ColorExtractor` ABC와 `CategoryClassifier` ABC는 반환
    타입이 달라서 상속으로 엮으면 타입이 꼬인다).

    `use_ensemble=True`면 단일 문구 대신 `_COLOR_ENSEMBLE_TEMPLATES` x `EN_COLOR_SYNONYMS`
    조합을 전부 평균해 스코어링한다(색상 개선안 1·2번, `score_label_groups` 위임).
    **실측 결과 회귀했다(N=10: 0.20 -> 0.10, `REPORT.md` §11)** — 권장하지 않는다,
    재현/참고용으로만 남겨둠.

    `use_white_balance=True`면 `gray_world_white_balance()`로 입력을 먼저 보정한다(VLM
    색상에 크게 도움됐던 전처리, `REPORT.md` §13). CLIP은 개선폭이 작지만(§13: 0.20->0.30)
    무해하고 카테고리에 부작용도 없었던 전처리라 옵션으로 노출해둔다.

    `use_debias=True`면 content-free 보정(Zhao et al. 2021, "Calibrate Before Use")을
    적용한다 — 실측 혼동행렬(`REPORT.md` §17)이 GRAY/NAVY/SILVER 같은 특정 라벨로 쏠리는
    "끌개" 현상을 보여줬는데, 이 라벨들은 실제 이미지 내용과 무관하게 CLIP 텍스트 임베딩
    자체가 이미지와 잘 맞는(사전 확률이 높은) 라벨일 수 있다. 무채색 중립 이미지로 각
    라벨의 사전 확률을 구해두고, 실제 이미지 점수를 그 사전 확률로 나눠 편향을 상쇄한다.
    앙상블(`use_ensemble`)과는 동시에 못 쓴다(단순화, 앙상블은 이미 폐기된 방향)."""

    # 2등 후보가 이 정도 확률 이상이어야 보조색상으로 인정한다 — 안 그러면 항상 2등 답까지
    # 억지로 보조색상으로 채워서 정확도를 스스로 깎아먹는다.
    SECONDARY_MIN_SCORE = 0.15

    def __init__(
        self,
        model_id: str,
        name: str = "clip_zeroshot",
        use_ensemble: bool = False,
        use_white_balance: bool = False,
        use_debias: bool = False,
    ):
        if use_ensemble and use_debias:
            raise ValueError("use_ensemble과 use_debias는 동시에 쓸 수 없다")
        self._model_id = model_id
        self.name = name
        self._use_ensemble = use_ensemble
        self._use_white_balance = use_white_balance
        self._use_debias = use_debias
        self._debias_prior: list[float] | None = None
        self._backend = None

    def _get_backend(self) -> "EmbeddingZeroShotClassifier":  # noqa: F821 — 지연 import
        if self._backend is None:
            from classify import EmbeddingZeroShotClassifier

            self._backend = EmbeddingZeroShotClassifier(self._model_id)
        return self._backend

    def extract(self, image_path: Path) -> ColorResult:
        codes = list(PALETTE) + [MULTI_LABEL]
        query_path = self._maybe_white_balance(image_path)
        if self._use_ensemble:
            groups = [
                [
                    t.format(color=syn)
                    for t in _COLOR_ENSEMBLE_TEMPLATES
                    for syn in EN_COLOR_SYNONYMS[code]
                ]
                for code in codes
            ]
            scores = self._get_backend().score_label_groups(query_path, groups)
        else:
            texts = [f"a photo of {EN_COLOR_LABELS[code]} clothing" for code in codes]
            scores = self._get_backend().score_labels(query_path, texts)
            if self._use_debias:
                if self._debias_prior is None:
                    self._debias_prior = self._compute_debias_prior(texts)
                scores = [s / max(prior, 1e-6) for s, prior in zip(scores, self._debias_prior)]

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

    def _maybe_white_balance(self, image_path: Path) -> Path:
        """`use_white_balance=True`면 보정본을 임시 파일로 저장해 그 경로를 반환한다.
        `classify.EmbeddingZeroShotClassifier.score_labels()`가 경로만 받기 때문에(PIL
        Image 객체를 직접 못 받음) 임시 파일을 거친다 — 검증 스파이크 범위에서는 이 정도
        오버헤드가 새 클래스를 만드는 것보다 낫다."""
        if not self._use_white_balance:
            return image_path
        import tempfile

        from PIL import Image

        with Image.open(image_path) as img:
            corrected = gray_world_white_balance(img.convert("RGB"))
        tmp_path = Path(tempfile.mkdtemp(prefix="clip_color_wb_")) / Path(image_path).name
        corrected.save(tmp_path)
        return tmp_path

    def _compute_debias_prior(self, texts: list[str]) -> list[float]:
        """content-free 보정의 사전 확률 — 무채색 중립(RGB 128,128,128) 이미지로 같은
        라벨 문구를 질의해 "이미지 내용과 무관한" 라벨별 기본 점수를 구한다. 프로세스당
        한 번만 계산해 재사용한다(`self._debias_prior` 캐시)."""
        import tempfile

        from PIL import Image

        neutral = Image.new("RGB", (224, 224), (128, 128, 128))
        tmp_path = Path(tempfile.mkdtemp(prefix="clip_color_calib_")) / "neutral.png"
        neutral.save(tmp_path)
        return self._get_backend().score_labels(tmp_path, texts)


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
    # 프롬프트 앙상블(색상 개선안 1·2번, 2026-08-03 추가) — 모델은 위와 동일, 스코어링만
    # 템플릿 x 동의어 앙상블로 바꾼 버전. REPORT.md §11 참고.
    "clip_vit_b32_ensemble": lambda: _make_clip_color("clip_vit_b32", ensemble=True),
    "clip_vit_l14_ensemble": lambda: _make_clip_color("clip_vit_l14", ensemble=True),
    "siglip_so400m_ensemble": lambda: _make_clip_color("siglip_so400m", ensemble=True),
    # 화이트밸런스 전처리(2026-08-03 추가) — VLM 색상엔 크게 도움됐던 전처리를 CLIP에도
    # 적용해본 버전. REPORT.md §17 참고(0.20 -> 0.30).
    "clip_vit_b32_wb": lambda: _make_clip_color("clip_vit_b32", white_balance=True),
    "clip_vit_l14_wb": lambda: _make_clip_color("clip_vit_l14", white_balance=True),
    "siglip_so400m_wb": lambda: _make_clip_color("siglip_so400m", white_balance=True),
    # content-free 편향 보정(2026-08-03 추가) — 혼동행렬(REPORT.md §17)에서 확인된
    # GRAY/NAVY/SILVER 쏠림을 상쇄해본다. 화이트밸런스와 결합한 버전도 같이 등록.
    "clip_vit_b32_debias": lambda: _make_clip_color("clip_vit_b32", debias=True),
    "clip_vit_b32_wb_debias": lambda: _make_clip_color(
        "clip_vit_b32", white_balance=True, debias=True
    ),
}
ACTIVE_COLOR_BACKEND = os.environ.get("PRODUCT_INFO_COLOR_BACKEND", "mock")


def _make_clip_color(
    model_key: str,
    ensemble: bool = False,
    white_balance: bool = False,
    debias: bool = False,
) -> ClipZeroShotColorExtractor:
    from classify import CATEGORY_MODELS  # 지연 import — 무거운 의존성 체인 회피

    suffix = "_ensemble" if ensemble else ""
    suffix += "_wb" if white_balance else ""
    suffix += "_debias" if debias else ""
    return ClipZeroShotColorExtractor(
        CATEGORY_MODELS[model_key],
        name=f"{model_key}{suffix}",
        use_ensemble=ensemble,
        use_white_balance=white_balance,
        use_debias=debias,
    )


def get_color_extractor(name: str | None = None) -> ColorExtractor:
    """이름 생략 시 `ACTIVE_COLOR_BACKEND`(환경변수 `PRODUCT_INFO_COLOR_BACKEND`로 덮어쓰기 가능)."""
    key = name or ACTIVE_COLOR_BACKEND
    try:
        return COLOR_BACKENDS[key]()
    except KeyError as exc:
        raise ValueError(
            f"unknown color backend: {key!r} (choices: {list(COLOR_BACKENDS)})"
        ) from exc
