"""AI-Hub "패션 액세서리 착용 데이터"(dataSetSn 71441) 라벨 → 우리 taxonomy v2.

`aihub_dataset.py`(의류 통합 데이터)와 **같은 `Record` 타입**을 내보내서, 두 소스를 한
인덱스로 합쳐 학습할 수 있게 한다. 우리 소분류 35종 중 의류 통합 데이터가 못 덮는
ACCESSORY 쪽(HAT · SUNGLASSES · JEWELRY)을 이 데이터셋이 채운다.

⚠️ 이 모듈은 **AI-Hub가 공개한 어노테이션 명세**(데이터셋 상세의 "어노테이션 포맷 3)
액세서리 어노테이션 포멧")를 근거로 작성했다. 로컬에 실물 샘플이 없어 폴더 구조·래핑
방식은 확인하지 못했다 — 그래서 파서가 **키 이름만 보고 중첩 어디서든 찾아내는** 방식이고,
`aihub_dataset.py scan --accessory-root ...`가 실제로 무엇을 찾았는지 표로 찍는다.
scan 출력이 기대와 다르면 이 모듈을 먼저 고칠 것.

두 종류의 JSON을 **조인**해야 한다 (의류 통합 데이터와 결정적으로 다른 점)
--------------------------------------------------------------------------
- **액세서리 속성 라벨**(`TL_제품_*.zip`, 각 ~1MB): `accessory_id` → `accessory_type1`
  (모자/안경테/선글라스/목걸이/귀걸이) · `accessory_color`(23종) · 소재/프린트/디테일.
  **여기에만 카테고리와 색상이 있다.**
- **이미지 단위 라벨**(`TL_제품 착용_*.zip` / `TL_제품_*`): `info[].accessory_id` +
  `info[].image.path` + 폴리곤 세그멘테이션. **여기엔 색상·카테고리가 없다.**

그래서 1패스로 속성 테이블을 만들고, 2패스로 이미지 라벨을 훑으며 `accessory_id`로 붙인다.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from aihub_dataset import (
    ALL_SUBCATEGORIES,
    COLOR_CODES,
    MIXED_LABEL,
    LoadStats,
    Record,
    clean,
    iter_label_files,
    to_float,
)

# --------------------------------------------------------------------------
# 카테고리 매핑 — `accessory_type1` 5종 중 4종만 우리 코드에 대응된다.
# --------------------------------------------------------------------------
ACCESSORY_TYPE_MAP: dict[str, str] = {
    "모자": "HAT",
    "선글라스": "SUNGLASSES",
    # 목걸이·귀걸이는 우리 taxonomy에서 둘 다 JEWELRY 하나로 접힌다(BE 시드에 목걸이/귀걸이
    # 구분이 없다). **N:1 매핑이라 JEWELRY 학습량이 다른 클래스의 2배로 들어온다** —
    # 층화 샘플링 상한(`--accessory-cap`)이 이걸 눌러 준다.
    "목걸이": "JEWELRY",
    "귀걸이": "JEWELRY",
}
assert set(ACCESSORY_TYPE_MAP.values()) <= set(ALL_SUBCATEGORIES)

EXCLUDED_ACCESSORY_TYPES: dict[str, str] = {
    # 우리 taxonomy에 SUNGLASSES는 있어도 "안경"은 없다. 도수 안경테를 SUNGLASSES로 보내면
    # 선글라스 판정이 흐려진다(렌즈 색이 정반대다) — 별도 코드가 생기기 전까지 제외.
    "안경테": "taxonomy v2에 안경(비선글라스)이 없다 — SUNGLASSES와 다른 물건",
}

# --------------------------------------------------------------------------
# 색상 매핑 — `accessory_color` 23종 → 우리 13종 + MIXED.
#
# 은퇴 코드(카키·스카이블루·와인·실버·골드)의 흡수처는 `color.py`의 `RETIRED_COLOR_MAP`을
# 그대로 따른다 — 같은 팔레트 축소를 두 곳에서 다르게 정하면 라벨이 갈린다.
# 명세에만 있고 `RETIRED_COLOR_MAP`엔 없는 3종은 여기서 판단했다(근거를 주석에 남긴다).
# --------------------------------------------------------------------------
ACCESSORY_COLOR_MAP: dict[str, str] = {
    "블랙": "BLACK",
    "화이트": "WHITE",
    "그레이": "GRAY",
    "레드": "RED",
    "핑크": "PINK",
    "오렌지": "ORANGE",
    "베이지": "BEIGE",
    "브라운": "BROWN",
    "옐로우": "YELLOW",
    "그린": "GREEN",
    "블루": "BLUE",
    "네이비": "NAVY",
    "퍼플": "PURPLE",
    "멀티컬러": MIXED_LABEL,
    # --- RETIRED_COLOR_MAP(color.py)과 동일한 흡수 ---
    "카키": "GREEN",
    "스카이블루": "BLUE",
    "와인": "RED",
    "실버": "GRAY",
    "골드": "YELLOW",
    # --- 이 모듈에서 판단한 3종 ---
    # 민트는 밝은 청록이라 GREEN/BLUE 어느 쪽도 가능한데, 색상환상 녹색 쪽이 가깝고
    # 카키(→GREEN)와 달리 파랑 계열로 보내면 NAVY/BLUE 판정을 흐린다.
    "민트": "GREEN",
    # 로즈골드는 금속 광택이 있는 분홍이다. GOLD가 YELLOW로 간 것과 달리 육안 주색은 분홍.
    "로즈골드": "PINK",
}

# 색이라 부를 수 없어 학습에서 빼는 값.
EXCLUDED_ACCESSORY_COLORS: dict[str, str] = {
    "투명": "무색 — 팔레트 13종 어디에도 대응되지 않는다(렌즈/프레임 투명)",
    "기타": "값 자체가 미상 — 지도 신호가 될 수 없다",
}

assert set(ACCESSORY_COLOR_MAP.values()) <= set(COLOR_CODES)


def _normalize(value: str | None) -> str | None:
    """공백을 없애고 비교한다 — 명세의 "스카이 블루"와 실제 "스카이블루"를 같이 받는다."""
    cleaned = clean(value)
    if cleaned is None:
        return None
    return "".join(str(cleaned).split())


def map_accessory_type(raw_type: str | None) -> tuple[str | None, str]:
    """`accessory_type1` → 우리 소분류 코드. 반환은 `(코드 또는 None, 사유)`."""
    key = _normalize(raw_type)
    if key is None:
        return None, "accessory_type1 없음"
    mapped = ACCESSORY_TYPE_MAP.get(key)
    if mapped is not None:
        return mapped, "직접 매핑"
    reason = EXCLUDED_ACCESSORY_TYPES.get(key)
    if reason is not None:
        return None, f"제외: {reason}"
    return None, f"알 수 없는 accessory_type1: {raw_type}"


def map_accessory_color(raw_color: str | None) -> str | None:
    """`accessory_color` 23종 → 우리 팔레트 코드. 제외 대상·미상은 None."""
    key = _normalize(raw_color)
    if key is None:
        return None
    return ACCESSORY_COLOR_MAP.get(key)


# --------------------------------------------------------------------------
# JSON 탐색 — 래핑 방식을 모르므로 **키 이름으로** 찾는다.
# --------------------------------------------------------------------------

_MAX_DEPTH = 6


def _walk_dicts(node: Any, depth: int = 0) -> Iterator[dict]:
    """중첩 dict/list를 훑으며 모든 dict를 낸다(깊이 제한 — 세그멘테이션 좌표 배열 방어)."""
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, dict):
        yield node
        for value in node.values():
            if isinstance(value, (dict, list)):
                yield from _walk_dicts(value, depth + 1)
    elif isinstance(node, list):
        for value in node[:64]:  # 좌표 리스트를 통째로 순회하지 않는다
            if isinstance(value, (dict, list)):
                yield from _walk_dicts(value, depth + 1)


@dataclass(frozen=True)
class AccessoryAttribute:
    accessory_id: str
    raw_type: str | None
    raw_color: str | None


def iter_attributes(js: Any) -> Iterator[AccessoryAttribute]:
    """속성 라벨 JSON에서 `(accessory_id, type1, color)`를 뽑는다."""
    for node in _walk_dicts(js):
        if "accessory_type1" not in node:
            continue
        accessory_id = clean(node.get("accessory_id"))
        if accessory_id is None:
            continue
        yield AccessoryAttribute(
            accessory_id=str(accessory_id),
            raw_type=clean(node.get("accessory_type1")),
            raw_color=clean(node.get("accessory_color")),
        )


@dataclass(frozen=True)
class AccessoryImage:
    accessory_id: str
    image_id: str | None
    image_path: str | None
    width: int | None
    height: int | None
    angle: str | None
    model_id: str | None


def iter_images(js: Any) -> Iterator[AccessoryImage]:
    """이미지 단위 라벨 JSON에서 `info[]`의 이미지 정보를 뽑는다."""
    for node in _walk_dicts(js):
        image = node.get("image")
        if not isinstance(image, dict) or "path" not in image:
            continue
        accessory_id = clean(node.get("accessory_id"))
        if accessory_id is None:
            continue
        width = to_float(image.get("width"))
        height = to_float(image.get("height"))
        yield AccessoryImage(
            accessory_id=str(accessory_id),
            image_id=clean(node.get("id")),
            image_path=clean(image.get("path")),
            width=int(width) if width else None,
            height=int(height) if height else None,
            angle=clean(image.get("angle")),
            model_id=clean(node.get("model_id")),
        )


def shot_type_of(image: AccessoryImage) -> str:
    """경로가 "제품 착용"이면 착용샷, 아니면 제품 단독컷.

    **우리 서비스 입력(flat/hanging)에 가까운 건 제품 단독컷이다.** 게이트 1이 의류 쪽에서
    묻는 것과 같은 질문이라, 이 값을 층화 평가에 그대로 쓴다.

    ⚠️ `model_id`는 신호로 쓰지 않는다 — 실측(2026-08-04)에서 `VS_제품_*`(제품 단독컷) 경로의
    이미지도 `model_id`가 "M000" 같은 더미 값으로 채워져 있어서, model_id 유무로 판정하면
    5,392건이 **전부** "worn"으로 잘못 찍혔다(실제로는 100% product). 경로가 유일하게
    믿을 수 있는 신호다 — `VS_제품_*.zip`은 "제품", `VS_제품 착용_*.zip`은 "제품 착용"으로
    폴더명 자체가 갈린다.
    """
    path = image.image_path or ""
    if "제품 착용" in path or "제품착용" in path:
        return "worn"
    return "product"


# --------------------------------------------------------------------------
# 로딩 — 2패스(속성 테이블 → 이미지 조인)
# --------------------------------------------------------------------------


@dataclass
class AccessoryStats:
    attribute_files: int = 0
    image_files: int = 0
    attributes: int = 0
    images: int = 0
    unmatched_images: int = 0  # accessory_id가 속성 테이블에 없는 경우
    other_files: int = 0  # 둘 다 아닌 JSON(메타/페어 등)
    reason_counts: Counter = field(default_factory=Counter)
    color_counts: Counter = field(default_factory=Counter)
    type_counts: Counter = field(default_factory=Counter)
    shot_counts: Counter = field(default_factory=Counter)
    examples: dict = field(default_factory=dict)


def build_attribute_table(
    root: Path, *, limit: int | None = None, stats: AccessoryStats | None = None
) -> dict[str, AccessoryAttribute]:
    """1패스 — `accessory_id` → 속성. 같은 id가 여러 번 나오면 첫 값을 쓴다."""
    tracker = stats if stats is not None else AccessoryStats()
    table: dict[str, AccessoryAttribute] = {}
    for path in iter_label_files(root, limit=limit):
        try:
            js = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        found = False
        for attribute in iter_attributes(js):
            found = True
            table.setdefault(attribute.accessory_id, attribute)
        if found:
            tracker.attribute_files += 1
    tracker.attributes = len(table)
    return table


def load_accessory_records(
    root: Path,
    *,
    limit: int | None = None,
    progress_every: int = 50000,
    stats: AccessoryStats | None = None,
    load_stats: LoadStats | None = None,
) -> Iterator[Record]:
    """2패스 — 이미지 라벨을 훑으며 속성 테이블과 조인해 `Record`를 낸다.

    같은 액세서리(`accessory_id`)의 모든 각도·모델 컷이 **같은 그룹 키**를 갖는다. 의류
    쪽처럼 파일명을 파싱할 필요가 없다 — id가 그대로 그룹이다(브리핑 §8의 누수 방지).
    """
    import sys

    tracker = stats if stats is not None else AccessoryStats()
    file_tracker = load_stats if load_stats is not None else LoadStats()

    table = build_attribute_table(root, stats=tracker)

    for path in iter_label_files(root, limit=limit):
        file_tracker.total_files += 1
        if progress_every and file_tracker.total_files % progress_every == 0:
            print(f"  ... {file_tracker.total_files:,}개 읽음", file=sys.stderr, flush=True)
        try:
            js = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            file_tracker.parse_errors += 1
            if len(file_tracker.error_samples) < 5:
                file_tracker.error_samples.append(f"{path}: {exc}")
            continue

        relative = str(path.relative_to(root)).replace("\\", "/")
        emitted = False
        for image in iter_images(js):
            emitted = True
            tracker.images += 1
            attribute = table.get(image.accessory_id)
            if attribute is None:
                tracker.unmatched_images += 1
                tracker.reason_counts["제외: accessory_id가 속성 테이블에 없음"] += 1
                continue

            subcategory, reason = map_accessory_type(attribute.raw_type)
            tracker.reason_counts[reason] += 1
            tracker.type_counts[attribute.raw_type or "(없음)"] += 1
            tracker.color_counts[attribute.raw_color or "(없음)"] += 1
            shot = shot_type_of(image)
            tracker.shot_counts[shot] += 1
            tracker.examples.setdefault(shot, []).append(image.image_path or relative)

            yield Record(
                label_path=relative,
                image_path=image.image_path,
                name=image.image_id or Path(relative).stem,
                width=image.width,
                height=image.height,
                group_key=f"acc:{image.accessory_id}",
                subcategory=subcategory,
                color=map_accessory_color(attribute.raw_color),
                # 접기 전 원본("실버"·"로즈골드" 등). 네이티브 라벨 학습에 쓴다 —
                # 접히는 손실이 큰 쪽이 바로 이 데이터셋이다(23종 → 14종).
                color_raw=attribute.raw_color,
                shot_type=shot,
                is_polo=False,
                source_type=attribute.raw_type,
                source="accessory",
            )
        if emitted:
            tracker.image_files += 1
        else:
            tracker.other_files += 1
