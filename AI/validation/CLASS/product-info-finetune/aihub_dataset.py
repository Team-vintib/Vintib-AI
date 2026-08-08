"""AI-Hub "의류 통합 데이터" 라벨 JSON → 우리 taxonomy v2 라벨 인덱스 + 착수 전 scan.

설계: `.claude/plans/ai/CH014-class-finetune.md`
지시서: `AI/validation/CLASS/CLASSIFIER_FINETUNE_BRIEF.md`
포맷 명세: Notion LAB-76 "[DATA] 의류 통합 데이터 — 어노테이션 포맷"

Throwaway/spike code — 프로덕션 코드가 아니다. `fashion_clip` 백본은 **동결**하고 그 위에
선형 헤드만 학습하는 게 목표이며(브리핑 §3), 이 모듈은 그 학습/평가에 쓸 **라벨 인덱스**를
만드는 첫 단계다. 이미지 픽셀은 건드리지 않는다(그건 `aihub_preprocess.py`).

실행 위치 — 이 스크립트는 원격 GPU 서버에서 돈다
------------------------------------------------
AI-Hub 데이터는 로컬에 없다(브리핑 §3-1). 그래서 경로를 하드코딩하지 않고 전부 `--root`로
받으며, `Path.cwd()`에 의존하지 않는다(원격 Jupyter 커널에 붙으면 파일은 로컬·실행은 원격이라
상대경로가 어긋난다). 장시간 작업이므로 노트북이 아니라 `argparse` 스크립트다 — 사용자가
`tmux` 안에서 돌린다.

두 가지 모드
------------
- ``scan``  : 라벨 JSON만 훑어 **착수 게이트 2개**(브리핑 §4)와 분포를 텍스트 표로 찍는다.
              이미지가 없어도 된다. 이 출력이 나오기 전에는 다음 단계로 가지 않는다.
- ``index`` : 파싱 + 라벨 매핑 + 그룹 단위 분할 + 층화 샘플링 → JSONL 두 개를 떨군다.

**scan 결과를 추측해서 코드에 박지 마라.** 특히 `SHORT_PANTS_MAX_CM`은 히스토그램을 보고
사람이 정하는 값이라 기본값이 `None`이다(= SHORT_PANTS 파생 안 함).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

_HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# 라벨 정본(`product-info-check/taxonomy.py`·`color.py`)을 **파일 경로로** 싣는다.
#
# `sys.path`에 형제 스파이크 폴더를 꽂지 않는 게 핵심이다. pytest 기본(prepend) import
# 모드에서 그 폴더를 sys.path에 올리면 그 안의 `dataset.py`가
# `REC/recommendation-embedding-finetune/dataset.py`를 가려 **CI 수집이 깨진다**
# (2026-08-03에 실제로 발생, `AI/CLAUDE.md` 기록). importlib으로 유일한 모듈명을 붙여
# 직접 로드하면 sys.path를 전혀 건드리지 않는다.
# --------------------------------------------------------------------------
_LABEL_SOURCE_DIR = _HERE.parent / "product-info-check"


def _load_label_module(stem: str) -> Any:
    """`product-info-check/<stem>.py`를 `_pic_<stem>`이라는 유일한 이름으로 로드한다."""
    module_name = f"_pic_{stem}"
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    path = _LABEL_SOURCE_DIR / f"{stem}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - 경로가 깨졌을 때만
        raise ImportError(f"라벨 정본을 로드할 수 없다: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_taxonomy = _load_label_module("taxonomy")
_color = _load_label_module("color")

ALL_SUBCATEGORIES: tuple[str, ...] = _taxonomy.ALL_SUBCATEGORIES
PALETTE_CODES: tuple[str, ...] = tuple(_color.PALETTE)
MIXED_LABEL: str = _color.MIXED_LABEL
COLOR_CODES: tuple[str, ...] = PALETTE_CODES + (MIXED_LABEL,)

# zero-shot 기준선을 재현할 때 쓰는 라벨 문구(정본 그대로). `aihub_evaluate.py`가 쓴다 —
# 여기서 한 번 노출해 두면 평가 스크립트가 `product-info-check`를 sys.path에 얹지 않아도 된다.
CATEGORY_PROMPT = _taxonomy.PROMPT_TEMPLATES["en_clip_style"]
EN_COLOR_LABELS: dict[str, str] = _color.EN_COLOR_LABELS

# --------------------------------------------------------------------------
# 재현성 상수 — 학습·평가 스크립트가 같은 값을 공유해 split을 재현한다(`AI/CLAUDE.md` 관례).
# --------------------------------------------------------------------------
SEED = 42
TRAIN_RATIO = 0.8
VAL_RATIO = 0.1
TEST_RATIO = 0.1
assert abs(TRAIN_RATIO + VAL_RATIO + TEST_RATIO - 1.0) < 1e-9

# 층화 샘플링 상한(브리핑 §8). 550k 전부 쓰지 않는다.
CATEGORY_CAP_PER_CLASS = 3000
COLOR_CAP_PER_CLASS = 2000
# 액세서리 소스 전용 상한 — **소스별 비중 조절 손잡이**.
#
# 기본값을 의류와 같게 둔 건 선형 분류 헤드에서 중요한 건 "소스별 총량"이 아니라 "클래스당
# 표본 수"이기 때문이다. 액세서리는 3종(HAT/SUNGLASSES/JEWELRY)뿐이라 같은 상한이어도
# 전체의 20% 남짓이다. 다만 이 데이터셋은 착용컷 비중이 높아(모델이 쓴 모자·낀 선글라스)
# 우리 입력(제품 단독컷)과 도메인이 어긋날 수 있다 — scan의 제품/착용 비율을 보고 낮추거나,
# `aihub_embed.py --shot-type product`로 제품컷만 골라 쓸 것.
ACCESSORY_CAP_PER_CLASS = 3000
# 홀드아웃 평가셋: 커버 클래스당 이 개수(브리핑 §11의 "커버 11종 × 100장").
EVAL_CAP_PER_CLASS = 100

# **scan 히스토그램을 보고 사람이 정한다.** None이면 SHORT_PANTS 파생을 하지 않는다 —
# 브리핑 §12: "실행 결과를 추측해서 채우지 마라".
SHORT_PANTS_MAX_CM: float | None = None

# --------------------------------------------------------------------------
# 라벨 매핑 (브리핑 §5 — LAB-76 §2의 매핑표는 taxonomy v1 기준이라 낡았다)
# --------------------------------------------------------------------------
DIRECT_CATEGORY_MAP: dict[str, str] = {
    "01outer_01coat": "COAT",
    "01outer_02jacket": "JACKET",
    # 사용자 확정(2026-08-04): 점퍼는 JACKET으로 흡수한다. 브리핑 §5는 "흡수 여부 미결정"
    # 이라 제외 목록에 뒀는데, 그 결정이 내려졌다. 3,467건이 JACKET 쪽으로 들어온다.
    "01outer_03jumper": "JACKET",
    "01outer_04cardigan": "CARDIGAN",
    "02top_02t-shirt": "TSHIRT",
    "02top_03sweater": "KNIT",
    "02top_04shirt": "SHIRT",
    # 사용자 확정(2026-08-04): 블라우스는 SHIRT로 흡수한다. 브리핑 §5는 "흡수 여부 미결정"
    # 이라 제외 목록에 뒀는데, 그 결정이 내려졌다. 29,719건이 SHIRT 쪽으로 들어온다 —
    # SHIRT는 폴로 이진 헤드(B)의 음성 클래스이기도 해서 학습량이 늘어나는 게 유리하다.
    "02top_01blouse": "SHIRT",
    "04bottom_02skirt": "SKIRT",
    "03-1onepiece(dress)": "DRESS",
    "03-2onepiece(jumpsuite)": "JUMPSUIT",
}
assert set(DIRECT_CATEGORY_MAP.values()) <= set(ALL_SUBCATEGORIES)

# 우리 코드에 대응이 없거나 흡수 여부가 미결정이라 학습에서 뺀다(브리핑 §5).
EXCLUDED_CATEGORY_TYPES: dict[str, str] = {
    # 사용자 확정(2026-08-04): vest는 제외 유지. taxonomy v2에 VEST가 없고(BE 시드에 없음),
    # 23,134건을 통째로 SLEEVELESS로 보내면 민소매 상의에 패딩 베스트가 섞인다.
    "02top_05vest": "제외 확정(2026-08-04) — taxonomy v2에 VEST가 없다",
    "04bottom_01pants": "하위 5종 구분 불가 — SHORT_PANTS 파생에만 쓴다",
}

# 파생 규칙(후드/민소매)을 **제외 대상 상의**(= vest)에도 적용할지.
#
# 기본값 False로 vest를 확실히 뺀다(사용자 확정). blouse는 이제 SHIRT로 매핑되므로 파생
# 대상에 정상 포함된다 — 후드 블라우스는 HOODIE, 민소매 블라우스는 SLEEVELESS가 된다.
# scan이 "이 값을 True로 바꾸면 몇 건이 늘어나는지"를 따로 찍어 준다.
DERIVE_FROM_EXCLUDED_TOPS = False

# AI-Hub `clothes.color` → 우리 팔레트. 대소문자·공백 정규화 후 조회한다(브리핑 §5).
# Navy는 LAB-76이 자기모순이라(§3-1엔 있고 §4-7엔 없다) **게이트 2**의 확인 대상이다 —
# 여기 매핑을 넣어 두는 것과 데이터에 실재하는 것은 별개다. scan이 실제 건수를 찍는다.
COLOR_MAP: dict[str, str] = {
    "black": "BLACK",
    "white": "WHITE",
    "gray": "GRAY",
    "red": "RED",
    "orange": "ORANGE",
    "pink": "PINK",
    "yellow": "YELLOW",
    "brown": "BROWN",
    "green": "GREEN",
    "blue": "BLUE",
    "purple": "PURPLE",
    "beige": "BEIGE",
    "navy": "NAVY",
    "mixed": MIXED_LABEL,
}
assert set(COLOR_MAP.values()) == set(COLOR_CODES)

SHOT_TYPES = ("front", "back", "wear")

# --------------------------------------------------------------------------
# JSON 파싱 — LAB-76이 기록한 함정 3개를 여기서 전부 흡수한다.
#   1) 최상위 키가 `metadata.clothes`처럼 **점 포함 평탄 키**다(중첩 객체가 아니다)
#   2) 빈 값이 `None`이 아니라 **문자열 "null"** 이고, 숫자도 문자열이다("56", "66.0")
#   3) 명세 표기(`annotation.point`)와 실제 키(`annotation_point`)가 다르다
# --------------------------------------------------------------------------


def clean(value: Any) -> Any:
    """`"null"`·빈 문자열을 `None`으로 바꾸고 문자열은 trim한다(함정 2)."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() == "null":
            return None
        return stripped
    return value


