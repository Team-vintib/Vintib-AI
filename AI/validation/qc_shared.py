"""품질검수 스파이크 두 개(SAM3 / CLIPSeg)가 공유하는 프롬프트·임계치·필터 로직.

`sam3-condition-check/sam3_qc_test.ipynb` 와 `clipseg-condition-check/clipseg_qc_test.ipynb`
가 **같은 이미지 · 같은 프롬프트 · 같은 후처리**로 돌아야 두 모델 비교가 성립한다.
각 노트북에 상수를 복사해 두면 한쪽만 고쳐져 조용히 어긋나므로 여기 한 곳에만 둔다.

노트북에서 쓰는 법(노트북 CWD 가 자기 폴더라 상위를 경로에 넣는다):

    import sys
    sys.path.insert(0, "..")
    from qc_shared import DEFECT_PROMPTS, BENIGN_PROMPTS, filter_by_garment

스파이크 코드다. 프로덕션(`worker/models/clipseg/`)에서 import 하지 않는다.
"""

from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent

# 두 노트북이 같은 이미지를 봐야 하므로 sam3 쪽 폴더를 공용으로 쓴다(gitignore 되어 있다).
SHARED_IMAGE_DIR = _HERE / "sam3-condition-check" / "sample_images"
SAM3_OUTPUT_DIR = _HERE / "sam3-condition-check" / "outputs"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


# --------------------------------------------------------------------------
# 하자 프롬프트 세트
# --------------------------------------------------------------------------
# 맨 명사("a scratch")는 **바닥·소품의 긁힘까지** 잡는다 — 실측에서 한 장에 29건이
# 검출됐고 상당수가 배경이었다. 프로덕션 CLIPSeg 프롬프트가
# "a stain on {color} {garment} fabric" 처럼 원단을 명시하는 이유가 이것이다.
#
# 다만 SAM3 는 논문상 **짧은 명사구**(예: "yellow school bus")로 학습돼 있어 문장을 길게
# 늘이면 오히려 나빠질 수 있다. 어느 표현이 실제로 나은지는 실측 대상이므로 세트로 만들어
# 두고 ACTIVE_PROMPT_SET 만 바꿔 비교한다.
PROMPT_SETS: dict[str, dict[str, str]] = {
    # 대조군 — 기존 프롬프트. 배경 오탐이 가장 많다.
    "bare": {
        "STAIN": "a stain",
        "SCRATCH": "a scratch",
        "TEAR": "a tear",
        "HOLE": "a hole",
    },
    # 원단 한정. LAB-12 CLIPSeg 프롬프트와 같은 골격이다.
    "fabric": {
        "STAIN": "a stain on fabric",
        "SCRATCH": "a scratch on fabric",
        "TEAR": "a tear in fabric",
        "HOLE": "a hole in fabric",
    },
    # 의류 명시. 명사구를 짧게 유지하려고 "clothing" 한 단어만 덧붙였다.
    "garment": {
        "STAIN": "a stain on clothing",
        "SCRATCH": "a scratch on clothing",
        "TEAR": "a tear in clothing",
        "HOLE": "a hole in clothing",
    },
}
ACTIVE_PROMPT_SET = "fabric"  # <- 여기만 바꾸면 두 노트북이 함께 스왑된다
DEFECT_PROMPTS: dict[str, str] = PROMPT_SETS[ACTIVE_PROMPT_SET]


# --------------------------------------------------------------------------
# 정상인데 하자로 오인되는 것들 (억제용)
# --------------------------------------------------------------------------
# 주름·접힘·그림자를 하자로 잡는 문제를 프롬프트로 푸는 방법이다. 같은 이미지에 이 개념들도
# 탐지시킨 뒤, 하자 인스턴스가 이들 영역에 잠겨 있으면 떨어뜨린다.
#
# CLIPSeg 백엔드의 `clean fabric` 대조 정규화(`registry.clean_margin`)와 같은 발상이다.
# 다만 SAM3 는 인스턴스 단위 출력이라 확률 감산 대신 **영역 겹침**으로 처리한다.
BENIGN_PROMPTS: dict[str, str] = {
    "WRINKLE": "a wrinkle on fabric",
    "FOLD": "a fold in fabric",
    "SHADOW": "a shadow",
    "SEAM": "a seam",
    "PRINT": "a printed pattern on fabric",
}

# 의류 영역 게이트 — 배경(바닥·소품) 탐지를 구조적으로 걷어낸다.
# 프롬프트만으로는 배경 오탐이 0 이 되지 않아서, 의류 마스크를 따로 뽑아 교집합으로 거른다.
# 005 계획 §고도화 경로 3(의류 영역 마스크로 배경 제외)에 해당한다.
GARMENT_PROMPT = "clothing"
GARMENT_OVERLAP_MIN = 0.6  # 하자 마스크의 이 비율 이상이 의류 안에 있어야 채택
RESTRICT_TO_GARMENT = True

BENIGN_CONTAINMENT = 0.6  # 하자 마스크가 양성 마스크에 이만큼 잠기면 억제 후보
SUPPRESS_BENIGN = True

# 판정 구간: PASS < 0.4 <= REVIEW <= 0.7 < FAIL
# ⚠️ 근거 없는 초기값이다. 라벨링된 검증셋 확보 후 스윕해서 확정해야 한다.
VERDICT_THRESHOLDS = (0.4, 0.7)


