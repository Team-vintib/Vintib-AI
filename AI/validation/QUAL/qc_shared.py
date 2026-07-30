"""품질검수 스파이크 세 개(SAM3 / CLIPSeg / 하이브리드)가 공유하는 프롬프트·임계치·필터 로직.

`sam3-condition-check/sam3_qc_test.ipynb`, `clipseg-condition-check/clipseg_qc_test.ipynb`,
`clipseg-sam3tracker-hybrid-check/hybrid_qc_test.ipynb` 가 **같은 이미지 · 같은 프롬프트 ·
같은 후처리**로 돌아야 아키텍처 비교가 성립한다.
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
# DIRT_MARK("a dirty mark")는 세 세트 모두 **똑같은 문구**를 쓴다 — LAB-12 가 검증한 게 이
# 표현 하나뿐이라 "on fabric"/"on clothing" 을 붙인 변형은 검증된 적이 없다. CLIPSeg 노트북을
# SAM3 와 같은 프롬프트로 맞추면서(공정 비교 목적) 이 개념이 빠졌었는데, LAB-12·프로덕션
# (`worker/models/clipseg/prompts.py`)이 검증한 오염 계열 핵심 프롬프트라 다시 넣는다.
PROMPT_SETS: dict[str, dict[str, str]] = {
    # 대조군 — 기존 프롬프트. 배경 오탐이 가장 많다.
    "bare": {
        "STAIN": "a stain",
        "SCRATCH": "a scratch",
        "TEAR": "a tear",
        "HOLE": "a hole",
        "DIRT_MARK": "a dirty mark",
    },
    # 원단 한정. LAB-12 CLIPSeg 프롬프트와 같은 골격이다.
    "fabric": {
        "STAIN": "a stain on fabric",
        "SCRATCH": "a scratch on fabric",
        "TEAR": "a tear in fabric",
        "HOLE": "a hole in fabric",
        "DIRT_MARK": "a dirty mark",
    },
    # 의류 명시. 명사구를 짧게 유지하려고 "clothing" 한 단어만 덧붙였다.
    "garment": {
        "STAIN": "a stain on clothing",
        "SCRATCH": "a scratch on clothing",
        "TEAR": "a tear in clothing",
        "HOLE": "a hole in clothing",
        "DIRT_MARK": "a dirty mark",
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
#
# 양성 후보를 **두 종류로 나눈다** — 억제 조건이 다르다.
#
# 1) 구조적 개구부(STRUCTURAL) — 암홀·넥라인·밑단·소매끝. "a hole in fabric" 프롬프트 자체가
#    손상된 구멍과 의류가 원래 갖고 있는 개구부를 구분하지 못한다(둘 다 "구멍"이라는 단어로는
#    같은 개념). 실측(검정 티셔츠 1장)에서 넥라인 1건 + 밑단 1건 + 소매끝 2건, 총 4건이 전부
#    HOLE 오탐이었다 — 처음엔 암홀·넥라인만 등록했는데 밑단·소매끝은 못 걸러 범위를 넓혔다.
#    크롭 여부와 무관하게 원본 이미지에서도 재현되는 문제다(git aa9a977, 크롭 도입 전에도
#    동일 프롬프트로 재현됨).
#    **이 항목들은 겹치면 confidence 비교 없이 곧바로 억제한다** — 실제 손상이 정확히 같은
#    모양·위치로 넥라인/소매끝 자체가 될 수는 없으니, 겹침 자체가 "이건 그 구조물이다"의
#    충분한 증거다. 아래(TEXTURE_BENIGN_PROMPTS)와 이 부분이 다른 이유다.
#
# 2) 질감형(TEXTURE) — 주름·접힘·그림자·솔기·프린트. 이 위에는 **실제 하자가 진짜로 생길 수
#    있다**(솔기 근처에 실밥이 뜯기거나, 주름 접힌 자리에 오염이 앉거나). 그래서 겹침만으로
#    억제하면 안 되고, **양성 쪽 confidence 가 하자보다 높을 때만** 억제한다 — 확신이 더 강한
#    쪽을 믿는다는 원칙이다.
STRUCTURAL_BENIGN_PROMPTS: dict[str, str] = {
    # 짧은 명사구로 통일한다 — SAM3 는 논문상 짧은 명사구로 학습돼 있어 수식어를 붙일수록
    # 반응이 약해진다("a scratch" -> "a scratch on fabric" 실측에서 이미 확인). HEM/CUFF 를
    # 처음엔 3단어로 넣었다가 억제가 안 됐는데, 이 길이 차이가 원인일 가능성이 있다.
    "ARMHOLE": "an armhole",
    "NECKLINE": "a neckline",
    "HEM": "a hem",
    "CUFF": "a cuff",
}

TEXTURE_BENIGN_PROMPTS: dict[str, str] = {
    "WRINKLE": "a wrinkle on fabric",
    "FOLD": "a fold in fabric",
    "SHADOW": "a shadow",
    "SEAM": "a seam",
    "PRINT": "a printed pattern on fabric",
}

BENIGN_PROMPTS: dict[str, str] = {**STRUCTURAL_BENIGN_PROMPTS, **TEXTURE_BENIGN_PROMPTS}

# 의류 영역 게이트 — 배경(바닥·소품) 탐지를 구조적으로 걷어낸다.
# 005 계획 §고도화 경로 3(의류 영역 마스크로 배경 제외)에 해당한다.
GARMENT_PROMPT = "clothing"
GARMENT_OVERLAP_MIN = 0.6  # 하자 마스크의 이 비율 이상이 의류 안에 있어야 채택
RESTRICT_TO_GARMENT = True

# ⚠️ 크롭(crop-then-detect) 여부 토글과 그 여유 비율(`GARMENT_CROP_PAD_RATIO`)은 **여기 없다.**
# 각 노트북(`sam3_qc_test.ipynb`/`clipseg_qc_test.ipynb`)의 설정 상수 셀에 `CROP_BEFORE_DETECT`
# 지역 변수로 따로 있다 — 두 노트북을 독립적으로 실험하려고 분리해 둔 건데, 이 토글을 여기
# 공유 모듈에 두면 한쪽만 켜고 다른 쪽은 끈 채로 비교할 수가 없어서다.
#
# 왜 기본값이 False(크롭 안 함)인지는 실측 근거가 있다 — 의류 bbox 로 이미지를 실제로 잘라낸
# 뒤 그 안에서만 탐지하면 배경 오탐은 줄지만, 실측 상품 사진 8장 중 6장에서 기존에 잡히던
# 오염/찢어짐을 더 못 잡거나(완전 미검출도 있었음) 전부 STAIN 으로만 쏠리는 회귀가 나왔다.
# 뚜렷한 하자만 크롭 여부와 무관하게 살아남았다 — 크롭이 작거나 애매한 하자에 더 해롭다.
# 가설: ① 의류 마스크가 소매 끝·밑단을 못 덮으면 그 부분이 통째로 잘려나간다 ② 확대되면서
# 유형을 구분하던 주변 맥락이 좁아져 개념 매칭이 한쪽으로 쏠린다. 상세 데이터·크롭 버전
# 스냅샷은 각 노트북의 `CROP_BEFORE_DETECT` 지역 변수 옆 주석과
# `sam3-condition-check/sam3_qc_test_seg_ver.ipynb` 참고.
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
    # garment_score: 의류 존재 여부만 확인하는 임계치라 하자 탐지(0.30)보다 훨씬 관대하게 잡는다.
    # ⚠️ 처음엔 여기도 0.30 을 그대로 썼다가, "clothing" 개념이 그 기준을 못 넘기면 의류를
    # 아예 못 찾아 크롭·필터가 통째로 no-op 되는 문제가 실측에서 나왔다(라이브 검수 이슈).
    # 존재 확인용 임계치와 정밀 판정용 임계치를 분리한 이유가 이것이다.
    "sam3": {"score": 0.30, "garment_score": 0.05},
    # worker/models/clipseg/registry.py 의 clipseg_rd64_refined defect_threshold
    "clipseg": {"prob": 0.45, "garment_prob": 0.05},
}

# 겹침 판정은 **기하학적 비율**이라 스케일과 무관하다 — 그래서 백엔드가 달라도 공유한다.
MIN_AREA_RATIO = 0.0015  # 이보다 작은 blob 은 노이즈로 버린다 (registry.py 와 같은 값)


# --------------------------------------------------------------------------
# 한글 라벨 — bbox 태그·JSON 출력에 쓴다
# --------------------------------------------------------------------------
KOREAN_LABELS: dict[str, str] = {
    "STAIN": "오염",
    "SCRATCH": "스크래치",
    "TEAR": "찢어짐",
    "HOLE": "구멍",
    "DIRT_MARK": "얼룩",  # worker/models/clipseg/scoring.py 의 DEFECT_LABELS 와 같은 한글
    # 양성(억제용) 태그도 함께 둔다 — 디버깅 시각화(§6 히트맵 등)에서 재사용한다.
    "WRINKLE": "주름",
    "FOLD": "접힘",
    "SHADOW": "그림자",
    "SEAM": "솔기",
    "PRINT": "프린트",
    "ARMHOLE": "암홀",
    "NECKLINE": "넥라인",
    "HEM": "밑단",
    "CUFF": "소매 끝단",
}


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


def korean_font_path(size: int = 18):
    """PIL `ImageFont` 로 쓸 한글 TTF 경로. `cv2.putText` 는 Hershey 폰트뿐이라 한글을 못
    그린다(빈 네모나 깨진 기호로 나온다) — 그래서 bbox 라벨은 cv2가 아니라 PIL 로 그린다.

    개발 환경(Windows)의 맑은 고딕을 우선 찾고, 없으면 None(호출부가 fallback 처리)."""
    from PIL import ImageFont

    for candidate in (
        r"C:\Windows\Fonts\malgun.ttf",
        r"C:\Windows\Fonts\malgunbd.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    ):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
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


def mask_iou(a: np.ndarray, b: np.ndarray) -> float:
    """|a ∩ b| / |a ∪ b| — 대칭 겹침 비율. 둘 다 비면 0.

    `containment` 와 달리 방향이 없다. 마스크 **정제 전/후 비교**에 쓴다 — 정제는 같은 대상의
    경계만 다듬는 것이라 IoU 가 높아야 정상이고, 낮으면 "정제"가 아니라 "대상이 바뀐" 것이다
    (SAM3Tracker 는 class-agnostic 이라 실제로 이 일이 일어난다).
    """
    a_bool, b_bool = a.astype(bool), b.astype(bool)
    union = int(np.logical_or(a_bool, b_bool).sum())
    if union == 0:
        return 0.0
    return float(np.logical_and(a_bool, b_bool).sum() / union)


def probs_to_instances(prob_map, tag, prompt, threshold, min_area_ratio=MIN_AREA_RATIO):
    """확률 히트맵 1장 -> 인스턴스 리스트. SAM3 PCS 출력과 같은 dict 스키마로 맞춘다.

    CLIPSeg 에는 인스턴스 개념이 없다(프롬프트당 확률맵 1장이 전부). 임계치로 이진화하고
    연결요소를 뽑아 `{type, prompt, bbox, confidence, mask}` 형태로 만들어야
    `filter_by_garment`/`suppress_benign`/`decide_verdict` 를 SAM3 와 똑같이 태울 수 있다.

    - `confidence` 는 blob 내부 확률의 **최댓값**(peak) — 프로덕션 `findings.py` 와 같다.
    - `min_area_ratio` 미만 blob 은 노이즈로 버린다 — `registry.py` 와 같은 값이 기본이다.
    - `threshold` 에 기본값을 두지 않는다. 백엔드마다 확률 스케일이 달라(`BACKEND_THRESHOLDS`)
      호출부가 어떤 임계치를 쓰는지 항상 명시해야 한다.

    ⚠️ 프로덕션(`worker/models/clipseg/findings.py`)은 scipy 없이 돌리려고 순수 numpy
    flood-fill 을 쓰고 여기는 `cv2.connectedComponentsWithStats` 를 쓴다. 결과는 같지만
    프로덕션 수치와 1:1 로 대조할 때는 확인이 필요하다.
    """
    import cv2

    binary = (prob_map > threshold).astype(np.uint8)
    total = prob_map.size
    if binary.sum() == 0:
        return []

    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=4)
    found = []
    for label in range(1, count):  # 0 은 배경
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area / total < min_area_ratio:
            continue
        mask = (labels == label).astype(np.uint8)
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])
        found.append(
            {
                "type": tag,
                "prompt": prompt,
                "bbox": [x, y, x + w, y + h],
                "confidence": round(float(prob_map[mask.astype(bool)].max()), 4),
                "mask": mask,
            }
        )
    return found


# --------------------------------------------------------------------------
# 크롭 기반 의류 게이트 — "의류만 세그먼트한 상태에서 탐지"
# --------------------------------------------------------------------------
# 이전 버전은 하자 탐지와 같은 임계치(0.30)로 "clothing" 을 찾아 마스크 겹침만으로 걸렀는데,
# 그 임계치를 못 넘으면 의류를 아예 못 찾아 필터가 통째로 no-op 됐다(원인은
# BACKEND_THRESHOLDS 의 garment_score/garment_prob 주석 참고). 지금은 관대한 전용 임계치로
# 의류 영역을 먼저 찾고, **그 bbox 로 이미지 자체를 잘라 그 안에서만** 하자 프롬프트를
# 돌린다 — 배경(바닥·소품)이 애초에 모델 입력에 들어가지 않는다.


def pick_largest(instances):
    """마스크 면적이 가장 큰 인스턴스 1개. 여러 조각으로 나뉘어 잡혀도 '진짜 의류'를 고르기 위함."""
    if not instances:
        return None
    return max(instances, key=lambda d: int(d["mask"].sum()))


def pad_bbox_clamped(bbox, pad_ratio, image_size):
    """bbox 를 pad_ratio 만큼 넓히고 이미지 경계 안으로 clamp. image_size = (width, height)."""
    img_w, img_h = image_size
    x1, y1, x2, y2 = bbox
    pad_x = int((x2 - x1) * pad_ratio) + 1
    pad_y = int((y2 - y1) * pad_ratio) + 1
    return [
        max(0, int(x1) - pad_x),
        max(0, int(y1) - pad_y),
        min(img_w, int(x2) + pad_x),
        min(img_h, int(y2) + pad_y),
    ]


def remap_instances_to_full(instances, crop_box, full_size):
    """크롭 좌표계의 인스턴스를 원본 이미지 좌표계로 되돌린다(bbox 오프셋 + mask 캔버스 배치).

    full_size = (width, height). 다운스트림(오버레이·§8 crop 등)이 전부 '원본 이미지 좌표'를
    전제하므로, 크롭 안에서 탐지한 뒤에는 반드시 이 함수로 되돌려야 한다.
    """
    x1, y1, x2, y2 = crop_box
    full_w, full_h = full_size
    out = []
    for inst in instances:
        bx1, by1, bx2, by2 = inst["bbox"]
        new_inst = dict(inst)
        new_inst["bbox"] = [bx1 + x1, by1 + y1, bx2 + x1, by2 + y1]
        full_mask = np.zeros((full_h, full_w), dtype=np.uint8)
        crop_h, crop_w = inst["mask"].shape
        full_mask[y1 : y1 + crop_h, x1 : x1 + crop_w] = inst["mask"]
        new_inst["mask"] = full_mask
        out.append(new_inst)
    return out


def remap_mask_to_full(mask, crop_box, full_size):
    """크롭 좌표계의 마스크 1장을 원본 크기 캔버스로 되돌린다."""
    x1, y1, _, _ = crop_box
    full_w, full_h = full_size
    full_mask = np.zeros((full_h, full_w), dtype=np.uint8)
    crop_h, crop_w = mask.shape
    full_mask[y1 : y1 + crop_h, x1 : x1 + crop_w] = mask
    return full_mask


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


def suppress_benign(
    defects,
    benigns,
    min_containment=BENIGN_CONTAINMENT,
    unconditional_types=frozenset(STRUCTURAL_BENIGN_PROMPTS),
):
    """정상 영역에 잠긴 하자 인스턴스를 억제한다. 억제 조건이 양성 종류에 따라 다르다.

    - **구조적 개구부**(`unconditional_types` — 기본은 STRUCTURAL_BENIGN_PROMPTS: 암홀·넥라인·
      밑단·소매끝) — 겹치기만 하면(`min_containment` 이상) confidence 비교 없이 곧바로
      억제한다. 실제 손상이 정확히 그 구조물 자체와 같은 모양·위치일 수는 없으니, 겹침 자체가
      "이건 그 구조물이다"의 충분한 증거다.
    - **질감형**(그 외 — 주름·접힘·그림자·솔기·프린트) — 겹침 + **양성 쪽 confidence 가 하자
      쪽보다 높을 때만** 억제한다. 이 위에는 실제 하자가 진짜로 생길 수 있어서(솔기 근처 실밥
      뜯김, 주름 자리 오염), 확신이 더 강한 쪽을 믿는다는 원칙이다. 이 조건이 없으면 주름 위에
      실제로 생긴 오염까지 지워진다.
    """
    kept, dropped = [], []
    for inst in defects:
        hit = None
        for benign in benigns:
            structural = benign["type"] in unconditional_types
            if not structural and benign["confidence"] < inst["confidence"]:
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


# --------------------------------------------------------------------------
# 시각화 — 두 노트북이 **같은 함수**로 그려야 그림도 눈으로 비교가 된다
# --------------------------------------------------------------------------
def draw_numbered_boxes(pil_image, instances, box_color=(255, 0, 0), thickness=4):
    """confidence 내림차순 1,2,3… 번호 + 한글 유형 라벨 + 빨간 박스. RGB ndarray 반환.

    `cv2.putText` 는 Hershey 폰트만 지원해 한글을 그리지 못한다(빈 네모/깨진 기호로 나온다).
    그래서 박스는 OpenCV로, **라벨 텍스트는 PIL** 로 그린다. box_color 는 PIL 기준 RGB.
    """
    from PIL import Image as PILImage
    from PIL import ImageDraw

    import cv2

    canvas = np.array(pil_image).copy()
    ordered = sorted(instances, key=lambda d: d["confidence"], reverse=True)

    for inst in ordered:
        x1, y1, x2, y2 = (int(v) for v in inst["bbox"])
        cv2.rectangle(canvas, (x1, y1), (x2, y2), box_color, thickness)

    pil_canvas = PILImage.fromarray(canvas)
    draw = ImageDraw.Draw(pil_canvas)
    font_size = max(14, int(0.022 * max(pil_canvas.size)))
    font = korean_font_path(font_size)

    if font is None:
        print("[주의] 한글 TTF 폰트를 못 찾았습니다 — 라벨이 기본 폰트로 그려져 한글이 깨집니다.")

    for no, inst in enumerate(ordered, start=1):
        x1, y1, _, _ = (int(v) for v in inst["bbox"])
        label_ko = KOREAN_LABELS.get(inst["type"], inst["type"])
        text = f"{no}. {label_ko} {inst['confidence']:.2f}"
        box = draw.textbbox((0, 0), text, font=font)  # font=None 이면 PIL 기본 비트맵 폰트
        tw, th = box[2] - box[0], box[3] - box[1]
        ty = max(y1 - th - 6, 0)
        draw.rectangle([x1, ty, x1 + tw + 8, ty + th + 6], fill=box_color)
        draw.text((x1 + 4, ty + 2), text, fill=(255, 255, 255), font=font)

    return np.array(pil_canvas)


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
    """mask(ndarray)를 뺀 JSON 직렬화 가능한 형태로 변환.

    `type` 은 코드(STAIN 등)로 그대로 두고 `label` 에 한글 표시명을 별도로 담는다 —
    FE 전달 스키마(안)이 `defect_type` + `label` 두 필드로 나눈 것과 같은 이유다.
    """
    fields = ("no", "type", "prompt", "bbox", "confidence", "garment_overlap")
    out = []
    for d in instances:
        row = {k: d[k] for k in fields if k in d}
        row["label"] = KOREAN_LABELS.get(d["type"], d["type"])
        out.append(row)
    return out