def to_float(value: Any) -> float | None:
    """숫자 필드가 문자열로 오는 걸 감안한 안전 캐스팅(함정 2). 실패하면 None."""
    cleaned = clean(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def _lookup(js: dict, block: str, key: str) -> Any:
    """평탄 키 블록에서 값을 꺼낸다(함정 1).

    `metadata.top.*` / `metadata.pants.*`는 **`metadata.clothes` 블록 안에** 들어 있다
    (LAB-76 실제 JSON 샘플 기준). 그래서 지정 블록에서 못 찾으면 `metadata.clothes`와
    최상위를 차례로 뒤진다 — 파일마다 배치가 갈려도 같은 값을 집는다.
    """
    for candidate in (block, "metadata.clothes", None):
        container = js if candidate is None else js.get(candidate)
        if isinstance(container, dict) and key in container:
            return clean(container[key])
    return None


@dataclass(frozen=True)
class RawLabel:
    """라벨 JSON 1개에서 뽑은 원본 값(우리 코드로 매핑하기 **전**)."""

    label_path: str  # --root 기준 상대경로
    image_path: str | None  # JSON에 적힌 값 그대로(경로 규약은 preprocess에서 해석)
    name: str
    width: int | None
    height: int | None
    source_type: str | None  # metadata.clothes.type
    color: str | None  # metadata.clothes.color
    shot_type: str | None  # metadata.model.type (front/back/wear)
    neck: str | None  # metadata.clothes.topneck_color_design
    sleeve: str | None  # metadata.clothes.sleeve_length_type
    pants_length: float | None  # metadata.pants.pants_length
    polygon_points: int  # annotation_point 길이 // 2 (0이면 마스크 없음)


def parse_label(js: dict, label_path: str = "") -> RawLabel:
    """라벨 JSON dict → `RawLabel`. 깨진 필드는 None으로 두고 계속한다(best-effort)."""
    dataset = js.get("dataset") if isinstance(js.get("dataset"), dict) else {}

    annotations = js.get("annotation")
    points: list = []
    if isinstance(annotations, list) and annotations:
        first = annotations[0]
        if isinstance(first, dict):
            raw_points = first.get("annotation_point")  # 함정 3: 실제 키 이름
            if isinstance(raw_points, list):
                points = raw_points

    width = to_float(dataset.get("dataset.width"))
    height = to_float(dataset.get("dataset.height"))
    name = clean(dataset.get("dataset.name")) or Path(label_path).stem

    return RawLabel(
        label_path=label_path,
        image_path=clean(dataset.get("dataset.image_path")),
        name=str(name),
        width=int(width) if width else None,
        height=int(height) if height else None,
        source_type=_lookup(js, "metadata.clothes", "metadata.clothes.type"),
        color=_lookup(js, "metadata.clothes", "metadata.clothes.color"),
        shot_type=_lookup(js, "metadata.model", "metadata.model.type"),
        neck=_lookup(js, "metadata.clothes", "metadata.clothes.topneck_color_design"),
        sleeve=_lookup(js, "metadata.clothes", "metadata.clothes.sleeve_length_type"),
        pants_length=to_float(_lookup(js, "metadata.pants", "metadata.pants.pants_length")),
        polygon_points=len(points) // 2,
    )


# --------------------------------------------------------------------------
# 라벨 매핑
# --------------------------------------------------------------------------

# 파생 규칙 1·2(후드/민소매)를 적용할 상의 타입 = **직접 매핑이 되는 상의 전부**.
# blouse가 SHIRT로 흡수되면서(2026-08-04) 자동으로 여기 들어온다. vest만 남아서 빠진다.
_DERIVABLE_TOPS = frozenset(code for code in DIRECT_CATEGORY_MAP if code.startswith("02top_"))


def _is_hood(neck: str | None) -> bool:
    return neck is not None and "hood" in neck.casefold()


def _is_sleeveless(sleeve: str | None) -> bool:
    return sleeve is not None and "sleeveless" in sleeve.casefold()


def is_polo(neck: str | None) -> bool:
    """(B) 폴로 이진 헤드 전용 플래그. 카테고리 라벨은 바꾸지 않는다(브리핑 §5)."""
    return neck is not None and "polo" in neck.casefold()


def map_subcategory(
    label: RawLabel,
    *,
    short_pants_max_cm: float | None = None,
    derive_from_excluded_tops: bool = DERIVE_FROM_EXCLUDED_TOPS,
    bottom_pseudo_labels: dict[str, str] | None = None,
) -> tuple[str | None, str]:
    """AI-Hub 라벨 → 우리 소분류 코드. 반환은 `(코드 또는 None, 사유)`.

    브리핑 §5의 우선순위 그대로: 후드 → 민소매 → 숏팬츠 → (하의 재라벨링) → 직접 매핑표.
    앞의 규칙이 이긴다. 매핑 못 한 이유를 문자열로 같이 돌려주는 건 scan이 "왜 몇 건이
    빠졌는지"를 집계하기 위해서다(조용히 버리면 커버리지를 오판한다).

    `bottom_pseudo_labels`: `aihub_bottom_label.py`가 만든 `{label_path: 소분류코드}` 맵
    (호출부가 이미 accepted/confidence로 걸러 넘긴다). AI-Hub 메타데이터에는 팬츠 소재
    컬럼이 없어(`EXCLUDED_CATEGORY_TYPES["04bottom_01pants"]`) `04bottom_01pants`를 직접
    매핑할 방법이 없었는데, 이미지 자체를 fashion_clip/VLM으로 재라벨링해 이 한계를
    우회한다 — 단 **길이 기반 SHORT_PANTS 판정이 항상 먼저다**(반바지는 소재와 무관하게
    SHORT_PANTS여야 한다).
    """
    source_type = label.source_type
    if source_type is None:
        return None, "clothes.type 없음"

    is_top = source_type.startswith("02top_")
    derivable_top = is_top and (derive_from_excluded_tops or source_type in _DERIVABLE_TOPS)

    if derivable_top and _is_hood(label.neck):
        return "HOODIE", "파생: topneck=hood"
    if derivable_top and _is_sleeveless(label.sleeve):
        return "SLEEVELESS", "파생: sleeve=sleeveless"

    if source_type == "04bottom_01pants":
        is_short = (
            short_pants_max_cm is not None
            and label.pants_length is not None
            and label.pants_length < short_pants_max_cm
        )
        if is_short:
            return "SHORT_PANTS", f"파생: pants_length<{short_pants_max_cm}"
        pseudo = bottom_pseudo_labels.get(label.label_path) if bottom_pseudo_labels else None
        if pseudo is not None:
            return pseudo, "파생: 하의 소재 재라벨링(aihub_bottom_label.py)"
        if short_pants_max_cm is None:
            return None, "제외: pants (SHORT_PANTS 임계 미정, 재라벨링도 없음)"
        if label.pants_length is None:
            return None, "제외: pants (pants_length 없음, 재라벨링도 없음)"
        return None, "제외: pants (임계 이상, 재라벨링도 없음)"

    direct = DIRECT_CATEGORY_MAP.get(source_type)
    if direct is not None:
        return direct, "직접 매핑"

    reason = EXCLUDED_CATEGORY_TYPES.get(source_type)
    if reason is not None:
        return None, f"제외: {reason}"
    return None, f"알 수 없는 clothes.type: {source_type}"


def map_color(raw_color: str | None) -> str | None:
    """AI-Hub `clothes.color` → 우리 팔레트 코드(대소문자·공백 정규화 후)."""
    if raw_color is None:
        return None
    return COLOR_MAP.get(raw_color.strip().casefold())


def load_bottom_pseudo_labels(path: Path, *, min_confidence: float | None = None) -> dict[str, str]:
    """`aihub_bottom_label.py` 출력 JSONL → `{label_path: 소분류코드}`.

    라벨링 스크립트가 이미 계산해 둔 `accepted`(신뢰도 임계 통과 여부)를 그대로 믿는 게
    기본이다. `min_confidence`를 주면 라벨링을 다시 안 돌리고 여기서 임계치만 다르게
    재적용할 수 있다(예: 처음엔 보수적으로 써 보고, 결과가 괜찮으면 임계치를 낮춰 더 많은
    행을 포함시키는 식).
    """
    labels: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            code = row.get("subcategory")
            if not code:
                continue
            if min_confidence is not None:
                if row.get("confidence", 0.0) < min_confidence:
                    continue
            elif not row.get("accepted", False):
                continue
            labels[row["label_path"]] = code
    return labels


# 그룹 키로 인정할 숫자 토큰의 최소 길이. `01_sou_000834_004168_wear_...`에서 선두 `01`을
# 건너뛰고 `000834`(의류 식별자)를 잡기 위한 값이다 — `004168`은 이미지별 id다.
GROUP_TOKEN_MIN_LEN = 4


def group_key_from_name(name: str) -> tuple[str, bool]:
    """파일명 → `(그룹 키, 규칙 적중 여부)`.

    같은 의류의 front/back/wear가 split을 넘나들면 누수라 지표가 부풀려진다(브리핑 §8).
    규칙에 안 맞는 파일명은 **자기 자신을 그룹 키로** 써서 최소한 누수는 안 나게 하고,
    그런 건수를 scan이 따로 찍는다(전부 폴백이면 그룹 분할이 사실상 no-op이라는 뜻).
    """
    stem = Path(name).stem
    for token in stem.split("_"):
        if token.isdigit() and len(token) >= GROUP_TOKEN_MIN_LEN:
            return token, True
    return stem, False


@dataclass(frozen=True)
class Record:
    """학습/평가에 실제로 쓰는 한 줄. 폴리곤 좌표는 담지 않는다 — 용량이 크고,
    `aihub_preprocess.py`가 `label_path`로 원본 JSON을 다시 읽으면 된다."""

    label_path: str
    image_path: str | None
    name: str
    width: int | None
    height: int | None
    group_key: str
    subcategory: str | None
    color: str | None
    # **접기 전 원본 색상 문자열**("실버", "Gray", "로즈골드" …).
    #
    # 팔레트로 미리 접어 학습하면(실버·그레이 → 둘 다 GRAY) 클래스 내부가 시각적으로
    # 갈라져(금속 광택 vs 직물) 선형 경계가 불리해진다. 네이티브 라벨로 학습한 뒤 argmax를
    # 접는 쪽이 정보 손실이 없고, 나중에 팔레트를 13종→10종으로 줄여도 **재학습 없이 접는
    # 맵만 바꾸면 된다**. `aihub_train_head.py --label-space native`가 이 컬럼을 쓴다.
    color_raw: str | None = None
    shot_type: str | None = None
    is_polo: bool = False
    source_type: str | None = None
    # 원본 `topneck_color_design`. (B) 폴로 이진 헤드가 음성 클래스를 "shirts collar"로
    # 정확히 집어내야 해서(브리핑 §3-B) `is_polo` 불리언만으론 부족하다.
    neck: str | None = None
    # 어느 AI-Hub 데이터셋에서 왔는지. 두 소스를 섞어 학습하므로 **소스별 비중을 조절하고
    # 소스별로 성능을 따로 보려면** 이 컬럼이 반드시 필요하다.
    #   "clothes"   — 008. 의류 통합 데이터 (dataSetSn 71501)
    #   "accessory" — 009. 패션 액세서리 착용 데이터 (dataSetSn 71441)
    source: str = "clothes"


def to_record(
    label: RawLabel,
    *,
    short_pants_max_cm: float | None = None,
    derive_from_excluded_tops: bool = DERIVE_FROM_EXCLUDED_TOPS,
    bottom_pseudo_labels: dict[str, str] | None = None,
) -> tuple[Record, str]:
    """`RawLabel` → `(Record, 카테고리 매핑 사유)`."""
    subcategory, reason = map_subcategory(
        label,
        short_pants_max_cm=short_pants_max_cm,
        derive_from_excluded_tops=derive_from_excluded_tops,
        bottom_pseudo_labels=bottom_pseudo_labels,
    )
    group_key, _matched = group_key_from_name(label.name)
    record = Record(
        label_path=label.label_path,
        image_path=label.image_path,
        name=label.name,
        width=label.width,
        height=label.height,
        group_key=group_key,
        subcategory=subcategory,
        color=map_color(label.color),
        color_raw=label.color,
        shot_type=label.shot_type,
        is_polo=is_polo(label.neck),
        source_type=label.source_type,
        neck=label.neck,
    )
    return record, reason


# --------------------------------------------------------------------------
# 파일 순회
# --------------------------------------------------------------------------


def iter_label_files(root: Path, limit: int | None = None) -> Iterator[Path]:
    """`root` 아래 모든 `*.json`을 정렬된 순서로 낸다(재현성 — os.walk 순서는 FS마다 다르다)."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for filename in sorted(filenames):
            if not filename.endswith(".json"):
                continue
            yield Path(dirpath) / filename
            count += 1
            if limit is not None and count >= limit:
                return


@dataclass
class LoadStats:
    total_files: int = 0
    parse_errors: int = 0
    group_fallbacks: int = 0
    error_samples: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.error_samples is None:
            self.error_samples = []


def load_labels(
    root: Path,
    *,
    limit: int | None = None,
    progress_every: int = 50000,
    stats: LoadStats | None = None,
) -> Iterator[RawLabel]:
    """`root` 아래 라벨 JSON을 전부 파싱해 `RawLabel`로 낸다. 깨진 파일은 세고 건너뛴다."""
    tracker = stats if stats is not None else LoadStats()
    for path in iter_label_files(root, limit=limit):
        tracker.total_files += 1
        if progress_every and tracker.total_files % progress_every == 0:
            print(f"  ... {tracker.total_files:,}개 읽음", file=sys.stderr, flush=True)
        try:
            js = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            tracker.parse_errors += 1
            if len(tracker.error_samples) < 5:
                tracker.error_samples.append(f"{path}: {exc}")
            continue
        if not isinstance(js, dict):
            tracker.parse_errors += 1
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        yield parse_label(js, label_path=relative)


# --------------------------------------------------------------------------
# 분할 — 그룹 단위로 먼저 나누고 그 안에서 층화한다(브리핑 §8)
# --------------------------------------------------------------------------


def split_groups(
    records: list[Record],
    *,
    seed: int = SEED,
    ratios: tuple[float, float, float] = (TRAIN_RATIO, VAL_RATIO, TEST_RATIO),
) -> dict[str, str]:
    """`group_key` → `"train"|"val"|"test"`.

    **그룹을 먼저 나눈다.** 같은 의류의 front/back/wear가 split을 넘나들면 지표가
    부풀려진다. 층화는 그룹의 대표 라벨(카테고리 우선, 없으면 색상)로 하고, 층 안에서
    시드 셔플 후 비율대로 자른다 — 층이 작아도 train이 먼저 채워진다.
    """
    members: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        members[record.group_key].append(record)

    strata: dict[str, list[str]] = defaultdict(list)
    for group_key, group_records in members.items():
        labels = [r.subcategory for r in group_records if r.subcategory] or [
            r.color for r in group_records if r.color
        ]
        stratum = Counter(labels).most_common(1)[0][0] if labels else "__unlabeled__"
        strata[stratum].append(group_key)

    train_ratio, val_ratio, _ = ratios
    assignment: dict[str, str] = {}
    for stratum in sorted(strata):
        keys = sorted(strata[stratum])
        random.Random(f"{seed}:{stratum}").shuffle(keys)
        total = len(keys)
        # **누적 경계**로 자른다(층별로 round를 따로 하면 반올림 오차가 쌓여 val이 통째로
        # 비는 층이 생긴다 — 실제로 소규모 픽스처에서 val=0이 나왔다).
        n_train = int(total * train_ratio)
        n_val = int(total * (train_ratio + val_ratio)) - n_train
        # 층이 아주 작아도(1~2개) train이 비지 않게 한다.
        if total and n_train == 0:
            n_train, n_val = 1, min(n_val, max(total - 1, 0))
        for index, key in enumerate(keys):
            if index < n_train:
                assignment[key] = "train"
            elif index < n_train + n_val:
                assignment[key] = "val"
            else:
                assignment[key] = "test"
    return assignment


def select_stratified(
    records: list[Record],
    *,
    category_cap: int,
    color_cap: int,
    accessory_cap: int | None = None,
    allow_cap_overflow: bool = False,
    seed: int = SEED,
) -> list[Record]:
    """클래스당 상한을 걸어 뽑는다. 카테고리 셋과 색상 셋의 **합집합**(중복 제거)이다.

    브리핑 §8: 색상 클래스당 2,000 × 14 + 커버 카테고리당 3,000 × 11 → 합쳐 5만 장 내외.

    **소스별 비중 조절** — `accessory_cap`을 주면 액세서리 소스 레코드에만 다른 상한을
    적용한다. 두 데이터셋은 규모가 딴판이라(의류 550,634건 vs 액세서리 착용컷만 수십만 건)
    같은 상한을 쓰면 액세서리 3종(HAT/SUNGLASSES/JEWELRY)이 의류 11종과 같은 비중을
    차지해 버린다. 특히 JEWELRY는 목걸이+귀걸이 2:1 매핑이라 혼자 두 배로 들어온다.

    **카테고리 상한은 기본적으로 진짜 상한이다.** 색상 쿼터를 채우는 2패스가 카테고리
    상한을 무시하면 상한을 걸어도 안 걸린다 — 실제로 `--accessory-cap 4`인데 JEWELRY가
    17건 들어오는 걸 확인했다(2026-08-04 스모크). 그래서 색상 패스도 카테고리 상한을
    존중한다. 그 대가로 희귀 색상의 쿼터가 덜 찰 수 있어, 못 채운 양을 함께 돌려준다.
    옛 동작(색상 우선, 카테고리 초과 허용)이 필요하면 `allow_cap_overflow=True`.

    중복 제거 키는 `(source, label_path, name)`이다 — 액세서리는 라벨 JSON 하나에 여러
    이미지가 들어 있어 `label_path`만으로는 유일하지 않다.
    """
    shuffled = list(records)
    random.Random(seed).shuffle(shuffled)

    def cap_of(record: Record) -> int:
        if accessory_cap is not None and record.source == "accessory":
            return accessory_cap
        return category_cap

    def key_of(record: Record) -> tuple[str, str, str]:
        return (record.source, record.label_path, record.name)

    chosen: set[tuple[str, str, str]] = set()
    category_counts: Counter[str] = Counter()
    for record in shuffled:
        if record.subcategory and category_counts[record.subcategory] < cap_of(record):
            category_counts[record.subcategory] += 1
            chosen.add(key_of(record))

    color_counts: Counter[str] = Counter()
    for record in shuffled:
        if key_of(record) in chosen:
            if record.color:
                color_counts[record.color] += 1
            continue
        if not record.color or color_counts[record.color] >= color_cap:
            continue
        if (
            not allow_cap_overflow
            and record.subcategory
            and category_counts[record.subcategory] >= cap_of(record)
        ):
            continue  # 카테고리 상한을 넘겨서까지 색상 쿼터를 채우지 않는다
        color_counts[record.color] += 1
        if record.subcategory:
            category_counts[record.subcategory] += 1
        chosen.add(key_of(record))

    return [record for record in shuffled if key_of(record) in chosen]


# --------------------------------------------------------------------------
# scan — 착수 게이트 2개 + 분포 (브리핑 §4)
# --------------------------------------------------------------------------


def _display_width(text: str) -> int:
    """터미널에서 차지하는 칸 수. 한글·전각 문자는 2칸이다.

    `str.ljust`는 문자 개수로 채우기 때문에 한글이 섞인 열이 어긋난다 — 이 리포트는 사람이
    읽고 그대로 붙여넣는 산출물이라 정렬이 실제로 중요하다.
    """
    import unicodedata

    return sum(2 if unicodedata.east_asian_width(char) in "WF" else 1 for char in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _display_width(text))


def _table(rows: list[tuple[str, ...]], headers: tuple[str, ...]) -> str:
    """사람이 읽고 그대로 복붙할 수 있는 고정폭 표."""
    all_rows = [tuple(str(cell) for cell in row) for row in (headers, *rows)]
    widths = [max(_display_width(row[i]) for row in all_rows) for i in range(len(headers))]
    lines = [
        "  ".join(_pad(str(headers[i]), widths[i]) for i in range(len(headers))),
        "  ".join("-" * widths[i] for i in range(len(headers))),
    ]
    for row in rows:
        lines.append("  ".join(_pad(str(row[i]), widths[i]) for i in range(len(headers))))
    return "\n".join(lines)


def _pct(count: int, total: int) -> str:
    return f"{100.0 * count / total:.1f}%" if total else "-"


def _histogram(values: list[float], bin_size: float) -> list[tuple[str, ...]]:
    buckets: Counter[int] = Counter(int(value // bin_size) for value in values)
    rows: list[tuple[str, ...]] = []
    for bucket in sorted(buckets):
        low = bucket * bin_size
        count = buckets[bucket]
        bar = "#" * min(50, max(1, round(50 * count / max(buckets.values()))))
        rows.append((f"{low:g}~{low + bin_size:g}", f"{count:,}", _pct(count, len(values)), bar))
    return rows


def run_scan(
    root: Path,
    *,
    limit: int | None,
    sample_paths: int,
    short_pants_max_cm: float | None,
    progress_every: int,
    color_top: int = 20,
    bottom_pseudo_labels: dict[str, str] | None = None,
) -> str:
    """라벨 JSON을 훑어 게이트 2개와 분포를 텍스트로 만든다. 이미지는 열지 않는다."""
    stats = LoadStats()
    shot_counts: Counter[str] = Counter()
    shot_examples: dict[str, list[str]] = defaultdict(list)
    color_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    neck_counts: Counter[str] = Counter()
    sleeve_counts: Counter[str] = Counter()
    mapped_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    group_sizes: Counter[str] = Counter()
    polo_counts: Counter[str] = Counter()
    pants_lengths: list[float] = []
    polygon_missing = 0
    size_missing = 0
    path_examples: list[tuple[str, str]] = []
    excluded_top_gain: Counter[str] = Counter()

    for label in load_labels(root, limit=limit, progress_every=progress_every, stats=stats):
        record, reason = to_record(
            label,
            short_pants_max_cm=short_pants_max_cm,
            bottom_pseudo_labels=bottom_pseudo_labels,
        )
        reason_counts[reason] += 1
        group_sizes[record.group_key] += 1

        _key, matched = group_key_from_name(label.name)
        if not matched:
            stats.group_fallbacks += 1

        type_counts[label.source_type or "(없음)"] += 1
        color_counts[label.color or "(없음)"] += 1
        shot = label.shot_type or "(없음)"
        shot_counts[shot] += 1
        if len(shot_examples[shot]) < sample_paths:
            shot_examples[shot].append(label.image_path or label.label_path)
        neck_counts[label.neck or "(없음)"] += 1
        sleeve_counts[label.sleeve or "(없음)"] += 1

        if record.subcategory:
            mapped_counts[record.subcategory] += 1
        if record.is_polo:
            polo_counts[label.source_type or "(없음)"] += 1
        if label.source_type == "04bottom_01pants" and label.pants_length is not None:
            pants_lengths.append(label.pants_length)
        if label.polygon_points == 0:
            polygon_missing += 1
        if not label.width or not label.height:
            size_missing += 1
        if len(path_examples) < 3 and label.image_path:
            path_examples.append((label.label_path, label.image_path))

        # DERIVE_FROM_EXCLUDED_TOPS를 켜면 늘어나는 건수(지금은 제외되는 blouse/vest 중
        # 후드·민소매인 것). 나중에 이 스위치를 뒤집을지 판단할 근거로만 센다.
        if label.source_type in {"02top_01blouse", "02top_05vest"}:
            if _is_hood(label.neck):
                excluded_top_gain["HOODIE"] += 1
            elif _is_sleeveless(label.sleeve):
                excluded_top_gain["SLEEVELESS"] += 1

    total = stats.total_files - stats.parse_errors
    out: list[str] = []

    def section(title: str) -> None:
        out.append("")
        out.append("=" * 78)
        out.append(title)
        out.append("=" * 78)

    out.append(f"루트          : {root}")
    out.append(f"라벨 JSON     : {stats.total_files:,}개 (파싱 실패 {stats.parse_errors:,})")
    out.append(f"유효 레코드   : {total:,}")
    out.append(f"SHORT_PANTS 임계 : {short_pants_max_cm if short_pants_max_cm else '미설정(None)'}")
    if stats.error_samples:
        out.append("파싱 실패 예시:")
        out.extend(f"  {sample}" for sample in stats.error_samples)

    section("게이트 1 — metadata.model.type (촬영유형)")
    rows = [(value, f"{count:,}", _pct(count, total)) for value, count in shot_counts.most_common()]
    out.append(_table(rows, ("값", "건수", "비율")))
    out.append("")
    out.append(">>> 판정은 사람이 한다. 아래 이미지를 값마다 직접 열어 보고,")
    out.append("    '옷만 찍은 상품컷'인지 '사람이 입은 사진'인지 확인할 것.")
    for value in shot_counts:
        out.append(f"  [{value}]")
        for example in shot_examples[value]:
            out.append(f"    {example}")

    section("게이트 2 — metadata.clothes.color (Navy 실재 여부)")
    # 콤마로 묶인 다색 조합("Black,White" 등)이 값 종류를 수백 개로 불려서 표가 감당 안 될
    # 만큼 길어진다(2026-08-04 실측: 500줄 이상). 색상은 이 작업의 우선순위가 아니므로
    # 기본으로 상위 N개만 찍고 나머지는 합계 한 줄로 접는다. 전체가 필요하면 --color-top 0.
    all_color_items = color_counts.most_common()
    shown_colors = all_color_items if color_top <= 0 else all_color_items[:color_top]
    rows = []
    for value, count in shown_colors:
        mapped = map_color(value) or "(매핑 없음)"
        rows.append((value, f"{count:,}", _pct(count, total), mapped))
    out.append(_table(rows, ("원본 값", "건수", "비율", "우리 코드")))
    hidden = all_color_items[len(shown_colors) :]
    if hidden:
        hidden_total = sum(count for _value, count in hidden)
        out.append(
            f"  ... 이하 {len(hidden):,}종 생략 (합계 {hidden_total:,}건, {_pct(hidden_total, total)})"
            f" — 전체를 보려면 --color-top 0"
        )
    navy_count = sum(count for value, count in color_counts.items() if map_color(value) == "NAVY")
    out.append("")
    out.append(f">>> Navy 실측 건수: {navy_count:,}")
    missing_palette = [
        code for code in COLOR_CODES if code not in {map_color(value) for value in color_counts}
    ]
    out.append(
        f">>> 우리 팔레트 {len(COLOR_CODES)}종 중 데이터에 없는 코드: "
        f"{missing_palette or '없음'}"
    )

    section("clothes.type 분포 (13종)")
    rows = []
    for value, count in type_counts.most_common():
        mapped = DIRECT_CATEGORY_MAP.get(value)
        note = mapped or EXCLUDED_CATEGORY_TYPES.get(value, "")
        rows.append((value, f"{count:,}", _pct(count, total), note))
    out.append(_table(rows, ("원본 값", "건수", "비율", "우리 코드 / 제외 사유")))

    section("매핑 결과 — 우리 소분류 코드별 건수")
    rows = [(code, f"{count:,}", _pct(count, total)) for code, count in mapped_counts.most_common()]
    out.append(_table(rows, ("우리 코드", "건수", "비율")) if rows else "(매핑된 건 없음)")
    out.append("")
    out.append(f"커버 클래스 수: {len(mapped_counts)} / {len(ALL_SUBCATEGORIES)}")
    out.append("")
    out.append("매핑/제외 사유별 건수:")
    rows = [
        (reason, f"{count:,}", _pct(count, total)) for reason, count in reason_counts.most_common()
    ]
    out.append(_table(rows, ("사유", "건수", "비율")))
    if excluded_top_gain:
        out.append("")
        out.append("참고 — DERIVE_FROM_EXCLUDED_TOPS=True로 바꾸면 늘어나는 건수:")
        out.append(
            _table(
                [(code, f"{count:,}") for code, count in excluded_top_gain.most_common()],
                ("우리 코드", "추가 건수"),
            )
        )

    section("pants_length 히스토그램 (SHORT_PANTS 임계 결정용)")
    if pants_lengths:
        out.append(f"04bottom_01pants 중 pants_length 있는 건수: {len(pants_lengths):,}")
        out.append(f"min={min(pants_lengths):g}  max={max(pants_lengths):g}")
        out.append(_table(_histogram(pants_lengths, 5.0), ("구간(cm)", "건수", "비율", "")))
    else:
        out.append("(pants_length 값이 하나도 없다 — SHORT_PANTS 파생 불가)")

    if bottom_pseudo_labels is not None:
        section("하의 소재 재라벨링 반영 결과 (--bottom-pseudo-labels)")
        out.append(f"로드된 재라벨링 건수: {len(bottom_pseudo_labels):,}")
        pants_codes = ("DENIM", "SLACKS", "CARGO_PANTS", "JOGGER_PANTS", "COTTON_PANTS")
        rows = [(code, f"{mapped_counts.get(code, 0):,}") for code in pants_codes]
        out.append(_table(rows, ("코드", "매핑된 건수(전체 실행 기준)")))
        out.append("")
        out.append(
            ">>> 위 표가 전부 0이면 --bottom-pseudo-labels 경로/키(label_path)가 "
            "실제 라벨과 안 맞는지 확인할 것."
        )

    section("topneck_color_design 분포 ((B) 폴로 헤드 학습량)")
    rows = [
        (value, f"{count:,}", _pct(count, total)) for value, count in neck_counts.most_common(30)
    ]
    out.append(_table(rows, ("값", "건수", "비율")))
    out.append("")
    out.append("polo 포함 건수 (clothes.type별):")
    rows = [(value, f"{count:,}") for value, count in polo_counts.most_common()]
    out.append(_table(rows, ("clothes.type", "건수")) if rows else "(polo 0건)")

    section("sleeve_length_type 분포 (SLEEVELESS 파생량)")
    rows = [
        (value, f"{count:,}", _pct(count, total)) for value, count in sleeve_counts.most_common()
    ]
    out.append(_table(rows, ("값", "건수", "비율")))

    section("그룹 키 크기 분포 (split 누수 방지, 브리핑 §8)")
    size_dist = Counter(group_sizes.values())
    rows = [
        (str(size), f"{count:,}", f"{size * count:,}") for size, count in sorted(size_dist.items())
    ]
    out.append(_table(rows, ("그룹 크기", "그룹 수", "이미지 수")))
    out.append("")
    out.append(f"총 그룹 수: {len(group_sizes):,}")
    out.append(f"파일명 규칙 미적중(자기 자신을 그룹으로 처리): {stats.group_fallbacks:,}")
    if size_dist and set(size_dist) == {1}:
        out.append(">>> 전부 크기 1이다 — 그룹 분할이 no-op이라는 뜻(브리핑 §8-2).")

    section("기타 — 전처리에 필요한 값들")
    out.append(f"annotation_point 없음 : {polygon_missing:,} ({_pct(polygon_missing, total)})")
    out.append(f"width/height 없음     : {size_missing:,} ({_pct(size_missing, total)})")
    out.append("")
    out.append("경로 샘플 (image_path를 실제 파일로 어떻게 이어 붙일지 판단용):")
    for label_path, image_path in path_examples:
        out.append(f"  label: {label_path}")
        out.append(f"  image: {image_path}")

    return "\n".join(out)


# --------------------------------------------------------------------------
# index — 파싱 + 매핑 + 분할 + 층화 샘플링 → JSONL
# --------------------------------------------------------------------------


def run_index(
    root: Path | None,
    out_dir: Path,
    *,
    limit: int | None,
    short_pants_max_cm: float | None,
    category_cap: int,
    color_cap: int,
    eval_cap: int,
    progress_every: int,
    accessory_root: Path | None = None,
    accessory_cap: int | None = None,
    allow_cap_overflow: bool = False,
    accessory_shot_type: str | None = None,
    bottom_pseudo_labels: dict[str, str] | None = None,
) -> str:
    stats = LoadStats()
    records: list[Record] = []
    dropped_no_image_shot_type = 0
    if root is not None:
        for label in load_labels(root, limit=limit, progress_every=progress_every, stats=stats):
            record, _reason = to_record(
                label,
                short_pants_max_cm=short_pants_max_cm,
                bottom_pseudo_labels=bottom_pseudo_labels,
            )
            if record.subcategory is None and record.color is None:
                continue  # 카테고리도 색상도 못 뽑으면 학습에 쓸 데가 없다
            records.append(record)

    accessory_stats = None
    if accessory_root is not None:
        # 지연 import — `aihub_accessory`가 이 모듈을 최상단에서 import하므로 여기서 들여온다.
        import aihub_accessory

        accessory_stats = aihub_accessory.AccessoryStats()
        for record in aihub_accessory.load_accessory_records(
            accessory_root,
            limit=limit,
            progress_every=progress_every,
            stats=accessory_stats,
            load_stats=stats,
        ):
            if record.subcategory is None and record.color is None:
                continue
            # 라벨은 착용샷("worn")이 훨씬 많은데(실측 94%), 그 실물 이미지(VS_제품 착용_*)는
            # 받지 않는 게 이 스파이크의 방침이다(90GB짜리라 스킵). 필터 없이 층화 샘플링하면
            # 카테고리 상한 대부분이 이미지 없는 worn 행으로 채워져 STEP 3에서 missing_image로
            # 버려진다 — 그래서 여기서 미리 걸러 상한이 "실제로 쓸 수 있는" 행만 채우게 한다.
            if accessory_shot_type and record.shot_type != accessory_shot_type:
                dropped_no_image_shot_type += 1
                continue
            records.append(record)

    assignment = split_groups(records)
    by_split: dict[str, list[Record]] = defaultdict(list)
    for record in records:
        by_split[assignment[record.group_key]].append(record)

    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.jsonl"
    with index_path.open("w", encoding="utf-8") as handle:
        for record in records:
            row = asdict(record)
            row["split"] = assignment[record.group_key]
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    selected: dict[str, list[Record]] = {
        "train": select_stratified(
            by_split["train"],
            category_cap=category_cap,
            color_cap=color_cap,
            accessory_cap=accessory_cap,
            allow_cap_overflow=allow_cap_overflow,
        ),
        "val": select_stratified(by_split["val"], category_cap=eval_cap, color_cap=eval_cap),
        "test": select_stratified(by_split["test"], category_cap=eval_cap, color_cap=eval_cap),
    }
    sample_path = out_dir / "sample.jsonl"
    with sample_path.open("w", encoding="utf-8") as handle:
        for split_name, split_records in selected.items():
            for record in split_records:
                row = asdict(record)
                row["split"] = split_name
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    lines = [
        f"라벨 JSON     : {stats.total_files:,}개 (파싱 실패 {stats.parse_errors:,})",
        f"인덱스 레코드 : {len(records):,}  → {index_path}",
        f"층화 샘플     : {sum(len(v) for v in selected.values()):,}  → {sample_path}",
        "",
    ]
    if accessory_shot_type:
        lines.append(
            f"액세서리 촬영유형 필터 '{accessory_shot_type}' 적용 — "
            f"{dropped_no_image_shot_type:,}건 제외(다른 촬영유형)"
        )
        lines.append("")
    # 빈 split은 조용히 넘어가면 안 된다 — 학습/평가가 그대로 깨진다.
    empty = [name for name in ("train", "val", "test") if not selected[name]]
    if empty:
        lines.append(f"⚠ 비어 있는 split: {empty} — 데이터가 너무 적거나 층이 잘게 쪼개졌다.")
        lines.append("")
    rows = [
        (
            name,
            f"{len(by_split[name]):,}",
            f"{len(selected[name]):,}",
            f"{len({r.group_key for r in by_split[name]}):,}",
        )
        for name in ("train", "val", "test")
    ]
    lines.append(_table(rows, ("split", "전체", "층화 샘플", "그룹 수")))

    lines.append("")
    lines.append("층화 샘플의 카테고리 분포 (소스별):")
    per_code: dict[str, Counter[str]] = defaultdict(Counter)
    for split_records in selected.values():
        for record in split_records:
            if record.subcategory:
                per_code[record.subcategory][record.source] += 1
    rows = [
        (code, f"{sum(sources.values()):,}", f"{sources['clothes']:,}", f"{sources['accessory']:,}")
        for code, sources in sorted(per_code.items(), key=lambda kv: -sum(kv[1].values()))
    ]
    lines.append(_table(rows, ("코드", "합계", "의류", "액세서리")))

    lines.append("")
    lines.append("층화 샘플의 색상 분포:")
    counts: Counter[str] = Counter()
    for split_records in selected.values():
        counts.update(r.color for r in split_records if r.color)
    lines.append(_table([(k, f"{v:,}") for k, v in counts.most_common()], ("코드", "건수")))

    lines.append("")
    lines.append("소스별 비중 (이 표를 보고 --category-cap / --accessory-cap을 조절한다):")
    source_counts: Counter[str] = Counter()
    for split_records in selected.values():
        source_counts.update(r.source for r in split_records)
    grand_total = sum(source_counts.values())
    lines.append(
        _table(
            [
                (name, f"{count:,}", _pct(count, grand_total))
                for name, count in source_counts.most_common()
            ],
            ("소스", "건수", "비율"),
        )
    )
    if accessory_stats is not None:
        lines.append("")
        lines.append(
            f"액세서리 조인: 속성 {accessory_stats.attributes:,}개 / "
            f"이미지 {accessory_stats.images:,}개 / "
            f"조인 실패 {accessory_stats.unmatched_images:,}개"
        )
    return "\n".join(lines)


def run_accessory_scan(root: Path, *, limit: int | None, sample_paths: int) -> str:
    """액세서리 데이터셋(71441) 전용 scan.

    의류 쪽과 묻는 게 다르다 — 여기선 **조인이 실제로 성립하는지**(속성 라벨과 이미지
    라벨이 `accessory_id`로 붙는지)와 **제품컷/착용컷 비율**이 핵심이다. 파서가 AI-Hub
    공개 명세만 보고 쓰였기 때문에(`aihub_accessory` 모듈 docstring) 이 출력이 곧 파서가
    맞았는지에 대한 답이다.
    """
    import aihub_accessory

    stats = aihub_accessory.AccessoryStats()
    load = LoadStats()
    records = list(
        aihub_accessory.load_accessory_records(
            root, limit=limit, progress_every=0, stats=stats, load_stats=load
        )
    )

    out: list[str] = []
    out.append("")
    out.append("=" * 78)
    out.append("액세서리 데이터셋 (009. 패션 액세서리 착용 데이터)")
    out.append("=" * 78)
    out.append(f"루트            : {root}")
    out.append(f"JSON 파일       : {load.total_files:,} (파싱 실패 {load.parse_errors:,})")
    out.append(f"  속성 라벨 파일 : {stats.attribute_files:,}")
    out.append(f"  이미지 라벨    : {stats.image_files:,}")
    out.append(f"  그 외          : {stats.other_files:,}  (메타/페어 등)")
    out.append(f"속성 테이블     : {stats.attributes:,}개 accessory_id")
    out.append(f"이미지 레코드   : {stats.images:,}  (조인 실패 {stats.unmatched_images:,})")
    out.append("")

    if not records and not stats.attributes:
        out.append(">>> ⚠ 아무것도 못 찾았다. 파서가 실제 구조와 다르다는 뜻이다.")
        out.append("    (기대: 속성 JSON에 accessory_type1/accessory_color,")
        out.append("     이미지 JSON에 info[].accessory_id + info[].image.path)")
        return "\n".join(out)

    out.append("accessory_type1 분포:")
    rows = []
    for value, count in stats.type_counts.most_common():
        mapped, _reason = aihub_accessory.map_accessory_type(value)
        rows.append((value, f"{count:,}", mapped or "(제외/미매핑)"))
    out.append(_table(rows, ("원본 값", "건수", "우리 코드")))

    out.append("")
    out.append("accessory_color 분포:")
    rows = []
    for value, count in stats.color_counts.most_common():
        mapped = aihub_accessory.map_accessory_color(value)
        rows.append((value, f"{count:,}", mapped or "(제외/미매핑)"))
    out.append(_table(rows, ("원본 값", "건수", "우리 코드")))

    out.append("")
    out.append("촬영유형 (제품 단독컷 vs 착용컷):")
    total = sum(stats.shot_counts.values())
    rows = [
        (value, f"{count:,}", _pct(count, total))
        for value, count in stats.shot_counts.most_common()
    ]
    out.append(_table(rows, ("값", "건수", "비율")))
    out.append("")
    out.append(">>> 우리 서비스 입력(flat/hanging)에 가까운 건 'product'(제품 단독컷)다.")
    out.append("    아래 경로를 열어 실제로 그런지 확인할 것.")
    for value, examples in stats.examples.items():
        out.append(f"  [{value}]")
        for example in examples[:sample_paths]:
            out.append(f"    {example}")

    out.append("")
    out.append("매핑된 우리 코드별 건수:")
    counts: Counter[str] = Counter(r.subcategory for r in records if r.subcategory)
    out.append(
        _table([(k, f"{v:,}") for k, v in counts.most_common()], ("코드", "건수"))
        if counts
        else "(매핑된 건 없음)"
    )

    out.append("")
    out.append("그룹 키(accessory_id) 크기 분포:")
    group_sizes = Counter(r.group_key for r in records)
    size_dist = Counter(group_sizes.values())
    out.append(
        _table(
            [(str(size), f"{n:,}", f"{size * n:,}") for size, n in sorted(size_dist.items())],
            ("그룹 크기", "그룹 수", "이미지 수"),
        )
    )
    out.append(f"총 그룹 수: {len(group_sizes):,}")
    return "\n".join(out)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI-Hub 의류 통합 데이터 라벨 스캔 / 인덱싱 (원격 서버에서 실행)",
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    def add_common(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--root",
            type=Path,
            default=None,
            help="의류 통합 데이터(71501) 라벨 JSON 디렉터리(하위 전체를 재귀 탐색)",
        )
        target.add_argument(
            "--accessory-root",
            type=Path,
            default=None,
            help="패션 액세서리 착용 데이터(71441) 라벨 JSON 디렉터리. 생략하면 안 쓴다",
        )
        target.add_argument("--limit", type=int, default=None, help="앞에서부터 N개만 읽는다")
        target.add_argument(
            "--short-pants-max-cm",
            type=float,
            default=SHORT_PANTS_MAX_CM,
            help="이 값 미만의 pants_length를 SHORT_PANTS로 본다(미지정이면 파생하지 않음)",
        )
        target.add_argument("--progress-every", type=int, default=50000)
        target.add_argument(
            "--bottom-pseudo-labels",
            type=Path,
            default=None,
            help="aihub_bottom_label.py가 만든 하의(04bottom_01pants) 재라벨링 JSONL. 주면 "
            "SHORT_PANTS로 못 뺀 통짜 팬츠를 DENIM/SLACKS/CARGO_PANTS/JOGGER_PANTS/"
            "COTTON_PANTS로 승격한다(accepted=true인 행만, --bottom-pseudo-min-confidence로 "
            "재조정 가능). 생략하면 기존과 동일하게 전부 제외된다",
        )
        target.add_argument(
            "--bottom-pseudo-min-confidence",
            type=float,
            default=None,
            help="재라벨링 JSONL의 confidence 재임계치. 생략하면 라벨링 스크립트가 이미 매긴 "
            "accepted 값을 그대로 믿는다",
        )

    scan = sub.add_parser("scan", help="착수 게이트 2개 + 분포를 텍스트 표로 출력")
    add_common(scan)
    scan.add_argument("--sample-paths", type=int, default=5, help="촬영유형별로 찍을 예시 경로 수")
    scan.add_argument(
        "--color-top",
        type=int,
        default=20,
        help="게이트 2 색상 표에 상위 몇 종까지 찍을지(다색 조합이 수백 종이라 기본은 요약). "
        "0이면 전체 출력",
    )
    scan.add_argument("--out", type=Path, default=None, help="출력을 파일로도 저장")

    index = sub.add_parser("index", help="파싱+매핑+분할+층화샘플 → JSONL")
    add_common(index)
    index.add_argument("--out-dir", type=Path, required=True)
    index.add_argument("--category-cap", type=int, default=CATEGORY_CAP_PER_CLASS)
    index.add_argument("--color-cap", type=int, default=COLOR_CAP_PER_CLASS)
    index.add_argument("--eval-cap", type=int, default=EVAL_CAP_PER_CLASS)
    index.add_argument(
        "--accessory-cap",
        type=int,
        default=ACCESSORY_CAP_PER_CLASS,
        help="액세서리 소스의 클래스당 상한(소스별 비중 조절). 의류와 따로 건다",
    )
    index.add_argument(
        "--allow-cap-overflow",
        action="store_true",
        help="색상 쿼터를 채우려고 카테고리 상한을 넘겨도 되게 한다(기본은 상한 엄수)",
    )
    index.add_argument(
        "--accessory-shot-type",
        default=None,
        help="액세서리 행을 이 촬영유형(예: product)만 남기고 거른다. 착용샷(worn) 실물"
        "이미지를 안 받았으면 반드시 줄 것 — 안 주면 상한 대부분이 이미지 없는 행으로 "
        "채워져 STEP 3에서 버려진다",
    )
    return parser


def _force_utf8_stdout() -> None:
    """Windows 콘솔 기본 인코딩(cp949)이 한글 리포트의 em-dash에서 터진다.

    원격 리눅스에선 문제가 없지만, 같은 스크립트를 로컬에서 `--limit`로 돌려 보는 경우가
    있어 출력 스트림을 UTF-8로 고정한다.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    args = build_parser().parse_args(argv)
    if args.root is None and args.accessory_root is None:
        print("--root 또는 --accessory-root 중 하나는 있어야 한다", file=sys.stderr)
        return 2
    for label, path in (("--root", args.root), ("--accessory-root", args.accessory_root)):
        if path is not None and not path.exists():
            print(f"{label} 경로가 없다: {path}", file=sys.stderr)
            return 2
    if args.bottom_pseudo_labels is not None and not args.bottom_pseudo_labels.exists():
        print(f"--bottom-pseudo-labels 경로가 없다: {args.bottom_pseudo_labels}", file=sys.stderr)
        return 2

    bottom_pseudo_labels = None
    if args.bottom_pseudo_labels is not None:
        bottom_pseudo_labels = load_bottom_pseudo_labels(
            args.bottom_pseudo_labels, min_confidence=args.bottom_pseudo_min_confidence
        )
        print(
            f"하의 재라벨링 {len(bottom_pseudo_labels):,}건 로드: {args.bottom_pseudo_labels}",
            file=sys.stderr,
        )

    if args.mode == "scan":
        parts: list[str] = []
        if args.root is not None:
            parts.append(
                run_scan(
                    args.root,
                    limit=args.limit,
                    sample_paths=args.sample_paths,
                    short_pants_max_cm=args.short_pants_max_cm,
                    progress_every=args.progress_every,
                    color_top=args.color_top,
                    bottom_pseudo_labels=bottom_pseudo_labels,
                )
            )
        if args.accessory_root is not None:
            parts.append(
                run_accessory_scan(
                    args.accessory_root, limit=args.limit, sample_paths=args.sample_paths
                )
            )
        report = "\n".join(parts)
        print(report)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(report, encoding="utf-8")
            print(f"\n(저장: {args.out})", file=sys.stderr)
        return 0

    report = run_index(
        args.root,
        args.out_dir,
        limit=args.limit,
        short_pants_max_cm=args.short_pants_max_cm,
        category_cap=args.category_cap,
        color_cap=args.color_cap,
        eval_cap=args.eval_cap,
        progress_every=args.progress_every,
        accessory_root=args.accessory_root,
        accessory_shot_type=args.accessory_shot_type,
        accessory_cap=args.accessory_cap,
        allow_cap_overflow=args.allow_cap_overflow,
        bottom_pseudo_labels=bottom_pseudo_labels,
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