# --------------------------------------------------------------------------
# 백엔드별 임계치 — 여기는 **공유하지 않는다**
# --------------------------------------------------------------------------
# 003 계획의 교훈("모델마다 점수 스케일이 달라 고정 임계치를 모델 무관하게 재사용하면 안 된다")이
# 그대로 적용된다. SAM3 의 `pred_logits.sigmoid() * presence_logits.sigmoid()` 와 CLIPSeg 의
# 픽셀 sigmoid 확률은 서로 비교할 수 있는 값이 아니다.
BACKEND_THRESHOLDS = {
    # post_process_instance_segmentation 의 threshold (HF 기본값)
    "sam3": {"score": 0.30},
    # worker/models/clipseg/registry.py 의 clipseg_rd64_refined defect_threshold
    "clipseg": {"prob": 0.45},
}

# 겹침 판정은 **기하학적 비율**이라 스케일과 무관하다 — 그래서 백엔드가 달라도 공유한다.
MIN_AREA_RATIO = 0.0015  # 이보다 작은 blob 은 노이즈로 버린다 (registry.py 와 같은 값)


# --------------------------------------------------------------------------
# 공용 후처리 — 두 노트북이 **똑같은 로직**을 써야 비교가 공정하다
# --------------------------------------------------------------------------
def use_korean_font():
    """matplotlib 제목·범례의 한글이 □□ 로 깨지지 않게 한글 폰트를 잡는다.

    기본 폰트(DejaVu Sans)에는 한글 글리프가 없어 "Glyph ... missing from font(s)" 경고와
    함께 두부 문자로 렌더된다. 개발 노트북(Windows)에는 맑은 고딕이 있다.
    후보를 전부 못 찾으면 조용히 넘어간다 — 그림이 안 나오는 것보단 낫다.
    """
    import matplotlib
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    for candidate in ("Malgun Gothic", "AppleGothic", "NanumGothic", "Gulim"):
        if candidate in available:
            matplotlib.rcParams["font.family"] = candidate
            # 한글 폰트로 바꾸면 마이너스 기호가 깨지므로 유니코드 마이너스를 끈다.
            matplotlib.rcParams["axes.unicode_minus"] = False
            return candidate
    return None


def list_images(image_dir=SHARED_IMAGE_DIR):
    """공용 이미지 폴더의 이미지 목록(하위 폴더 포함, 정렬)."""
    image_dir = Path(image_dir)
    if not image_dir.is_dir():
        return []
    return sorted(p for p in image_dir.rglob("*") if p.suffix.lower() in IMAGE_EXTS)


def containment(a: np.ndarray, b: np.ndarray) -> float:
    """|a ∩ b| / |a| — a 가 b 안에 얼마나 잠겨 있는가. a 가 비면 0."""
    a_bool = a.astype(bool)
    area = int(a_bool.sum())
    if area == 0:
        return 0.0
    return float(np.logical_and(a_bool, b.astype(bool)).sum() / area)


def filter_by_garment(instances, garment_mask, min_overlap=GARMENT_OVERLAP_MIN):
    """의류 영역 밖의 인스턴스를 떨어뜨린다. (kept, dropped) 반환.

    `garment_mask` 가 None 이면(의류를 못 찾음) **아무것도 거르지 않는다** — 의류 탐지가
    실패했는데 전부 버리면 "하자 없음"과 "판정 실패"가 구별되지 않는다.
    """
    if garment_mask is None:
        return list(instances), []

    kept, dropped = [], []
    for inst in instances:
        overlap = containment(inst["mask"], garment_mask)
        inst["garment_overlap"] = round(overlap, 4)
        (kept if overlap >= min_overlap else dropped).append(inst)
    return kept, dropped


def suppress_benign(defects, benigns, min_containment=BENIGN_CONTAINMENT):
    """주름·접힘·그림자 등 정상 영역에 잠긴 하자 인스턴스를 억제한다.

    억제 조건은 두 가지를 모두 만족할 때다:
      1. 하자 마스크가 양성 마스크에 `min_containment` 이상 잠겨 있고,
      2. **양성 쪽 confidence 가 하자 쪽보다 높다.**

    2번이 없으면 주름 위에 실제로 생긴 오염까지 지워진다. 같은 모델의 같은 sigmoid 스케일이라
    두 점수를 비교하는 것 자체는 성립한다.
    """
    kept, dropped = [], []
    for inst in defects:
        hit = None
        for benign in benigns:
            if benign["confidence"] < inst["confidence"]:
                continue
            if containment(inst["mask"], benign["mask"]) >= min_containment:
                hit = benign
                break
        if hit is None:
            kept.append(inst)
        else:
            inst["suppressed_by"] = f"{hit['type']}({hit['confidence']:.2f})"
            dropped.append(inst)
    return kept, dropped


def renumber(instances):
    """confidence 내림차순으로 정렬하고 no 를 1부터 다시 매긴다."""
    ordered = sorted(instances, key=lambda d: d["confidence"], reverse=True)
    for no, inst in enumerate(ordered, start=1):
        inst["no"] = no
    return ordered


def decide_verdict(instances, thresholds=VERDICT_THRESHOLDS):
    """인스턴스별 confidence 최댓값으로 PASS / REVIEW / FAIL 판정. (verdict, peak) 반환."""
    review_at, fail_at = thresholds
    peak = max((d["confidence"] for d in instances), default=0.0)
    if peak > fail_at:
        return "FAIL", peak
    if peak >= review_at:
        return "REVIEW", peak
    return "PASS", peak


def to_serializable(instances):
    """mask(ndarray)를 뺀 JSON 직렬화 가능한 형태로 변환."""
    fields = ("no", "type", "prompt", "bbox", "confidence", "garment_overlap")
    return [{k: d[k] for k in fields if k in d} for d in instances]
